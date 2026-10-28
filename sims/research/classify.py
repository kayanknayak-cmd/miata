import csv,re,statistics as st,collections,json
cats=[
 ("music_marble", r"marble ?music|music ?marble|marbl?asmr|instrument|ringtone|song|melody|\bmusic\b|piano|xylophone|anthem|despacito|baby shark|bella ciao|\bapt\b"),
 ("ip_character", r"minecraft|steve|sprunki|alphabet ?lore|numberblock|roblox|among ?us|sonic|mario|pokemon|pokémon|skibidi|labubu|squid game|catnap|poppy|huggy|princess|pacman|pac-man|ghast|creeper|brawl"),
 ("tetris_softbody", r"tetris"),
 ("scale_escalation", r"\b0 ?vs|\b1 vs|vs 1 ?(million|billion|thousand)|million|billion|\d+ ?vs ?\d+|0% ?vs|100%"),
 ("domino", r"domino"),
 ("marble_run", r"marble ?run|marble|balls? on|ball|spiral|stair|escalator|circuit|race"),
 ("destruction", r"destruct|shatter|break|crush|hydraulic|press|explo|smash|crash|glass"),
 ("cloth_hair_chain", r"cloth|hair|chain|rope|armou?r|silk|fabric"),
 ("fluid", r"fluid|water|liquid|slime|honey|lava|pour"),
 ("soft_body_generic", r"soft ?body|jelly|squish|soft"),
 ("loop_mech", r"button|loop|shift|gear|endless|infinite|perfect fit|sort"),
]
cats=[(n,re.compile(p,re.I)) for n,p in cats]
def cat(t):
    for n,p in cats:
        if p.search(t): return n
    return "other"
rows=[]
for r in csv.reader(open('shorts.tsv'),delimiter='\t'):
    if len(r)<4: continue
    try: v=int(r[2])
    except: continue
    rows.append(dict(ch=r[0],id=r[1],v=v,t=r[3],c=cat(r[3])))
json.dump(rows,open('rows.json','w'))
if __name__=='__main__':
    g=collections.defaultdict(list)
    for x in rows: g[x['c']].append(x)
    print(f"{'format':18} {'n':>5} {'chans':>5} {'median':>10} {'mean':>12} {'%>1M':>6} {'%>10M':>6}")
    for k,xs in sorted(g.items(),key=lambda kv:-st.median([x['v'] for x in kv[1]])):
        vs=[x['v'] for x in xs]
        print(f"{k:18} {len(vs):5} {len({x['ch'] for x in xs}):5} {int(st.median(vs)):>10,} {int(st.mean(vs)):>12,} {100*sum(v>1e6 for v in vs)/len(vs):5.1f}% {100*sum(v>1e7 for v in vs)/len(vs):5.1f}%")
