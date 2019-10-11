from flask_restplus import Resource, fields, marshal
from peewee import fn, JOIN
from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import Series, Event, Race, db

import logging

logger = logging.getLogger(__name__)
cache_timeout = 900


def register(api, cache):
    ns = api.namespace('events', 'Events')

    def make_discipline(event):
        return {'name': event.discipline,
                'display': event.discipline.split('_')[0].title(),
                }

    series = ns.model('Series',
                      {'id': fields.Integer,
                       'name': fields.String,
                       })

    event = ns.model('YearEvent',
                     {'id': fields.Integer,
                      'name': fields.String,
                      'date': fields.Date,
                      'series': fields.Nested(series, allow_null=True),
                      })

    discipline = ns.model('Discipline',
                          {'name': fields.String,
                           'display': fields.String,
                           })

    event_with_discipline = ns.clone('EventWithDiscipline', event,
                                     {'discipline': fields.Nested(discipline, attribute=make_discipline),
                                      })

    discipline_with_events = ns.clone('DisciplineWithEvents', discipline,
                                      {'events': fields.List(fields.Nested(event)),
                                       })

    @ns.route('/recent/')
    @ns.response(200, 'Success', [event_with_discipline])
    @ns.response(500, 'Server Error')
    class RecentEvents(Resource):
        """
        Get recent events from any year and discipline, sorted by date
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            query = (Event.select(Event, Series, fn.MAX(Race.date).alias('date'))
                          .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                          .join(Race, src=Event)
                          .order_by(Race.date.desc())
                          .group_by(Event)
                          .limit(6))
            return ([marshal(e, event_with_discipline) for e in query], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})

    @ns.route('/years/')
    @ns.response(200, 'Success', [fields.Integer])
    @ns.response(500, 'Server Error')
    class YearList(Resource):
        """
        Get a list of years that we have data for
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            query = (Event.select(fn.DISTINCT(Event.year))
                          .order_by(Event.year.desc())
                          .namedtuples())
            return ([r.year for r in query], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})

    @ns.route('/years/<int:year>/')
    @ns.response(200, 'Success', [discipline_with_events])
    @ns.response(404, 'Not Found')
    @ns.response(500, 'Server Error')
    class YearEvents(Resource):
        """
        Get a list of events for this year, grouped by discipline
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self, year):
            disciplines = []
            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                query = (Event.select(Event, Series, fn.MAX(Race.date).alias('date'))
                              .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                              .join(Race, src=Event)
                              .where(Event.year == year)
                              .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                              .group_by(Event, Series)
                              .order_by(fn.MAX(Race.date).desc(), Event.id.desc()))
                data = {'name': upgrade_discipline,
                        'display': upgrade_discipline.split('_')[0].title(),
                        'events': query,
                        }
                disciplines.append(data)
            return ([marshal(d, discipline_with_events) for d in disciplines], 200, {'Cache-Control': f'public, max-age={cache_timeout}'})
