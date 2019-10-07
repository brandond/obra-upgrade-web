from flask import Flask, request
from flask_restplus import Resource, fields, marshal
from peewee import fn, JOIN
from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import Series, Event, Race, db

import logging

logger = logging.getLogger(__name__)


def register(api, cache):
    ns = api.namespace('events', 'Events')

    series = ns.model('Series', {
        'id': fields.Integer,
        'name': fields.String,
        })

    event = ns.model('YearEvent', {
        'id': fields.Integer,
        'name': fields.String,
        'date': fields.Date,
        'series': fields.Nested(series, allow_null=True),
        })

    discipline = ns.model('YearDiscipline', {
        'name': fields.String,
        'display': fields.String,
        'events': fields.List(fields.Nested(event))
        })

    @ns.route('/years/')
    @ns.response(200, 'Success', [fields.Integer])
    @ns.response(500, 'Server Error')
    class YearList(Resource):
        @db.atomic()
        @cache.cached(timeout=900)
        def get(self):
            query = (Event.select(fn.DISTINCT(Event.year))
                          .order_by(Event.year.desc())
                          .namedtuples())
            return [r.year for r in query]

    @ns.route('/years/<int:year>')
    @ns.response(200, 'Success', [discipline])
    @ns.response(404, 'Not Found')
    @ns.response(500, 'Server Error')
    class YearEvents(Resource):
        @db.atomic()
        @cache.cached(timeout=900)
        def get(self, year):
            disciplines = []
            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                query = (Event.select(Event, Series, fn.MAX(Race.date).alias('date'))
                              .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                              .join(Race, src=Event)
                              .where(Event.year == year)
                              .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                              .group_by(Event, Series)
                              .order_by(fn.MAX(Race.date).asc(), Event.id.asc()))
                data = {
                    'name': upgrade_discipline,
                    'display': upgrade_discipline.split('_')[0].title(),
                    'events': query,
                    }
                disciplines.append(data)
            return [marshal(d, discipline) for d in disciplines]
