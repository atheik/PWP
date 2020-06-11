from flask import Blueprint
from flask_restful import Api

from imagenet_browser.resources.synset import SynsetCollection, SynsetItem, SynsetHyponymCollection
from imagenet_browser.resources.image import SynsetImageCollection, ImageCollection, ImageItem

api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)

api.add_resource(SynsetCollection, "/synsets/")
api.add_resource(SynsetItem, "/synsets/<wnid>/")
api.add_resource(SynsetHyponymCollection, "/synsets/<wnid>/hyponyms/")
api.add_resource(SynsetImageCollection, "/synsets/<wnid>/images/")
api.add_resource(ImageItem, "/synsets/<wnid>/images/<imid>/")
api.add_resource(ImageCollection, "/images/")

'''
Resource           GET POST PUT DELETE URI
-------------------------------------------------------------------------
synset collection  X   X               /api/synsets/
synset item        X        X   X      /api/synsets/<wnid>/
hyponyms of synset X                   /api/synsets/<wnid>/hyponyms/
images of synset   X   X               /api/synsets/<wnid>/images/
image item         X        X   X      /api/synsets/<wnid>/images/<imid>/
image collection   X                   /api/images/
'''
