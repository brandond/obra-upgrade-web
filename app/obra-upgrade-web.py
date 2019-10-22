import os
from importlib import import_module

from flask import Blueprint, Flask
from flask_caching import Cache
from flask_restplus import Api


def create_application():
    app = Flask(__name__, static_folder=None)
    app_api_v1 = Blueprint('api_v1', __name__)
    api = Api(app_api_v1, version='1.0', title='OBRA Hacks', contact='brad@oatmail.org')
    cache = Cache(app=app, with_jinja2_ext=False, config={'CACHE_TYPE': os.environ.get('CACHE_TYPE', 'uwsgi'),
                                                          'CACHE_UWSGI_NAME': 'default'})

    for name in ['disciplines', 'events', 'notifications', 'people', 'ranks', 'results', 'upgrades']:
        import_module('ns.' + name).register(api, cache)

    app.register_blueprint(app_api_v1, url_prefix='/api/v1')
    return app


application = create_application()
