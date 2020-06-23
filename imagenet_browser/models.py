from datetime import datetime
from random import randint
import click
from flask.cli import with_appcontext
from imagenet_browser import db
from imagenet_browser.constants import *

hyponyms = db.Table(
    "hyponyms",
    db.Column("synset_wnid", db.Integer, db.ForeignKey("synset.wnid"), primary_key=True),
    db.Column("synset_hyponym_wnid", db.Integer, db.ForeignKey("synset.wnid"), primary_key=True)
)

class Synset(db.Model):
    wnid = db.Column(db.String(9), unique=True, nullable=False, primary_key=True)
    words = db.Column(db.String(256), nullable=False)
    gloss = db.Column(db.String(512), nullable=False)

    image = db.relationship("Image", back_populates="synset")
    hyponyms = db.relationship(
        "Synset",
        secondary=hyponyms,
        primaryjoin=wnid==hyponyms.c.synset_wnid,
        secondaryjoin=wnid==hyponyms.c.synset_hyponym_wnid,
        order_by="Synset.wnid"
    )

    @staticmethod
    def get_schema():
        schema = {
            "type": "object",
            "required": ["wnid", "words", "gloss"]
        }
        props = schema["properties"] = {}
        props["wnid"] = {
            "description": "The WordNet ID unique to the synset; nouns only",
            "type": "string",
            "pattern": "^n[0-9]{8}$"
        }
        props["words"] = {
            "description": "The words of the synset; rough synonyms",
            "type": "string"
        }
        props["gloss"] = {
            "description": "The gloss of the synset; a brief definition",
            "type": "string"
        }
        return schema


class Image(db.Model):
    synset_wnid = db.Column(db.Integer, db.ForeignKey("synset.wnid"), primary_key=True)
    imid = db.Column(db.Integer, nullable=False, primary_key=True)
    url = db.Column(db.String(512), nullable=False)
    date = db.Column(db.String(), nullable=False)

    synset = db.relationship("Synset", back_populates="image")

    @staticmethod
    def get_schema():
        schema = {
            "type": "object",
            "required": ["imid", "url"]
        }
        props = schema["properties"] = {}
        props["imid"] = {
            "description": "The ID of the image",
            "type": "integer",
        }
        props["url"] = {
            "description": "The URL of the image; HTTP only",
            "type": "string",
            "pattern": "^https?://"
        }
        props["date"] = {
            "description": "The date of the last access to the image through the URL; ISO 8601",
            "type": "string",
            "pattern": "^(199[1-9]|2[0-9]{3})-(0*([1-9]|1[0-2]))-(0*([1-9]|[12][0-9]|3[01]))$"
        }
        return schema


@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()

@click.command("load-db")
@with_appcontext
def load_db_command():
    with open(DB_LOAD_DIR + "words.txt", "r") as words_file, open(DB_LOAD_DIR + "gloss.txt", "r") as gloss_file:
        for words_line, gloss_line in zip(words_file, gloss_file):
            wnid_first, words = words_line.split(sep="\t", maxsplit=1)
            wnid_second, gloss = gloss_line.split(sep="\t", maxsplit=1)

            assert wnid_first == wnid_second
            wnid = wnid_first
            words = words[:-1]
            gloss = gloss[:-1]

            synset = Synset(
                wnid=wnid,
                words=words,
                gloss=gloss
            )
            db.session.add(synset)
        db.session.commit()

    # TODO poor performance

    with open(DB_LOAD_DIR + "fall11_urls.txt", "r", encoding="iso-8859-1") as urls_file:
        wnid_old = None
        for urls_line in urls_file:
            wnid_imid, url = urls_line.split(sep="\t", maxsplit=1)
            wnid, imid = wnid_imid.split(sep="_", maxsplit=1)
            url = url[:-1]

            if wnid != wnid_old:
                synset = Synset.query.filter_by(wnid=wnid).first()
                wnid_old = wnid
                db.session.commit()

            image = Image(
                imid=imid,
                url=url,
                date=datetime(2011, randint(9, 12), randint(1, 30)).isoformat().split("T")[0],
                synset=synset
            )
            db.session.add(image)
        db.session.commit()

    # TODO poor performance

    with open(DB_LOAD_DIR + "wordnet.is_a.txt", "r") as hyponyms_file:
        wnid_old = None
        for hyponyms_line in hyponyms_file:
            wnid, wnid_hyponym = hyponyms_line.split(sep=" ", maxsplit=1)
            wnid_hyponym = wnid_hyponym[:-1]

            if wnid != wnid_old:
                synset = Synset.query.filter_by(wnid=wnid).first()
                wnid_old = wnid

            synset_hyponym = Synset.query.filter_by(wnid=wnid_hyponym).first()
            synset.hyponyms.append(synset_hyponym)
        db.session.commit()
