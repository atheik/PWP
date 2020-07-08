import os
import pytest
import tempfile
import json
from jsonschema import validate
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, StatementError
from imagenet_browser import create_app, db
from imagenet_browser.models import Synset, Image

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def client():
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)
    
    with app.app_context():
        db.create_all()
        _populate_db()
        
    yield app.test_client()
    
    os.close(db_fd)
    os.unlink(db_fname)

def _populate_db():
    synset = Synset(wnid="n02103406", words="working dog", gloss="any of several breeds of usually large powerful dogs bred to work as draft animals and guard and guide dogs")
    synset_image_one = Image(imid=9, url="http://farm3.static.flickr.com/2056/2203156496_bf1b977326.jpg", date=None, synset=synset)
    synset_image_two = Image(imid=282, url="http://farm3.static.flickr.com/2250/2144303881_9ed6f44542.jpg", date=None, synset=synset)
    synset_hyponym = Synset(wnid="n02109047", words="Great Dane", gloss="very large powerful smooth-coated breed of dog")
    synset_hyponym_image = Image(imid=11, url="http://farm1.static.flickr.com/123/403783566_7a838f13c2.jpg", date=None, synset=synset_hyponym)
    synset.hyponyms.append(synset_hyponym)
    synset_hyponym_to_be = Synset(wnid="n02109391", words="hearing dog", gloss="dog trained to assist the deaf by signaling the occurrence of certain sounds")
    db.session.add(synset_image_one)
    db.session.add(synset_image_two)
    db.session.add(synset_hyponym_image)
    db.session.add(synset_hyponym_to_be)
    db.session.commit()

def _get_synset_json(hyponym_to_be=False):
    
    if hyponym_to_be:
        return {"wnid": "n02109391", "words": "hearing dog", "gloss": "dog trained to assist the deaf by signaling the occurrence of certain sounds"}
    return {"wnid": "n02121620", "words": "cat, true cat", "gloss": "feline mammal usually having thick soft fur and no ability to roar: domestic cats; wildcats"}

def _get_image_json():

    return {"imid": 2, "url": "http://static.flickr.com/2221/2074431221_e062a9a16d.jpg"}
    
def _check_namespace(client, response):
    
    ns_href = response["@namespaces"]["imagenet_browser"]["name"]
    resp = client.get(ns_href)
    assert resp.status_code == 200
    
def _check_control_get_method(ctrl, client, obj):
    
    href = obj["@controls"][ctrl]["href"]
    resp = client.get(href)
    assert resp.status_code == 200
    
def _check_control_delete_method(ctrl, client, obj):
    
    method = obj["@controls"][ctrl]["method"]
    assert method.lower() == "delete"

    href = obj["@controls"][ctrl]["href"]
    resp = client.delete(href)
    assert resp.status_code == 204
    
def _check_control_put_method(ctrl, client, obj, valid_json=_get_synset_json()):
    
    method = obj["@controls"][ctrl]["method"]
    assert method.lower() == "put"

    encoding = obj["@controls"][ctrl]["encoding"]
    assert encoding.lower() == "json"

    schema = obj["@controls"][ctrl]["schema"]
    validate(valid_json, schema)

    href = obj["@controls"][ctrl]["href"]
    resp = client.put(href, json=valid_json)
    assert resp.status_code == 204

    obj.update(valid_json)
    
def _check_control_post_method(ctrl, client, obj, valid_json=_get_synset_json()):
    
    method = obj["@controls"][ctrl]["method"]
    assert method.lower() == "post"

    encoding = obj["@controls"][ctrl]["encoding"]
    assert encoding.lower() == "json"

    schema = obj["@controls"][ctrl]["schema"]
    validate(valid_json, schema)

    href = obj["@controls"][ctrl]["href"]
    resp = client.post(href, json=valid_json)
    assert resp.status_code == 201


class TestEntryPoint(object):
    
    RESOURCE_URL = "/api/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200


class TestSynsetCollection(object):
    
    RESOURCE_URL = "/api/synsets/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_synset", client, body)
        assert len(body["items"]) == 3
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

    def test_post(self, client):

        valid = _get_synset_json()
        
        resp = client.post(self.RESOURCE_URL, json=valid, content_type="application/x-www-form-urlencoded")
        assert resp.status_code == 415
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.location.endswith(self.RESOURCE_URL + valid["wnid"] + "/")

        resp = client.get(resp.location)
        assert resp.status_code == 200
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        del valid["wnid"]
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400
        
        
class TestSynsetItem(object):
    
    RESOURCE_URL = "/api/synsets/n02103406/"
    INVALID_URL = "/api/synsets/n00000000/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_get_method("profile", client, body)
        _check_control_get_method("collection", client, body)
        _check_control_put_method("edit", client, body)
        resp = client.get(self.RESOURCE_URL.replace("/n02103406/", "/" + body["wnid"] + "/"))
        body = json.loads(resp.data)
        _check_control_delete_method("imagenet_browser:delete", client, body)

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put(self, client):

        valid = _get_synset_json()
        
        resp = client.put(self.RESOURCE_URL, json=valid, content_type="application/x-www-form-urlencoded")
        assert resp.status_code == 415
        
        resp = client.put(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        valid["wnid"] = "n02109047"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        valid["wnid"] = "n02103406"
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204
        
        del valid["wnid"]
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400
        
    def test_delete(self, client):

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404


class TestSynsetHyponymCollection(object):
    
    RESOURCE_URL = "/api/synsets/n02103406/hyponyms/"
    INVALID_URL = "/api/synsets/n00000000/hyponyms/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_hyponym", client, body, valid_json=_get_synset_json(hyponym_to_be=True))
        assert len(body["items"]) == 1
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_post(self, client):

        valid = _get_synset_json(hyponym_to_be=True)
        
        resp = client.post(self.RESOURCE_URL, json=valid, content_type="application/x-www-form-urlencoded")
        assert resp.status_code == 415
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.location.endswith(self.RESOURCE_URL + valid["wnid"] + "/")

        resp = client.get(resp.location)
        assert resp.status_code == 200
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409

        valid["wnid"] = "n00000000"
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 404
        
        del valid["wnid"]
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

        resp = client.post(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        
class TestSynsetHyponymItem(object):
    
    RESOURCE_URL = "/api/synsets/n02103406/hyponyms/n02109047/"
    INVALID_URL = "/api/synsets/n02103406/hyponyms/n00000000/"
    INVALID_URL_ALT = "/api/synsets/n00000000/hyponyms/n00000000/"
    
    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_get_method("profile", client, body)
        _check_control_get_method("collection", client, body)
        _check_control_delete_method("imagenet_browser:delete", client, body)

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

        resp = client.get(self.INVALID_URL_ALT)
        assert resp.status_code == 404

    def test_delete(self, client):

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL_ALT)
        assert resp.status_code == 404


class TestSynsetImageCollection(object):
    
    RESOURCE_URL = "/api/synsets/n02103406/images/"
    INVALID_URL = "/api/synsets/n00000000/images/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_image", client, body, valid_json=_get_image_json())
        assert len(body["items"]) == 2
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_post(self, client):

        valid = _get_image_json()
        
        resp = client.post(self.RESOURCE_URL, json=valid, content_type="application/x-www-form-urlencoded")
        assert resp.status_code == 415
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 201
        assert resp.location.endswith(self.RESOURCE_URL + str(valid["imid"]) + "/")

        resp = client.get(resp.location)
        assert resp.status_code == 200
        
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        del valid["imid"]
        resp = client.post(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400

        resp = client.post(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        
class TestSynsetImageItem(object):
    
    RESOURCE_URL = "/api/synsets/n02103406/images/9/"
    INVALID_URL = "/api/synsets/n02103406/images/0/"
    
    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_get_method("profile", client, body)
        _check_control_get_method("collection", client, body)
        _check_control_put_method("edit", client, body, valid_json=_get_image_json())
        resp = client.get(self.RESOURCE_URL.replace("/9/", "/" + str(body["imid"]) + "/"))
        body = json.loads(resp.data)
        _check_control_delete_method("imagenet_browser:delete", client, body)

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_put(self, client):

        valid = _get_image_json()
        
        resp = client.put(self.RESOURCE_URL, json=valid, content_type="application/x-www-form-urlencoded")
        assert resp.status_code == 415
        
        resp = client.put(self.INVALID_URL, json=valid)
        assert resp.status_code == 404
        
        valid["imid"] = 282
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 409
        
        valid["imid"] = 9
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 204
        
        del valid["imid"]
        resp = client.put(self.RESOURCE_URL, json=valid)
        assert resp.status_code == 400
        
    def test_delete(self, client):

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404


class TestImageCollection(object):
    
    RESOURCE_URL = "/api/images/"

    def test_get(self, client):

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        assert len(body["items"]) == 3
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)
