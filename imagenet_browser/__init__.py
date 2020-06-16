import os
import json
from flask import Flask, Response, url_for
from flask_sqlalchemy import SQLAlchemy
from imagenet_browser.constants import *

db = SQLAlchemy()

# Based on http://flask.pocoo.org/docs/1.0/tutorial/factory/#the-application-factory
# Modified to use Flask SQLAlchemy
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "development.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    from . import models
    from . import api
    app.cli.add_command(models.init_db_command)
    app.cli.add_command(models.load_db_command)
    app.register_blueprint(api.api_bp)

    @app.route(LINK_RELATIONS_URL)
    def send_link_relations():
        return "link relations"

    @app.route("/profiles/<profile>/")
    def send_profile(profile):
        return "{} profile".format(profile)

    from . import utils

    @app.route("/api/")
    def entry_point():
        body = utils.ImagenetBrowserBuilder()

        body.add_namespace("imagenet_browser", LINK_RELATIONS_URL)
        body.add_control("imagenet_browser:synsetcollection", url_for("api.synsetcollection"))
        body.add_control("imagenet_browser:imagecollection", url_for("api.imagecollection"))

        return Response(json.dumps(body), 200, mimetype=MASON)

    return app