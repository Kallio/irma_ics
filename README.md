# irma_ics
Convert irma calendar [https://irma.suunnistusliitto.fi/public/competitioncalendar/list](https://irma.suunnistusliitto.fi/public/competitioncalendar/list)  to caldav format 
Usage instructions

    python3 -m venv venv
    source venv/bin/activate
    pip install requests ics pytz
    LOGLEVEL=DEBUG python3 irma_ics.py ilmodedis
  or
  
    LOGLEVEL=DEBUG python3 irma_ics.py  

Known bugs/features
  - Output doesn't fully follow the standard. (It works good enough with OSX Sonoma ical.app anyhow)
  - Do not hammer the IRMA server. once in a week update might be more than enough for calendar updates ( Cache functionality tries to avoid the problem in the code anyways)
  - This tool doesn't check bike or other special orienteering modes, maybe in future?
  - IRMA has a region limits but this is intended for my personal use and I like to know all events ( you never know if you happen to visit in  other region)
  - I'm not a coder. I can hack some things together ( and I have friends that can help)  and this is intended to be more like inspirational code for someone that can create more robust setup  
