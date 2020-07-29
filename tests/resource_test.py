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
    """
    Enable SQLite foreign keys.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def client():
    """
    The application factory for resource tests.
    Create and initialize the Flask application by using the main application factory with a test configuration.
    The test configuration defines a database that is a new temporary file which is closed after the generator is empty.
    The database is populated with an initial database using the _populate_db function.
    Yields a test client to the application as a generator object.
    Methods defined in this file that are prefixed with 'test_' and have 'client' as their parameter will obtain a test client to a new application,
    and as such a new database, from this application factory.
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
        _populate_db()
        
    yield app.test_client()
    
    os.close(db_fd)
    os.unlink(db_fname)

def _populate_db():
    """
    Populate the initial database.
    All relationships possible using the database models are present in this initial database.
    Synsets have a one-to-many relationship with images and many-to-many relationship with themselves.
    """
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
    """
    Return a dictionary, representing a valid synset, that is serializable to JSON.
    """
    
    if hyponym_to_be:
        return {"wnid": "n02109391", "words": "hearing dog", "gloss": "dog trained to assist the deaf by signaling the occurrence of certain sounds"}
    return {"wnid": "n02121620", "words": "cat, true cat", "gloss": "feline mammal usually having thick soft fur and no ability to roar: domestic cats; wildcats"}

def _get_image_json():
    """
    Return a dictionary, representing a valid image, that is serializable to JSON.
    """

    return {"imid": 2, "url": "http://static.flickr.com/2221/2074431221_e062a9a16d.jpg"}
    
def _check_namespace(client, response):
    """
    Assert that the route for the link relations view works.
    """
    
    ns_href = response["@namespaces"]["imagenet_browser"]["name"]
    resp = client.get(ns_href)
    assert resp.status_code == 200
    
def _check_control_get_method(ctrl, client, obj):
    """
    Assert that a GET sent to the control's href succeeds.
    """
    
    href = obj["@controls"][ctrl]["href"]
    resp = client.get(href)
    assert resp.status_code == 200
    
def _check_control_delete_method(ctrl, client, obj):
    """
    Assert that the control's method type is DELETE.
    Assert that a DELETE sent to the control's href succeeds.
    """
    
    method = obj["@controls"][ctrl]["method"]
    assert method.lower() == "delete"

    href = obj["@controls"][ctrl]["href"]
    resp = client.delete(href)
    assert resp.status_code == 204
    
def _check_control_put_method(ctrl, client, obj, valid_json=_get_synset_json()):
    """
    Assert that the control's method type is PUT.
    Assert that the control's encoding type is JSON.
    Check that valid JSON validates against the control's schema.
    Assert that a PUT sent to the control's href succeeds when using valid JSON in the request body.
    To simplify the resource tests where this function is called, update the object that the control is part of with values from the valid JSON.
    """
    
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
    """
    Assert that the control's method type is POST.
    Assert that the control's encoding type is JSON.
    Check that valid JSON validates against the control's schema.
    Assert that a POST sent to the control's href succeeds when using valid JSON in the request body.
    """
    
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
    """
    This class contains the resource tests for the entry point.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200


class TestSynsetCollection(object):
    """
    This class contains the resource tests for the SynsetCollection resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace and the POST-using control are valid.
        Assert that the number of items in the collection reflects those added in the initial database population.
        Check that the GET-using controls are valid for each item in the collection.
        Assert that a GET sent to the resource URL fails when using an invalid query parameter.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_synset", client, body)
        assert len(body["items"]) == 3
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.RESOURCE_URL + "?start=first")
        assert resp.status_code == 400

    def test_post(self, client):
        """
        Assert that a POST sent to the resource URL fails when using an invalid Content-Type in the request headers.
        Assert that a POST sent to the resource URL succeeds when using valid JSON in the request body.
        Assert that the Location header of the newly created item is valid.
        Assert that a GET sent to the Location header URL succeeds.
        Assert that a POST sent to the resource URL fails when using a clashing WordNet ID in the request body.
        Assert that a POST sent to the resource URL fails when there is no WordNet ID in the request body.
        """

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
    """
    This class contains the resource tests for the SynsetItem resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/n02103406/"
    INVALID_URL = "/api/synsets/n00000000/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace, GET-using controls, and the PUT-using control are valid.
        Assert that a GET sent to the updated resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the DELETE-using control is valid.
        Assert that a GET sent to the invalid URL fails.
        """

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
        """
        Assert that a PUT sent to the resource URL fails when using an invalid Content-Type in the request headers.
        Assert that a PUT sent to the invalid URL fails.
        Assert that a PUT sent to the resource URL fails when using a clashing WordNet ID in the request body.
        Assert that a PUT sent to the resource URL succeeds when using valid JSON in the request body.
        Assert that a PUT sent to the resource URL fails when there is no WordNet ID in the request body.
        """

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
        """
        Assert that a DELETE sent to the resource URL succeeds.
        Assert that a DELETE sent to the resource URL fails when the resource was already deleted.
        Assert that a DELETE sent to the invalid URL fails.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404


class TestSynsetHyponymCollection(object):
    """
    This class contains the resource tests for the SynsetHyponymCollection resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/n02103406/hyponyms/"
    INVALID_URL = "/api/synsets/n00000000/hyponyms/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace and the POST-using control are valid.
        Assert that the number of items in the collection reflects those added in the initial database population.
        Check that the GET-using controls are valid for each item in the collection.
        Assert that a GET sent to the resource URL fails when using an invalid query parameter.
        Assert that a GET sent to the invalid URL fails.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_hyponym", client, body, valid_json=_get_synset_json(hyponym_to_be=True))
        assert len(body["items"]) == 1
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.RESOURCE_URL + "?start=first")
        assert resp.status_code == 400

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_post(self, client):
        """
        Assert that a POST sent to the resource URL fails when using an invalid Content-Type in the request headers.
        Assert that a POST sent to the resource URL succeeds when using valid JSON in the request body.
        Assert that the Location header of the newly created item is valid.
        Assert that a GET sent to the Location header URL succeeds.
        Assert that a POST sent to the resource URL fails when using a clashing WordNet ID in the request body.
        Assert that a POST sent to the resource URL fails when using a non-existing WordNet ID in the request body.
        Assert that a POST sent to the resource URL fails when there is no WordNet ID in the request body.
        Assert that a POST sent to the invalid URL fails.
        """

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
    """
    This class contains the resource tests for the SynsetHyponymItem resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/n02103406/hyponyms/n02109047/"
    INVALID_URL = "/api/synsets/n02103406/hyponyms/n00000000/"
    INVALID_URL_ALT = "/api/synsets/n00000000/hyponyms/n00000000/"
    
    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace, GET-using controls, and the DELETE-using control are valid.
        Assert that a GET sent to the invalid URL fails.
        Assert that a GET sent to the alternative invalid URL fails.
        """

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
        """
        Assert that a DELETE sent to the resource URL succeeds.
        Assert that a DELETE sent to the resource URL fails when the resource was already deleted.
        Assert that a DELETE sent to the invalid URL fails.
        Assert that a DELETE sent to the alternative invalid URL fails.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL_ALT)
        assert resp.status_code == 404


class TestSynsetImageCollection(object):
    """
    This class contains the resource tests for the SynsetImageCollection resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/n02103406/images/"
    INVALID_URL = "/api/synsets/n00000000/images/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace and the POST-using control are valid.
        Assert that the number of items in the collection reflects those added in the initial database population.
        Check that the GET-using controls are valid for each item in the collection.
        Assert that a GET sent to the resource URL fails when using an invalid query parameter.
        Assert that a GET sent to the invalid URL fails.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        _check_control_post_method("imagenet_browser:add_image", client, body, valid_json=_get_image_json())
        assert len(body["items"]) == 2
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.RESOURCE_URL + "?start=first")
        assert resp.status_code == 400

        resp = client.get(self.INVALID_URL)
        assert resp.status_code == 404

    def test_post(self, client):
        """
        Assert that a POST sent to the resource URL fails when using an invalid Content-Type in the request headers.
        Assert that a POST sent to the resource URL succeeds when using valid JSON in the request body.
        Assert that the Location header of the newly created item is valid.
        Assert that a GET sent to the Location header URL succeeds.
        Assert that a POST sent to the resource URL fails when using a clashing WordNet ID and image ID in the request body.
        Assert that a POST sent to the resource URL fails when there is no image ID in the request body.
        Assert that a POST sent to the invalid URL fails.
        """

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
    """
    This class contains the resource tests for the SynsetImageItem resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/synsets/n02103406/images/9/"
    INVALID_URL = "/api/synsets/n02103406/images/0/"
    
    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace, GET-using controls, and the PUT-using control are valid.
        Assert that a GET sent to the updated resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the DELETE-using control is valid.
        Assert that a GET sent to the invalid URL fails.
        """

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
        """
        Assert that a PUT sent to the resource URL fails when using an invalid Content-Type in the request headers.
        Assert that a PUT sent to the invalid URL fails.
        Assert that a PUT sent to the resource URL fails when using a clashing image ID in the request body.
        Assert that a PUT sent to the resource URL succeeds when using valid JSON in the request body.
        Assert that a PUT sent to the resource URL fails when there is no image ID in the request body.
        """

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
        """
        Assert that a DELETE sent to the resource URL succeeds.
        Assert that a DELETE sent to the resource URL fails when the resource was already deleted.
        Assert that a DELETE sent to the invalid URL fails.
        """

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 204

        resp = client.delete(self.RESOURCE_URL)
        assert resp.status_code == 404

        resp = client.delete(self.INVALID_URL)
        assert resp.status_code == 404


class TestImageCollection(object):
    """
    This class contains the resource tests for the ImageCollection resource.
    All methods prefixed with 'test_' that have the 'client' parameter will obtain a test client to a new application,
    and as such a new database, from the application factory.
    """
    
    RESOURCE_URL = "/api/images/"

    def test_get(self, client):
        """
        Assert that a GET sent to the resource URL succeeds.
        Check that the response body is deserializable JSON.
        Check that the namespace is valid.
        Assert that the number of items in the collection reflects those added in the initial database population.
        Check that the GET-using controls are valid for each item in the collection.
        Assert that a GET sent to the resource URL fails when using an invalid query parameter.
        """

        resp = client.get(self.RESOURCE_URL)
        assert resp.status_code == 200

        body = json.loads(resp.data)
        _check_namespace(client, body)
        assert len(body["items"]) == 3
        for item in body["items"]:
            _check_control_get_method("self", client, item)
            _check_control_get_method("profile", client, item)

        resp = client.get(self.RESOURCE_URL + "?start=first")
        assert resp.status_code == 400
