# cut every car out, keep only clean full-car side/3-4 shots, save RGBA crops + stats
import sys,os,glob,json
import numpy as np
from PIL import Image,ImageOps,ImageFilter
from scipy import ndimage
from rembg import remove,new_session
src,dst=sys.argv[1],sys.argv[2]; os.makedirs(dst,exist_ok=True)
sess=new_session("isnet-general-use"); meta=[]
for f in sorted(glob.glob(f"{src}/*/*.jpg")):
    gen=f.split("/")[-2]; key=f"{gen}_{os.path.basename(f)[:-4]}"; out=f"{dst}/{key}.png"
    try: im=ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    except Exception: continue
    im.thumbnail((1600,1600))
    a=np.asarray(remove(im,session=sess,only_mask=True),float)/255
    H,W=a.shape; solid=a>0.5
    lab,n=ndimage.label(solid)
    if n==0: continue
    sizes=ndimage.sum(solid,lab,range(1,n+1)); big=np.argmax(sizes)+1; comp=lab==big
    area=comp.sum()/(H*W); share=sizes.max()/sizes.sum()
    ys,xs=np.where(comp); x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max(); bw,bh=x1-x0,y1-y0
    fuzzy=((a>0.08)&(a<0.92)).sum()/max(1,comp.sum())
    fill=comp.sum()/(bw*bh)
    why=[]
    if area<0.12: why.append("small")
    if share<0.85: why.append("multi")
    if x0<4 or x1>W-5 or y0<4: why.append("cropped")
    if not 1.55<bw/bh<3.4: why.append("aspect")
    if fuzzy>0.18: why.append("fuzzy")
    if not 0.45<fill<0.85: why.append("fill")
    if why: continue
    alpha=np.where(comp|((a>0.5)&ndimage.binary_dilation(comp,iterations=6)),a,0)
    alpha=ndimage.binary_fill_holes(alpha>0.5)*np.maximum(alpha,0)  # keep windows solid-ish
    rgba=np.dstack([np.asarray(im),(np.clip(alpha,0,1)*255).astype(np.uint8)])[y0:y1+1,x0:x1+1]
    Image.fromarray(rgba).save(out)
    # paint colour: median of saturated body pixels
    px=np.asarray(im)[y0:y1+1,x0:x1+1][alpha[y0:y1+1,x0:x1+1]>0.9]
    hsv=np.asarray(Image.fromarray(px[None].astype(np.uint8)).convert("HSV"))[0]
    sat=hsv[hsv[:,1]>90]; hue=float(np.median(sat[:,0])) if len(sat)>len(hsv)*0.15 else -1
    meta.append(dict(key=key,gen=gen,src=f,aspect=bw/bh,hue=hue,val=float(np.median(hsv[:,2]))))
    print(key,round(bw/bh,2),hue,flush=True)
json.dump(meta,open(f"{dst}/meta.json","w"),indent=1)
print("kept",len(meta))
