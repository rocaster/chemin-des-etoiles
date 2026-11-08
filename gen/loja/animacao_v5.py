"""Pipeline v5 inteiramente novo: fontes GenerateImage → chroma → rig por partes.
Não importa geradores/contornos antigos. Não altera fogueira/avatares/paletas.
Os 18 originais novos + proveniência estão em fontes-v5/.
"""
from pathlib import Path
from functools import lru_cache
import colorsys,json,math
from collections import deque
from PIL import Image,ImageDraw,ImageFilter,ImageFont,ImageChops
ROOT=Path(__file__).resolve().parents[2]
FONTES=Path(__file__).resolve().parent/'fontes-v5'
PETS=['dragao','lobo','raposa','tigre','corvo','fenix','gato','cervo','coruja','coelho']
HEROIS=[f'{c}-{g}' for c in ['cavaleiro','arqueiro','mago','bardo'] for g in ['m','f']]
NOMES_PETS=['Dragão bebê','Lobo','Raposa','Tigre','Corvo místico','Fênix','Gato das sombras','Cervo dourado','Coruja sábia','Coelho cristal']
NOMES_HEROIS=['Cavaleiro','Cavaleira','Arqueiro','Arqueira','Mago','Maga','Bardo','Barda']
QUADROS=8
PALETAS={None:None,'esmeralda':145,'ametista':275,'rubi':350}
DISTINTOS={
'dragao':'Bebê verde de cabeça arredondada, olhos âmbar, barriga marfim, chifres, asas turquesa e cauda em lança; inclina cabeça, abre asa e balança cauda.',
'lobo':'Lobinho cinza prateado com grandes orelhas, rufos de pelo, peito/patas claros e cauda grossa; cabeça curiosa, orelha e cauda móveis.',
'raposa':'Raposinha ruiva de grandes olhos, orelhas altas e cauda volumosa com ponta marfim; inclina cabeça, mexe orelha e abana a cauda.',
'tigre':'Tigrinho laranja com bochechas creme, listras marrons e patas grossas; cabeça curiosa, orelha redonda e cauda listrada móveis.',
'corvo':'Corvinho violeta cabeçudo, grande bico, olhos luminosos e penas em camadas; inclina cabeça e abre/fecha asa e cauda de penas.',
'fenix':'Fênix dourada com crista e longas penas flamejantes; cabeça inclinável, asa e leque da cauda articulados.',
'gato':'Gatinho roxo de olhos dourados, peito lilás, patas arredondadas e cauda com fumacinha; cabeça, orelha e cauda independentes.',
'cervo':'Cervato dourado sentado, orelhas largas, pintas, pequenos cascos e chifres dourados; cabeça inclinável, orelha e cauda móveis.',
'coruja':'Corujinha marrom de discos creme, olhos castanhos e óculos de latão; inclina cabeça, mexe tufo e abre uma asa.',
'coelho':'Coelhinho branco-azulado de orelhas cristalinas, uma dobrada, olhos castanhos e cauda de algodão; cabeça, orelha e cauda móveis.'}
STYLE={'versao':5,'origem':'18 desenhos novos GenerateImage; nenhum sprite/contorno de pet anterior usado','quadros':8,'tamanho_quadro':[48,48],'tamanho_heroi':[96,128],'trabalho_pets':[96,96],'trabalho_herois':[96,128],'vista':'três quartos','contorno':'marrom quente sem preto puro','fundo':'transparente','linha_pes':43,'animacao':'rig por partes: corpo, cabeça, braços/asas, orelhas/cauda; não translação da imagem inteira'}


def limpar_fonte(path,tamanho,limite,base_y):
    im=Image.open(path).convert('RGB');px=im.load();mask=Image.new('L',im.size);mp=mask.load()
    # Chroma magenta/rosa (varia um pouco entre as 18 fontes JPEG). Não rembg,
    # não há download/modelo/credencial; branco/cristais ficam preservados.
    for y in range(im.height):
        for x in range(im.width):
            r,g,b=px[x,y]
            key=r>b*.95 and r>g*1.6 and b>g*1.5 and min(r,b)>65 and r+b-2*g>150
            mp[x,y]=0 if key else 255
            if not key and max(r,g,b)<38:px[x,y]=(62,43,33)
    # Remove só componentes de chroma grandes/conectados ao fundo. Reflexos
    # rosa internos na roupa/cabelo NÃO são buracos de transparência.
    candidates=bytearray(mask.tobytes());alpha=bytearray([255])*len(candidates)
    w,h=im.size
    for start in range(len(candidates)):
        if candidates[start]!=0:continue
        q=deque([start]);candidates[start]=1;component=[];edge=False
        while q:
            pos=q.popleft();component.append(pos);x=pos%w;y=pos//w
            edge=edge or x==0 or y==0 or x==w-1 or y==h-1
            for nb in ([pos-1] if x else [])+([pos+1] if x<w-1 else [])+([pos-w] if y else [])+([pos+w] if y<h-1 else []):
                if candidates[nb]==0:candidates[nb]=1;q.append(nb)
        if edge or len(component)>3000:
            for pos in component:alpha[pos]=0
    mask=Image.frombytes('L',im.size,bytes(alpha))
    rgba=im.convert('RGBA');rgba.putalpha(mask)
    crop=rgba.crop(mask.getbbox());w,h=crop.size
    scale=min(limite[0]/w,limite[1]/h)
    crop=crop.resize((round(w*scale),round(h*scale)),Image.Resampling.BOX)
    crop=grade_limpa(crop,56)
    out=Image.new('RGBA',tamanho);out.alpha_composite(crop,((tamanho[0]-crop.width)//2,base_y-crop.height+1))
    return out


def grade_limpa(im,cores=56,palette=None):
    alpha=im.getchannel('A').point(lambda n:255 if n>=128 else 0)
    rgb=im.convert('RGB')
    q=(rgb.quantize(palette=palette,dither=Image.Dither.NONE) if palette else rgb.quantize(colors=cores,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)).convert('RGBA');q.putalpha(alpha)
    # Transparência canônica, sem restos rosa escondidos/contorno preto puro.
    p=q.load()
    for y in range(q.height):
        for x in range(q.width):
            r,g,b,a=p[x,y]
            if not a:p[x,y]=(0,0,0,0)
            elif max(r,g,b)<35:p[x,y]=(62,43,33,255)
    return q


def preparar_fontes():
    for tipo in PETS+HEROIS:
        hero=tipo in HEROIS;folder=FONTES/('herois' if hero else 'pets');folder.mkdir(exist_ok=True)
        size=(192,256) if hero else (192,192)
        im=limpar_fonte(FONTES/'originais'/f'{tipo}.jpg',size,(172,236) if hero else (172,168),245 if hero else 175)
        im.save(folder/f'{tipo}.png',optimize=True)
    base.cache_clear()


@lru_cache(maxsize=18)
def base(tipo):
    hero=tipo in HEROIS
    return grade_limpa(Image.open(FONTES/('herois' if hero else 'pets')/f'{tipo}.png').resize((96,128) if hero else (96,96),Image.Resampling.BOX),64)


def fonte(n):
    p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(str(p),n) if p.exists() else ImageFont.load_default(size=n)

if __name__=='__main__':preparar_fontes()

@lru_cache(maxsize=1)
def rigs():return json.loads((FONTES/'rigs.json').read_text(encoding='utf-8'))


def mascara_poligono(size,points):
    mask=Image.new('L',size);ImageDraw.Draw(mask).polygon([tuple(p) for p in points],fill=255)
    return mask


def mascara_tecido(tipo,im):
    mask=Image.new('L',im.size);m=mask.load();p=im.load()
    classe=tipo.split('-')[0]
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=p[x,y]
            if not a:continue
            h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            ok=False
            if classe=='cavaleiro':ok=y>32 and .54<h<.76 and s>.42
            elif classe=='arqueiro':ok=y>32 and .19<h<.48 and s>.20
            elif classe=='mago':
                ok=.64<h<.87 and s>.25
                # Cabelo/rosto/olhos da maga são identidade, não roupa.
                if tipo=='mago-f' and ((33<x<59 and 23<y<47) or (58<x<70 and 28<y<70) or (29<x<40 and 31<y<61)):ok=False
                if tipo=='mago-m' and 34<x<57 and 22<y<40:ok=False
            elif classe=='bardo':
                ok=(h<.06 or h>.94) and s>.45 and v>.10
                if 35<x<60 and 15<y<36:ok=False
            if ok:m[x,y]=255
    return mask


def recolorir(tipo,im,paleta):
    if paleta is None:return im.copy()
    if paleta not in PALETAS:raise ValueError('Paleta inválida')
    im=im.copy();m=mascara_tecido(tipo,im);p=im.load()
    for y in range(im.height):
        for x in range(im.width):
            if not m.getpixel((x,y)):continue
            r,g,b,a=p[x,y];h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            c=colorsys.hsv_to_rgb(PALETAS[paleta]/360,s,v)
            p[x,y]=tuple(round(n*255) for n in c)+(a,)
    return im


@lru_cache(maxsize=72)
def separar(tipo,paleta=None):
    spec=rigs()[tipo];im=recolorir(tipo,base(tipo),paleta) if tipo in HEROIS else base(tipo).copy()
    masks={part['nome']:mascara_poligono(im.size,part['poligono']) for part in spec['partes']}
    # Orelha/tufo/chifre é filha da cabeça. As demais partes são independentes.
    for part in spec['partes']:
        for poly in part.get('poligonos_extra',[]):
            masks[part['nome']]=ImageChops.lighter(masks[part['nome']],mascara_poligono(im.size,poly))
    groups={};used=Image.new('L',im.size)
    for part in reversed(spec['partes']):
        name=part['nome'];mask=masks[name]
        if part['papel']=='orelha':mask=ImageChops.multiply(mask,masks['cabeca'])
        mask=ImageChops.subtract(mask,used);mask=ImageChops.multiply(mask,im.getchannel('A'))
        layer=im.copy();layer.putalpha(mask);groups[name]=layer
        used=ImageChops.lighter(used,mask)
    body=im.copy();body.putalpha(ImageChops.subtract(im.getchannel('A'),used))
    # Underpainting na silhueta NOVA: tronco sob livro/alaúde/braços e
    # sobreposição de juntas. Sem isso um recorte plano deixa fendas ao girar.
    # Propaga cor do próprio tronco, nunca o item que foi destacado.
    repair=Image.new('L',im.size);rd=ImageDraw.Draw(repair)
    nx,ny=spec['partes'][0]['pivo']
    if tipo in HEROIS:
        rd.polygon([(33,34),(62,34),(72,64),(68,79),(28,79),(26,54)],fill=255)
    else:
        rd.polygon([(nx-20,ny-6),(nx+20,ny-6),(nx+22,spec['linha_pes']-6),(nx-16,spec['linha_pes']-6)],fill=255)
    if spec.get('reparo_extra'):rd.polygon([tuple(p) for p in spec['reparo_extra']],fill=255)
    for part in spec['partes']:
        if part['papel']=='orelha':continue
        x,y=part['pivo'];rd.ellipse((x-6,y-6,x+6,y+6),fill=255)
    repair=ImageChops.multiply(repair,im.getchannel('A'))
    bp=body.load();queue=deque();seen=set()
    for y in range(im.height):
        for x in range(im.width):
            if bp[x,y][3]:queue.append((x,y,bp[x,y]));seen.add((x,y))
    while queue:
        x,y,c=queue.popleft()
        for xx,yy in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
            if not(0<=xx<im.width and 0<=yy<im.height) or (xx,yy) in seen or not repair.getpixel((xx,yy)):continue
            seen.add((xx,yy));bp[xx,yy]=c;queue.append((xx,yy,c))
    groups['corpo']=body
    return groups


ANGLES=[0,2,5,3,1,-2,-5,-3]
TAIL=[0,7,13,6,-2,-8,-13,-6]
ARM=[0,-4,-8,-5,1,5,8,4]
FREE=[0,4,8,11,5,-3,-7,-4]
BREATH=[1,1.008,1.018,1.008,1,.992,.985,.992]


def transformar(layer,angle,pivot,dy=0,dx=0):
    return layer.rotate(angle,resample=Image.Resampling.NEAREST,center=tuple(pivot),translate=(dx,dy))


def quadro_trabalho(tipo,n,paleta=None):
    if tipo not in PETS+HEROIS or n not in range(QUADROS):raise ValueError('Personagem/quadro inválido')
    spec=rigs()[tipo];parts=separar(tipo,paleta);size=tuple(spec['tamanho']);foot=spec['linha_pes']
    result=Image.new('RGBA',size);head=parts['cabeca'].copy();entries={p['nome']:p for p in spec['partes']}
    for p in spec['partes']:
        if p['papel']=='orelha':
            ear=transformar(parts[p['nome']],TAIL[(n+1)%8]*.55,p['pivo'])
            head.alpha_composite(ear)
    # Camada de trás: cauda. Corpo respira com pés ancorados no estrado.
    for p in spec['partes']:
        if p['papel']=='cauda':result.alpha_composite(transformar(parts[p['nome']],TAIL[n],p['pivo']))
    scale=BREATH[n]
    body=parts['corpo'].transform(size,Image.Transform.AFFINE,(1,0,0,0,1/scale,foot-foot/scale),resample=Image.Resampling.NEAREST)
    result.alpha_composite(body)
    dy=round((entries['cabeca']['pivo'][1]-foot)*(scale-1))
    for p in spec['partes']:
        role=p['papel']
        if role not in {'asa','item','braco'}:continue
        angles=TAIL if role=='asa' else ARM if role=='item' else FREE
        result.alpha_composite(transformar(parts[p['nome']],angles[n],p['pivo'],dy))
    # Inclinação + pequeno deslocamento lateral, não translação de todo sprite.
    result.alpha_composite(transformar(head,ANGLES[n],entries['cabeca']['pivo'],dy,1 if n in (2,3,4) else -1 if n in (6,7) else 0))
    return result


@lru_cache(maxsize=10)
def paleta_pet(tipo):
    frames=[quadro_trabalho(tipo,n).resize((48,48),Image.Resampling.BOX) for n in range(8)]
    return sheet(frames).convert('RGB').quantize(colors=56,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)


def quadro_pet(tipo,n):
    if tipo not in PETS:raise ValueError('Pet inválido')
    return grade_limpa(quadro_trabalho(tipo,n).resize((48,48),Image.Resampling.BOX),56,palette=paleta_pet(tipo))


def quadro_heroi(tipo,n,paleta=None):
    if tipo not in HEROIS:raise ValueError('Herói inválido')
    return quadro_trabalho(tipo,n,paleta)


def sheet(frames):
    w,h=frames[0].size;out=Image.new('RGBA',(w*len(frames),h))
    for n,f in enumerate(frames):out.paste(f,(w*n,0))
    return out


def gif(frames,path,size=None):
    # Fundo neutro no GIF para evitar halos/limites de transparência do formato.
    seq=[]
    for f in frames:
        if size:f=f.resize(size,Image.Resampling.NEAREST)
        b=Image.new('RGB',f.size,'#e8dcc0');b.paste(f,(0,0),f);seq.append(b)
    seq[0].save(path,save_all=True,append_images=seq[1:],duration=350,loop=0,disposal=2,optimize=False)


def board(ids,names,path,hero=False,frame=0):
    cols=4 if hero else 5;cw=480;ch=620 if hero else 540
    b=Image.new('RGB',(cols*cw,100+math.ceil(len(ids)/cols)*ch),'#e8dcc0');d=ImageDraw.Draw(b)
    d.text((30,16),'NOVAS POSES V5 · HERÓIS' if hero else 'COMPANHEIROS V5 · DEZ DESENHOS NOVOS',font=fonte(27),fill='#583e2e')
    d.text((30,56),'Cabeça e membros articulados · 8 quadros · fontes novas / fundo transparente',font=fonte(18),fill='#7a6048')
    for i,(tipo,nome) in enumerate(zip(ids,names)):
        x=(i%cols)*cw;y=100+(i//cols)*ch
        d.rounded_rectangle((x+10,y,x+cw-10,y+ch-12),radius=12,fill='#f7efd9',outline='#bca47e',width=2)
        im=quadro_trabalho(tipo,frame).resize((384,512) if hero else (384,384),Image.Resampling.NEAREST)
        b.paste(im,(x+48,y+8),im)
        d.text((x+24,y+(520 if hero else 393)),nome,font=fonte(21),fill='#553a28')
        # Todos os quadros reais no tamanho esperado pelo aplicativo.
        if not hero:
            for n in range(8):
                f=quadro_pet(tipo,n);b.paste(f,(x+48+n*48,y+435),f)
            d.text((x+48,y+492),'Matriz 96 px ↑ · jogo 48 px / 8 quadros ↑',font=fonte(13),fill='#826d50')
    b.save(path)
    return b


def gerar_pets(root=ROOT,previews=True):
    out=root/'static/loja/pets';out.mkdir(parents=True,exist_ok=True)
    for t in PETS:sheet([quadro_pet(t,n) for n in range(8)]).save(out/f'{t}.png',optimize=True)
    (out.parent/'pets-design.json').write_text(json.dumps(DISTINTOS,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    (out.parent/'pets-estilo.json').write_text(json.dumps(STYLE,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    if previews:
        dest=root.parent/'prints-loja';dest.mkdir(exist_ok=True,parents=True);(dest/'anim').mkdir(exist_ok=True)
        board(PETS,NOMES_PETS,dest/'arte-pets-preview.png')
        for t in PETS:gif([quadro_trabalho(t,n) for n in range(8)],dest/'anim'/f'{t}.gif',(384,384))
        frames=[board(PETS,NOMES_PETS,dest/'anim'/f'.pets-{n}.png',frame=n) for n in range(8)]
        frames[0].save(dest/'anim/todos-pets.gif',save_all=True,append_images=frames[1:],duration=350,loop=0,disposal=2,optimize=False)
        for n in range(8):(dest/'anim'/f'.pets-{n}.png').unlink()


def gerar_herois(root=ROOT,previews=True):
    out=root/'static/loja/herois/poses-v5';out.mkdir(parents=True,exist_ok=True)
    for t in HEROIS:
        for p in PALETAS:
            sheet([quadro_heroi(t,n,p) for n in range(8)]).save(out/(t+(f'-{p}' if p else '')+'.png'),optimize=True)
    if previews:
        dest=root.parent/'prints-loja';dest.mkdir(exist_ok=True,parents=True);(dest/'anim').mkdir(exist_ok=True)
        board(HEROIS,NOMES_HEROIS,dest/'poses-herois-preview.png',True)
        for t in HEROIS:gif([quadro_heroi(t,n) for n in range(8)],dest/'anim'/f'{t}.gif',(384,512))
        frames=[board(HEROIS,NOMES_HEROIS,dest/'anim'/f'.herois-{n}.png',True,n) for n in range(8)]
        frames[0].save(dest/'anim/todos-herois.gif',save_all=True,append_images=frames[1:],duration=350,loop=0,disposal=2,optimize=False)
        for n in range(8):(dest/'anim'/f'.herois-{n}.png').unlink()


def exportar_partes():
    for t in PETS+HEROIS:
        out=FONTES/'partes'/t;out.mkdir(parents=True,exist_ok=True)
        for name,im in separar(t).items():im.save(out/f'{name}.png',optimize=True)
        if t in HEROIS:mascara_tecido(t,base(t)).save(out/'mascara-tecido.png')
