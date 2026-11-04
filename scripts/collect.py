import json,glob,os,re,html,sys
S=os.path.dirname(os.path.abspath(__file__))
def strip(h):
    h=html.unescape(h or ""); h=re.sub(r"<br\s*/?>|</p>|</li>|</div>|</h\d>","\n",h); h=re.sub(r"<[^>]+>"," ",h); h=html.unescape(h)
    return re.sub(r"[ \t\xa0]+"," ",h)
out=[]
for f in glob.glob(S+"/gh/*.json"):
    try: d=json.load(open(f))
    except: continue
    c=os.path.basename(f)[:-5]
    for j in d.get("jobs",[]):
        out.append(dict(ats="greenhouse",co=c,title=j["title"],loc=j.get("location",{}).get("name",""),url=j.get("absolute_url"),text=strip(j.get("content")),updated=j.get("updated_at"),comp=None))
for f in glob.glob(S+"/ash/*.json"):
    try: d=json.load(open(f))
    except: continue
    c=os.path.basename(f)[:-5]
    for j in d.get("jobs",[]):
        locs=[j.get("location","")]+[s.get("location","") for s in (j.get("secondaryLocations") or [])]
        comp=(j.get("compensation") or {}).get("compensationTierSummary") or (j.get("compensation") or {}).get("scrapeableCompensationSalarySummary")
        out.append(dict(ats="ashby",co=c,title=j["title"],loc=" | ".join(x for x in locs if x),url=j.get("jobUrl"),text=j.get("descriptionPlain",""),updated=j.get("publishedAt"),comp=comp,wp=j.get("workplaceType"),remote=j.get("isRemote")))
for f in glob.glob(S+"/lev/*.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,list): continue
    c=os.path.basename(f)[:-5]
    for j in d:
        sr=j.get("salaryRange")
        comp=f"{sr.get('currency')} {sr.get('min')}-{sr.get('max')} {sr.get('interval')}" if sr else None
        txt=(j.get("descriptionPlain","") or "")+"\n"+"\n".join(l.get("text","")+": "+strip(l.get("content","")) for l in j.get("lists",[]))+"\n"+(j.get("additionalPlain","") or "")
        out.append(dict(ats="lever",co=c,title=j["text"],loc=(j.get("categories") or {}).get("location","") or "",url=j.get("hostedUrl"),text=txt,updated=j.get("createdAt"),comp=comp,wp=j.get("workplaceType")))
json.dump(out,open(S+"/all.json","w"))
LOC=re.compile(r"toronto|ontario|\bON\b|canada|GTA|mississauga|markham|vaughan|oakville|brampton",re.I)
T=re.compile(r"account manager|account strateg|customer success|client success|client partner|relationship manager|digital market|marketing (specialist|manager|coordinator|associate)|growth market|performance market|paid (media|search|social)|ppc|sem\b|seo|crm|lifecycle|email market|social media|partner manager|partnerships|account executive|customer experience|client services|campaign|demand gen|marketing operations|community|support specialist|customer support|onboarding|implementation",re.I)
sel=[j for j in out if LOC.search(j["loc"] or "") and T.search(j["title"])]
print(len(out),len(sel))
for j in sel: print(j["ats"],"|",j["co"],"|",j["title"],"|",j["loc"][:70],"|",j["comp"])
json.dump(sel,open(S+"/sel.json","w"))
