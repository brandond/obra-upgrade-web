from flask_restplus import Resource, fields, marshal
from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import Points, Result, Person, Race, Event, db
from peewee import fn
from datetime import date
import logging

logger = logging.getLogger(__name__)
cache_timeout = 900


def register(api, cache):
    ns = api.namespace('upgrades', 'Upgrade Alerts')

    person = ns.model('Person',
                      {'id': fields.Integer,
                       'first_name': fields.String,
                       'last_name': fields.String,
                       'team_name': fields.String,
                       'name': fields.String(attribute=lambda p: '{} {}'.format(p.first_name, p.last_name).title() if p else None),
                       })

    points = ns.model('PointsWithPersonAndRace',
                      {'value': fields.Integer,
                       'sum_value': fields.Integer,
                       'sum_categories': fields.List(fields.Integer),
                       'notes': fields.String,
                       'needs_upgrade': fields.Boolean,
                       'last_date': fields.Date,
                       'person': fields.Nested(person, attribute=lambda p: p.result.person),
                       })

    discipline = ns.model('UpgradesDiscipline',
                          {'name': fields.String,
                           'display': fields.String,
                           'results': fields.List(fields.Nested(points))
                           })

    @ns.route('/')
    @ns.response(200, 'Success', [discipline])
    @ns.response(500, 'Server Error')
    class Upgrades(Resource):
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)
            disciplines = []

            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                query = (Points.select(Points,
                                       Result.id,
                                       Person,
                                       fn.MAX(Race.date).alias('last_date'))
                               .join(Result, src=Points)
                               .join(Person, src=Result)
                               .join(Race, src=Result)
                               .join(Event, src=Race)
                               .where(Race.date >= start_date)
                               .where(~(Race.name.contains('Junior')))
                               .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                               .group_by(Person)
                               .having(Points.needs_upgrade == True)
                               .order_by(Points.sum_categories.asc(),
                                         Points.sum_value.desc()))

                disciplines.append({'name': upgrade_discipline,
                                    'display': upgrade_discipline.split('_')[0].title(),
                                    'results': query,
                                    })

            return ([marshal(d, discipline) for d in disciplines], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})

    @ns.route('/recent/')
    @ns.response(200, 'Success', [points])
    @ns.response(500, 'Server Error')
    class UpgradesRecent(Resource):
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)

            query = (Points.select(Points,
                                   Result.id,
                                   Person,
                                   fn.MAX(Race.date).alias('last_date'))
                           .join(Result, src=Points)
                           .join(Person, src=Result)
                           .join(Race, src=Result)
                           .join(Event, src=Race)
                           .where(Race.date >= start_date)
                           .where(~(Race.name.contains('Junior')))
                           .group_by(Person)
                           .having(Points.needs_upgrade == True)
                           .order_by(Points.sum_categories.asc(),
                                     Points.sum_value.desc())
                           .limit(6))

            return ([marshal(p, points) for p in query], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})
