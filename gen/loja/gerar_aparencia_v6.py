"""Derivados de apresentação v6. Nunca sobrescreve arte original/fogueira.
Mapa: recorte da pose v5. Combate: somente tecido, geometria dos 12 quadros intacta.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import colorsys,math
ROOT=Path(__file__).resolve().parents[2]
HEROIS=[f'{c}-{g}' for c in ('cavaleiro','arqueiro','mago','bardo') for g in ('m','f')]
CORES={'esmeralda':145,'ametista':275,'rubi':350}

# Os mesmos pivôs/transformações do acervo de combate; só usados para
# localizar o tecido, sem regenerar atores, animação ou geometria.
QUADROS=[(0,0,0,1),(0,0,0,.975),(-2,0,-5,1),(9,-3,10,1),(-5,0,-7,1),(-2,0,-3,1),(-2,0,-18,1),(-6,2,-50,1),(-10,5,-84,.96),(0,0,0,.9),(0,-13,0,1.04),(0,-6,0,1)]
def tecido(avatar,x,y,rgba,quadro=0):
    r,g,b,a=rgba
    if not a:return False
    h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
    dx,dy,graus,ey=QUADROS[quadro]
    a=math.radians(graus);xx=x-64-dx;yy=y-94-dy
    x,y=64+math.cos(a)*xx+math.sin(a)*yy,94+(-math.sin(a)*xx+math.cos(a)*yy)/ey
    classe=avatar.split('-')[0]
    if classe=='cavaleiro':return y>30 and .54<h<.76 and s>.38
    if classe=='arqueiro':return .19<h<.48 and s>.20
    if classe=='mago':
        # Cabelo violeta e brilho na palma da maga compartilham matizes do
        # manto. Preservar cabeça/chapéu/cabelos/magia é mais importante que
        # recolorir todo pixel roxo: o tecido livre abaixo deles recebe a cor.
        return y>68 and .64<h<.87 and s>.25
    return y>30 and (h<.05 or h>.94) and s>.45 and v>.10

def main():
    mapa=ROOT/'static/loja/mapa';batalha=ROOT/'static/loja/batalha'
    mapa.mkdir(parents=True,exist_ok=True);batalha.mkdir(parents=True,exist_ok=True)
    for avatar in HEROIS:
        for paleta in (None,*CORES):
            nome=avatar+(f'-{paleta}' if paleta else '')
            im=Image.open(ROOT/f'static/loja/herois/poses-v5/{nome}.png').convert('RGBA').crop((16,0,80,64))
            retrato=Image.new('RGBA',(64,64),'#9c8b66');retrato.alpha_composite(im)
            mask=Image.new('L',(64,64));ImageDraw.Draw(mask).ellipse((1,1,62,62),fill=255)
            retrato.putalpha(mask);retrato.save(mapa/f'{nome}.png',optimize=True)
            retrato.resize((128,128),Image.Resampling.NEAREST).save(mapa/f'{nome}@2x.png',optimize=True)
        src=Image.open(ROOT/f'static/batalha/heroi-{avatar}.png').convert('RGBA')
        mini=src.resize((1536,100),Image.Resampling.NEAREST)
        assert mini.resize(src.size,Image.Resampling.NEAREST).tobytes()==src.tobytes(), 'Fonte mudou de grade'
        for paleta,graus in CORES.items():
            novo=mini.copy();p=novo.load()
            for y in range(100):
                for x in range(1536):
                    rgba=p[x,y]
                    if tecido(avatar,x%128,y,rgba,quadro=x//128):
                        h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in rgba[:3]))
                        p[x,y]=tuple(round(c*255) for c in colorsys.hsv_to_rgb(graus/360,s,v))+(rgba[3],)
            novo.resize(src.size,Image.Resampling.NEAREST).save(batalha/f'{avatar}-{paleta}.png',optimize=True)
    print('64 retratos de mapa v5 + 24 paletas de combate; originais intactos.')
if __name__=='__main__':main()
