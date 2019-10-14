import logging
from datetime import date
from email.utils import formatdate
from time import time

from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import (Event, Person, Points, Race,
                                            Result, Series, db)
from peewee import JOIN, Window, fn

from flask_restplus import Resource, fields, marshal

logger = logging.getLogger(__name__)
cache_timeout = 900


def register(api, cache):
    ns = api.namespace('upgrades', 'Upgrade Status and Events')

    def make_discipline(event):
        return {'name': event.discipline,
                'display': event.discipline.split('_')[0].title(),
                }

    result = ns.model('Result',
                      {'id': fields.Integer,
                       'place': fields.String,
                       'time': fields.Integer,
                       'laps': fields.Integer,
                       'value': fields.Integer(attribute=lambda r: r.points.value),
                       'sum_value': fields.Integer(attribute=lambda r: r.points.sum_value),
                       'sum_categories': fields.List(fields.Integer, attribute=lambda r: r.points.sum_categories),
                       'notes': fields.String(attribute=lambda r: r.points.notes),
                       'needs_upgrade': fields.Boolean(attribute=lambda r: r.points.needs_upgrade),
                       })

    person = ns.model('Person',
                      {'id': fields.Integer,
                       'first_name': fields.String,
                       'last_name': fields.String,
                       'team_name': fields.String,
                       'name': fields.String(attribute=lambda p: '{} {}'.format(p.first_name, p.last_name).title() if p else None),
                       })

    series = ns.model('Series',
                      {'id': fields.Integer,
                       'name': fields.String,
                       })

    event = ns.model('Event',
                     {'id': fields.Integer,
                      'name': fields.String,
                      'year': fields.Integer,
                      'series': fields.Nested(series, allow_null=True),
                      })

    race = ns.model('Race',
                    {'id': fields.Integer,
                     'name': fields.String,
                     'date': fields.Date,
                     'starters': fields.Integer,
                     'categories': fields.List(fields.Integer),
                     })

    discipline = ns.model('Discipline',
                          {'name': fields.String,
                           'display': fields.String,
                           })

    event_with_discipline = ns.clone('EventWithDiscipline', event,
                                     {'discipline': fields.Nested(discipline, attribute=make_discipline),
                                      })

    # Race with event info
    race_with_event = ns.clone('RaceWithEvent', race,
                               {'event': fields.Nested(event_with_discipline),
                                })

    # Results for upgrades - contains person info and race data
    result_with_person_and_race = ns.clone('ResultWithPersonAndRace', result,
                                           {'race': fields.Nested(race),
                                            'person': fields.Nested(person),
                                            })

    result_with_person_and_race_with_event = ns.clone('ResultWithPersonAndRaceWithEvent', result,
                                                      {'race': fields.Nested(race_with_event),
                                                       'person': fields.Nested(person),
                                                       })

    # Container for grouping results by discipline
    discipline_results = ns.model('DisciplineResultsWithRaceAndPerson',
                                  {'name': fields.String,
                                   'display': fields.String,
                                   'results': fields.List(fields.Nested(result_with_person_and_race)),
                                   })

    @ns.route('/pending/')
    @ns.response(200, 'Success', [discipline_results])
    @ns.response(500, 'Server Error')
    class UpgradesPending(Resource):
        """
        Get pending upgrades, grouped by discipline, sorted by category and points
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)
            disciplines = []

            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                # Subquery to find the most recent result for each person
                last_result = (Result.select()
                                     .join(Race, src=Result)
                                     .join(Event, src=Race)
                                     .join(Person, src=Result)
                                     .where(Race.date >= start_date)
                                     .where(Race.categories.length() > 0)
                                     .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                                     .select(fn.DISTINCT(fn.FIRST_VALUE(Result.id)
                                                           .over(partition_by=[Result.person_id],
                                                                 order_by=[Race.date.desc(), Race.created.desc()],
                                                                 start=Window.preceding()
                                                                 )
                                                         ).alias('first_id')))

                query = (Result.select(Result,
                                       Race,
                                       Event,
                                       Person,
                                       Points)
                               .join(Race, src=Result)
                               .join(Event, src=Race)
                               .join(Person, src=Result)
                               .join(Points, src=Result)
                               .where(Result.id << last_result)
                               .where(Points.needs_upgrade == True)
                               .where(~(Race.name.contains('Junior')))
                               .order_by(Points.sum_categories.asc(),
                                         Points.sum_value.desc()))

                disciplines.append({'name': upgrade_discipline,
                                    'display': upgrade_discipline.split('_')[0].title(),
                                    'results': query,
                                    })

            return ([marshal(d, discipline_results) for d in disciplines],
                    200,
                    {'Expires': formatdate(timeval=time() + cache_timeout, usegmt=True)})

    @ns.route('/pending/top/')
    @ns.response(200, 'Success', [result_with_person_and_race_with_event])
    @ns.response(500, 'Server Error')
    class UpgradesPendingTop(Resource):
        """
        Get the top pending upgrades, sorted by category and points
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)

            # Subquery to find the most recent result for each person
            last_result = (Result.select()
                                 .join(Race, src=Result)
                                 .join(Event, src=Race)
                                 .join(Person, src=Result)
                                 .where(Race.date >= start_date)
                                 .where(Race.categories.length() > 0)
                                 .select(fn.DISTINCT(fn.FIRST_VALUE(Result.id)
                                                       .over(partition_by=[Result.person_id],
                                                             order_by=[Race.date.desc(), Race.created.desc()],
                                                             start=Window.preceding()
                                                             )
                                                     ).alias('first_id')))

            query = (Result.select(Result,
                                   Race,
                                   Event,
                                   Series,
                                   Person,
                                   Points)
                           .join(Race, src=Result)
                           .join(Event, src=Race)
                           .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                           .join(Person, src=Result)
                           .join(Points, src=Result)
                           .where(Result.id << last_result)
                           .where(~(Race.name.contains('Junior')))
                           .where(Points.needs_upgrade == True)
                           .order_by(Points.sum_categories.asc(),
                                     Points.sum_value.desc())
                           .limit(6))

            return ([marshal(r, result_with_person_and_race_with_event) for r in query],
                    200,
                    {'Expires': formatdate(timeval=time() + cache_timeout, usegmt=True)})

    @ns.route('/recent/')
    @ns.response(200, 'Success', [discipline_results])
    @ns.response(500, 'Server Error')
    class UpgradesRecent(Resource):
        """
        Get historical upgrades, grouped by discipline, sorted by date, category, name
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)
            disciplines = []

            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                query = (Result.select(Result,
                                       Race,
                                       Event,
                                       Series,
                                       Person,
                                       Points)
                               .join(Race, src=Result)
                               .join(Event, src=Race)
                               .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                               .join(Person, src=Result)
                               .join(Points, src=Result)
                               .where(Race.date >= start_date)
                               .where(~(Race.name.contains('junior')))
                               .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                               .where(Points.notes.contains('upgraded') | Points.notes.contains('downgraded'))
                               .order_by(Race.date.desc(),
                                         Points.sum_categories.asc(),
                                         Person.last_name.asc(),
                                         Person.first_name.asc()))

                disciplines.append({'name': upgrade_discipline,
                                    'display': upgrade_discipline.split('_')[0].title(),
                                    'results': query,
                                    })

            return ([marshal(d, discipline_results) for d in disciplines],
                    200,
                    {'Expires': formatdate(timeval=time() + cache_timeout, usegmt=True)})

    @ns.route('/recent/top/')
    @ns.response(200, 'Success', [result_with_person_and_race_with_event])
    @ns.response(500, 'Server Error')
    class UpgradesRecentTop(Resource):
        """
        Get recent historical upgrades, sorted by date, category, name
        """
        @db.atomic()
        @cache.cached(timeout=cache_timeout)
        def get(self):
            cur_year = date.today().year
            start_date = date(cur_year - 1, 1, 1)

            query = (Result.select(Result,
                                   Race,
                                   Event,
                                   Series,
                                   Person,
                                   Points)
                           .join(Race, src=Result)
                           .join(Event, src=Race)
                           .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                           .join(Person, src=Result)
                           .join(Points, src=Result)
                           .where(Race.date >= start_date)
                           .where(~(Race.name.contains('Junior')))
                           .where(Points.notes.contains('upgraded') | Points.notes.contains('downgraded'))
                           .order_by(Race.date.desc(),
                                     Points.sum_categories.asc(),
                                     Person.last_name.asc(),
                                     Person.first_name.asc())
                           .limit(6))

            return ([marshal(r, result_with_person_and_race_with_event) for r in query],
                    200,
                    {'Expires': formatdate(timeval=time() + cache_timeout, usegmt=True)})
