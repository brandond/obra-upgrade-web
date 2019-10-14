import logging
import os
from datetime import date

from obra_upgrade_calculator import data, scrapers, upgrades

import uwsgi
from uwsgidecorators import rbtimer

logger = logging.getLogger(__name__)
logger.info('{} imported'.format(__name__))
full_scrape_done = False


@rbtimer(600, target='spooler')
def scrape_events(num):
    # Most of this is cribbed from obra_upgrade_calculator.commands
    if 'NO_SCRAPE' in os.environ:
        logger.debug('Year scrape disabled by NO_SCRAPE')
        return

    global full_scrape_done
    cur_year = date.today().year

    if full_scrape_done:
        years = [cur_year]
    else:
        years = range(cur_year - 6, cur_year + 1)
        full_scrape_done = True

    changed = False
    for discipline in data.DISCIPLINE_MAP.keys():
        for year in years:
            scrapers.scrape_year(year, discipline)

        if scrapers.scrape_new(discipline):
            if upgrades.recalculate_points(discipline, incremental=True):
                upgrades.sum_points(discipline)
                changed = True

    if changed:
        uwsgi.cache_clear('default')


@rbtimer(1800, target='spooler')
def scrape_recent(num):
    if 'NO_SCRAPE' in os.environ:
        logger.debug('Recent event re-scrape disabled by NO_SCRAPE')
        return

    changed = False
    for discipline in data.DISCIPLINE_MAP.keys():
        if scrapers.scrape_recent(discipline, 3):
            if upgrades.recalculate_points(discipline, incremental=True):
                upgrades.sum_points(discipline)
                changed = True

    if changed:
        uwsgi.cache_clear('default')
