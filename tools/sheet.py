import sys,glob,os
from PIL import Image,ImageDraw
fs=sorted(glob.glob(sys.argv[1]+"/*.png")); W,H,C=240,120,10
c=Image.new("RGB",(W*C,H*((len(fs)+C-1)//C)),(40,170,160)); d=ImageDraw.Draw(c)
for i,f in enumerate(fs):
    im=Image.open(f); im.thumbnail((W-6,H-16)); x,y=(i%C)*W,(i//C)*H
    c.paste(im,(x+3,y+14),im); d.text((x+3,y+1),os.path.basename(f)[:-4],fill=(255,255,255))
c.save(sys.argv[2],quality=85)
