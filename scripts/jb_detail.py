"""Fetch Job Bank posting details for relevant Toronto/GTA listings -> jb/details.json"""
import urllib.request, re, html, json, time, os, http.cookiejar
S = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(u):
    return op.open(urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "en-CA,en"}), timeout=40).read().decode("utf-8", "ignore")

GTA = re.compile(r"\b(toronto|north york|scarborough|etobicoke|east york|york|mississauga|brampton|markham|vaughan|concord|thornhill|richmond hill|oakville|burlington|milton|bolton|newmarket|aurora|pickering|ajax|whitby|oshawa|woodbridge|maple|stouffville|caledon|halton hills|georgetown)\b", re.I)
T = re.compile(r"account manager|account coordinator|customer success|client success|client service|client relations|account executive|digital marketing|marketing (coordinator|specialist|manager|analyst|associate|consultant)|social media|\bseo\b|search engine|ppc|paid (media|search|social)|\bsem\b|\bcrm\b|e-?commerce (specialist|coordinator|manager)|customer experience|customer service (specialist|manager|team lead|supervisor)|relationship manager|business development|campaign|content marketing|email marketing|online marketing|brand (manager|specialist|coordinator)", re.I)
EXCL = re.compile(r"web site develop|developer|insurance|mortgage|farm|clerk", re.I)

lst = json.load(open(S + "/jb/list.json"))
keep = [x for x in lst if T.search(x["title"]) and not EXCL.search(x["title"]) and GTA.search(x["location"] or "")]
print(len(lst), "listings;", len(keep), "relevant in GTA")

def clean(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
out = []
for x in keep:
    u = f"https://www.jobbank.gc.ca/jobsearch/jobposting/{x['jid']}"
    try:
        t = get(u)
    except Exception as e:
        print("ERR", x["jid"], e); continue
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    flat = clean(body)
    rec = dict(x)
    rec["url"] = u
    m = re.search(r"Work location\s+(On site|Hybrid|Remote|On the road|Various)[^|]*?", flat)
    rec["work_location"] = m.group(1) if m else ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:to\s*(\d+(?:\.\d+)?)\s*)?hours per week", flat)
    rec["hours"] = (float(m.group(1)) + float(m.group(2) or m.group(1))) / 2 if m else None
    rec["hours_text"] = m.group(0) if m else ""
    m = re.search(r'<span property="streetAddress">(.*?)</span>', t, re.S)
    street = clean(m.group(1)) if m else ""
    m = re.search(r'<span property="addressLocality">(.*?)</span>', t, re.S)
    city = clean(m.group(1)) if m else ""
    m = re.search(r'<span property="postalCode">(.*?)</span>', t, re.S)
    pc = clean(m.group(1)) if m else ""
    rec["address"] = ", ".join(p for p in [street, city + (", ON" if city else ""), pc] if p)
    m = re.search(r"Terms of employment\s+(.*?)\s+(?:Starts|vacanc|Benefits)", flat)
    rec["terms"] = m.group(1)[:80] if m else ""
    m = re.search(r'href="(https?://[^"]*(?:indeed\.com|talent\.com|jobillico|careerbeacon|ziprecruiter)[^"]*)"', t)
    rec["source_url"] = html.unescape(m.group(1)) if m else ""
    i = flat.find("Job details")
    j = flat.find("Report a problem")
    rec["text"] = flat[i:j if j > i else i + 6000][:8000]
    out.append(rec)
    time.sleep(0.5)
json.dump(out, open(S + "/jb/details.json", "w"), indent=1)
print(len(out), "details saved")
from collections import Counter
print(Counter(r["work_location"] for r in out), Counter(r["source"] for r in out))
