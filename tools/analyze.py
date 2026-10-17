import librosa,numpy as np,glob,sys
for f in sorted(glob.glob("*.mp3")):
    y,sr=librosa.load(f,sr=22050,mono=True)
    tempo,beats=librosa.beat.beat_track(y=y,sr=sr); bt=librosa.frames_to_time(beats,sr=sr)
    onset=librosa.onset.onset_strength(y=y,sr=sr); rms=librosa.feature.rms(y=y)[0]
    hop=512/sr; win=int(30/hop)
    # best 30s window: high loudness + strong beat pulse, starting on a beat
    best=(0,0)
    for s in bt[::4]:
        a=int(s/hop); 
        if a+win>len(rms): break
        sc=rms[a:a+win].mean()*onset[a:a+win].mean()*(1-rms[a:a+win].std()/rms[a:a+win].mean()*0.5)
        if sc>best[0]: best=(sc,s)
    reg=np.std(np.diff(bt))/np.mean(np.diff(bt))
    print(f"{f:26s} dur={len(y)/sr:5.0f}s bpm={float(np.atleast_1d(tempo)[0]):6.1f} beat_jitter={reg:.3f} punch={onset.mean():.2f} best30@{best[1]:.1f}s score={best[0]*100:.2f}")
