import urllib.request, urllib.parse, re, html, json, time, os, http.cookiejar
S=os.path.dirname(os.path.abspath(__file__))
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
def get(u):
    r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"en-CA,en"}); return op.open(r,timeout=40).read().decode("utf-8","ignore")
Q=["account manager","customer success manager","client success manager","client services manager","account coordinator","digital marketing specialist","digital marketing manager","marketing coordinator","marketing specialist","social media specialist","SEO specialist","PPC specialist","paid media","email marketing specialist","CRM specialist","customer experience specialist","customer service specialist","relationship manager","e-commerce specialist","marketing analyst","business development manager","account executive"]
seen={}; 
def clean(s): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()
for q in Q:
    for page in (1,2,3,4):
        u="https://www.jobbank.gc.ca/jobsearch/jobsearch?"+urllib.parse.urlencode({"searchstring":q,"locationstring":"Toronto","fprov":"ON","sort":"D","page":page})
        try: t=get(u)
        except Exception as e: print("ERR",q,e); continue
        arts=re.findall(r'<article id="article-(\d+)".*?</article>',t,re.S)
        blocks=re.findall(r'(<article id="article-\d+".*?</article>)',t,re.S)
        n=0
        for b in blocks:
            jid=re.search(r'article-(\d+)',b).group(1)
            if jid in seen: continue
            title=clean((re.search(r'<span class="noctitle">(.*?)</span>',b,re.S) or [None,""])[1]) if re.search(r'<span class="noctitle">',b) else ""
            src=clean((re.search(r'<span class="job-source[^"]*"><span class="wb-inv">(.*?)</span>',b,re.S) or [None,""])[1]) if re.search(r'job-source',b) else ""
            def li(c):
                m=re.search(r'<li class="%s">(.*?)</li>'%c,b,re.S); return clean(m.group(1)) if m else ""
            seen[jid]=dict(jid=jid,title=title,date=li("date"),business=li("business"),location=li("location").replace("Location","").strip(),salary=li("salary").replace("Salary","",1).strip(),source=src or "Job Bank",query=q)
            n+=1
        print(q,page,len(blocks),"new",n); time.sleep(0.6)
json.dump(list(seen.values()),open(S+"/jb/list.json","w"),indent=1)
print(len(seen))
