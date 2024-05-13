# irma_ics
Convert irma calendar (https://irma.suunnistusliitto.fi/irma/public/competitioncalendar/view)  to caldav format 
Usage instructions

    python3 -m venv venv
    source venv/bin/activate
    pip install requests ics
    LOGLEVEL=DEBUG python3 irma_ics.py ilmodedis
  or
  
    LOGLEVEL=DEBUG python3 irma_ics.py events 

Final usage might be like

    python3 irma_ics.py events > irma_evemts.ics && python3 irma_ics.py events > irma_ilmodedis.ics ; scp irma*.ics suunnistaja@server.metsä:/var/www/html/calendars/

Known bugs/features
  - Output doesn't fully follow the standard. (It works good enough with OSX Sonoma ical.app anyhow)
  - Irma user interface might get refresh soon and then the parsing functionality will fail.
  - Do not hammer the IRMA server. once in a week update might be more than enough for calendar updates
  - This tool doesn't check bike or other special orienteering modes, maybe in future?
  - IRMA has a region limits but this is intended for my personal use and I like to know all events ( you never know if you happen to visit in  other region)
  - I'm not a coder. I can hack some things together ( and I have friends that can help)  and this is intended to be more like inspirational code for someone that can create more robust setup  
