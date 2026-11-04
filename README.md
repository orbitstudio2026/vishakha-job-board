# Vishakha's Toronto job board

Toronto / GTA and remote-Canada openings for account management, customer success and digital marketing roles, with salary and place of work for every job. Pulled 4 Nov 2026.

## What's here

| Path | What it is |
|---|---|
| `docs/index.html` | The dashboard: job table, preference tags, salary and place-of-work filters, compensation chart. Served by GitHub Pages. |
| `docs/data/jobs.json` | The data the dashboard reads (206 jobs). |
| `data/Vishakha_Toronto_Jobs_Salary.xlsx` | Excel export, with a Method sheet explaining each column. |
| `data/Vishakha_Toronto_Jobs_Salary.csv` | The same rows as CSV (imports into Google Sheets). |
| `scripts/` | The scripts that collected and scored the jobs. |

## Tracking applications

Each job row has a circle in the **Applied** column. Tick it after applying, and the job is marked Applied with the date and appears under the **Applied** tab. Ticks are saved in the browser you use, so they stay between visits on that device. Use **Back up list** in the "My applications" card to save a copy, and **Restore from backup** to load it on another browser or device.

## Filters

- **Work type chips:** Full-time, Part-time, Contract, and Remote, Hybrid, On-site. Pick several in one group to see any of them.
- Other filters: salary range, pay frequency, place of work, category, source, and preference tags.

## Opening the dashboard

- **GitHub Pages:** Settings → Pages → Source: "Deploy from a branch", Branch `main`, folder `/docs`. The page appears at `https://<your-user>.github.io/<repo-name>/`.
- **On your computer:** `cd docs && python3 -m http.server`, then open http://localhost:8000. Opening `index.html` directly from Finder won't load the data because browsers block local file reads.

## Salary rules

- Every salary comes from the posting itself: the employer's own career site first, then Job Bank, then Indeed or another board.
- `Salary Verification Status` separates **Employer-disclosed (verified)**, meaning the salary is on the employer's site, from **Board-advertised (not verified)**, meaning it's on a job board only.
- Jobs with no Canadian salary show **Salary Not Disclosed** and stay in the list.
- No salary is invented or AI-estimated. Third-party averages (Glassdoor, Payscale) appear only as a labelled reference, never as a job's salary.
- Hourly pay is converted to a yearly figure as rate × weekly hours × 52, using the posted hours, or 37.5 h/week when none are given. The result is labelled as an estimate.

## Screening and scoring

- **Sales-intensity screen:** roles with commission are scored for quota, commission, OTE pay, prospecting and closing. High scorers are screened out of the shortlist but kept in the data.
- **Match score:** category fit + resume skills + location + level, minus points for sales intensity. Salary does not change the score.

## Refreshing the data

Run these from the `scripts/` folder, in this order:

```bash
bash fetch_ats.sh          # employer feeds: Greenhouse, Ashby, Lever
python3 collect.py         # filter to relevant Toronto roles
python3 wd.py              # Workday employers (TD, Manulife, Sun Life, CIBC, BMO, RBC, MLSE, Thomson Reuters)
python3 jobbank.py         # Job Bank listing search
python3 jb_detail.py       # Job Bank posting details (address, hours, work setting)
python3 build.py           # merge, salary normalisation, screen, score
python3 export.py ../data  # CSV + Excel
cp jobs_flat.json ../docs/data/jobs.json
```

`scripts/indeed/` holds the Indeed postings gathered through the Indeed connector. Indeed doesn't allow automated scraping, so refresh those by hand.
