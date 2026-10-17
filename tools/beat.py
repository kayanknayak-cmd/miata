# synth 144 BPM retro beat, 30s
import numpy as np,wave,sys
sr=44100; bpm=144; spb=60/bpm; dur=float(sys.argv[2]) if len(sys.argv)>2 else 30; n=int(sr*dur); y=np.zeros(n)
def add(at,sig):
    s=int(at*sr); e=min(n,s+len(sig)); y[s:e]+=sig[:e-s]
t=lambda d:np.arange(int(sr*d))/sr
kick=np.sin(2*np.pi*(50+90*np.exp(-t(.3)*30))*t(.3))*np.exp(-t(.3)*9)
sn=(np.random.randn(len(t(.2)))*.6+np.sin(2*np.pi*190*t(.2))*.4)*np.exp(-t(.2)*18)
hat=np.random.randn(len(t(.05)))*np.exp(-t(.05)*90)*.25
roots=[45,45,40,43]  # A F# ... bass notes (midi-ish -> hz below)
hz=lambda m:440*2**((m-69)/12)
for b in range(int(dur/spb)):
    T=b*spb; bar=b//4
    if b%4 in (0,2) or (b%8==7): add(T,kick)
    if b%4 in (1,3): add(T,sn*.8)
    for k in range(2): add(T+k*spb/2,hat*(1 if k else .6))
    f=hz(roots[bar%4]); tt=t(spb*.9)
    add(T,np.sign(np.sin(2*np.pi*f*tt))*.12*np.exp(-tt*3))
    if b>=36: add(T+spb/2,np.sin(2*np.pi*f*4*tt[:len(tt)//2])*.08*np.exp(-tt[:len(tt)//2]*8))  # arp joins in 2nd half
y=np.tanh(y*1.4)*.8
# vinyl crackle
cr=np.zeros(n); idx=np.random.randint(0,n,int(dur*25)); cr[idx]=np.random.randn(len(idx))*.3; y+=cr
w=wave.open(sys.argv[1],"wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((np.clip(y,-1,1)*32767).astype(np.int16).tobytes()); w.close()
