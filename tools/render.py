# 30s @ 12fps, 144 BPM => exactly 5 frames per beat, 72 beats.
import sys,os,glob,random,math,subprocess
import numpy as np
from PIL import Image,ImageFilter,ImageOps,ImageDraw,ImageFont,ImageChops
S=sys.argv[1]; NFR=int(sys.argv[2]) if len(sys.argv)>2 else 360
W,H=1920,1080; FPB=5; rnd=random.Random(7)
OUT=f"{S}/frames"; os.makedirs(OUT,exist_ok=True)
for f in glob.glob(OUT+"/*.png"): os.remove(f)
gens=["NA","NB","NC","ND"]; years={"NA":"'89","NB":"'98","NC":"'06","ND":"'15"}
pools={g:sorted(glob.glob(f"{S}/src/{g}/*.jpg")) for g in gens}
pools={g:p for g,p in pools.items() if p}
order=[g for g in gens if g in pools]
font=lambda s:ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",s)
paper=Image.fromarray(np.clip(np.random.default_rng(1).normal(236,6,(H,W)),0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)).convert("RGB")
paper=Image.blend(paper,Image.new("RGB",(W,H),(240,228,200)),0.45)
def fit(p):
    im=ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    return ImageOps.fit(im,(W,H),Image.LANCZOS,centering=(0.5,0.55))
def sketch(im):
    g=ImageOps.grayscale(im); inv=ImageOps.invert(g).filter(ImageFilter.GaussianBlur(9))
    a=np.asarray(g,float); b=np.asarray(inv,float)
    d=np.clip(a*255/(255-b+1),0,255)            # colour-dodge pencil
    d=np.clip((d-120)*1.9+120,0,255)
    ink=Image.fromarray(d.astype(np.uint8)).convert("RGB")
    return ImageChops.multiply(ink,paper)
def film(im,t):
    a=np.asarray(im,float)/255
    a=np.clip((a-0.5)*1.12+0.5,0,1); a[...,0]*=1.06; a[...,2]=a[...,2]*0.88+0.04   # warm, lifted blacks
    a=a*0.92+0.05
    yy,xx=np.mgrid[0:H,0:W]; v=1-0.55*(((xx-W/2)/W)**2+((yy-H/2)/H)**2)*2.2
    return Image.fromarray((np.clip(a*v[...,None],0,1)*255).astype(np.uint8))
def grain(im,amt):
    n=np.random.normal(0,amt,(H//2,W//2)); n=np.kron(n,np.ones((2,2)))
    return Image.fromarray(np.clip(np.asarray(im,float)+n[...,None],0,255).astype(np.uint8))
def leak(im,strength):
    x=rnd.randint(-200,W); L=Image.new("RGB",(W,H)); d=ImageDraw.Draw(L)
    d.ellipse([x,-300,x+900,H+300],fill=(255,110,30)); L=L.filter(ImageFilter.GaussianBlur(160))
    return ImageChops.add(im,Image.eval(L,lambda v:int(v*strength)))
def stamp(im,txt):
    d=ImageDraw.Draw(im); f=font(54)
    for o in (6,3): d.text((W-330,H-120),txt,font=f,fill=(255,120,20))
    d.text((W-330,H-120),txt,font=f,fill=(255,190,90)); return im
def frame_border(im):  # flipbook page edge + corner number
    d=ImageDraw.Draw(im); d.rectangle([0,0,W-1,H-1],outline=(40,30,20),width=14); return im
seg=NFR/len(order); cache={}
for i in range(NFR):
    t=i/NFR; gi=min(int(i/seg),len(order)-1); g=order[gi]; beat=i%FPB==0; bar=i%(FPB*4)==0
    hold=2 if (i//FPB)%8==7 else 1                        # mostly 1 photo per frame, breather every 8th beat
    pool=pools[g]; idx=(i//hold)%len(pool) if hold>1 else rnd.randrange(len(pool))
    p=pool[idx]
    if p not in cache: cache[p]=fit(p)
    im=cache[p]
    if beat:  # punch-in zoom on each beat
        z=1.08; c=im.crop((int(W*(1-1/z)/2),int(H*(1-1/z)/2),int(W*(1+1/z)/2),int(H*(1+1/z)/2))).resize((W,H))
        im=c
    # sketch -> colour: pure pencil for first half, develops through 3rd quarter, full film after
    mix=np.clip((t-0.45)/0.3,0,1)
    out=sketch(im) if mix<1 else None
    col=film(im,t)
    out=col if out is None else Image.blend(out,col,float(mix))
    dx,dy=rnd.randint(-10,10),rnd.randint(-6,6)            # gate weave
    out=ImageChops.offset(out,dx,dy)
    out=grain(out,14 if mix>0 else 7)
    if mix>0 and (bar or rnd.random()<0.12): out=leak(out,0.6 if bar else 0.3)
    if bar and i>0: out=Image.blend(out,Image.new("RGB",(W,H),(255,250,235)),0.55)   # flash on downbeat
    stamp(out,years[g]); frame_border(out)
    out.save(f"{OUT}/{i:04d}.png")
print("frames",NFR)
