# v3: vertical 1080x1920 @12fps, 30s. Shot types rotate on the beat; virtual camera moves every frame.
import sys,os,glob,json,random,math
import numpy as np, librosa
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
S,CUT,TRACK,START=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4])
REJECT=set(sys.argv[5].split(",")) if len(sys.argv)>5 else set()
W,H,FPS,DUR=1080,1920,12,30.0; N=int(FPS*DUR); rnd=random.Random(3)
OUT=f"{S}/frames3"; os.makedirs(OUT,exist_ok=True); [os.remove(f) for f in glob.glob(OUT+"/*.png")]
F=lambda n,s:ImageFont.truetype(f"{S}/fonts/{n}.ttf",s)
y,sr=librosa.load(TRACK,sr=22050,offset=START,duration=DUR)
_,bf=librosa.beat.beat_track(y=y,sr=sr); beats=sorted(set(int(round(t*FPS)) for t in librosa.frames_to_time(bf,sr=sr)))
beats=[b for b in beats if b<N]; beatset=set(beats)
def beat_of(i): return max([k for k,b in enumerate(beats) if b<=i],default=-1)
meta=[m for m in json.load(open(f"{CUT}/meta.json")) if m["key"] not in REJECT]
gens=["NA","NB","NC","ND"]; YR={"NA":"1989","NB":"1998","NC":"2005","ND":"2015"}
pool={g:sorted([m for m in meta if m["gen"]==g],key=lambda m:(m["hue"]<0,(m["hue"]+20)%256,-m["val"])) for g in gens}
cache={}
def car(m,maxw=960,maxh=480):
    k=(m["key"],maxw,maxh)
    if k not in cache:
        im=Image.open(f"{CUT}/{m['key']}.png"); a=np.asarray(im)[...,3]>128; h=a.sum(0); q=max(1,len(h)*3//10)
        if h[:q].mean()<h[-q:].mean(): im=im.transpose(Image.FLIP_LEFT_RIGHT)
        s=min(maxw/im.width,maxh/im.height); cache[k]=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
    return cache[k]
PAL=[((233,196,106),(231,111,81)),((42,157,143),(244,162,97)),((244,162,97),(38,70,83)),((231,111,81),(250,237,205)),
     ((250,237,205),(214,40,57)),((38,70,83),(233,196,106)),((214,93,129),(255,214,165)),((95,158,160),(240,128,60))]
CREAM=(250,237,205); INK=(30,20,20)
def ease(x): x=min(max(x,0),1); return 1-(1-x)**3
def text(im,s,xy,font,fill,anchor="mm"):
    d=ImageDraw.Draw(im); d.text((xy[0]+7,xy[1]+7),s,font=font,fill=INK,anchor=anchor); d.text(xy,s,font=font,fill=fill,anchor=anchor)
def sunburst(bg,acc,ang,cy=1000):
    im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im); R=2400
    for k in range(16):
        a0=math.radians(ang+k*22.5); a1=a0+math.radians(11)
        d.polygon([(W//2,cy),(W//2+R*math.cos(a0),cy+R*math.sin(a0)),(W//2+R*math.cos(a1),cy+R*math.sin(a1))],fill=tuple(int(c*0.9+a*0.1) for c,a in zip(bg,acc)))
    r=430; d.ellipse([W//2-r,cy-r,W//2+r,cy+r],fill=acc)
    for k in range(6): yy=cy+60+k*62; d.rectangle([0,yy,W,yy+8+k*5],fill=bg)
    return im
def stripes(im,y0,off,acc):
    d=ImageDraw.Draw(im)
    for k,c in enumerate([acc,CREAM,acc]): d.rectangle([0,y0+k*34,W,y0+k*34+20],fill=c)
    for x in range(-200,W+200,160):                                       # road dashes that scroll
        xx=x+int(off)%160; d.rectangle([xx,y0+130,xx+80,y0+142],fill=CREAM)
def put(im,c,cx,base,scale=1.0,blur=0,shadow=True):
    if scale!=1: c=c.resize((max(1,int(c.width*scale)),max(1,int(c.height*scale))),Image.LANCZOS)
    if blur:                                                              # horizontal motion smear
        c2=Image.new("RGBA",(c.width+blur*2,c.height),(0,0,0,0))
        for k in range(0,blur*2+1,max(1,blur//4)): c2.alpha_composite(c,(k,0))
        c=Image.blend(c2,c2,1); c.putalpha(c.getchannel("A").point(lambda v:min(255,int(v*1.0))))
    if shadow:
        s=Image.new("L",(W,H),0); ImageDraw.Draw(s).ellipse([cx-c.width//2+30,base-30,cx+c.width//2-30,base+30],fill=140)
        im.paste(INK,mask=s.filter(ImageFilter.GaussianBlur(20)))
    im.paste(c,(int(cx-c.width/2),int(base-c.height)),c)
def camera(im,zoom,rot,dx,dy):
    im=im.rotate(rot,resample=Image.BICUBIC,center=(W/2,H/2),translate=(dx,dy),fillcolor=INK)
    if zoom!=1:
        cw,ch=W/zoom,H/zoom; im=im.crop((int((W-cw)/2),int((H-ch)/2),int((W+cw)/2),int((H+ch)/2))).resize((W,H),Image.BICUBIC)
    return im
def film(im,flash):
    a=np.asarray(im,float)/255; a=a*0.88+0.07; a[...,0]*=1.04; a[...,2]=a[...,2]*0.93+0.02
    yy,xx=np.ogrid[0:H,0:W]; a=a*(1-0.9*(((xx-W/2)/W)**2+((yy-H/2)/H)**2))[...,None]
    a=a+np.kron(np.random.normal(0,0.045,(H//3,W//3)),np.ones((3,3)))[:H,:W][...,None]
    if flash: a=a+flash*np.array([1,0.85,0.6])
    return ImageChops.offset(Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)),rnd.randint(-5,5),rnd.randint(-4,4))
# ---- shot plan: beats grouped into gens; each gen cycles shot types
SHOTS=["drivein","flip","detail","driveby","grid","flip"]
LEN={"drivein":2,"flip":3,"detail":2,"driveby":3,"grid":2}
nb=len(beats); outro_b=nb-5; per=(outro_b-0)/4
plan=[]  # (start_beat,end_beat,gen,shot)
for gi,g in enumerate(gens):
    b=round(gi*per); end=round((gi+1)*per); k=0
    while b<end:
        sh=SHOTS[k%len(SHOTS)]; e=min(end,b+LEN[sh]); plan.append((b,e,g,sh)); b=e; k+=1
plan.append((outro_b,nb+99,"ND","outro"))
def shot_at(bi):
    for p in plan:
        if p[0]<=bi<p[1]: return p
    return plan[0]
fc=0; prevg=None
for i in range(N):
    bi=max(0,beat_of(i)); b0,b1,g,sh=shot_at(bi)
    s0=beats[min(b0,nb-1)]; s1=beats[b1] if b1<nb else N; u=(i-s0)/max(1,s1-s0)    # progress through shot 0..1
    onbeat=i in beatset; since=i-beats[bi] if bi>=0 else 9
    bg,acc=PAL[bi%len(PAL)]; p=pool[g]; m=p[fc%len(p)]; fc+=1
    zoom,rot,dx,dy=1.0,0.0,0,0
    if sh=="outro":
        hero=max(pool["ND"],key=lambda m:(m["hue"]>=0 and (m["hue"]<12 or m["hue"]>245),m["val"]))
        im=sunburst((250,237,205),(214,40,57),i*1.5); stripes(im,1330,0,(214,40,57))
        c=car(hero); x=W/2+ (1-ease(u*2.5))*1400
        put(im,c,x,1330,blur=int((1-ease(u*2.5))*60))
        sc=1+2.5*(1-ease((u-0.2)*4)); 
        if u>0.2: text(im,"MIATA",(W//2,330),F("Monoton",int(220*sc)),CREAM)
        if u>0.45: text(im,"1989  /  NOW",(W//2,1600),F("Bungee",96),CREAM)
        zoom=1.0+0.08*u
    elif sh=="flip":
        im=sunburst(bg,acc,i*4); stripes(im,1330,i*40,acc)
        put(im,car(m),W/2,1330,scale=1.08 if since==0 else 1.0)
        zoom=1.0+0.18*u; rot=-4*u
    elif sh=="drivein":
        im=sunburst(bg,acc,i*6); stripes(im,1330,i*90,acc)
        d=ImageDraw.Draw(im)
        for k in range(14): yy=rnd.randint(500,1500); xx=rnd.randint(0,W); d.rectangle([xx,yy,xx+rnd.randint(150,500),yy+6],fill=CREAM)
        x=W/2+(1-ease(u*1.6))*1300; put(im,car(m),x,1330,blur=int((1-ease(u*1.6))*70)+4)
        zoom=1.12-0.12*ease(u); rot=3*(1-u)
    elif sh=="driveby":
        im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im)
        for k in range(8): xx=(k*260-int(i*120))%(W+400)-200; d.rectangle([xx,0,xx+120,1300],fill=acc)   # scrolling pillars
        stripes(im,1330,i*160,acc)
        x=-500+(W+1000)*u; put(im,car(m),x,1330,blur=24)
        zoom=1.15; dx=(0.5-u)*120
    elif sh=="detail":
        im=Image.new("RGB",(W,H),acc)
        c=car(m,2600,1300); fx=rnd.choice([0.18,0.35,0.7]); fy=rnd.choice([0.45,0.7])         # punch into a light / wheel
        put(im,c,W/2+(0.5-fx)*c.width,H/2+(1-fy)*c.height+c.height*0.0+300,shadow=False)
        rot=rnd.uniform(-8,8); zoom=1.05+0.1*u
    elif sh=="grid":
        im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im); cw,ch=W//3,H//5
        shown=min(9,3*(since+1) if since<3 else 9)
        for k in range(shown):
            r_,c_=divmod(k,3); 
            if (r_+c_)%2: d.rectangle([c_*cw,300+r_*ch*1.4,(c_+1)*cw,300+(r_+1)*ch*1.4],fill=acc)
            mm=p[(fc+k*7)%len(p)]; cc=car(mm,cw-30,int(ch*1.2)); put(im,cc,c_*cw+cw//2,300+(r_+1)*ch*1.4-30,shadow=False)
        zoom=1.0+0.06*math.sin(u*math.pi)
    if sh!="outro":                                                        # gen title, slams in at gen start
        gs=[q for q in plan if q[2]==g][0]; tin=(i-beats[gs[0]])/6
        sc=1+2.2*(1-ease(tin)); 
        text(im,"MX-5",(W//2,330),F("Monoton",170),CREAM)
        text(im,g,(W//2,560),F("Bungee",int(250*sc)),acc if acc!=bg else CREAM)
        text(im,YR[g],(W//2,1640),F("Bungee",120),CREAM)
    if since==0 and sh not in ("outro",): zoom*=1.04; dx+=rnd.randint(-14,14); dy+=rnd.randint(-14,14)   # beat shake
    newgen=prevg is not None and g!=prevg
    if newgen or (prevg=="ND" and sh=="outro" and u<0.05): pass
    im=camera(im,zoom,rot,dx,dy)
    if newgen:                                                             # whip pan smear into the new gen
        im=im.filter(ImageFilter.BoxBlur(0)).transform(im.size,Image.AFFINE,(1,0,-260,0,1,0)); im=Image.blend(im,im.filter(ImageFilter.GaussianBlur(18)),0.8)
    flash=0.5 if newgen else (0.12 if since==0 else 0)
    if i>=N-6: flash=-(i-(N-6)+1)/6
    prevg=g if sh!="outro" else "outro"
    film(im,flash).save(f"{OUT}/{i:04d}.png")
print("done",N,"shots",len(plan))
