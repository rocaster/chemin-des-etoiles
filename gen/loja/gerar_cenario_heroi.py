"""Diorama original procedimental em pixel art; sem rede/arte externa."""
from pathlib import Path
from PIL import Image,ImageDraw
import random
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'static/loja/cenario'

def gerar():
    OUT.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(224,192),'#192c34');d=ImageDraw.Draw(im);r=random.Random(711)
    # Céu/claridade filtrada, em faixas discretas (não blur).
    cores=['#1d3238','#223c40','#29474a','#325452','#3a6057']
    for i,c in enumerate(cores):d.rectangle((0,24+i*23,224,51+i*23),fill=c)
    for x in [7,29,188,213]:
        d.polygon([(x-12,0),(x+13,0),(x+8,139),(x-9,143)],fill='#1b292f')
        d.line((x+3,10,x,132),fill='#33483d',width=3)
        d.polygon([(x-38,0),(x+40,0),(x+33,35),(x+15,47),(x-21,44)],fill='#1e3a3b')
    for i in range(80):
        x,y=r.randrange(224),r.randrange(8,143);col=r.choice(['#3a5847','#48634d','#2c4a42'])
        d.rectangle((x,y,x+3,y+2),fill=col)
    # Raios quentes sem halo suave; linguagem de luz pixelada.
    for poly in [[(126,0),(143,0),(81,136),(54,137)],[(153,0),(161,0),(120,142),(103,142)]]:
        layer=Image.new('RGBA',im.size);ImageDraw.Draw(layer).polygon(poly,fill='#e9d28d16')
        im=Image.alpha_composite(im.convert('RGBA'),layer);d=ImageDraw.Draw(im)
    d.polygon([(0,146),(32,137),(76,143),(120,133),(175,142),(224,134),(224,192),(0,192)],fill='#354b3d')
    for i in range(130):
        x,y=r.randrange(224),r.randrange(143,192);d.line((x,y,x+2,y-2),fill=r.choice(['#56744b','#6a7a51','#293c33']))
    # Pequeno estrado de pedra, não moldura: chão comum do herói e pet.
    d.ellipse((22,145,209,181),fill='#16282c');d.ellipse((25,139,207,174),fill='#5b6963')
    d.rectangle((27,147,205,159),fill='#626e66');d.ellipse((27,134,205,165),fill='#9a9d80')
    d.ellipse((33,136,200,160),fill='#a9aa8a')
    for a,b in [((55,139),(65,157)),((94,136),(95,161)),((134,136),(132,160)),((175,140),(167,158)),((39,148),(190,149))]:d.line((a,b),fill='#777f6b',width=1)
    for i in range(18):
        x=r.randrange(25,205);y=r.choice([157,163,167]);d.rectangle((x,y,x+4,y+1),fill='#697b50')
    # Lanterna lateral, flores e cogumelos: detalhes de refúgio, sem competir.
    d.rectangle((16,102,18,151),fill='#4e3e31');d.line((17,103,29,103),fill='#9c8050',width=2)
    d.rectangle((24,105,33,119),fill='#6f5232');d.rectangle((26,108,31,116),fill='#f1ce75')
    d.rectangle((25,106,32,107),fill='#b69255');d.rectangle((27,110,29,114),fill='#fff0b3')
    for x,y in [(14,164),(195,172),(207,153)]:
        d.rectangle((x,y,x+1,y+6),fill='#c6b886');d.rectangle((x-3,y-2,x+4,y+1),fill='#9b6950');d.point((x-1,y-1),fill='#dfc69a')
    im.save(OUT/'refugio.png',optimize=True)
    cushion=Image.new('RGBA',(48,32));p=ImageDraw.Draw(cushion)
    p.ellipse((3,22,45,30),fill='#13252e77')
    p.polygon([(4,17),(10,12),(38,12),(44,17),(42,25),(8,25)],fill='#493b42')
    p.polygon([(6,16),(12,10),(37,10),(42,16),(38,22),(11,22)],fill='#82766e')
    p.line([(8,17),(14,13),(35,13),(40,17)],fill='#c5aa77',width=1)
    p.line([(13,21),(37,21)],fill='#ba9869',width=1);p.point((24,17),fill='#e1c786')
    cushion.save(OUT/'almofada.png',optimize=True)
    print('Refúgio 224×192 e almofada 48×32 gerados.')


def preview(destino):
    base=Image.open(OUT/'refugio.png').convert('RGBA')
    canvas=Image.new('RGB',(1008,530),'#25323e');d=ImageDraw.Draw(canvas)
    for col,pet in enumerate([None,'dragao']):
        cena=base.copy()
        hero=Image.open(ROOT/'static/loja/herois/espada/cavaleiro-m.png').convert('RGBA')
        hero=hero.resize((round(hero.width*117/hero.height),117),Image.Resampling.NEAREST)
        cena.alpha_composite(hero,(73,147-hero.height))
        if pet:
            animal=Image.open(ROOT/f'static/loja/pets/{pet}.png').crop((0,0,48,48));cena.alpha_composite(animal,(144,147-43))
        else:cena.alpha_composite(Image.open(OUT/'almofada.png'),(145,147-25))
        cena=cena.resize((448,384),Image.Resampling.NEAREST);canvas.paste(cena,(30+col*500,60),cena)
        d.text((35+col*500,25),'REFUGIO COM ESPADA - '+('pet equipado' if pet else 'lugar reservado para pet'),fill='#f7dfa1')
        d.text((35+col*500,460),'Prancha de arte; nao e screenshot de navegador.',fill='#c4c7ba')
    canvas.save(destino)
if __name__=='__main__':
    gerar()
    preview(ROOT.parent/'prints-loja/heroi-v2-preview.png')
