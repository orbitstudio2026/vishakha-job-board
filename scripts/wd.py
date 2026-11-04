import json,urllib.request,re,os,html
S=os.path.dirname(os.path.abspath(__file__))
T=[("td","wd3","TD_Bank_Careers","TD Bank"),("manulife","wd3","MFCJH_Jobs","Manulife"),("sunlife","wd3","Experienced-Jobs","Sun Life"),("cibc","wd3","search","CIBC"),("bmo","wd3","External","BMO"),("rbc","wd3","RBCGLOBAL1","RBC"),("thomsonreuters","wd5","External_Career_Site","Thomson Reuters"),("mlse","wd3","MLSE","MLSE")]
Q=["digital marketing","account manager","client success","relationship manager","marketing specialist","customer experience","social media","CRM","campaign","SEO","paid media","client service"]
TI=re.compile(r"marketing|account manager|client|customer|social|crm|campaign|seo|search engine|paid|digital|relationship manager|engagement|content|brand",re.I)
EX=re.compile(r"director|vp|avp|chief|intern|co-op|head of|investment banking|risk|underwrit|engineer|developer|actuar|wholesaler|advisor|mortgage|insurance sales|financial planning|lending|credit",re.I)
def post(url,body):
    r=urllib.request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","Accept":"application/json"})
    return json.load(urllib.request.urlopen(r,timeout=30))
def get(url):
    r=urllib.request.Request(url,headers={"Accept":"application/json"}); return json.load(urllib.request.urlopen(r,timeout=30))
seen={};out=[]
for t,wd,site,name in T:
    base=f"https://{t}.{wd}.myworkdayjobs.com/wday/cxs/{t}/{site}"
    pub=f"https://{t}.{wd}.myworkdayjobs.com/{site}"
    for q in Q:
        try: d=post(base+"/jobs",{"appliedFacets":{},"limit":20,"offset":0,"searchText":q+" Toronto"})
        except Exception as e: print("ERR",t,q,e); continue
        for j in d.get("jobPostings",[]):
            p=j.get("externalPath")
            if not p or p in seen: continue
            if not TI.search(j["title"]) or EX.search(j["title"]): continue
            seen[p]=1
            try: det=get(base+p)["jobPostingInfo"]
            except Exception as e: print("ERRD",p,e); continue
            txt=html.unescape(re.sub(r"<[^>]+>"," ",html.unescape(det.get("jobDescription",""))))
            txt=re.sub(r"\s+"," ",txt)
            loc=det.get("location","")+" "+" ".join(det.get("additionalLocations",[]) or [])
            if not re.search(r"toronto|ontario|mississauga|markham|waterloo|canada",loc,re.I): continue
            out.append(dict(ats="workday",co=name,title=det["title"],loc=loc.strip(),url=det.get("externalUrl"),text=txt,updated=det.get("startDate"),comp=None,timeType=det.get("timeType"),remote=det.get("remoteType")))
            print(name,"|",det["title"],"|",loc[:60],"|",det.get("remoteType"),"|",det.get("startDate"))
json.dump(out,open(S+"/wd_sel.json","w"))
print(len(out))
