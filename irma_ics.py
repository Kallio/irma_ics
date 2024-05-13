"""Convert irma calendar to caldav.

Usage instructions::

    python3 -m venv venv
    source venv/bin/activate
    pip install requests ics
    LOGLEVEL=DEBUG python irma_ics.py ilmodedis
or
    LOGLEVEL=DEBUG python irma_ics.py events


"""

import re
import os
from pathlib import Path
from datetime import datetime, timedelta
import sys
import argparse
import logging
import urllib
import requests
import arrow.parser
from ics import Calendar, Event, DisplayAlarm

LOGGER = logging.getLogger("irma-ics")
logging.basicConfig(level=os.environ.get("LOGLEVEL", logging.WARNING))

BASE_URL = "https://irma.suunnistusliitto.fi"

CALENDAR_URL = (
    f"{BASE_URL}/irma/public/competitioncalendar"
    "/view?dicsipline=SUUNNISTUS&competitionOpen=ALL"
)

EVENT_KEYS = {
    "1. ilmoittautumisporras": "emit_registration_date",
    "Kilpailupäivä": "event_name",
    "Päivämäärä": "event_date",
    "taso": "event_level",
    "WWW": "competition_www",
}

DATE_FORMATS = [
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M:%S",
]


def get_cache(identifier):
    """magic cache"""
    filename = re.sub(r"[^0-9a-zA-Z]+", "_", identifier)
    filename = re.sub(r"jsessionid_[A-Z0-9]+_", "_", filename)
    cache = Path(f"cache/{filename}")
    cache.parent.mkdir(exist_ok=True)
    return cache


def get_url(url):
    """Return page from local cache"""

    cache = get_cache(url)
    if cache.exists():
        LOGGER.debug("Cached %s", cache.name)
        return cache.read_text("utf8")

    response = requests.get(url)
    cache.write_text(response.text, "utf8")
    return response.text


def parse_event_urls(html):
    """return event info urls from event calendar"""
    for line in html.splitlines():
        match = re.match('.*(/irma/public/competition/view[^"]+)', line)
        if match:
            yield match.group(1)


def parse_rows(html):
    """Parse table rows / columns from html"""
    for row in re.sub(r"\s+", " ", html).split("(.*?)= range_start.isoformat()) and (iso_date(event_info["event_date"]) <= range_end.isoformat()):
            ics = Event()
            ics.name = f" {event_name}"
            ics.begin = iso_date(event_info["event_date"])
            ics.url =event_info["url"]
            ics.make_all_day()

    # Lisää hälytys 1 päivä ennen emit_registration_date:tä, jos se on saatavilla
            if "emit_registration_date" in event_info:
                ics.alarm = event_info["emit_registration_date"]

            yield ics
    except (ValueError, arrow.parser.ParserError) as exception:
        LOGGER.warning("create_ics_events:raceday:%s:%s", event_name, str(exception))

def create_ics_ilmodedis(event_info):
    """Return event ilmodedis from calendar """
    event_name = normalize_event_name(event_info)
    range_start = datetime.now()
    range_end = range_start +timedelta(days=365)

    try:
        if (iso_date(event_info["emit_registration_date"]) >= range_start.isoformat()) and (iso_date(event_info["emit_registration_date"]) <= range_end.isoformat()):
            ics = Event()
            ics.name = f"ilmodedis: {event_name}"
            ics.begin = iso_date(event_info["emit_registration_date"])
            ics.url =event_info["url"]
            ics.make_all_day()
            yield ics
    except (ValueError, arrow.parser.ParserError) as exception:
        LOGGER.warning("create_ics_events:emit_date:%s:%s", event_name, str(exception))


def event_key(event):
    """unique key for removing duplicates"""
    return str(event.begin) + str(event.name)

def main():
    """print ics calendar from irma events"""


    parser=argparse.ArgumentParser(description="choose ilmodedis or events")
    parser.add_argument("type")
    args=parser.parse_args()


    main_page = get_url(CALENDAR_URL)

    events = {}

    for event_url in parse_event_urls(main_page):
        event_page = get_url(BASE_URL + event_url)
        event_info = parse_event_info(event_page)
         # Lisätään tapahtuman URL sen tietoihin
        event_info["url"] =BASE_URL +'/irma/public/competition/view?' +urllib.parse.urlparse(BASE_URL+event_url).query
        if args.type=="ilmodedis":
            for event in create_ics_ilmodedis(event_info):
                    events[event_key(event)] = event

        else :
            for event in create_ics_events(event_info):
                    events[event_key(event)] = event


    calendar = Calendar()

    for event in events.values():
        calendar.events.add(event)


    print("".join(calendar.serialize_iter()))


if __name__ == "__main__":
    main()
