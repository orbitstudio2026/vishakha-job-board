#!/usr/bin/env bash
# Downloads public job feeds from employer career sites (Greenhouse, Ashby, Lever) into scripts/gh, scripts/ash, scripts/lev.
# Run from the repo root: bash scripts/fetch_ats.sh
set -u
D="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$D/gh" "$D/ash" "$D/lev"
COMPANIES="hootsuite faire geotab ritual thinkific touchbistro wealthsimple koho clearco 1password nudge loopio trulioo waveapps cohere maple pelmorex sproutsocial klue fellow jobber benevity float drata rewind tealbook neofinancial hightouch attabotics stackadapt lightspeed docebo wattpad reddit spotify coinbase instacart lyft airbnb pinterest affirm stripe databricks okta twilio braze gitlab intercom"
for c in $COMPANIES; do
  curl -s -m 30 -o "$D/gh/$c.json"  "https://boards-api.greenhouse.io/v1/boards/$c/jobs?content=true"
  curl -s -m 30 -o "$D/ash/$c.json" "https://api.ashbyhq.com/posting-api/job-board/$c?includeCompensation=true"
  curl -s -m 30 -o "$D/lev/$c.json" "https://api.lever.co/v0/postings/$c?mode=json"
  echo "fetched $c"
done
