import json
from datetime import datetime
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from imagenet_browser.models import Synset, Image
from imagenet_browser import db
from imagenet_browser.utils import ImagenetBrowserBuilder, create_error_response
from imagenet_browser.constants import *

class SynsetImageCollection(Resource):
    """
    Subclass of Resource that defines the HTTP method handlers for the SynsetImageCollection resource.
    Error scenarios for the various methods are described in the calls to create_error_response, or alternatively, in the resource tests.
    All images of a synset.
    """

    def get(self, wnid):
        """
        Build and return a list of all images of the synset.
        A list has IMAGE_PAGE_SIZE items with the starting index being controlled by the query parameter.
        As such, the next and prev controls become available when appropriate.
        """
        try:
            start = int(request.args.get("start", default=0))
        except ValueError:
            return create_error_response(
                400,
                "Invalid query parameter",
                "Query parameter 'start' must be an integer"
            )

        synset = Synset.query.filter_by(wnid=wnid).first()
        if not synset:
            return create_error_response(
                404,
                "Not found",
                "No synset with WordNet ID of '{}' found".format(wnid)
            )

        body = ImagenetBrowserBuilder()

        body.add_namespace("imagenet_browser", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.synsetimagecollection", wnid=wnid) + "?start={}".format(start))
        body.add_control_add_image(wnid=wnid)
        body.add_control("imagenet_browser:synsetitem", url_for("api.synsetitem", wnid=wnid))

        images = Image.query.filter(Image.synset_wnid == wnid).order_by(Image.imid).offset(start)

        if start >= IMAGE_PAGE_SIZE:
            body.add_control("prev", url_for("api.synsetimagecollection", wnid=wnid) + "?start={}".format(start - IMAGE_PAGE_SIZE))
        if images.count() > IMAGE_PAGE_SIZE:
            body.add_control("next", url_for("api.synsetimagecollection", wnid=wnid) + "?start={}".format(start + IMAGE_PAGE_SIZE))

        body["items"] = []
        for image in images.limit(IMAGE_PAGE_SIZE):
            item = ImagenetBrowserBuilder(
                imid=image.imid,
                url=image.url,
                date=image.date
            )
            item.add_control("self", url_for("api.synsetimageitem", wnid=wnid, imid=image.imid))
            item.add_control("profile", IMAGE_PROFILE)
            body["items"].append(item)

        return Response(json.dumps(body), 200, mimetype=MASON)

    def post(self, wnid):
        """
        Add a new image to the synset and return its location in the response headers.
        The image representation must be valid against the image schema.
        """
        synset = Synset.query.filter_by(wnid=wnid).first()
        if not synset:
            return create_error_response(
                404,
                "Not found",
                "No synset with WordNet ID of '{}' found".format(wnid)
            )

        if not request.json:
            return create_error_response(
                415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, Image.get_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        try:
            request.json["date"]
        except KeyError:
            request.json["date"] = datetime.now().isoformat().split("T")[0]

        image = Image(
            imid=request.json["imid"],
            url=request.json["url"],
            date=request.json["date"],
            synset=synset
        )

        try:
            db.session.add(image)
            db.session.commit()
        except IntegrityError:
            return create_error_response(
                409,
                "Already exists",
                "Image with WordNet ID of '{}' and image ID of '{}' already exists".format(
                    wnid, request.json["imid"]
                )
            )

        return Response(status=201, headers={
            "Location": url_for("api.synsetimageitem", wnid=wnid, imid=request.json["imid"])
        })

class SynsetImageItem(Resource):
    """
    Subclass of Resource that defines the HTTP method handlers for the SynsetImageItem resource.
    Error scenarios for the various methods are described in the calls to create_error_response, or alternatively, in the resource tests.
    An image of a synset identified by its numerical ID.
    """

    def get(self, wnid, imid):
        """
        Build and return the image representation.
        """
        image = Image.query.filter(Image.synset_wnid == wnid, Image.imid == imid).first()
        if not image:
            return create_error_response(
                404,
                "Not found",
                "No image with WordNet ID of '{}' and image ID of '{}' found".format(wnid, imid)
            )

        body = ImagenetBrowserBuilder(
            imid=imid,
            url=image.url,
            date=image.date
        )
        body.add_namespace("imagenet_browser", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.synsetimageitem", wnid=wnid, imid=imid))
        body.add_control("profile", IMAGE_PROFILE)
        body.add_control("collection", url_for("api.synsetimagecollection", wnid=wnid))
        body.add_control_edit_image(wnid=wnid, imid=imid)
        body.add_control_delete_image(wnid=wnid, imid=imid)
        body.add_control("imagecollection", url_for("api.imagecollection"))

        return Response(json.dumps(body), 200, mimetype=MASON)

    def put(self, wnid, imid):
        """
        Replace the image representation with a new one.
        Must validate against the image schema.
        """
        image = Image.query.filter(Image.synset_wnid == wnid, Image.imid == imid).first()
        if not image:
            return create_error_response(
                404,
                "Not found",
                "No image with WordNet ID of '{}' and image ID of '{}' found".format(wnid, imid)
            )

        if not request.json:
            return create_error_response(
                415,
                "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, Image.get_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        try:
            request.json["date"]
        except KeyError:
            request.json["date"] = image.date

        image.imid = request.json["imid"]
        image.url = request.json["url"]
        image.date = request.json["date"]

        try:
            db.session.commit()
        except IntegrityError:
            return create_error_response(
                409,
                "Already exists",
                "Image with WordNet ID of '{}' and image ID of '{}' already exists".format(
                    wnid, request.json["imid"]
                )
            )

        return Response(status=204)

    def delete(self, wnid, imid):
        """
        Delete the image.
        """
        image = Image.query.filter(Image.synset_wnid == wnid, Image.imid == imid).first()
        if not image:
            return create_error_response(
                404,
                "Not found",
                "No image with WordNet ID of '{}' and image ID of '{}' found".format(wnid, imid)
            )

        db.session.delete(image)
        db.session.commit()

        return Response(status=204)

class ImageCollection(Resource):
    """
    Subclass of Resource that defines the HTTP method handlers for the ImageCollection resource.
    Error scenarios for the various methods are described in the calls to create_error_response, or alternatively, in the resource tests.
    """

    def get(self):
        """
        Build and return a list of all images known to the API.
        A list has IMAGE_PAGE_SIZE items with the starting index being controlled by the query parameter.
        As such, the next and prev controls become available when appropriate.
        """
        body = ImagenetBrowserBuilder()
        
        body.add_namespace("imagenet_browser", LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.imagecollection"))

        try:
            start = int(request.args.get("start", default=0))
        except ValueError:
            return create_error_response(
                400,
                "Invalid query parameter",
                "Query parameter 'start' must be an integer"
            )

        images = Image.query.order_by(Image.synset_wnid, Image.imid).offset(start)

        if start >= IMAGE_PAGE_SIZE:
            body.add_control("prev", url_for("api.imagecollection") + "?start={}".format(start - IMAGE_PAGE_SIZE))
        if images.count() > IMAGE_PAGE_SIZE:
            body.add_control("next", url_for("api.imagecollection") + "?start={}".format(start + IMAGE_PAGE_SIZE))

        body["items"] = []
        for image in images.limit(IMAGE_PAGE_SIZE):
            item = ImagenetBrowserBuilder(
                synset_wnid=image.synset_wnid,
                imid=image.imid,
                url=image.url,
                date=image.date
            )
            item.add_control("self", url_for("api.synsetimageitem", wnid=image.synset_wnid, imid=image.imid))
            item.add_control("profile", IMAGE_PROFILE)
            body["items"].append(item)
            
        return Response(json.dumps(body), 200, mimetype=MASON)
