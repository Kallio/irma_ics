#!/bin/bash
set -e

# Config
initial_url="https://irma.suunnistusliitto.fi/public/competitioncalendar/list?year=upcoming&tab=competition&area=all&competition=ALL"
api_url="https://irma.suunnistusliitto.fi/connect/CompetitionCalendarEndpoint/view"
suburl="https://irma.suunnistusliitto.fi/connect/CompetitionEndpoint/viewCompetitionDay"
cookies_file="cookies.txt"
html_file="irma_init.html"
cache_dir="cache"
cache_expiry=2880  # in minutes (2 days)

# Clean previous run
mkdir -p "$cache_dir"/"$cache_dir"
rm -f "$cache_dir"/"$html_file"

# Step 1: Fetch initial HTML page and save cookies
fetch_fresh_cookies() {
#  curl -s -L -c "$cookies_file" "$initial_url" -o "$html_file"
  csrf_token=$(curl -s -L -c "$cookies_file" "$initial_url"|grep -oP 'name="_csrf" content="\K[^"]+' || grep -oP 'name="csrf-token" content="\K[^"]+')
  if [ -z "$csrf_token" ]; then
    echo "ERROR: CSRF token not found in HTML."
    exit 1
  fi
}

# Check if session is valid
check_session_valid() {
  local test_payload='{"year":null,"month":"1","upcoming":"ONE_WEEK","disciplines":[],"areaId":null,"calendarType":"all","competitionOpen":"ALL"}'
  local response

  response=$(curl -s -X POST "$api_url" \
    -H "Content-Type: application/json" \
    -H "X-CSRF-TOKEN: $csrf_token" \
    -b "$cookies_file" \
    -d "$test_payload")

  echo "$response" | jq -e 'type=="array"' > /dev/null
}

# Refresh cookies if missing or session invalid
if [ ! -s "$cookies_file" ]; then
  fetch_fresh_cookies
else
  csrf_token=$(curl -s -L -c "$cookies_file" "$initial_url" |grep -oP 'name="_csrf" content="\K[^"]+' || grep -oP 'name="csrf-token" content="\K[^"]+' )
  if ! check_session_valid; then
    echo "Session expired or invalid — refreshing cookies..."
    fetch_fresh_cookies
  fi
fi

# Step 2: Define JSON payload
front_json='{
  "year": null,
  "month": "1",
  "upcoming": "ONE_WEEK",
  "disciplines": [],
  "areaId": null,
  "calendarType": "all",
  "competitionOpen": "ALL"
}'

# Step 3: Fetch with cache function
echo "Fetching competition data..."
fetch_cached() {
  local url="$1"
  local identifier="$2"
  local json_data="$3"
  local cache_file hash

  hash=$(echo -n "$url$identifier" | sha256sum | awk '{print $1}')
  cache_file="$cache_dir/$hash"

  if [ -f "$cache_file" ]; then
    if find "$cache_file" -mmin -"$cache_expiry" | grep -q "$cache_file"; then
      cat "$cache_file"
      return
    fi
  fi

  local response
  response=$(curl -s --compressed -X POST "$url" \
    -H 'User-Agent: Mozilla/5.0' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -H "X-CSRF-TOKEN: $csrf_token" \
    -H "Referer: $initial_url" \
    -H 'Origin: https://irma.suunnistusliitto.fi' \
    -b "$cookies_file" \
    -d "$json_data")

  echo "$response" > "$cache_file"
  echo "$response"
}

response=$(fetch_cached "$api_url" "competition_calendar" "$front_json")

# Step 4: Output ICS files
> irma_events.ics
> irma_ilmodedis.ics

cat >> irma_events.ics <<EOF
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//IRMA//EN
EOF

cat >> irma_ilmodedis.ics <<EOF
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//IRMA//EN
EOF

# Step 5: Process events
echo "$response" | jq -c '.[]' | while read -r event; do
  comp_date=$(echo "$event" | jq -r '.competitionDate')
  comp_name=$(echo "$event" | jq -r '.competitionDayName')
  comp_id=$(echo "$event" | jq -r '.dayId')
  clubs=$(echo "$event" | jq -r '[.organisingClubs[].name] | join(", ")')

  comp_ts=$(date -d "$comp_date" +%s)
  comp_ts_offset=$(( comp_ts + 10800 ))
  comp_date_str=$(date -d "@$comp_ts_offset" +"%Y%m%d")
  url="https://irma.suunnistusliitto.fi/public/competition/view/$comp_id"

  cat >> irma_events.ics <<EOF
BEGIN:VEVENT
UID:${comp_id}@irma
SUMMARY:${comp_name}
DTSTART;VALUE=DATE:${comp_date_str}
DESCRIPTION:J\ärjest\äv\ät seurat: ${clubs}\\n${url}
URL:${url}
STATUS:CONFIRMED
END:VEVENT
EOF

  reg_allowed=$(echo "$event" | jq -r '.registrationAllowed')
  if [ "$reg_allowed" = "true" ]; then
    reg_json="{\"id\": $comp_id, \"discipline\": \"SUUNNISTUS\"}"
    reg_response=$(fetch_cached "$suburl" "$comp_id" "$reg_json")
    reg_date=$(echo "$reg_response" | jq -r '.registrationPeriod.firstRegistrationPeriodClosingDate')

    if [ "$reg_date" != "null" ]; then
      reg_ts=$(date -d "$reg_date" +%s)
      reg_ts_offset=$(( reg_ts + 10800 ))
      reg_date_str=$(date -d "@$reg_ts_offset" +"%Y%m%d")

      cat >> irma_ilmodedis.ics <<EOF
BEGIN:VEVENT
UID:ilmodedis-${comp_id}@irma
SUMMARY:Ilmodedis ${comp_name}
DTSTART;VALUE=DATE:${reg_date_str}
DESCRIPTION:J\ärjest\äv\ät seurat: ${clubs}\\n${url}
STATUS:TENTATIVE
END:VEVENT
EOF
    fi
  fi
done

echo "END:VCALENDAR" >> irma_events.ics
echo "END:VCALENDAR" >> irma_ilmodedis.ics

echo "ICS files written: irma_events.ics and irma_ilmodedis.ics"
