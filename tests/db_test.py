import os
import pytest
import tempfile
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError
from imagenet_browser import create_app, db
from imagenet_browser.models import Synset, Image

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable SQLite foreign keys.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def app():
    """
    The application factory for database tests.
    Create and initialize the Flask application by using the main application factory with a test configuration.
    The test configuration defines a database that is a new temporary file which is closed after the generator is empty.
    Yields the application as a generator object.
    Functions defined in this file that are prefixed with 'test_' and have 'app' as their parameter will obtain a new application,
    and as such also a new database, from this application factory.
    They will also be considered pytest fixtures and will thus be evaluated when invoking 'pytest'.
    """
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)
    
    with app.app_context():
        db.create_all()
        
    yield app
    
    os.close(db_fd)
    os.unlink(db_fname)

def _get_synset(wnid="n02103406", words="working dog", gloss="any of several breeds of usually large powerful dogs bred to work as draft animals and guard and guide dogs"):
    """
    Return an instance of the Synset model.
    """
    return Synset(
        wnid=wnid,
        words=words,
        gloss=gloss
    )

def _get_image(imid=9, url="http://farm3.static.flickr.com/2056/2203156496_bf1b977326.jpg", date=None, synset=None):
    """
    Return an instance of the Image model.
    """
    return Image(
        imid=imid,
        url=url,
        date=date,
        synset=synset
    )

def test_create_instances(app):
    """
    Database test that creates instances of models, commits them to the database, checks that they exist, and checks their relationships.
    Synsets have a one-to-many relationship with images and many-to-many relationship with themselves.
    Due to the 'app' parameter, this function will obtain a new application, and as such also a new database, from the application factory.
    """
    
    with app.app_context():
        synset = _get_synset()
        synset_image = _get_image(synset=synset)
        synset_hyponym = _get_synset(wnid="n02109047", words="Great Dane", gloss="very large powerful smooth-coated breed of dog")
        synset_hyponym_image = _get_image(imid=11, url="http://farm1.static.flickr.com/123/403783566_7a838f13c2.jpg", synset=synset_hyponym)
        synset.hyponyms.append(synset_hyponym)
        db.session.add(synset_image)
        db.session.add(synset_hyponym_image)
        db.session.commit()
        
        assert Synset.query.count() == 2
        assert Image.query.count() == 2
        db_synset = Synset.query.filter_by(wnid="n02103406").first()
        db_synset_image = Image.query.filter(Image.synset_wnid == "n02103406", Image.imid == 9).first()
        db_synset_hyponym = Synset.query.filter_by(wnid="n02109047").first()
        db_synset_hyponym_image = Image.query.filter(Image.synset_wnid == "n02109047", Image.imid == 11).first()
        
        assert db_synset_image.synset == db_synset
        assert db_synset_image in db_synset.images
        assert db_synset_hyponym_image.synset == db_synset_hyponym
        assert db_synset_hyponym_image in db_synset_hyponym.images
    
def test_image_ondelete_synset(app):
    """
    Database test that checks that the database engine side CASCADE works for ON DELETE in the one-to-many relationship between synsets and images.
    Due to the 'app' parameter, this function will obtain a new application, and as such also a new database, from the application factory.
    """
    
    with app.app_context():
        synset = _get_synset()
        synset_image = _get_image(synset=synset)
        db.session.add(synset_image)
        db.session.commit()

        db_synset = Synset.query.filter_by(wnid="n02103406").first()
        db.session.delete(db_synset)
        db.session.commit()

        db_synset_image = Image.query.filter(Image.synset_wnid == "n02103406", Image.imid == 9).first()
        assert not db_synset_image

def test_image_onupdate_synset(app):
    """
    Database test that checks that the database engine side CASCADE works for ON UPDATE in the one-to-many relationship between synsets and images.
    Due to the 'app' parameter, this function will obtain a new application, and as such also a new database, from the application factory.
    """

    with app.app_context():
        synset = _get_synset()
        synset_image = _get_image(synset=synset)
        db.session.add(synset_image)
        db.session.commit()

        db_synset = Synset.query.filter_by(wnid="n02103406").first()
        db_synset.wnid = "n00000000"
        db.session.commit()

        db_synset_image = Image.query.filter(Image.synset_wnid == "n00000000", Image.imid == 9).first()
        assert db_synset_image.synset_wnid == db_synset.wnid

def test_synset_ondelete_synset(app):
    """
    Database test that checks that the database engine side CASCADE works for ON DELETE in the many-to-many relationship synsets have with themselves.
    Due to the 'app' parameter, this function will obtain a new application, and as such also a new database, from the application factory.
    """

    with app.app_context():
        synset = _get_synset()
        synset_hyponym = _get_synset(wnid="n02109047", words="Great Dane", gloss="very large powerful smooth-coated breed of dog")
        synset.hyponyms.append(synset_hyponym)
        db.session.add(synset)
        db.session.add(synset_hyponym)
        db.session.commit()

        db_synset_hyponym = Synset.query.filter_by(wnid="n02109047").first()
        db.session.delete(db_synset_hyponym)
        db.session.commit()

        db_synset = Synset.query.filter_by(wnid="n02103406").first()
        assert not db_synset.hyponyms

def test_synset_onupdate_synset(app):
    """
    Database test that checks that the database engine side CASCADE works for ON UPDATE in the many-to-many relationship synsets have with themselves.
    Due to the 'app' parameter, this function will obtain a new application, and as such also a new database, from the application factory.
    """

    with app.app_context():
        synset = _get_synset()
        synset_hyponym = _get_synset(wnid="n02109047", words="Great Dane", gloss="very large powerful smooth-coated breed of dog")
        synset.hyponyms.append(synset_hyponym)
        db.session.add(synset)
        db.session.add(synset_hyponym)
        db.session.commit()

        db_synset_hyponym = Synset.query.filter_by(wnid="n02109047").first()
        db_synset_hyponym.wnid = "n00000000"
        db.session.commit()

        db_synset = Synset.query.filter_by(wnid="n02103406").first()
        assert db_synset_hyponym in db_synset.hyponyms
