import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import feedparser


class TXEventScraper(EventScraper):
    state = 'tx'

    _tz = pytz.timezone('US/Central')

    def scrape(self, chamber, session):
        if session != '82':
            raise NoDataForPeriod(session)

        self.scrape_committee_upcoming(session, chamber)

    def scrape_committee_upcoming(self, session, chamber):
        chamber_name = {'upper': 'senate',
                        'lower': 'house',
                        'other': 'joint'}[chamber]
        url = ("http://www.capitol.state.tx.us/MyTLO/RSS/RSS.aspx?"
               "Type=upcomingmeetings%s" % chamber_name)

        with self.urlopen(url) as page:
            feed = feedparser.parse(page)

            for entry in feed['entries']:
                try:
                    title, date = entry['title'].split(' - ')
                except ValueError:
                    continue

                try:
                    time = re.match('Time: (\d+:\d+ (A|P)M)',
                                    entry['description']).group(1)
                except AttributeError:
                    # There are a few broken events in their feeds
                    # sometimes
                    continue

                when = "%s %s" % (date, time)
                when = datetime.datetime.strptime(when, '%m/%d/%Y %I:%M %p')
                when = self._tz.localize(when)

                location = entry['description'].split('Location: ')[1]

                description = 'Committee Meeting\n'
                description += entry['title'] + '\n'
                description += entry['description']

                event = Event(session, when, 'committee:meeting',
                              description,
                              location=location)
                event.add_participant('committee', title)

                event['_guid'] = entry['guid']
                event['link'] = entry['link']

                event.add_source(url)

                self.save_event(event)
