import os
import json
from flask import Flask, Response, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy import event
from imagenet_browser.constants import *

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable SQLite foreign keys.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Based on http://flask.pocoo.org/docs/1.0/tutorial/factory/#the-application-factory
# Modified to use Flask SQLAlchemy
def create_app(test_config=None):
    """
    The application factory.
    Create and initialize the Flask application using either the passed configuration or 'config.py' if available.
    Register Click commands for 'flask' command line invocation used for initial database creation and loading.
    Register a blueprint for view grouping.
    Register link relations, profile, and entry point views.
    Return the application.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "development.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    if not test_config: # pragma: no cover
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
        """
        The route's view function listening for GET.
        Return a plain text description of where to find link relations.
        """
        return "For link relations, refer to https://imagenetbrowser.docs.apiary.io/#reference/link-relations"

    @app.route("/profiles/<profile>/")
    def send_profile(profile):
        """
        The route's view function listening for GET.
        Return a plain text description of where to find profile information.
        """
        return "For profiles, refer to https://imagenetbrowser.docs.apiary.io/#reference/profiles"

    from . import utils

    @app.route("/api/")
    def entry_point():
        """
        The route's view function listening for GET.
        Build and return the hypermedia response for the entry point.
        """
        body = utils.ImagenetBrowserBuilder()

        body.add_namespace("imagenet_browser", LINK_RELATIONS_URL)
        body.add_control("imagenet_browser:synsetcollection", url_for("api.synsetcollection"))
        body.add_control("imagenet_browser:imagecollection", url_for("api.imagecollection"))

        return Response(json.dumps(body), 200, mimetype=MASON)

    return app
