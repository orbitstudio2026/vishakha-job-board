"""Build the job dataset with salary + compensation intelligence.
Inputs: sel.json (Greenhouse/Ashby/Lever feeds), wd_sel.json (Workday feeds).
Output: jobs.json
"""
import json, os, re, statistics

S = os.path.dirname(os.path.abspath(__file__))
FETCHED = "2026-11-04"
raw = json.load(open(S + "/sel.json")) + json.load(open(S + "/wd_sel.json"))

ATS_NAME = {"greenhouse": "Greenhouse", "ashby": "Ashby", "lever": "Lever", "workday": "Workday"}
CO_NAME = {"stackadapt": "StackAdapt", "gitlab": "GitLab", "airbnb": "Airbnb", "stripe": "Stripe", "lyft": "Lyft",
           "faire": "Faire", "braze": "Braze", "affirm": "Affirm", "okta": "Okta", "reddit": "Reddit",
           "instacart": "Instacart", "pinterest": "Pinterest", "databricks": "Databricks", "clearco": "Clearco",
           "rewind": "Rewind", "loopio": "Loopio", "docebo": "Docebo", "klue": "Klue", "cohere": "Cohere",
           "1password": "1Password", "jobber": "Jobber", "float": "Float", "wealthsimple": "Wealthsimple",
           "trulioo": "Trulioo", "spotify": "Spotify", "pelmorex": "Pelmorex"}

# ---------------- Location preferences (Toronto / GTA, or remote within Canada) ----------------
GTA = r"toronto|etobicoke|north york|scarborough|markham|mississauga|oakville|burlington|whitby|vaughan|brampton|richmond hill|pickering|ajax|oshawa|milton"
def location_ok(loc):
    l = loc.lower()
    if re.search(GTA, l): return True
    if re.search(r"remote[^|;]*canada|canada[^|;]*remote|^canada$|^remote canada|\bcanada\b", l) and not re.search(r"^(calgary|vancouver|montr)", l):
        return True
    if l.strip() == "ontario" or l.strip() == "ontario, canada": return True
    return False

# ---------------- Exclusions: seniority / irrelevant functions ----------------
EXCL_TITLE = re.compile(r"\b(director|vp|avp|chief|head of|principal|staff|architect|engineer\w*|developer|data science|"
                        r"compensation analyst|privacy|graphic designer|investment|intern|co-op|sr\. manager|senior manager|"
                        r"senior director|team lead|scientist|product owner|tech lead|sourcing|enterprise account executive|strategic\s+core|strategic\s+account|named core|"
                        r"emerging enterprise|platform administrator|revenue operations)\b", re.I)

# ---------------- Categories ----------------
CATS = [
    ("Customer / Client Success", r"customer success|client success|founder success|client engagement"),
    ("Account Management", r"account manager|client account manager|client partner|key account"),
    ("Relationship Management", r"relationship manager"),
    ("Digital & Performance Marketing", r"seo|search engine|paid search|paid media|ppc|performance marketing|growth marketing|growth media|digital channels|digital marketing"),
    ("Social Media", r"social media"),
    ("Marketing (Brand / Product / Lifecycle / Ops)", r"marketing|brand|demand gen|content|campaign|partnerships"),
    ("CRM & Analytics", r"crm|analyst|insights"),
    ("Client Service / Customer Experience", r"client service|customer experience|client associate|customer service|support specialist|client relations|client services|implementation"),
    ("Sales / Account Executive", r"account executive|business development|sales"),
]
def category(title):
    t = title.lower()
    if re.search(r"account executive", t): return "Sales / Account Executive"
    for name, rx in CATS:
        if re.search(rx, t): return name
    return "Other"

# ---------------- Salary extraction ----------------
NUM = r"\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?\s?[kK]|\d+(?:\.\d+)?"
def num(s):
    s = s.strip().replace(" ", "").replace(",", "")
    if s.lower().endswith("k"): return float(s[:-1]) * 1000
    return float(s)

def extract_salary(j):
    """Return dict(min,max,currency,frequency,basis,advertised) or None. Only Canada / CAD figures accepted."""
    t = j.get("text") or ""
    comp = j.get("comp")
    # 1. Ashby / Lever structured compensation (employer-entered on their career page)
    if comp:
        m = re.search(r"CA\$\s?(" + NUM + r")\s?[–-]\s?CA\$\s?(" + NUM + r")", comp)
        if m:
            return dict(min=num(m.group(1)), max=num(m.group(2)), currency="CAD", frequency="Annual",
                        basis="Base salary", advertised=comp.split(" • ")[0])
        m = re.search(r"CAD\s+(\d+)-(\d+)\s+(\w+)", comp)
        if m:
            return dict(min=float(m.group(1)), max=float(m.group(2)), currency="CAD",
                        frequency="Hourly" if "hour" in m.group(3).lower() else "Annual", basis="Base salary", advertised=comp)
    pats = [
        (r"expected pay range for this position is:?\s*\$(" + NUM + r")\s*-\s*\$(" + NUM + r")", None),
        (r"base salary for this position is:?\s*\$(" + NUM + r")\s*-\s*\$(" + NUM + r")", None),
        (r"For Ontario, Canada, the base compensation range for this role is \$(" + NUM + r") CAD - \$(" + NUM + r") CAD", None),
        (r"Compensation Range/Rate:\s*\$(" + NUM + r")\s*-\s*\$?(" + NUM + r")\s*annual", None),
        (r"Salary\s*:\s*\$(" + NUM + r")\s*-\s*\$(" + NUM + r")", None),
        # Okta-style: Canada-specific line
        (r"(?:base salary|OTE \(On Target Earning\)) range for this position for candidates located in Canada is between:\s*\$(" + NUM + r")\s*[—–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Canada[^$]{0,40}Base Salary Band\s*\$(" + NUM + r")\s*[—–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Base Salary Band\s*\$(" + NUM + r")\s*[—–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Canada Annual Pay Range\s*\$(" + NUM + r")\s*[—–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Toronto area is (?:CAD )?\$(" + NUM + r")\s*(?:CAD)?\s*-\s*(?:CAD )?\$(" + NUM + r")", None),
        (r"Canada, the pay range[^$]*CA\$(" + NUM + r")\s*-\s*CA\$(" + NUM + r")/year", None),
        (r"CAN base pay range per year:\s*\$(" + NUM + r")\s*-\s*\$(" + NUM + r")", None),
        (r"CAN\s+\$(" + NUM + r")\s*[—–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Canada base range for this position is \$(" + NUM + r")\s*[–-]\s*\$(" + NUM + r")\s*CAD", None),
        (r"Canada-based roles only: The annual base salary for this role is between \$(" + NUM + r") CAD and \$(" + NUM + r") CAD", None),
        (r"minimum annual salary of \$(" + NUM + r"), a midpoint of \$[\d,]+,? and a maximum salary of \$(" + NUM + r")", None),
        (r"Salary range is expected to be between \$(" + NUM + r")\s*CAD\s*-\s*\$(" + NUM + r")", "CADONLY"),
        (r"Salary Range:\s*(\d{2,3},\d{3})/[\d ]+\s*-\s*(\d{2,3},\d{3})", None),
        (r"annualized base salary range for this role is \$(" + NUM + r") to \$(" + NUM + r")", None),
        (r"Pay Details:\s*(?:[\d ]+\$/)?\$?(" + NUM + r")\s*-\s*(?:[\d ]+\$/)?\$?(" + NUM + r")", None),
    ]
    for p, flag in pats:
        m = re.search(p, t, re.I)
        if m:
            lo, hi = num(m.group(1)), num(m.group(2))
            freq = "Hourly" if hi < 200 else "Annual"
            snippet = t[m.start():m.end()].strip()
            basis = "OTE: on-target earnings (base + variable)" if re.search(r"\bOTE\b", snippet) else "Base salary"
            if freq == "Hourly":
                snippet = re.sub(r"\s+", " ", snippet) + " per hour"
            return dict(min=lo, max=hi, currency="CAD", frequency=freq, basis=basis, advertised=re.sub(r"\s+", " ", snippet)[:220])
    # Jobber fixed structure
    m = re.search(r"base salary of \$(" + NUM + r") and a commission of \$(" + NUM + r"), for an On-Target Earnings \(OTE\) of \$(" + NUM + r")", t)
    if m:
        b = num(m.group(1))
        return dict(min=b, max=b, currency="CAD", frequency="Annual", basis="Base salary (fixed)",
                    advertised=f"Fixed base ${b:,.0f} + ${num(m.group(2)):,.0f} commission = ${num(m.group(3)):,.0f} OTE",
                    ote=num(m.group(3)))
    # Faire single hourly figure
    m = re.search(r"Canada: The starting pay for this role is \$(\d+(?:\.\d+)?) CAD per hour", t)
    if m:
        v = float(m.group(1))
        return dict(min=v, max=v, currency="CAD", frequency="Hourly", basis="Starting base pay", advertised=m.group(0))
    return None

def us_only_salary(t):
    return bool(re.search(r"USA-based roles only|United States Salary Range|Referenced Salary Location [A-Za-z ]+, (Massachusetts|Michigan)", t or ""))

def weekly_hours(t):
    m = re.search(r"Hours:\s*(\d+(?:\.\d+)?)", t or "")
    return float(m.group(1)) if m else None

# ---------------- Compensation details ----------------
def comp_details(j, sal):
    t = (j.get("text") or "")
    comp = j.get("comp") or ""
    d = {}
    # bonus
    m = re.search(r"CA\$[\d.,K]+\s?[–-]\s?CA\$[\d.,K]+ Bonus|CA\$[\d.,K]+ Bonus", comp)
    if m: d["bonus"] = m.group(0)
    elif "Offers Bonus" in comp: d["bonus"] = "Bonus offered (amount not disclosed)" + (" — " + comp.split("• ")[-1] if re.search(r"\d+%$", comp) else "")
    elif re.search(r"discretionary variable compensation|eligible for (?:a |an )?(?:annual )?bonus|bonus (?:program|plan)|may also be eligible for bonus|incentive pay|not inclusive of potential equity offering, bonus", t, re.I):
        d["bonus"] = "Bonus / variable pay eligible (amount not disclosed)"
    # commission
    m = re.search(r"CA\$[\d.,K]+\s?[–-]\s?CA\$[\d.,K]+ Commission|CA\$[\d.,K]+ Commission", comp)
    if m: d["commission"] = m.group(0)
    elif "Offers Commission" in comp: d["commission"] = "Commission offered (amount not disclosed)"
    elif sal and sal.get("ote"): d["commission"] = f"${sal['ote']-sal['min']:,.0f} commission at target (uncapped)"
    elif re.search(r"commission", t, re.I): d["commission"] = "Commission component mentioned in posting"
    elif re.search(r"\bOTE\b|On Target Earning", t): d["commission"] = "Variable pay via OTE (on-target earnings)"
    # equity
    if "Offers Equity" in comp or re.search(r"\b(equity|RSUs?|stock options|share purchase)\b", t, re.I):
        d["equity"] = "Equity / share plan mentioned"
    # benefits
    ben = []
    for label, rx in [("Health & dental", r"dental|health (?:benefits|insurance|package|coverage)|extended health"),
                      ("Retirement / pension matching", r"rrsp|pension|retirement|group rrsp|dpsp"),
                      ("Paid time off", r"vacation|paid time off|\bPTO\b|time off"),
                      ("Parental leave", r"parental leave|maternity|parental top"),
                      ("Wellness / learning stipend", r"stipend|wellness (?:allowance|budget|account)|learning budget|education reimbursement"),
                      ("Hybrid / remote flexibility", r"hybrid|work from home|remote-first|flexib")]:
        if re.search(rx, t, re.I): ben.append(label)
    if ben: d["benefits"] = ", ".join(ben)
    return d

# ---------------- Sales-intensity screening ----------------
def sales_intensity(title, t, cd):
    s = 0; why = []
    def add(n, w):
        nonlocal s; s += n; why.append(w)
    tl = title.lower()
    if re.search(r"account executive|business development|\bsdr\b|\bbdr\b|hunter|sales", tl): add(40, "sales title")
    if re.search(r"\bquota", t, re.I): add(15, "quota")
    if "commission" in cd: add(15, "commission")
    if re.search(r"\bOTE\b|on[- ]target earning", t, re.I): add(10, "OTE pay")
    if re.search(r"cold[- ]call|outbound|prospecting|prospect(?:s)? ", t, re.I): add(15, "prospecting / outbound")
    if re.search(r"net[- ]new|new logo|new business|hunt", t, re.I): add(10, "new-business hunting")
    if re.search(r"close deals|closing deals|close new|full[- ]cycle sales|full sales cycle", t, re.I): add(10, "closing deals")
    # commission share of base pay (when amounts are disclosed)
    m = re.search(r"\$([\d,]+)\s?K?\s?commission|CA\$([\d.,]+)K?(?:\s?[–-]\s?CA\$([\d.,]+)K?)? Commission", cd.get("commission",""), re.I)
    if m and cd.get("_base"):
        vals=[x for x in m.groups() if x]
        v=float(vals[-1].replace(",",""))
        if v < 1000: v*=1000
        if v/cd["_base"] >= 0.30: add(25, f"commission ≈{round(100*v/cd['_base'])}% of base")
    s = min(s, 100)
    lvl = "High" if s >= 60 else "Medium" if s >= 30 else "Low"
    return s, lvl, why

# ---------------- Match engine (inferred from resume) ----------------
CAT_W = {"Account Management": 30, "Customer / Client Success": 30, "Digital & Performance Marketing": 30,
         "Relationship Management": 22, "Marketing (Brand / Product / Lifecycle / Ops)": 22, "Social Media": 22,
         "CRM & Analytics": 22, "Client Service / Customer Experience": 16, "Sales / Account Executive": 14, "Other": 8}
SKILLS = [r"\bcrm\b", r"salesforce", r"\bseo\b", r"ppc|paid search|google ads|sem\b", r"email marketing|lifecycle",
          r"social media", r"lead gen", r"account management|manage (?:a )?portfolio|book of business", r"data analysis|analytics|data-driven",
          r"digital marketing", r"stakeholder", r"campaign", r"forecast", r"\bsmb\b|small (?:and|&) medium|small business",
          r"telecom|telus", r"hubspot|genesys", r"retention|renewal|churn", r"onboard", r"relationship"]
def level_fit(title):
    tl = title.lower()
    if re.search(r"\bassociate\b|representative|specialist i\b|coordinator", tl) and not re.search(r"senior|sr\.", tl): return 8, "Below her level"
    if re.search(r"senior|sr\.|lead\b", tl): return 15, "Stretch / senior"
    return 20, "Good level"

def match(j, cat, inten, loc):
    t = j.get("text") or ""
    sc = CAT_W.get(cat, 8)
    hits = [rx for rx in SKILLS if re.search(rx, t, re.I)]
    sc += min(len(hits), 10) * 3.5
    sc += 15  # location already passes Toronto/GTA/remote-Canada filter
    lf, lfl = level_fit(j["title"])
    sc += lf
    if inten == "High": sc -= 20
    elif inten == "Medium": sc -= 8
    return int(max(0, min(100, round(sc)))), len(hits), lfl

def work_mode(j):
    t = (j.get("text") or "") + " " + (j.get("loc") or "")
    rt = (j.get("remote") or "") if isinstance(j.get("remote"), str) else ""
    wp = (j.get("wp") or "")
    if rt in ("Onsite",): return "On-site"
    if rt == "Office Focused": return "Hybrid (office-focused)"
    if str(wp).lower() == "hybrid": return "Hybrid"
    if str(wp).lower() == "remote" or j.get("remote") is True or re.search(r"remote", j.get("loc") or "", re.I): return "Remote (Canada)"
    if str(wp).lower() == "hybrid" or re.search(r"hybrid|working arrangement hybrid|\bhub\b", t, re.I): return "Hybrid"
    if re.search(r"on-?site|in[- ]office", t, re.I): return "On-site"
    return mode_from_text(t)

def employment_type(structured, title, text):
    """Full-time / Part-time / Contract / Not stated, from a structured field first, then the title, then the posting text."""
    st = (structured or "").lower()
    tl = (title or "").lower()
    tx = (text or "").lower()
    if re.search(r"contract|fixed[- ]term|temporary|\bsta\b|\d+[- ](?:month|year)", tl): return "Contract"
    if "part" in st: return "Part-time"
    if re.search(r"contract|temporary|fixed", st): return "Contract"
    if "full" in st or "permanent" in st: return "Full-time"
    if re.search(r"\bpart[- ]time\b", tx) and not re.search(r"\bfull[- ]time\b", tx): return "Part-time"
    if re.search(r"\b(?:\d+[- ]month|fixed[- ]term|contract (?:role|position)|temporary (?:role|position)|1\.5[- ]year contract)\b", tx): return "Contract"
    if re.search(r"\bfull[- ]time\b|\bpermanent\b|\bregular,? full", tx): return "Full-time"
    return "Not stated"

def mode_from_text(t):
    if re.search(r"\b(\d|two|three|four)\s+days?\s+(?:a|per)\s+week\s+(?:in|at)\s+(?:the|our)?\s*office|\bhybrid\b", t, re.I): return "Hybrid"
    if re.search(r"fully remote|100% remote|remote[- ]first|work from anywhere|remote within canada|this (?:role|position) is remote", t, re.I): return "Remote (Canada)"
    if re.search(r"on-?site five days|in[- ]person|work location: in person|on-?site|in the office five days", t, re.I): return "On-site"
    return "Not stated"

def clean_loc(loc):
    loc = re.sub(r"\s+", " ", loc).strip()
    return loc[:90]

# ---------------- Build ----------------
seen = {}; jobs = []
for j in raw:
    if not location_ok(j["loc"]): continue
    if EXCL_TITLE.search(j["title"]): continue
    key = (j["co"], re.sub(r"\s+"," ",j["title"]).strip().lower())
    if key in seen:
        prev = seen[key]
        if prev is not None and clean_loc(j["loc"]) not in prev["location"]:
            prev["location"] = (prev["location"] + " · " + clean_loc(j["loc"]))[:160]
        continue
    seen[key] = None
    t = j.get("text") or ""
    sal = extract_salary(j)
    cat = category(j["title"])
    if cat == "Other": continue
    cd = comp_details(j, sal)
    if sal: cd["_base"] = (sal["min"]+sal["max"])/2 if sal["frequency"]=="Annual" else None
    inten, lvl, why = sales_intensity(j["title"], t, cd)
    ms, nskill, lfl = match(j, cat, lvl, j["loc"])
    rec = dict(
        emp_type=employment_type(j.get("timeType") or j.get("emp"), j["title"], t),
        id=len(jobs) + 1, title=j["title"].strip(), company=CO_NAME.get(j["co"], j["co"]), location=clean_loc(j["loc"]),
        work_mode=work_mode(j), category=cat, url=j["url"], posted=(str(j.get("updated") or "")[:10] if isinstance(j.get("updated"), str) else ""),
        match=ms, skill_hits=nskill, level_fit=lfl,
        sales_intensity=inten, sales_level=lvl, sales_reasons=why,
        shortlist=(lvl != "High"),
        bonus=cd.get("bonus", ""), commission=cd.get("commission", ""), equity=cd.get("equity", ""), benefits=cd.get("benefits", ""),
        ats=ATS_NAME[j["ats"]],
    )
    if sal:
        ann_note = ""
        if sal["frequency"] == "Hourly":
            hrs = weekly_hours(t)
            h = hrs if hrs else 37.5
            ann_lo, ann_hi = sal["min"] * h * 52, sal["max"] * h * 52
            ann_note = (f"Estimate: hourly rate × {h:g} h/week (stated in posting) × 52 weeks" if hrs
                        else "Estimate: hourly rate × 37.5 h/week (assumed, not stated) × 52 weeks")
        elif sal["frequency"] == "Monthly":
            ann_lo, ann_hi = sal["min"] * 12, sal["max"] * 12
            ann_note = "Estimate: monthly × 12"
        else:
            ann_lo, ann_hi = sal["min"], sal["max"]
        rec.update(salary_disclosed=True, sal_min=sal["min"], sal_max=sal["max"], currency="CAD", frequency=sal["frequency"],
                   pay_basis=sal["basis"], advertised=sal["advertised"], annual_min=round(ann_lo), annual_max=round(ann_hi),
                   annual_note=ann_note,
                   salary_source=f"Employer career page ({ATS_NAME[j['ats']]} posting)",
                   salary_status="Employer-disclosed · verified on employer posting " + FETCHED)
    else:
        note = "Only a US-dollar range is published; no Canadian range given" if us_only_salary(t) else ""
        rec.update(salary_disclosed=False, sal_min=None, sal_max=None, currency="", frequency="", pay_basis="",
                   advertised="Salary Not Disclosed", annual_min=None, annual_max=None, annual_note=note,
                   salary_source="—", salary_status="Salary Not Disclosed")
    jobs.append(rec); seen[key] = rec

# ---------------- Job Bank (Government of Canada) listings, incl. Indeed / Talent.com partner postings ----------------
JB_FREQ = {"annually": "Annual", "hourly": "Hourly", "monthly": "Monthly", "weekly": "Weekly", "biweekly": "Biweekly"}
def jb_salary(s):
    m = re.search(r"\$([\d,]+(?:\.\d+)?)(?:\s*(?:to|–|-|—)\s*\$([\d,]+(?:\.\d+)?))?\s*(?:CAD\s*)?(annually|hourly|monthly|biweekly|weekly)", s)
    if not m: return None
    lo = float(m.group(1).replace(",", "")); hi = float((m.group(2) or m.group(1)).replace(",", ""))
    freq = JB_FREQ[m.group(3)]
    # Job Bank occasionally mislabels an annual figure as hourly; treat implausible hourly values as annual
    if freq == "Hourly" and lo > 500: freq = "Annual"
    if freq == "Monthly" and lo > 20000: freq = "Annual"
    return lo, hi, freq, "to be negotiated" in s

jb_path = S + "/jb/details.json"
jb = json.load(open(jb_path)) if os.path.exists(jb_path) else []
for x in jb:
    title = x["title"].strip()
    title = title[:1].upper() + title[1:]
    key = (x["business"].lower(), title.lower())
    if key in seen: continue
    t = x.get("text") or ""
    cat = category(title)
    if cat == "Other": continue
    pseudo = {"title": title, "text": t, "loc": x["location"], "co": x["business"], "comp": None}
    cd = comp_details(pseudo, None)
    sal = jb_salary(x["salary"] or "")
    if sal: cd["_base"] = (sal[0] + sal[1]) / 2 if sal[2] == "Annual" else None
    inten, lvl, why = sales_intensity(title, t, cd)
    ms, nskill, lfl = match(pseudo, cat, lvl, x["location"])
    wl = {"On site": "On-site", "Hybrid": "Hybrid", "Remote": "Remote (Canada)"}.get(x.get("work_location"), "") or mode_from_text(t)
    src = x["source"] or "Job Bank"
    if src == "Job Bank":
        s_src, s_stat, board = "Official job posting (Job Bank, Government of Canada)", "Employer-advertised on Job Bank · not cross-checked on employer site", "Job Bank"
    elif src == "indeed.com":
        s_src, s_stat, board = "Indeed job listing (via Job Bank)", "Employer-advertised on Indeed · not cross-checked on employer site", "Indeed"
    else:
        s_src, s_stat, board = f"{src} job listing (via Job Bank)", f"Employer-advertised on {src} · not cross-checked on employer site", src
    rec = dict(emp_type=employment_type(x.get("terms"), title, t), id=len(jobs) + 1, title=title, company=x["business"], location=x["location"].replace(" (ON)", ", ON"),
               address=x.get("address", ""), work_mode=wl, category=cat, url=x.get("source_url") or x["url"], board_url=x["url"],
               posted="", posted_text=x.get("date", ""), match=ms, skill_hits=nskill, level_fit=lfl,
               sales_intensity=inten, sales_level=lvl, sales_reasons=why, shortlist=(lvl != "High"),
               bonus=cd.get("bonus", ""), commission=cd.get("commission", ""), equity=cd.get("equity", ""), benefits=cd.get("benefits", ""),
               ats=board, hours_text=x.get("hours_text", ""), terms=x.get("terms", ""))
    if sal:
        lo, hi, freq, neg = sal
        hrs = x.get("hours")
        if freq == "Hourly":
            h = hrs or 37.5
            a_lo, a_hi = lo * h * 52, hi * h * 52
            note = (f"Estimate: hourly rate × {h:g} h/week (stated in posting) × 52 weeks" if hrs else "Estimate: hourly rate × 37.5 h/week (assumed, not stated) × 52 weeks")
        elif freq == "Monthly": a_lo, a_hi, note = lo * 12, hi * 12, "Estimate: monthly × 12"
        elif freq == "Biweekly": a_lo, a_hi, note = lo * 26, hi * 26, "Estimate: biweekly × 26 pay periods"
        elif freq == "Weekly": a_lo, a_hi, note = lo * 52, hi * 52, "Estimate: weekly × 52"
        else: a_lo, a_hi, note = lo, hi, ""
        rec.update(salary_disclosed=True, sal_min=lo, sal_max=hi, currency="CAD", frequency=freq,
                   pay_basis="Base salary" + (" (to be negotiated)" if neg else ""), advertised=x["salary"],
                   annual_min=round(a_lo), annual_max=round(a_hi), annual_note=note, salary_source=s_src, salary_status=s_stat)
    else:
        rec.update(salary_disclosed=False, sal_min=None, sal_max=None, currency="", frequency="", pay_basis="",
                   advertised="Salary Not Disclosed", annual_min=None, annual_max=None, annual_note="",
                   salary_source="—", salary_status="Salary Not Disclosed")
    jobs.append(rec); seen[key] = rec

# ---------------- Indeed (via the user's Indeed connector) ----------------
import glob as _g
for f in sorted(_g.glob(S + "/indeed/batch*.json")):
    for x in json.load(open(f)):
        title = x["title"]; co = x["company"]
        key = (co.lower(), title.lower())
        if key in seen: continue
        t = x.get("text", "")
        cat = category(title)
        if cat == "Other": continue
        pseudo = {"title": title, "text": t, "loc": x["location"], "co": co, "comp": None}
        cd = comp_details(pseudo, None)
        sal = jb_salary(x.get("salary", "") or "")
        if sal: cd["_base"] = (sal[0] + sal[1]) / 2 if sal[2] == "Annual" else None
        inten, lvl, why = sales_intensity(title, t, cd)
        ms, nskill, lfl = match(pseudo, cat, lvl, x["location"])
        wl = {"On site": "On-site", "Hybrid": "Hybrid", "Remote": "Remote (Canada)"}.get(x.get("work"), "") or mode_from_text(t)
        rec = dict(emp_type=employment_type(x.get("type"), title, t), id=len(jobs) + 1, title=title, company=co, location=x["location"], address=x.get("address", ""), work_mode=wl,
                   category=cat, url=x["url"], board_url="", posted="", posted_text=x.get("posted", ""), match=ms, skill_hits=nskill,
                   level_fit=lfl, sales_intensity=inten, sales_level=lvl, sales_reasons=why, shortlist=(lvl != "High"),
                   bonus=cd.get("bonus", ""), commission=cd.get("commission", ""), equity=cd.get("equity", ""), benefits=cd.get("benefits", ""),
                   ats="Indeed", hours_text=x.get("hours", ""), terms="")
        if sal:
            lo, hi, freq, neg = sal
            rec.update(salary_disclosed=True, sal_min=lo, sal_max=hi, currency="CAD", frequency=freq, pay_basis="Base salary",
                       advertised=x["salary"], annual_min=round(lo), annual_max=round(hi), annual_note="",
                       salary_source="Indeed job listing (employer-advertised)",
                       salary_status="Employer-advertised on Indeed · not cross-checked on employer site")
        else:
            rec.update(salary_disclosed=False, sal_min=None, sal_max=None, currency="", frequency="", pay_basis="",
                       advertised="Salary Not Disclosed", annual_min=None, annual_max=None, annual_note="",
                       salary_source="—", salary_status="Salary Not Disclosed")
        jobs.append(rec); seen[key] = rec

# ---------------- Place of work (city, address, arrangement) for every job ----------------
GTA_CITIES = ["Toronto", "North York", "Scarborough", "Etobicoke", "East York", "Mississauga", "Brampton", "Markham", "Vaughan", "Concord",
              "Thornhill", "Richmond Hill", "Oakville", "Burlington", "Milton", "Bolton", "Newmarket", "Aurora", "Pickering", "Ajax", "Whitby",
              "Oshawa", "Woodbridge", "Maple", "Stouffville", "Caledon"]
for r in jobs:
    loc = r["location"]
    found = [c for c in GTA_CITIES if re.search(r"\b" + c + r"\b", loc, re.I)]
    remote = r["work_mode"].startswith("Remote")
    if found:
        place = ", ".join(dict.fromkeys(found[:3])) + ", ON"
    elif remote or re.search(r"canada", loc, re.I):
        place = "Remote within Canada"
    else:
        place = loc
    others = re.split(r"[;|·]|\s{2,}", loc)
    non_gta = [o for o in others if o.strip() and not any(re.search(r"\b" + c + r"\b", o, re.I) for c in GTA_CITIES)]
    r["place"] = place
    r["place_note"] = "Also posted for other cities" if found and non_gta else ""
    r.setdefault("address", "")
    r.setdefault("board_url", "")
    r.setdefault("hours_text", "")
    if r["work_mode"] == "Not stated": r["work_mode_note"] = "The posting does not say whether the role is on-site, hybrid or remote"
    else: r["work_mode_note"] = ""
    if r["work_mode"] == "Remote (Canada)" and found: r["place"] = place + " (remote option)"

# ---------------- Compensation intelligence ----------------
MARKET = {  # third-party market averages — NOT employer-confirmed
    "Account Management": "Market average (Glassdoor, Toronto, Oct 2026): CA$55,128–106,710 (25th–75th pct.)",
    "Customer / Client Success": "Market average (Glassdoor, Toronto, Nov 2026): median CA$84,596; CA$66,438–110,129",
    "Digital & Performance Marketing": "Market average (Payscale, Digital Marketing Specialist, Toronto): ~CA$57,946",
    "Social Media": "Market average (Payscale, Digital Marketing Specialist, Toronto): ~CA$57,946",
}
by_cat = {}
for r in jobs:
    if r["salary_disclosed"] and r["frequency"] == "Annual" and "OTE" not in r["pay_basis"]:
        by_cat.setdefault(r["category"], []).append((r["annual_min"] + r["annual_max"]) / 2)
for r in jobs:
    r["market_ref"] = MARKET.get(r["category"], "")
    mids = by_cat.get(r["category"], [])
    r["cat_median"] = round(statistics.median(mids)) if len(mids) >= 3 else None
    r["pay_flag"] = ""
    if r["salary_disclosed"] and r["cat_median"] and r["frequency"] == "Annual" and "OTE" not in r["pay_basis"]:
        mid = (r["annual_min"] + r["annual_max"]) / 2
        ratio = mid / r["cat_median"]
        r["vs_median_pct"] = round((ratio - 1) * 100)
        if ratio >= 1.25: r["pay_flag"] = "High for category"
        elif ratio <= 0.75: r["pay_flag"] = "Low for category"
    else:
        r["vs_median_pct"] = None
    r["commission_flag"] = bool(r["commission"])

jobs.sort(key=lambda r: -r["match"])
for i, r in enumerate(jobs, 1): r["id"] = i
json.dump(dict(generated=FETCHED, candidate="Vishakha Chauhan", jobs=jobs), open(S + "/jobs.json", "w"), indent=1)
print(len(jobs), "jobs;", sum(r["salary_disclosed"] for r in jobs), "with salary;", sum(not r["shortlist"] for r in jobs), "screened out")
for r in jobs:
    print(f"{r['match']:3} {r['sales_level'][0]} {'$' if r['salary_disclosed'] else '-'} {r['company'][:11]:11} | {r['title'][:55]:55} | {r['category'][:18]:18} | {r['work_mode'][:14]:14} | "
          f"{(str(r['sal_min'])+'-'+str(r['sal_max'])+' '+r['frequency']) if r['salary_disclosed'] else r['annual_note'][:30]} | {r['pay_flag']} | {r['commission'][:30]}")
