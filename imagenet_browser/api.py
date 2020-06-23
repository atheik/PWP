from flask import Blueprint
from flask_restful import Api

from imagenet_browser.resources.synset import SynsetCollection, SynsetItem, SynsetHyponymCollection, SynsetHyponymItem
from imagenet_browser.resources.image import SynsetImageCollection, ImageCollection, SynsetImageItem

api_bp = Blueprint("api", __name__, url_prefix="/api")
api = Api(api_bp)

api.add_resource(SynsetCollection, "/synsets/")
api.add_resource(SynsetItem, "/synsets/<wnid>/")
api.add_resource(SynsetHyponymCollection, "/synsets/<wnid>/hyponyms/")
api.add_resource(SynsetHyponymItem, "/synsets/<wnid>/hyponyms/<hyponym_wnid>/")
api.add_resource(SynsetImageCollection, "/synsets/<wnid>/images/")
api.add_resource(SynsetImageItem, "/synsets/<wnid>/images/<imid>/")
api.add_resource(ImageCollection, "/images/")

'''
Resource                  GET POST PUT DELETE URI
-----------------------------------------------------------------------------------
synset collection         X   X               /api/synsets/
synset item               X        X   X      /api/synsets/<wnid>/
synset hyponym collection X   X               /api/synsets/<wnid>/hyponyms/
synset hyponym item       X            X      /api/synsets/<wnid>/hyponyms/<hyponym_wnid>/
synset image collection   X   X               /api/synsets/<wnid>/images/
synset image item         X        X   X      /api/synsets/<wnid>/images/<imid>/
image collection          X                   /api/images/
'''
