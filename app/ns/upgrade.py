from flask import Flask, request
from flask_restplus import Resource, fields, marshal
from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import Series, Event, db
import logging

logger = logging.getLogger(__name__)


def register(api, cache):
    ns = api.namespace('upgrades', 'Upgrade Alerts')

    @ns.route('/<string:discipline>')
    @ns.response(200, 'Success')
    @ns.response(404, 'Not Found')
    @ns.response(500, 'Server Error')
    class YearList(Resource):
        @db.atomic()
        @cache.cached(timeout=900)
        def get(self, discipline):
            pass


