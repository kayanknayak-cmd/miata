# v2: vertical 1080x1920 @12fps, 30s. Car locked centre-frame, swaps every frame; world swaps on the beat.
import sys,os,glob,json,random
import numpy as np, librosa
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
S,CUT,TRACK,START=sys.argv[1],sys.argv[2],sys.argv[3],float(sys.argv[4])
REJECT=set(sys.argv[5].split(",")) if len(sys.argv)>5 else set()
W,H,FPS,DUR=1080,1920,12,30.0; N=int(FPS*DUR); rnd=random.Random(3)
OUT=f"{S}/frames2"; os.makedirs(OUT,exist_ok=True); [os.remove(f) for f in glob.glob(OUT+"/*.png")]
F=lambda n,s:ImageFont.truetype(f"{S}/fonts/{n}.ttf",s)
# beats inside the 30s window -> frame numbers
y,sr=librosa.load(TRACK,sr=22050,offset=START,duration=DUR)
_,bf=librosa.beat.beat_track(y=y,sr=sr); beats=sorted(set(int(round(t*FPS)) for t in librosa.frames_to_time(bf,sr=sr)))
beatset=set(beats); print("beats",len(beats))
# cars
meta=[m for m in json.load(open(f"{CUT}/meta.json")) if m["key"] not in REJECT]
def load(m):
    im=Image.open(f"{CUT}/{m['key']}.png"); a=np.asarray(im)[...,3]>128
    h=a.sum(0); k=max(1,len(h)*3//10)
    if h[:k].mean()<h[-k:].mean(): im=im.transpose(Image.FLIP_LEFT_RIGHT)   # near (taller) end always on the left
    s=min(960/im.width,480/im.height); return im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
gens=["NA","NB","NC","ND"]; label={"NA":("NA","1989"),"NB":("NB","1998"),"NC":("NC","2005"),"ND":("ND","2015")}
pool={g:sorted([m for m in meta if m["gen"]==g],key=lambda m:(m["hue"]<0,(m["hue"]+20)%256,-m["val"])) for g in gens}
cache={}
def car(m):
    if m["key"] not in cache: cache[m["key"]]=load(m)
    return cache[m["key"]]
PAL=[((233,196,106),(231,111,81)),((42,157,143),(244,162,97)),((244,162,97),(38,70,83)),((231,111,81),(250,237,205)),
     ((250,237,205),(214,40,57)),((38,70,83),(233,196,106)),((214,93,129),(255,214,165)),((95,158,160),(240,128,60))]
def background(pi,t):
    bg,acc=PAL[pi%len(PAL)]; im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im)
    cx,cy,r=W//2,1020,470                                   # retro sun, sliced
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=acc)
    for k in range(7):
        yy=cy+40+k*58+int(t*60)%58; d.rectangle([0,yy,W,yy+8+k*4],fill=bg)
    for k,c in enumerate([acc,(250,237,205),acc]):          # 70s triple stripe along the floor
        d.rectangle([0,1330+k*34,W,1330+k*34+20],fill=c)
    return im
def shadow(cw,ch):
    s=Image.new("L",(W,H),0); ImageDraw.Draw(s).ellipse([W//2-cw//2+30,1290,W//2+cw//2-30,1350],fill=150)
    return s.filter(ImageFilter.GaussianBlur(22))
def film(im,i,flash):
    a=np.asarray(im,float)/255
    a=a*0.88+0.07; a[...,0]=a[...,0]*1.04; a[...,2]=a[...,2]*0.93+0.02          # faded print
    yy,xx=np.ogrid[0:H,0:W]; v=1-0.9*(((xx-W/2)/W)**2+((yy-H/2)/H)**2)
    a=a*v[...,None]
    n=np.kron(np.random.normal(0,0.045,(H//3,W//3)),np.ones((3,3)))[:H,:W]; a=a+n[...,None]
    if flash: a=a+flash*np.array([1,0.85,0.6])
    im=Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8))
    return ImageChops.offset(im,rnd.randint(-5,5),rnd.randint(-4,4))      # gate weave
def text(im,s,xy,font,fill,anchor="mm",shadow_c=(30,20,20)):
    d=ImageDraw.Draw(im); d.text((xy[0]+6,xy[1]+6),s,font=font,fill=shadow_c,anchor=anchor); d.text(xy,s,font=font,fill=fill,anchor=anchor)
# timeline: intro 1 car per beat, then a car every frame through NA->ND, outro hero hold
first_fast=beats[4] if len(beats)>4 else 24; outro=N-30
seg=(outro-first_fast)/4; pi=0; prev=None; lastswap=-9
for i in range(N):
    if i<first_fast: g="NA"
    elif i<outro: g=gens[min(3,int((i-first_fast)/seg))]
    else: g="ND"
    onbeat=i in beatset
    if onbeat: pi+=1
    p=pool[g]
    if i<first_fast:  m=p[(beats.index(max([b for b in beats if b<=i],default=0)) if i>=beats[0] else 0)%len(p)]
    elif i<outro:     m=p[(i-first_fast)%len(p)]
    else:             m=max(pool["ND"],key=lambda m:(m["hue"]>=0 and (m["hue"]<12 or m["hue"]>245)))  # red ND hero
    c=car(m)
    bounce=1.07 if onbeat else (1.03 if i-1 in beatset else 1.0)
    if i>=outro: bounce=1.0+0.004*(i-outro)
    cc=c.resize((int(c.width*bounce),int(c.height*bounce)),Image.LANCZOS) if bounce!=1 else c
    im=background(pi,i/FPS)
    blk=Image.new("RGB",(W,H),(25,15,15)); im=Image.composite(blk,im,shadow(cc.width,cc.height))
    im.paste(cc,(W//2-cc.width//2,1330-cc.height),cc)
    gen,yr=label[g]
    if i<outro:
        text(im,"MX-5",(W//2,250),F("Monoton",190),(250,237,205))
        text(im,gen,(W//2,500),F("Bungee",260),PAL[pi%len(PAL)][1] if PAL[pi%len(PAL)][1]!=PAL[pi%len(PAL)][0] else (250,237,205))
        text(im,yr,(W//2,1600),F("Bungee",120),(250,237,205))
    else:
        text(im,"MIATA",(W//2,330),F("Monoton",220),(250,237,205))
        text(im,"1989  /  NOW",(W//2,1600),F("Bungee",96),(250,237,205))
    newgen=prev is not None and g!=prev; prev=g
    flash=0.55 if newgen else (0.12 if onbeat else 0)
    if i>=N-6: flash=-(i-(N-6)+1)/6
    out=film(im,i,flash)
    out.save(f"{OUT}/{i:04d}.png")
print("done",N)
