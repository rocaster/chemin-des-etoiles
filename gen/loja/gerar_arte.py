"""Arte original determinística em pixels (Pillow), sem rede nem arquivos privados.
Executar da raiz: python gen/loja/gerar_arte.py. Não altera os sprites originais.
"""
from pathlib import Path
import colorsys
import json
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'static/loja'
for folder in ('pets', 'selos', 'paletas'):
    (OUT / folder).mkdir(parents=True, exist_ok=True)

# Pet pipeline v5: cada espécie tem anatomia e silhueta próprias.
try:
    from .gerar_pets import quadro_pet as pet, PETS
except ImportError:
    from gerar_pets import quadro_pet as pet, PETS
for kind in PETS:
    sheet = Image.new('RGBA', (384,48))
    for frame in range(8): sheet.paste(pet(kind,frame), (frame*48,0))
    sheet.save(OUT/'pets'/f'{kind}.png', optimize=True)

# Selos originais, 32 px, linguagem comum de medalhão e símbolos únicos.
icons = ['castelo','invicto','primeira','teimoso','falador','preciso','atrapalhado']
for i,kind in enumerate(icons):
    im=Image.new('RGBA',(32,36));d=ImageDraw.Draw(im)
    d.polygon([(7,23),(7,35),(15,30),(23,35),(23,23)],fill='#88434b')
    d.regular_polygon((16,16,14),8,fill='#5f422c',outline='#231c25')
    d.regular_polygon((16,16,11),8,fill='#d6ac5e',outline='#ffdf8c')
    ink='#4a3541'
    if kind=='castelo':
        for x in (9,15,21):d.rectangle((x,10,x+2,22),fill=ink)
        d.rectangle((9,16,23,22),fill=ink);d.rectangle((15,18,17,23),fill='#f8d280')
    elif kind=='invicto':d.polygon([(9,9),(23,9),(22,20),(16,25),(10,20)],fill=ink)
    elif kind=='primeira':d.text((13,9),'1',fill=ink)
    elif kind=='teimoso':d.arc((9,9,23,23),20,310,fill=ink,width=3);d.polygon([(20,8),(25,11),(20,13)],fill=ink)
    elif kind=='falador':d.rectangle((8,10,24,20),fill=ink);d.polygon([(10,19),(10,24),(16,20)],fill=ink)
    elif kind=='preciso':d.line([(9,16),(14,21),(23,11)],fill=ink,width=3)
    else:d.line([(11,11),(21,21)],fill=ink,width=3);d.line([(21,11),(11,21)],fill=ink,width=3)
    im.save(OUT/'selos'/f'{kind}.png',optimize=True)

catalog=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'))
for source in sorted((ROOT/'static/fogueira').glob('sprite-*-aberto.png')):
    avatar=source.stem.removeprefix('sprite-').removesuffix('-aberto');classe=avatar.split('-')[0]
    for palette in (i for i in catalog['itens'] if i['categoria']=='personagem'):
        im=Image.open(source).convert('RGBA');px=im.load();w,h=im.size
        for y in range(h):
            for x in range(w):
                r,g,b,a=px[x,y]
                if not a:continue
                hue,sat,val=colorsys.rgb_to_hsv(r/255,g/255,b/255)
                match = {'cavaleiro':.52<hue<.72,'arqueiro':.18<hue<.47,'mago':.69<hue<.88,'bardo':(hue<.055 or hue>.96) and y>h*.33}[classe]
                if match and sat>.35:
                    rgb=colorsys.hsv_to_rgb(palette['matiz']/360,sat,val)
                    px[x,y]=tuple(round(c*255) for c in rgb)+(a,)
        im.save(OUT/'paletas'/f'{avatar}-{palette["paleta"]}.png',optimize=True)
print('10 pets × 4 quadros, 7 selos, 24 recolorações de tecido gerados.')
