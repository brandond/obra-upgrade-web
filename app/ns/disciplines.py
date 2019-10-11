from flask_restplus import Resource, fields, marshal
import logging
from obra_upgrade_calculator import data

logger = logging.getLogger(__name__)
cache_timeout = 86400


def register(api, cache):
    ns = api.namespace('disciplines', 'Race Disciplines')
    discipline = ns.model('RaceDiscipline',
                          {'name': fields.String,
                           'display': fields.String,
                           })

    @ns.route('/')
    @ns.response(200, 'Success', [discipline])
    @ns.response(400, 'Bad Request')
    @ns.response(500, 'Server Error')
    class People(Resource):
        @cache.cached(timeout=cache_timeout)
        def get(self):
            disciplines = [{'name': d, 'display': d.split('_')[0].title()} for d in sorted(data.DISCIPLINE_MAP.keys())]
            return ([marshal(d, discipline) for d in disciplines], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})
