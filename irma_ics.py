import json
import os 
import hashlib
from datetime import datetime, timedelta
import arrow.parser
import logging
import pytz

from pathlib import Path
# import argparse
import urllib
import requests
from ics import Calendar, Event, DisplayAlarm
LOGGER = logging.getLogger("irma-ics")
logging.basicConfig(level=os.environ.get("LOGLEVEL", logging.WARNING))


# Create a new calendar
calendar = Calendar()
ilmodediscalendar = Calendar()
base_url = "https://irma.suunnistusliitto.fi/public/competition/view/"       
range_start = datetime.now()
filecache_expiry = range_start+timedelta(days=2)
range_end = range_start+timedelta(days=36)

def get_cache(identifier):
    """magic cache"""
    filename = identifier
    cache = Path(f"cache/{filename}")
    cache.parent.mkdir(exist_ok=True)
    return cache

def get_url(url,cookies,heades,json_data,identifier):
    """Return page from local cache"""
    """ create unique cache identifier for url """
    hs = hashlib.sha256((url+identifier).encode('utf-8')).hexdigest()
    cache = get_cache(hs)
    if cache.exists() and (datetime.fromtimestamp(cache.stat().st_mtime).isoformat() <= filecache_expiry.isoformat()) :
        LOGGER.debug("Cached %s", cache.name)
        return cache.read_text("utf8")
   
    response = requests.post(url,
    cookies=cookies,
    headers=headers,
    json=json_data,
    )
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data from {url}")

    cache.write_text(response.text, "utf8")
    return response.text

cookies = {
    'JSESSIONID': '4CBF14F076D63FA6C56DABD308589315',
    'csrfToken': 'd5d9fb69-bd73-447a-9351-5a0e5ed0586f',
    'locale': 'fi',
}

headers = {
  #  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br, zstd',
   # 'Referer': 'https://irma.suunnistusliitto.fi/public/competitioncalendar/list',
    'Content-Type': 'application/json',
    'X-CSRF-Token': 'd5d9fb69-bd73-447a-9351-5a0e5ed0586f',
    'Origin': 'https://irma.suunnistusliitto.fi',
    #'Connection': 'keep-alive',
    # 'Cookie': 'JSESSIONID=4CBF14F076D63FA6C56DABD308589316; csrfToken=d5d9fb69-bd73-447a-9351-5a0e5ed0586f; locale=fi',
    #'Sec-Fetch-Dest': 'empty',
    #'Sec-Fetch-Mode': 'cors',
    #'Sec-Fetch-Site': 'same-origin',
    'Priority': 'u=0',
}

front_page_json_data = {
    'year': None, # can be 2028,2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2007,2000,2
    'discipline': 'SUUNNISTUS', # can be also "HIIHTO","PYORAILY","TARKKUUS"
    'areaId': None,
    'calendarType': 'all',
    'competitionOpen': 'ALL',
}

#{areaId can be {"id":1,"name":"Etelä-Pohjanmaa","abbreviation":"E-P"},{"id":2,"name":"FSO","abbreviation":"FSO"},{"id":3,"name":"Häme","abbreviation":"Häme"},{"id":6,"name":"Kaakko","abbreviation":"Kaak"},{"id":7,"name":"Kainuu","abbreviation":"Kain"},{"id":4,"name":"Keski-Pohjanmaa","abbreviation":"K-P"},{"id":5,"name":"Keski-Suomi","abbreviation":"K-S"},{"id":9,"name":"Lappi","abbreviation":"Lap"},{"id":10,"name":"Pohjois-Pohjanmaa","abbreviation":"P-P"},{"id":8,"name":"Päijät-Häme","abbreviation":"P-H"},{"id":12,"name":"Satakunta","abbreviation":"Sata"},{"id":11,"name":"Savo-Karjala","abbreviation":"S-K"},{"id":13,"name":"Uusimaa","abbreviation":"Uusi"},{"id":14,"name":"Varsinais-Suomi","abbreviation":"V-S"}]

f = get_url('https://irma.suunnistusliitto.fi/connect/CompetitionCalendarEndpoint/view',cookies,headers,front_page_json_data,"0")
data = json.loads(f)

# Parse each event and add to the calendar
for item in data:
    
    try:
        if ((item['competitionDate']) >= range_start.isoformat()) and ((item['competitionDate']) <= range_end.isoformat()):
            event = Event()
            event.name = item['competitionDayName']
            event.begin =datetime.strptime(item['competitionDate'], "%Y-%m-%dT%H:%M:%S.%f%z")+timedelta(hours=3)
            event.status = "CONFIRMED"  
            competition_id = item['dayId']
            event.url =f"{base_url}{competition_id}"
            event.make_all_day()
            event.description = f"Järjestävät seurat: {', '.join(club['name'] for club in item['organisingClubs'])}"
            event.categories = [item['sport']]
            print(str(event.begin) + event.name)
            calendar.events.add(event)
            
            if item['registrationAllowed'] is True:
                ilmodedis = Event()
                ilmodedis.begin = datetime.strptime(item['competitionDate'], "%Y-%m-%dT%H:%M:%S.%f%z")+timedelta(days=-10)+timedelta(hours=3)
                ilmodedis.name = "#Ilmodedis "+item['competitionDayName']
                ilmodedis.status = "TENTATIVE"
                print(ilmodedis.name)
                suburl= 'https://irma.suunnistusliitto.fi/connect/CompetitionEndpoint/viewCompetitionDay'
                competition_id = item['dayId']
                ilmodedis.url=f"{base_url}{competition_id}"
                ilmodedis.make_all_day()
                ilmodedis.categories = [item['sport']]
                json_data = { 'id': competition_id,}
                ff = get_url(suburl, cookies,headers,json_data,str(competition_id),)
                competitiondata = json.loads(ff)
                ilmodedis.begin = datetime.strptime(competitiondata['registrationPeriod']['firstRegistrationPeriodClosingDate'], "%Y-%m-%dT%H:%M:%S.%f%z")+timedelta(hours=3)
                ilmodedis.name = "Ilmodedis "+item['competitionDayName']
                ilmodedis.status = "TENTATIVE"
                ilmodedis.make_all_day()
                print(str(ilmodedis.begin) + ilmodedis.name)
                ilmodediscalendar.events.add(ilmodedis)
                               
    except (ValueError, arrow.parser.ParserError) as exception:
        LOGGER.warning("create_ics_error:%s:%s", event_name, str(exception))
   
# Write the calendar to an .ics file
with open('irma_events.ics', 'w', encoding='utf-8') as f:
    print(" generating competitioninfo")
    f.writelines(calendar)
with open('irma_ilmodedis.ics', 'w', encoding='utf-8') as fd:
    print(" generating ilmodedis")
    fd.writelines(ilmodediscalendar)
