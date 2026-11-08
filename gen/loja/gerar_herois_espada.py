"""Sprites derivados EXCLUSIVOS de /heroi e da prévia de paletas na loja.

Não sobrescreve fogueira, avatares, paletas anteriores ou telas congeladas.
Edição inteira na grade nativa de 4 px, sem interpolação. Mantém a pose,
cabeça, roupa e pés do cavaleiro-m; só ele troca a lenha por espada.
Todos os outros personagens, incluindo cavaleira, usam arquivos originais.
A cavaleira já segura uma espada: sua arte é preservada.

Uso: python gen/loja/gerar_herois_espada.py
Se quiser regenerar tudo: gerar_arte.py primeiro, este script depois.
"""
from pathlib import Path
import colorsys
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DESTINO = ROOT / 'static/loja/herois/espada'
NOMES = {'cavaleiro-m':'Cavaleiro','cavaleiro-f':'Cavaleira','arqueiro-m':'Arqueiro',
         'arqueiro-f':'Arqueira','mago-m':'Mago','mago-f':'Maga','bardo-m':'Bardo','bardo-f':'Barda'}
# ponta, guarda, pomo, meia largura da lâmina (coordenadas nativas).
ESPADAS = {'cavaleiro-m': ((53,29),(28,41),(18,46),2.3)}


def pano(cor, paleta):
    """Apenas reconstruções sob o objeto removido seguem o tecido comprado."""
    if not paleta:
        return cor
    r,g,b = (int(cor[i:i+2],16)/255 for i in (1,3,5))
    h,s,v=colorsys.rgb_to_hsv(r,g,b)
    rgb=colorsys.hsv_to_rgb(paleta['matiz']/360,s,v)
    return '#'+''.join(f'{round(v*255):02x}' for v in rgb)


def poligono(im,pontos,cor):
    ImageDraw.Draw(im).polygon(pontos,fill=cor)


def retirar_objeto(im, avatar, paleta):
    """Apenas lenha do cavaleiro masculino; nenhuma máscara para outro herói."""
    if avatar != 'cavaleiro-m':
        raise ValueError('Só cavaleiro-m pode ter arte derivada.')
    original=im.copy()
    shape=[(22,41),(35,35),(41,32),(48,28),(51,28),(54,31),(54,37),
           (46,41),(36,46),(29,50),(24,49),(22,47)]
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon(shape,fill=255)
    for y in range(im.height):
        for x in range(im.width):
            if not mask.getpixel((x,y)):continue
            if x>41:
                im.putpixel((x,y),(0,0,0,0))
            else:
                # Aço/tecido sob a lenha: a túnica continua a mesma.
                cor=pano('#072c72' if x<33 else '#031c50',paleta)
                if y<39 and x<37:cor='#8c8884' if (x+y)%4<2 else '#55535c'
                if x in (26,34):cor='#86602d'
                if y>47:cor='#201d25'
                im.putpixel((x,y),tuple(int(cor[i:i+2],16) for i in (1,3,5))+(255,))
    # Sem ombro "cortado" atrás da mão direita.
    poligono(im,[(40,37),(44,37),(46,41),(40,45),(37,44)],'#171823')
    return original


def espada(im,ponta,guarda,pomo,largura):
    """Aço frio, filete luminoso, guarda dourada e punho de couro escuro.
    Polígonos rasterizados em coordenadas inteiras; nada de filtro ou blur.
    """
    d=ImageDraw.Draw(im)
    gx,gy=guarda;tx,ty=ponta;px,py=pomo
    dist=math.hypot(tx-gx,ty-gy);ux,uy=(tx-gx)/dist,(ty-gy)/dist
    nx,ny=-uy,ux
    def point(a,b):return (round(a),round(b))
    def offset(x,y,n):return point(x+nx*n,y+ny*n)
    # Punho e pomo vêm antes da lâmina, para não ocultar a junção.
    d.line([pomo,guarda],fill='#241b28',width=5)
    d.line([pomo,guarda],fill='#68432f',width=3)
    d.line([offset(px,py,-.7),offset(gx,gy,-.7)],fill='#ac7950',width=1)
    for f in (.25,.5,.75):
        x,y=px+(gx-px)*f,py+(gy-py)*f
        d.line([offset(x,y,-1),offset(x,y,1)],fill='#362533',width=1)
    d.ellipse((px-2,py-2,px+2,py+2),fill='#282132',outline='#a97b3e')
    d.point(point(px-1,py-1),fill='#f1d78d')
    # Silhueta da lâmina e três planos de aço. A ponta converge sem corte.
    base=(gx+ux*2,gy+uy*2)
    left=offset(*base,largura);right=offset(*base,-largura)
    shoulder=(tx-ux*4,ty-uy*4)
    pts=[left,offset(*shoulder,largura*.7),ponta,offset(*shoulder,-largura*.7),right]
    d.polygon(pts,fill='#393746')
    center=point(*base)
    d.polygon([center,offset(*base,largura-1),offset(*shoulder,max(.4,largura-1.3)),ponta],fill='#dddcc8')
    d.polygon([center,offset(*base,-(largura-1)),offset(*shoulder,-max(.4,largura-1.3)),ponta],fill='#8196a4')
    d.line([center,ponta],fill='#eff4df',width=1)
    # Guarda: metal dourado, sem mudar a roupa ou a pose das mãos.
    a=offset(gx,gy,5);b=offset(gx,gy,-5)
    d.line([a,guarda,b],fill='#322330',width=4)
    d.line([a,guarda,b],fill='#ab7838',width=2)
    d.line([offset(gx-ux,gy-uy,4),offset(gx-ux,gy-uy,-4)],fill='#edd393',width=1)
    d.point(guarda,fill='#dcaa51')


def recuperar_maos(im,original,avatar):
    """Mãos originais por cima da empunhadura; não cria outra pose."""
    if avatar != 'cavaleiro-m':
        raise ValueError('Só cavaleiro-m pode ter arte derivada.')
    polygons={'cavaleiro-m': [[(18,41),(21,41),(25,44),(24,48),(21,48),(18,45)],[(44,35),(50,35),(50,38),(47,41),(43,40)]]}
    mask=Image.new('L',im.size);d=ImageDraw.Draw(mask)
    for poly in polygons.get(avatar,[]):d.polygon(poly,fill=255)
    # Limita à mão visível: transparentes não recortam a espada por acidente.
    alpha=original.getchannel('A')
    from PIL import ImageChops
    mask=ImageChops.multiply(mask,alpha)
    im.paste(original,(0,0),mask)


def derivar(source,avatar,paleta=None):
    if avatar != 'cavaleiro-m':
        raise ValueError('Só cavaleiro-m pode ter arte derivada.')
    source=source.convert('RGBA')
    im=source.resize((source.width//4,source.height//4),Image.Resampling.NEAREST)
    if avatar in ESPADAS:
        original=retirar_objeto(im,avatar,paleta)
        espada(im,*ESPADAS[avatar])
        recuperar_maos(im,original,avatar)
    return im.resize(source.size,Image.Resampling.NEAREST)


def gerar():
    DESTINO.mkdir(parents=True,exist_ok=True)
    try:
        from .limpar_derivados_obsoletos import limpar
    except ImportError:
        from limpar_derivados_obsoletos import limpar
    limpar(DESTINO)
    catalogo=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'))
    paletas=[None]+[i for i in catalogo['itens'] if i['categoria']=='personagem']
    arquivos=[]
    for avatar in ESPADAS:
        for paleta in paletas:
            suffix='-'+paleta['paleta'] if paleta else ''
            source=ROOT/('static/loja/paletas/'+avatar+suffix+'.png' if paleta else 'static/fogueira/sprite-'+avatar+'-aberto.png')
            destino=DESTINO/(avatar+suffix+'.png')
            derivar(Image.open(source),avatar,paleta).save(destino,optimize=True)
            arquivos.append(destino)
            # Apenas os olhos fechados são transplantados; nada de recolorir
            # novamente roupa/espada ou trocar a pose no segundo quadro.
            caixas = {'cavaleiro-m':(24,16,34,20)}
            caixa=tuple(v*4 for v in caixas[avatar])
            fechado=Image.open(ROOT/('static/fogueira/sprite-'+avatar+'-fechado.png')).convert('RGBA')
            frame=Image.open(destino).convert('RGBA')
            frame.paste(fechado.crop(caixa),caixa[:2])
            outro=DESTINO/(avatar+suffix+'-fechado.png')
            frame.save(outro,optimize=True)
            arquivos.append(outro)
    return arquivos


def preview(destino):
    """Prancha de arte, não screenshot. Oito poses × quatro cores."""
    import sys
    sys.path.insert(0,str(ROOT))
    from herois import sprite_heroi
    paletas=[None,'esmeralda','ametista','rubi']
    font=ImageFont.load_default(size=15)
    board=Image.new('RGB',(880,8*290+70),'#25323e');d=ImageDraw.Draw(board)
    d.text((20,12),'V3: SO CAVALEIRO-M DERIVADO - demais artes originais, inclusive cavaleira',fill='#f5dda3',font=font)
    for i,n in enumerate(['Original','Esmeralda','Ametista','Rubi']):d.text((i*220+60,42),n,fill='#adbec7',font=font)
    for row,(avatar,nome) in enumerate(NOMES.items()):
        y=70+row*290
        d.line((10,y,870,y),fill='#536373')
        for col,paleta in enumerate(paletas):
            im=Image.open(ROOT/'static'/sprite_heroi(avatar,paleta)).convert('RGBA')
            im=im.resize((im.width//2,im.height//2),Image.Resampling.NEAREST)
            x=col*220+(220-im.width)//2
            board.paste(im,(x,y+22),im)
        d.text((10,y+270),nome,fill='#f5dda3',font=font)
    destino=Path(destino);destino.parent.mkdir(parents=True,exist_ok=True);board.save(destino)


if __name__=='__main__':
    files=gerar()
    preview(ROOT.parent/'prints-loja/heroi-espada-preview.png')
    print(f'{len(files)} sprites derivados: só cavaleiro-m. Outros 7 personagens usam originais.')
