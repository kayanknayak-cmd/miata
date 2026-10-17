import json,sys,time,urllib.request,urllib.parse,os
UA={"User-Agent":"miata-edit/1.0 (kayanknayak@gmail.com)"}
def get(params):
    u="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode({**params,"format":"json"})
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
        except Exception: time.sleep(5*2**i)
    return {}
out=sys.argv[1]
cats={"NA":["Mazda MX-5 (NA)","Eunos Roadster"],"NB":["Mazda MX-5 (NB)"],"NC":["Mazda MX-5 (NC)"],"ND":["Mazda MX-5 (ND)"]}
for gen,names in cats.items():
    os.makedirs(f"{out}/{gen}",exist_ok=True); files=[]
    for n in names:
        cont={}
        while True:
            r=get({"action":"query","generator":"categorymembers","gcmtitle":"Category:"+n,"gcmtype":"file","gcmlimit":"50","prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":"1600",**cont})
            for p in r.get("query",{}).get("pages",{}).values():
                ii=(p.get("imageinfo") or [{}])[0]; m=ii.get("extmetadata",{})
                if p["title"].lower().endswith((".jpg",".jpeg")) and ii.get("width",0)>=1400 and ii.get("width",0)>ii.get("height",1)*1.15:
                    files.append((p["title"],ii["thumburl"],m.get("LicenseShortName",{}).get("value",""),m.get("Artist",{}).get("value","")))
            if "continue" not in r: break
            cont={k:v for k,v in r["continue"].items()}; time.sleep(1)
    print(gen,len(files),file=sys.stderr,flush=True); cred=[]
    for i,(t,u,lic,a) in enumerate(files):
        fn=f"{out}/{gen}/{i:03d}.jpg"
        for k in range(5):
            if os.path.exists(fn) and open(fn,"rb").read(2)==b"\xff\xd8": break
            try: open(fn,"wb").write(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read())
            except Exception: pass
            time.sleep(1+3*k)
        cred.append(f"{gen}/{i:03d}.jpg\t{t}\t{lic}\t{a}")
    open(f"{out}/{gen}/credits.tsv","w").write("\n".join(cred))
