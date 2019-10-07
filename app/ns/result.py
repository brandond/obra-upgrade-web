from flask import Flask, request
from flask_restplus import Resource, fields, marshal
from peewee import prefetch, JOIN
from obra_upgrade_calculator.data import DISCIPLINE_MAP
from obra_upgrade_calculator.models import Series, Event, Person, Race, Result, Points, db
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


def register(api, cache):
    ns = api.namespace('results', 'Race Results')

    def fill_results(pdr): 
        if not pdr['results']:
            return []
        # Default filler point just pulls info from last race category
        last_points = Points(sum_categories=pdr['results'][-1].race.categories)
        # Backfill points from last to first
        for result in reversed(pdr['results']):
            if result.points:
                last_points = deepcopy(result.points[0])
                last_points.result = None
                last_points.notes = ''
                last_points.value = 0
            else:
                result.points.append(last_points)
        return pdr['results']

    # Base stuff and relationships
    person = ns.model('Person', {
        'id': fields.Integer,
        'first_name': fields.String,
        'last_name': fields.String,
        'name': fields.String(attribute=lambda p: '{} {}'.format(p.first_name, p.last_name)),
        })

    series = ns.model('Series', {
        'id': fields.Integer,
        'name': fields.String,
        })

    event = ns.model('Event', {
        'id': fields.Integer,
        'name': fields.String,
        'year': fields.Integer,
        'series': fields.Nested(series, allow_null=True),
        })

    race = ns.model('Race', {
        'id': fields.Integer,
        'name': fields.String,
        'date': fields.Date,
        'starters': fields.Integer,
        'categories': fields.List(fields.Integer),
        })

    result = ns.model('Result', {
        'id': fields.Integer,
        'place': fields.String,
        'time': fields.Integer,
        'value': fields.Integer(attribute=lambda r: r.points[0].value if r.points else None),
        'sum_value': fields.Integer(attribute=lambda r: r.points[0].sum_value if r.points else None),
        'sum_categories': fields.List(fields.Integer, attribute=lambda r: r.points[0].sum_categories if r.points else None),
        'notes': fields.String(attribute=lambda r: r.points[0].notes if r.points else None),
        'needs_upgrade': fields.Boolean(attribute=lambda r: r.points[0].needs_upgrade if r.points else None),
        })

    # Race with extra info for personal results
    race_with_event = ns.clone('RaceWithEvent', race, {
        'event': fields.Nested(event),
        })

    # Results for a race - contains person info without race data
    result_with_person = ns.clone('ResultWithPerson', result, {
        'person': fields.Nested(person),
        })

    # Results for a person - contains event info without person data
    result_with_race = ns.clone('ResultWithRace', result, {
        'race': fields.Nested(race_with_event),
        })

    # Container for grouping of results by race for an event
    event_race_results = ns.clone('EventRaceResults', race, {
        'results': fields.List(fields.Nested(result_with_person)),
        })

    # Container for grouping results by discipline for a person
    person_discipline_results = ns.model('PersonDisciplineResults', {
        'name': fields.String,
        'display': fields.String,
        'results': fields.List(fields.Nested(result_with_race), attribute=fill_results),
        })

    # Contains all results for a person, grouped by discipline
    person_results = ns.clone('PersonResults', person, {
        'disciplines': fields.List(fields.Nested(person_discipline_results)),
        })

    # Contains all results for an event, grouped by race
    event_results = ns.clone('EventResults', event, {
        'races': fields.List(fields.Nested(event_race_results))
        })

    @ns.route('/person/<int:id>')
    @ns.response(200, 'Success', person_results)
    @ns.response(400, 'Bad Request')
    @ns.response(500, 'Server Error')
    class ResultsForPerson(Resource):
        @db.atomic()
        @cache.cached(timeout=900)
        def get(self, id):
            db_person = Person.get_by_id(id)
            db_person.disciplines = []
            for upgrade_discipline in sorted(DISCIPLINE_MAP.keys()):
                query = (Result.select(Result, Points, Race, Event, Series)
                               .join(Points, src=Result, join_type=JOIN.LEFT_OUTER)
                               .join(Race, src=Result)
                               .join(Event, src=Race)
                               .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                               .where(Result.person == db_person)
                               .where(Event.discipline << DISCIPLINE_MAP[upgrade_discipline])
                               .order_by(Race.date.desc(), Race.id.desc()))
                db_person.disciplines.append({
                    'name': upgrade_discipline,
                    'display': upgrade_discipline.split('_')[0].title(),
                    'results': prefetch(query, Points, Race, Event, Series)
                    })
            return marshal(db_person, person_results)

    @ns.route('/event/<int:id>')
    @ns.response(200, 'Success', event_results)
    @ns.response(400, 'Bad Request')
    @ns.response(500, 'Server Error')
    class ResultsForEvent(Resource):
        @db.atomic()
        @cache.cached(timeout=900)
        def get(self, id):
            query = (Event.select(Event, Series, Race, Result, Points, Person)
                          .join(Series, src=Event, join_type=JOIN.LEFT_OUTER)
                          .join(Race, src=Event)
                          .join(Result, src=Race)
                          .join(Points, src=Result, join_type=JOIN.LEFT_OUTER)
                          .join(Person, src=Result)
                          .where(Event.id == id)
                          .order_by(Race.id.asc(), Result.id.asc()))
            for event in prefetch(query, Series, Race, Result, Points, Person):
                return marshal(event, event_results)
