from flask import Flask, request
from flask_restplus import Resource, fields, marshal
import logging
from obra_upgrade_calculator import data

logger = logging.getLogger(__name__)


def register(api, cache):
    ns = api.namespace('discipline', 'Race Disciplines')
    discipline = ns.model('RaceDiscipline', {
        'name': fields.String,
        'display': fields.String,
        })

    @ns.route('/')
    @ns.response(200, 'Success', [discipline])
    @ns.response(400, 'Bad Request')
    @ns.response(500, 'Server Error')
    class People(Resource):
        def get(self):
            return [marshal({'name': d, 'display': d.split('_')[0].title()}, discipline) for d in sorted(data.DISCIPLINE_MAP.keys())]
