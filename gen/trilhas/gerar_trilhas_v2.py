#!/usr/bin/env python3
"""Original SNES-inspired soundtrack, deterministic synthesis (numpy/scipy + ffmpeg).
Run: /tmp/ytv/bin/python /workspace/ncl/gen/trilhas/gerar_trilhas_v2.py
No reference recording is sampled; battle/boss and all game code are read-only.
Circular note tails and circular hall convolution make steady-state musical loops.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, zipfile, sys
import numpy as np
from scipy.signal import resample_poly
from scipy.io import wavfile
ROOT=Path('/workspace/ncl'); OUT=ROOT/'out/static/audio/trilhas'; BK=Path('/tmp/bk-trilhas-v1')
SR=22050
SPECS=[('mapa',70,'Fá maior',20,-32,65,'Sereno e pastoral; harpa, cordas e melodia suave.'),('missao',100,'Fá maior',32,-23,65,'Aventura heroica: introdução, A, B com metais, interlúdio e reprise.'),('conversa',66,'Si bemol maior',20,-30,70,'Diálogo espaçado; harpa e cordas, sem bateria.'),('historia',88,'Fá maior',24,-25,65,'Balada de bardo; harpa em primeiro plano e bateria leve.'),('biblioteca',64,'Ré menor',20,-28,62,'Contemplativo: cordas e harpa, sem bateria.'),('cartas',84,'Ré menor harmônico',24,-25,62,'Mistério: arpejos, pulso melódico e percussão delicada.')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):return subprocess.run(args,check=True,**kw)
def adsr(t,d,attack,release,sustain=.72):
    # Note lasts d; release continues beyond the gate.
    env=np.minimum(t/max(attack,.001),1)*(sustain+(1-sustain)*np.exp(-t/0.15))
    return env*np.minimum(np.maximum((d+release-t)/release,0),1)
def tone(midi,d,kind):
    rel={'strings':.55,'harp':1.3,'lead':.14,'brass':.22,'bass':.1,'flute':.32}[kind]
    t=np.arange(round((d+rel)*SR))/SR; f=440*2**((midi-69)/12)
    p=2*np.pi*f*t
    if kind=='harp':
        s=sum(a*np.sin(p*h)*np.exp(-t*(2.2+h*.38)) for h,a in [(1,1),(2,.42),(3,.23),(4,.12),(6,.04)])
        e=np.minimum(t/.003,1)*np.minimum(np.maximum((d+rel-t)/.18,0),1)
    elif kind=='strings':
        s=np.zeros_like(t)
        for det in [-.003,0,.0035]:
            for h in range(1,9):s+=np.sin(p*h*(1+det)+.18*h)*np.exp(-h/4)/h/3
        e=adsr(t,d,.28,rel,.9)
    elif kind=='lead':
        # Band-limited pulse with mellow triangle fundamental and delayed vibrato.
        pv=p+.028*np.sin(2*np.pi*5.1*t)*np.minimum(t/.25,1)
        s=sum(np.sin(pv*h)*np.sin(np.pi*.48*h)/h*np.exp(-h/11) for h in range(1,17))
        s+=.25*np.sin(pv); e=adsr(t,d,.018,rel,.72)
    elif kind=='flute':
        # Soft 16-bit woodwind; generated harmonics, no external samples.
        pv=p+.014*np.sin(2*np.pi*4.8*t)*np.minimum(t/.3,1)
        s=np.sin(pv)+.18*np.sin(2*pv)+.045*np.sin(3*pv)
        e=adsr(t,d,.055,rel,.82)
    elif kind=='brass':
        s=sum(np.sin(p*h)*np.exp(-h/6)/h for h in range(1,14))
        s+=.15*np.sin(p*1.002);e=adsr(t,d,.065,rel,.8)
    else:
        s=np.sin(p)+.28*np.sin(2*p)+.12*np.sin(3*p)
        e=adsr(t,d,.006,rel,.55)*np.exp(-t*.8)
    return (s*e).astype(np.float32)
def drum(kind,rng):
    dur={'kick':.24,'snare':.19,'hat':.07,'crash':1.3}[kind];t=np.arange(int(dur*SR))/SR
    noise=rng.standard_normal(len(t)); high=noise-np.concatenate(([0],noise[:-1]))
    if kind=='kick':s=np.sin(2*np.pi*(47*t+65*.035*(1-np.exp(-t/.035))))*np.exp(-t*22)
    elif kind=='snare':s=(.32*np.sin(2*np.pi*185*t)+.35*high)*np.exp(-t*28)
    elif kind=='hat':s=.15*high*np.exp(-t*65)
    else:s=.22*high*np.exp(-t*3.8)
    return (s*np.minimum(t/.002,1)).astype(np.float32)
def add(buf,s,start,gain,pan):
    i=round(start*SR)%len(buf); weights=np.array([np.cos((pan+1)*np.pi/4),np.sin((pan+1)*np.pi/4)])*gain
    s=s[:,None]*weights
    k=min(len(s),len(buf)-i);buf[i:i+k]+=s[:k]
    if k<len(s):buf[:len(s)-k]+=s[k:]
# Original scale-degree phrases, one bar per tuple (degrees measured from tonic).
A=[[(2,1),(4,1),(3,.5),(2,.5),(0,1)],[(1,1.5),(2,.5),(4,2)],[(5,1),(4,.5),(3,.5),(2,1),(0,1)],[(2,2),(1,1),(0,1)],[(3,1),(5,1),(4,1),(3,1)],[(2,1.5),(0,.5),(1,1),(2,1)],[(1,1),(2,1),(3,1),(1,1)],[(4,2),(6,1),(4,1)]]
B=[[(5,1.5),(7,.5),(6,1),(5,1)],[(4,1),(5,1),(7,2)],[(8,1),(7,1),(5,1),(4,1)],[(6,2),(4,2)],[(5,1),(4,.5),(3,.5),(5,1),(7,1)],[(6,1.5),(5,.5),(4,1),(2,1)],[(3,1),(2,1),(1,1),(3,1)],[(4,1.5),(3,.5),(1,1),(6,1)]]
# Plaza-only original folk-like phrases, lighter than the quest theme.
PRACA_A=[[(0,1),(2,.5),(3,.5),(4,1),(2,1)],[(1,1),(2,1),(4,2)],[(5,1.5),(4,.5),(2,1),(0,1)],[(2,1),(1,1),(2,2)],[(3,1),(4,.5),(5,.5),(7,1),(5,1)],[(4,1),(2,1),(0,2)],[(1,1),(3,1),(2,1),(1,1)],[(4,2),(3,1),(6,1)]]
PRACA_B=[[(5,1),(7,1),(5,1),(4,1)],[(4,1.5),(2,.5),(4,2)],[(3,1),(5,1),(7,1),(5,1)],[(6,2),(4,2)],[(7,1),(5,.5),(4,.5),(2,1),(5,1)],[(5,1),(3,1),(4,2)],[(3,1),(2,1),(1,2)],[(4,1),(3,1),(1,1),(6,1)]]
PRACA_SPEC=('praca',94,'Fá maior',28,-27,65,'Praça livre: passeio alegre e relaxado, harpa, cordas, pulso melódico e metais discretos.')
# Character selection: NEW melodies, not rotations/transpositions of A/B/PRACA.
# E-flat major, 80 BPM, 22 bars (2 intro + 8 A + 8 B + 4 return) = 66 seconds.
PERSONAGEM_SPEC=('personagem',80,'Mi bemol maior',22,-27,63,'Fogueira acolhedora no inicio da jornada: harpa, flauta 16-bit, cordas quentes, baixo redondo e percussao muito suave.')
PERSONAGEM_A=[[(0,1),(2,1.5),(4,.5),(2,1)],[(5,1),(4,1),(2,.5),(1,.5),(0,1)],[(3,1.5),(5,.5),(7,1),(5,1)],[(4,2),(2,1),(0,1)],[(5,1),(7,1),(6,.5),(5,.5),(4,1)],[(3,1),(1,1),(2,1),(3,1)],[(5,1.5),(4,.5),(3,1),(2,1)],[(1,1),(4,1),(6,1.5),(4,.5)]]
PERSONAGEM_B=[[(7,1.5),(5,.5),(3,2)],[(5,1),(7,1),(9,1),(7,1)],[(8,1),(5,1),(3,1),(1,1)],[(6,2),(4,1),(1,1)],[(2,1.5),(4,.5),(6,1),(4,1)],[(5,1),(7,1),(5,2)],[(3,1),(5,1),(4,1),(3,1)],[(4,1.5),(6,.5),(8,1),(6,1)]]
PERSONAGEM_RETURN=[[(0,2),(2,1),(4,1)],[(5,1),(3,1),(2,2)],[(1,1.5),(3,.5),(5,1),(3,1)],[(4,2),(1,1),(6,1)]]
def build(spec,seed):
    name,bpm,key,bars,target,tonic,mood=spec;beat=60/bpm; n=round(bars*4*beat*SR);buf=np.zeros((n,2),np.float32);rng=np.random.default_rng(seed)
    minor=name in ('biblioteca','cartas'); scale=[0,2,3,5,7,8,10] if minor else [0,2,4,5,7,9,11]
    if name=='cartas':scale[-1]=11
    def note(deg,octave=0):return tonic+12*octave+12*(deg//7)+scale[deg%7]
    # Triads and bass inversions: descending I-V/7-vi-iii-IV-I/3-ii-V.
    progA=[(0,2,4,0),(4,6,8,-1),(5,7,9,-2),(2,4,6,-5),(3,5,7,-4),(0,2,4,-5),(1,3,5,-6),(4,6,8,-3)]
    progB=[(3,5,7,-4),(0,2,4,0),(1,3,5,-6),(4,6,8,-3),(5,7,9,-2),(3,5,7,-4),(1,3,5,-6),(4,6,8,-3)]
    if name=='personagem':
        progA=[(0,2,4,0),(0,2,5,0),(3,5,7,-4),(0,2,4,-5),(5,7,9,-2),(1,3,5,-6),(3,5,7,-4),(4,6,8,-3)]
        progB=[(3,5,7,-4),(5,7,9,-2),(1,3,5,-6),(4,6,8,-3),(2,4,6,-5),(5,7,9,-2),(3,5,7,-4),(4,6,8,-3)]
    def section(bar):
        if name=='personagem':
            if bar<2:return 'intro',bar
            if bar<10:return 'A',bar-2
            if bar<18:return 'B',bar-10
            return 'return',bar-18
        if name=='praca':
            if bar<4:return 'intro',bar
            if bar<12:return 'A',bar-4
            if bar<20:return 'B',bar-12
            return 'A',bar-20
        if name=='missao':
            if bar<4:return 'intro',bar
            if bar<12:return 'A',bar-4
            if bar<20:return 'B',bar-12
            if bar<24:return 'inter',bar-20
            return 'A',bar-24
        if bars==20:
            if bar<4:return 'intro',bar
            return ('A',bar-4) if bar<12 else ('B',bar-12)
        return ('A',bar) if bar<8 else (('B',bar-8) if bar<16 else ('A',bar-16))
    for bar in range(bars):
        sec,idx=section(bar);ch=(progB if sec=='B' else progA)[idx%8];start=bar*4*beat
        if sec in ('intro','inter') and idx==3:ch=progA[-1]
        if name=='personagem' and sec=='return':ch=[progA[0],progA[2],progA[5],progA[7]][idx]
        for j,deg in enumerate(ch[:3]):add(buf,tone(note(deg,-1),4*beat,'strings'),start,.08 if name=='personagem' else .095,[-.65,.1,.65][j])
        # Arpeggiation continues under each phrase, without a repeated ostinato melody.
        steps=8 if name not in ('conversa','biblioteca') else 4
        if name=='personagem' and sec=='intro':steps=4
        pattern=[0,1,2,1,0,2,1,2]
        for k in range(steps):
            deg=ch[pattern[(k+bar%2)%8]];amp=.17 if name=='historia' else (.095 if name=='personagem' else .11)
            add(buf,tone(note(deg),.36*beat,'harp'),start+k*4/steps*beat,amp,(-.45 if k%2==0 else .45))
        if name not in ('biblioteca','conversa'):
            for b in ([0,2] if name in ('mapa','historia','praca','personagem') else [0,1.5,2,3]):
                add(buf,tone(note(ch[3],-2),.63*beat,'bass'),start+b*beat,.1 if name=='personagem' else (.15 if name!='mapa' else .07),0)
        # Distinct transpositions/phrase rotations yield six original related themes.
        phrases=B if sec=='B' else A
        rotation={'mapa':2,'missao':0,'conversa':4,'historia':1,'biblioteca':3,'cartas':5,'praca':0,'personagem':0}[name]
        if name=='praca':phrases=PRACA_B if sec=='B' else PRACA_A
        if name=='personagem':phrases=PERSONAGEM_RETURN if sec=='return' else (PERSONAGEM_B if sec=='B' else PERSONAGEM_A)
        phrase=phrases[(idx+rotation)%len(phrases)]
        melodic=sec not in ('intro','inter')
        if name in ('conversa','biblioteca','mapa') and idx%2==1:melodic=False
        if melodic:
            pos=0
            for j,(deg,length) in enumerate(phrase):
                # library uses a restrained harp response instead of bright lead.
                kind='harp' if name in ('historia','biblioteca') else ('flute' if name=='personagem' else 'lead')
                gain={'mapa':.075,'missao':.24,'conversa':.065,'historia':.22,'biblioteca':.12,'cartas':.16,'praca':.145,'personagem':.13}[name]
                if name in ('conversa','biblioteca') and j>1:pos+=length;continue
                add(buf,tone(note(deg),length*beat*.86,kind),start+pos*beat,gain,.08)
                if sec=='B' and name=='missao':add(buf,tone(note(deg,-1),length*beat*.88,'brass'),start+pos*beat,.16,-.18)
                if sec=='B' and name=='praca':add(buf,tone(note(deg,-1),length*beat*.72,'brass'),start+pos*beat,.045,-.2)
                if sec=='B' and name=='personagem':add(buf,tone(note(deg,-1),length*beat*.7,'harp'),start+pos*beat,.032,-.2)
                pos+=length
        if name in ('missao','historia','cartas','praca') and sec not in ('intro','inter'):
            strength={'missao':1,'historia':.38,'cartas':.3,'praca':.48}[name]
            for b in [0,2]:add(buf,drum('kick',rng),start+b*beat,.23*strength,0)
            for b in [1,3]:add(buf,drum('snare',rng),start+b*beat,.15*strength,.12)
            for k in range(8):add(buf,drum('hat',rng),start+k*.5*beat,.15*strength,.42)
            if idx==0 and sec=='B':add(buf,drum('crash',rng),start,.14*strength,-.35)
        if name=='personagem' and sec not in ('intro','return') and bar%2:
            add(buf,drum('kick',rng),start,.035,0)
            for b in [1.5,3.5]:add(buf,drum('hat',rng),start+b*beat,.035,.35)
    # Diffuse hall: circular convolution preserves reverb tails across the loop.
    impulse=np.zeros((n,2),np.float32)
    for c in range(2):
        for delay,g in [(.039,.23),(.071,.17),(.113,.12),(.173,.08)]:impulse[int((delay+c*.006)*SR),c]+=g
        count=int(2.9*SR);tt=np.arange(count)/SR
        diffuse=rng.standard_normal(count)*np.exp(-tt*2.1)*.0018
        diffuse[:int(.03*SR)]=0;impulse[:count,c]+=diffuse
    wet=np.fft.irfft(np.fft.rfft(buf,axis=0)*np.fft.rfft(impulse,axis=0),n=n,axis=0)
    buf=buf+.8*wet
    buf=resample_poly(buf,2,1,axis=0)
    # Codec-safe micro-envelope only at the seam (30 ms per side, 10 ms guard).
    # No musical outro/fade-out: the last dominant resolves immediately to tonic.
    # Circular tails preserve the arrangement; guard suppresses Vorbis edge ringing.
    k=1323;hold=441;u=np.linspace(0,1,k-hold);w=np.concatenate([np.ones(hold),(1+np.cos(np.pi*u))/2])
    buf[:k]*=(1-w[:,None])
    buf[-k:]*=(1-w[::-1,None])
    rms=np.sqrt(np.mean(buf**2));buf*=10**(target/20)/rms
    return np.clip(np.rint(buf*32767),-32768,32767).astype('<i2')
def main():
    BK.mkdir(exist_ok=True)
    protected={p.name:sha(p) for name in ['batalha','chefe'] for p in [OUT/f'trilha-{name}.wav',OUT/f'trilha-{name}.ogg']}
    for name,*_ in SPECS:
        for ext in ['wav','ogg']:
            p=OUT/f'trilha-{name}.{ext}'
            if not (BK/p.name).exists():shutil.copy2(p,BK/p.name)
    old=json.loads((ROOT/'gen/trilhas/relatorio-trilhas.json').read_text());rows={r['name']:r for r in old}; samples=[]
    for i,spec in enumerate(SPECS):
        name,bpm,key,bars,target,tonic,mood=spec
        pcm=build(spec,20261107+i);wav=OUT/f'trilha-{name}.wav';ogg=wav.with_suffix('.ogg')
        wavfile.write(wav,44100,pcm)
        run(['ffmpeg','-y','-v','error','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)])
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(ogg),'-f','f32le','-acodec','pcm_f32le','-'])
        dec=np.frombuffer(raw,np.float32).reshape(-1,2);x=pcm.astype(np.float64)/32768
        rms=float(20*np.log10(np.sqrt(np.mean(x*x))));ogg_rms=float(20*np.log10(np.sqrt(np.mean(dec*dec))))
        seam=float(np.max(np.abs(dec[-1]-dec[0])));deltas=np.max(np.abs(np.diff(dec,axis=0)),axis=1)
        p99=float(np.percentile(deltas,99));peak=float(20*np.log10(np.max(np.abs(x))))
        assert abs(rms-target)<1.5 and abs(ogg_rms-target)<1.5
        assert seam < .001  # decoded OGG boundary discontinuity below -60 dBFS, (name,seam,p99)
        assert len(dec)==len(pcm), (name,len(dec),len(pcm))
        row=dict(name=name,bpm=bpm,key=key,bars=bars,duration_s=round(len(x)/44100,3),mood=mood,peak_dbfs=round(peak,2),rms_dbfs=round(rms,2),target_rms_dbfs=target,loop_seam_delta=float(np.max(np.abs(x[-1]-x[0]))),neighbor_delta_p99=p99,ogg_duration_s=round(len(dec)/44100,3),ogg_rms_dbfs=round(ogg_rms,2),ogg_seam_delta=seam,ogg_seam_dbfs=round(20*np.log10(max(seam,1e-12)),2),wav=str(wav),ogg=str(ogg),wav_bytes=wav.stat().st_size,ogg_bytes=ogg.stat().st_size,version=2,generator='gen/trilhas/gerar_trilhas_v2.py',loop_method='Caudas e reverberação circulares; ponte cosseno local de 30 ms, sem fade-out.',reference='M. J. Hood Music — 16-Bit Fantasy RPG Adventure Music 1 (estilo; melodias originais)',wav_sha256=sha(wav),ogg_sha256=sha(ogg))
        rows[name]=row
        # Audition excerpts alone normalized to -21 dBFS so the soft tracks are audible;
        # production WAV/OGG keep their original requested low targets.
        start=int((12 if name!='missao' else 26)*44100);snippet=x[start:start+20*44100].copy()
        snippet*=10**(-21/20)/np.sqrt(np.mean(snippet**2));fade=np.linspace(0,1,441)
        snippet[:441]*=fade[:,None];snippet[-441:]*=fade[::-1,None]
        samples.extend([snippet,np.zeros((int(.65*44100),2))]);print(json.dumps(row,ensure_ascii=False),flush=True)
    for filename,digest in protected.items():assert sha(OUT/filename)==digest
    (ROOT/'gen/trilhas/relatorio-trilhas.json').write_text(json.dumps([rows[r['name']] for r in old],ensure_ascii=False,indent=2)+'\n')
    sample=ROOT/'previews/trilhas-v2-amostra.mp3';tmp=Path('/tmp/trilhas-v2-amostra.wav')
    wavfile.write(tmp,44100,(np.concatenate(samples)*32767).astype(np.int16))
    run(['ffmpeg','-y','-v','error','-i',str(tmp),'-c:a','libmp3lame','-b:a','160k',str(sample)])
    patch=ROOT/'patch-trilhas-v2.zip'
    with zipfile.ZipFile(patch,'w',zipfile.ZIP_DEFLATED) as z:
        for name,*_ in SPECS:
            p=OUT/f'trilha-{name}.ogg';z.write(p,f'static/audio/trilhas/{p.name}')
    assert sample.stat().st_size<10_000_000 and patch.stat().st_size<25_000_000
    (ROOT/'gen/trilhas/verificacao-trilhas-v2.json').write_text(json.dumps(dict(protected_sha256=protected,protected_unchanged=True,sample_bytes=sample.stat().st_size,patch_bytes=patch.stat().st_size,sample_order=[s[0] for s in SPECS],sample_note='Somente na amostra: trechos de 20 s normalizados a -21 dBFS; lacunas de 0,65 s. Arquivos do jogo mantêm RMS solicitado.'),ensure_ascii=False,indent=2)+'\n')
    print('OK: 6 loops decodificados, RMS e emendas verificados; batalha/chefe idênticos; amostra e patch prontos.',flush=True)
def main_praca():
    """Generate ONLY plaza assets. All pre-existing WAV/OGG files are hash-protected."""
    protected={p.name:sha(p) for p in OUT.iterdir() if p.suffix in ('.wav','.ogg') and not p.name.startswith('trilha-praca.')}
    pcm=build(PRACA_SPEC,2026110707);x=pcm.astype(np.float64)/32768
    wav=OUT/'trilha-praca.wav';ogg=wav.with_suffix('.ogg');wavfile.write(wav,44100,pcm)
    run(['ffmpeg','-y','-v','error','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)])
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(ogg),'-f','f32le','-acodec','pcm_f32le','-'])
    dec=np.frombuffer(raw,np.float32).reshape(-1,2)
    rms=float(20*np.log10(np.sqrt(np.mean(x*x))));ogg_rms=float(20*np.log10(np.sqrt(np.mean(dec*dec))))
    seam=float(np.max(np.abs(dec[-1]-dec[0])))
    assert len(dec)==len(pcm) and abs(rms+27)<1.5 and abs(ogg_rms+27)<1.5 and seam<.001
    row=dict(name='praca',bpm=94,key='Fá maior',bars=28,duration_s=round(len(x)/44100,3),mood=PRACA_SPEC[-1],rms_dbfs=round(rms,2),target_rms_dbfs=-27,peak_dbfs=round(float(20*np.log10(np.max(np.abs(x)))),2),loop_seam_delta=float(np.max(np.abs(x[-1]-x[0]))),ogg_duration_s=round(len(dec)/44100,3),ogg_rms_dbfs=round(ogg_rms,2),ogg_seam_delta=seam,ogg_seam_dbfs=round(20*np.log10(max(seam,1e-12)),2),wav=str(wav),ogg=str(ogg),wav_bytes=wav.stat().st_size,ogg_bytes=ogg.stat().st_size,version=2,generator='gen/trilhas/gerar_trilhas_v2.py --only-praca',loop_method='Caudas/reverberação circulares; proteção cosseno de 30 ms; sem fade-out musical.',wav_sha256=sha(wav),ogg_sha256=sha(ogg))
    report=ROOT/'gen/trilhas/relatorio-trilhas.json';rows=json.loads(report.read_text());rows=[r for r in rows if r['name']!='praca'];rows.append(row)
    report.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    # Sample keeps the actual production level, to audition its -27 dBFS density.
    run(['ffmpeg','-y','-v','error','-ss','13','-i',str(wav),'-t','30','-af','afade=t=in:d=0.02,afade=t=out:st=29.9:d=0.1','-c:a','libmp3lame','-b:a','160k',str(ROOT/'previews/trilha-praca-amostra.mp3')])
    for filename,digest in protected.items():assert sha(OUT/filename)==digest
    print(json.dumps(row,ensure_ascii=False,indent=2));print('Oito trilhas anteriores intactas (WAV e OGG).')
def main_personagem():
    """Generate ONLY character music, append measurements, preserve all older assets."""
    protected={p.name:sha(p) for p in OUT.iterdir() if p.suffix in ('.wav','.ogg') and not p.name.startswith('trilha-personagem.')}
    for phrase in PERSONAGEM_A+PERSONAGEM_B+PERSONAGEM_RETURN:assert sum(n for _,n in phrase)==4
    assert PERSONAGEM_A not in (A,B,PRACA_A,PRACA_B) and PERSONAGEM_B not in (A,B,PRACA_A,PRACA_B)
    pcm=build(PERSONAGEM_SPEC,2026110710);x=pcm.astype(np.float64)/32768
    wav=OUT/'trilha-personagem.wav';ogg=wav.with_suffix('.ogg');wavfile.write(wav,44100,pcm)
    run(['ffmpeg','-y','-v','error','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)])
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(ogg),'-f','f32le','-acodec','pcm_f32le','-'])
    dec=np.frombuffer(raw,np.float32).reshape(-1,2)
    rms=float(20*np.log10(np.sqrt(np.mean(x*x))));ogg_rms=float(20*np.log10(np.sqrt(np.mean(dec*dec))))
    seam=float(np.max(np.abs(dec[-1]-dec[0])));duration=len(x)/44100
    assert len(dec)==len(pcm) and 60<=duration<=75
    assert abs(rms+27)<.1 and abs(ogg_rms+27)<.5 and seam<.001
    assert np.max(np.abs(x))<.95 and np.isfinite(dec).all()
    row=dict(name='personagem',bpm=80,key='Mi bemol maior',bars=22,duration_s=round(duration,3),mood=PERSONAGEM_SPEC[-1],instruments=['harpa sintetizada','flauta suave 16-bit','cordas em tres vozes','baixo senoidal','bumbo e chocalho sintetizados muito discretos'],arrangement='2 compassos introdutorios + 8 A + 8 B + 4 retorno; dominante resolve na tonica no reinicio',rms_dbfs=round(rms,2),target_rms_dbfs=-27,peak_dbfs=round(float(20*np.log10(np.max(np.abs(x)))),2),loop_seam_delta=float(np.max(np.abs(x[-1]-x[0]))),ogg_duration_s=round(len(dec)/44100,3),ogg_rms_dbfs=round(ogg_rms,2),ogg_seam_delta=seam,ogg_seam_dbfs=round(20*np.log10(max(seam,1e-12)),2),wav=str(wav),ogg=str(ogg),wav_bytes=wav.stat().st_size,ogg_bytes=ogg.stat().st_size,version=2,generator='gen/trilhas/gerar_trilhas_v2.py --only-personagem',loop_method='Notas e hall circulares; guarda de 10 ms e ponte cosseno local de 30 ms por lado como nas v2. Sem fade-out musical.',reference='M. J. Hood Music — 16-Bit Fantasy RPG Adventure Music 1: referencia de estilo; todas as notas e timbres sao sintetizados, sem amostras ou melodia da referencia.',composition_sha256=hashlib.sha256(json.dumps([PERSONAGEM_A,PERSONAGEM_B,PERSONAGEM_RETURN]).encode()).hexdigest(),wav_sha256=sha(wav),ogg_sha256=sha(ogg))
    report=ROOT/'gen/trilhas/relatorio-trilhas.json';rows=json.loads(report.read_text())
    assert all(r['key']!=row['key'] for r in rows if r['name']!='personagem')
    praca=next(r for r in rows if r['name']=='praca');assert abs(ogg_rms-praca['ogg_rms_dbfs'])<.5
    rows=[r for r in rows if r['name']!='personagem'];rows.append(row)
    report.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    sample=ROOT/'trilha-personagem-amostra.mp3'
    run(['ffmpeg','-y','-v','error','-ss','9','-i',str(wav),'-t','30','-af','afade=t=in:d=0.02,afade=t=out:st=29.9:d=0.1','-c:a','libmp3lame','-b:a','160k',str(sample)])
    for filename,digest in protected.items():assert sha(OUT/filename)==digest
    verify=ROOT/'gen/trilhas/verificacao-trilhas-v2.json';v=json.loads(verify.read_text())
    v['personagem']=dict(protected_other_tracks_sha256=protected,protected_unchanged=True,ogg_matches_master_frames=True,duration_in_requested_range=True,level_matches_praca_db=round(ogg_rms-praca['ogg_rms_dbfs'],3),sample=str(sample),sample_bytes=sample.stat().st_size,sample_seconds=30,sample_note='Trecho 9–39 s no nivel real de producao, sem normalizacao extra; fade curto apenas no MP3 de demonstracao.',ogg_seam_delta=seam,ogg_seam_below_minus60_dbfs=seam<.001,master_excluded_from_deploy=True,reference_sampled=False,subjective_listening_done=False)
    verify.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(row,ensure_ascii=False,indent=2),flush=True)
    print('OK: loop e RMS verificados; nove trilhas anteriores identicas; amostra de 30 s pronta.',flush=True)
if __name__=='__main__':
    if '--only-personagem' in sys.argv and '--only-praca' in sys.argv:raise SystemExit('Escolha somente uma opcao --only-.')
    if '--only-personagem' in sys.argv:main_personagem()
    elif '--only-praca' in sys.argv:main_praca()
    else:main()
