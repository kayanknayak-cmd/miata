import json,sys,time,urllib.request,urllib.parse,os
UA={"User-Agent":"miata-edit/1.0 (kayanknayak@gmail.com)"}
def get(params):
    u="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode({**params,"format":"json"})
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
        except Exception as e: time.sleep(2**i)
    return {}
out=sys.argv[1]; per=int(sys.argv[2])
cats={"NA":["Mazda MX-5 (NA)","Eunos Roadster","Mazda Miata"],"NB":["SKIP"],"NC":["SKIP"],"ND":["SKIP"]}
for gen,names in cats.items():
    files=[]
    for n in names:
        r=get({"action":"query","generator":"categorymembers","gcmtitle":"Category:"+n,"gcmtype":"file","gcmlimit":"120","prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":"960"})
        for p in r.get("query",{}).get("pages",{}).values():
            ii=p.get("imageinfo",[{}])[0]; t=p["title"]
            if not t.lower().endswith((".jpg",".jpeg")): continue
            lic=ii.get("extmetadata",{}).get("LicenseShortName",{}).get("value","")
            files.append((t,ii.get("thumburl"),lic,ii.get("extmetadata",{}).get("Artist",{}).get("value","")))
        print(gen,n,len(files),file=sys.stderr)
        if files: break
    if not files: continue
    os.makedirs(f"{out}/{gen}",exist_ok=True); cred=[]
    for i,(t,u,lic,a) in enumerate(files[:per]):
        fn=f"{out}/{gen}/{i:03d}.jpg"
        if not os.path.exists(fn):
            try: open(fn,"wb").write(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read()); time.sleep(0.2)
            except Exception as e: print("fail",t,e,file=sys.stderr); continue
        cred.append(f"{gen}/{i:03d}.jpg\t{t}\t{lic}\t{a}")
    open(f"{out}/{gen}/credits.tsv","w").write("\n".join(cred))
