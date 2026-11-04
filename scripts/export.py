import json,csv,sys,os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
S=os.path.dirname(os.path.abspath(__file__)); OUT=sys.argv[1]
d=json.load(open(S+"/jobs.json")); jobs=d["jobs"]
def money(v,freq):
    if v is None: return ""
    return round(v,2) if freq=="Hourly" else int(round(v))
rows=[]
for r in jobs:
    ann = "" if r["annual_min"] is None else (f"{r['annual_min']:,}" if r["annual_min"]==r["annual_max"] else f"{r['annual_min']:,} – {r['annual_max']:,}")
    if ann and r["annual_note"]: ann += f" ({r['annual_note']})"
    if not ann and r["annual_note"]: ann = r["annual_note"]
    comp=[x for x in [r["pay_basis"] and "Basis: "+r["pay_basis"], r["bonus"] and "Bonus: "+r["bonus"], r["commission"] and "Commission: "+r["commission"], r["equity"] and "Equity: "+r["equity"], r["benefits"] and "Benefits: "+r["benefits"]] if x]
    rows.append({
     "Rank":r["id"],"Position Title":r["title"],"Company":r["company"],"Place of Work":r.get("place",""),"Street Address":r.get("address",""),"Posted Location":r["location"],"Work Arrangement":r["work_mode"] if r["work_mode"]!="Not stated" else "Not stated in posting","Weekly Hours":r.get("hours_text",""),"Found On":("Employer career site ("+r["ats"]+")") if r["ats"] in ("Greenhouse","Ashby","Lever","Workday") else (r["ats"]+(" (via Job Bank)" if r["ats"]!="Job Bank" else " (Government of Canada)")),
     "Job Category":r["category"],"Match Score":r["match"],"Shortlist":"Yes" if r["shortlist"] else "No – screened out (high sales intensity)",
     "Sales Intensity":f'{r["sales_level"]} ({r["sales_intensity"]}/100)' + (": "+", ".join(r["sales_reasons"]) if r["sales_reasons"] else ""),
     "Minimum Salary":money(r["sal_min"],r["frequency"]) if r["salary_disclosed"] else "Salary Not Disclosed",
     "Maximum Salary":money(r["sal_max"],r["frequency"]) if r["salary_disclosed"] else "Salary Not Disclosed",
     "Currency":r["currency"],"Salary Frequency":r["frequency"],"Advertised Compensation":r["advertised"],
     "Annual Equivalent":ann,"Compensation Details":"; ".join(comp),
     "Commission Flag":"Yes" if r["commission_flag"] else "No",
     "Pay vs Category":(f'{r["pay_flag"]} ({r["vs_median_pct"]:+d}% vs category median ${r["cat_median"]:,})' if r["pay_flag"] else (f'{r["vs_median_pct"]:+d}% vs category median ${r["cat_median"]:,}' if r["vs_median_pct"] is not None else "")),
     "Market Reference (third-party estimate)":r["market_ref"],
     "Salary Source":r["salary_source"],"Salary Verification Status":r["salary_status"],
     "Application Link":r["url"],"Job Bank Listing":r.get("board_url",""),"Posted / Updated":r["posted"] or r.get("posted_text",""),
    })
cols=list(rows[0].keys())
with open(OUT+"/Vishakha_Toronto_Jobs_Salary.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
wb=Workbook(); ws=wb.active; ws.title="Jobs"
ws.append(cols)
for r in rows: ws.append([r[c] for c in cols])
hdr=PatternFill("solid",fgColor="1F3A5F")
for c in ws[1]: c.font=Font(bold=True,color="FFFFFF"); c.fill=hdr; c.alignment=Alignment(wrap_text=True,vertical="top")
widths={"Place of Work":26,"Street Address":32,"Posted Location":30,"Found On":30,"Job Bank Listing":40,"Position Title":42,"Company":14,"Location":30,"Advertised Compensation":44,"Compensation Details":60,"Annual Equivalent":36,"Market Reference (third-party estimate)":48,"Salary Source":34,"Salary Verification Status":44,"Application Link":50,"Sales Intensity":40,"Pay vs Category":38,"Shortlist":22,"Job Category":28}
for i,c in enumerate(cols,1): ws.column_dimensions[get_column_letter(i)].width=widths.get(c,14)
for row in ws.iter_rows(min_row=2):
    for c in row: c.alignment=Alignment(wrap_text=True,vertical="top")
    link=row[cols.index("Application Link")]; link.hyperlink=link.value; link.font=Font(color="1F5FBF",underline="single")
ws.freeze_panes="C2"; ws.auto_filter.ref=ws.dimensions
n=wb.create_sheet("Method")
for line in [
 ["Generated",d["generated"]],["Candidate",d["candidate"]],
 ["Salary source priority","1) Employer career page  2) Official job posting  3) Indeed  4) LinkedIn  5) Glassdoor / other. All disclosed salaries here came from priority 1: the employer's own career-page posting (Greenhouse, Ashby, Lever or Workday feed)."],
 ["Employer-disclosed vs estimate","Minimum/Maximum Salary columns hold only employer-advertised figures. Market Reference column holds third-party averages (Glassdoor/Payscale) and is never an employer-confirmed salary. No AI-generated salary estimates are used."],
 ["Not disclosed","Jobs with no Canadian salary in the posting show 'Salary Not Disclosed' and stay in the list. Postings that publish only a US-dollar range are noted in Annual Equivalent."],
 ["Annual equivalent","Annual roles: same as advertised. Hourly roles: rate × weekly hours × 52. Weekly hours are taken from the posting when stated (TD postings list them); otherwise 37.5 h/week is assumed and labelled. Paid weeks assumed 52. Always an estimate."],
 ["OTE","Where the employer publishes on-target earnings (base + variable) instead of base salary, Pay Basis says so; OTE roles are left out of category comparisons."],
 ["Pay vs Category","Midpoint of the advertised annual range compared with the median midpoint of other disclosed annual (non-OTE) roles in the same category. ≥25% above = High for category; ≥25% below = Low for category. Needs 3+ disclosed roles in the category."],
 ["Sales-intensity screening","Score 0–100: sales title +40, quota +15, commission +15, OTE pay +10, prospecting/outbound +15, new-business hunting +10, closing deals +10, commission ≥30% of base +25. High (≥60) = screened out of shortlist but kept in file; Medium (30–59) = kept with a warning; Low (<30). Any role with a commission component goes through this screen."],
 ["Match score (inferred from resume)","Category fit up to 30 (account management, client success, digital/performance marketing highest) + resume-skill overlap up to 35 (CRM, Salesforce, SEO, PPC, email, social, lead gen, analytics, SMB, telecom...) + location 15 (Toronto/GTA or remote Canada) + level fit up to 20; minus 20 for high and 8 for medium sales intensity."],
 ["Job sources","Employer career sites (Greenhouse, Ashby, Lever, Workday feeds), Canada's Job Bank, and Indeed / Talent.com / other boards whose postings Job Bank republishes. Indeed's own website blocks automated access."],
 ["Place of work","City (GTA) or remote, street address when the posting gives one, and work arrangement. 'Not stated in posting' when the posting does not say on-site, hybrid or remote."],
 ["Location preference","Toronto / GTA (incl. Markham, Etobicoke, Oakville, Burlington, Whitby, Mississauga) or remote within Canada."]]:
    n.append(line)
n.column_dimensions["A"].width=30; n.column_dimensions["B"].width=120
for row in n.iter_rows():
    row[0].font=Font(bold=True)
    for c in row: c.alignment=Alignment(wrap_text=True,vertical="top")
wb.save(OUT+"/Vishakha_Toronto_Jobs_Salary.xlsx")
# flat JSON for dashboard
flat=[]
for r in jobs:
    x=dict(r); x["sales_reasons"]=", ".join(r["sales_reasons"]); flat.append(x)
json.dump(flat,open(S+"/jobs_flat.json","w"))
print(len(rows),"rows", os.path.getsize(S+"/jobs_flat.json"),"bytes json")
