"""Seis cenários pessoais novos: pixel art 224×192, mesmo estrado/linha de pés.
Não altera o refúgio original nem a fogueira. Pranchas PIL não são screenshots.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import random,json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'static/loja/cenario'
CENAS=['floresta','taverna','ceu-estrelado','praia-tropical','mundo-doces','jardim-japones']

def faixas(d,cores):
    for i,c in enumerate(cores):d.rectangle((0,i*32,224,(i+1)*32),fill=c)
def nuvem(d,x,y,c='#f3ddc5'):
    for box in [(0,5,28,13),(6,0,20,14),(19,4,36,13)]:d.rectangle(tuple(v+(x if k%2==0 else y) for k,v in enumerate(box)),fill=c)
def arvore(d,x,y,cor='#2f5a4a'):
    d.rectangle((x-3,y+12,x+3,145),fill='#3b3433')
    for dx,dy,w in [(-14,0,30),(-22,14,46),(-28,29,58)]:d.polygon([(x+dx,y+dy+20),(x+dx+w//2,y+dy-10),(x+dx+w,y+dy+20)],fill=cor)
def plataforma(d):
    d.ellipse((22,145,209,181),fill='#182b32');d.ellipse((25,139,207,174),fill='#5b6963')
    d.rectangle((27,147,205,159),fill='#626e66');d.ellipse((27,134,205,165),fill='#9a9d80');d.ellipse((33,136,200,160),fill='#a9aa8a')
    for a,b in [((55,139),(65,157)),((94,136),(95,161)),((134,136),(132,160)),((175,140),(167,158)),((39,148),(190,149))]:d.line((a,b),fill='#777f6b',width=1)
def gerar(tipo):
    r=random.Random(770+sum(map(ord,tipo)));im=Image.new('RGB',(224,192));d=ImageDraw.Draw(im)
    if tipo=='floresta':
        faixas(d,['#213442','#29434b','#355b55','#43725d','#385c45','#304b3f'])
        for x,y,c in [(28,36,'#315347'),(85,51,'#3e6954'),(154,40,'#345c4c'),(209,23,'#2b4b40')]:arvore(d,x,y,c)
        for x in [6,35,203,219]:
            d.rectangle((x-6,0,x+5,150),fill='#283c38');d.line((x,5,x-2,140),fill='#536351',width=2)
            d.polygon([(x-30,0),(x+33,0),(x+24,32),(x,44),(x-29,28)],fill='#2b5146')
        for i in range(100):
            x,y=r.randrange(224),r.randrange(130);d.rectangle((x,y,x+2,y+1),fill=r.choice(['#5f815d','#496d53','#365c4b']))
        layer=Image.new('RGBA',im.size);z=ImageDraw.Draw(layer)
        z.polygon([(127,0),(141,0),(82,139),(57,139)],fill='#e9df9c22');im=Image.alpha_composite(im.convert('RGBA'),layer);d=ImageDraw.Draw(im)
        d.rectangle((0,153,224,192),fill='#334b3c')
    elif tipo=='taverna':
        faixas(d,['#382e33','#594039','#6c4a39','#5a3d32','#75533a','#62442e'])
        for y in range(12,136,14):
            d.line((0,y,224,y),fill='#3c3130',width=2)
            for x in range((y//14%2)*15,224,32):d.line((x,y,x,y+12),fill='#4e3b32')
        for x in [0,36,185,217]:d.rectangle((x,0,x+7,138),fill='#352c2b');d.line((x+2,0,x+2,134),fill='#8b6744')
        d.rectangle((43,0,176,7),fill='#3e302b');d.rectangle((144,35,177,82),fill='#3b3033');d.rectangle((148,39,173,78),fill='#e5be72')
        d.rectangle((158,39,161,78),fill='#6b4b34');d.rectangle((148,58,173,61),fill='#6b4b34')
        d.rectangle((13,77,47,131),fill='#393336');d.rectangle((18,83,41,125),fill='#34292c')
        for x,y in [(23,112),(29,106),(34,113)]:d.polygon([(x-4,124),(x, y),(x+5,124)],fill='#eda85f');d.rectangle((x,117,x+2,123),fill='#f7da8b')
        for x in [183,201]:
            d.ellipse((x-8,106,x+8,131),fill='#49392d');d.rectangle((x-7,111,x+7,129),fill='#956a42');d.line((x-7,115,x+7,115),fill='#43382d',width=2);d.line((x-7,125,x+7,125),fill='#43382d',width=2)
        for y in range(137,192,10):d.line((0,y,224,y),fill='#48382c',width=2)
    elif tipo=='ceu-estrelado':
        faixas(d,['#1b253f','#26344e','#34445c','#48576a','#3d515c','#344a51'])
        for i in range(95):
            x,y=r.randrange(224),r.randrange(108);d.point((x,y),fill=r.choice(['#c3d6d2','#8babbf','#f0dca0']))
        for x,y in [(38,25),(164,37),(105,12),(188,69)]:d.line((x-2,y,x+2,y),fill='#efdfb3');d.line((x,y-2,x,y+2),fill='#efdfb3')
        d.ellipse((173,15,194,36),fill='#eee0ba');d.ellipse((181,12,197,30),fill='#26344e')
        d.polygon([(0,121),(37,79),(65,105),(96,66),(137,112),(168,83),(224,120),(224,162),(0,162)],fill='#364854')
        d.polygon([(0,142),(36,119),(81,139),(132,106),(176,136),(224,113),(224,192),(0,192)],fill='#2c4248')
    elif tipo=='praia-tropical':
        faixas(d,['#729cb1','#94bdc6','#94c7ce','#3b8d9e','#c6b789','#cdbb87'])
        nuvem(d,28,21);nuvem(d,117,40,'#e2dfc8');d.ellipse((174,24,192,42),fill='#f2d69c')
        for y,c in [(90,'#61b3bb'),(102,'#68b9bd'),(115,'#a4d2c8'),(124,'#e7ddbb')]:d.line((0,y,224,y-3),fill=c,width=3)
        d.polygon([(152,87),(162,72),(189,70),(204,88)],fill='#5c8069');d.line((152,88,209,88),fill='#b8b896',width=3)
        for x,sgn in [(18,1),(211,-1)]:
            d.line([(x-5,144),(x+sgn*3,97),(x+sgn*10,55)],fill='#695941',width=7);d.line([(x-3,143),(x+sgn*5,98),(x+sgn*10,55)],fill='#ac8b58',width=2)
            for dx,dy in [(-33,9),(-23,-9),(2,-17),(28,-9),(34,10)]:d.polygon([(x+sgn*10,55),(x+dx,55+dy),(x+dx+5,64+dy),(x+sgn*10,59)],fill='#3b715a')
            d.rectangle((x+4,61,x+9,65),fill='#67513d')
        d.rectangle((0,154,224,192),fill='#cdbb87')
        for i in range(40):x,y=r.randrange(224),r.randrange(145,192);d.point((x,y),fill='#e6d6a9')
    elif tipo=='mundo-doces':
        faixas(d,['#b38ea8','#c6a1b4','#dab6c1','#d7aab3','#bc8fa3','#ac8195'])
        nuvem(d,39,27,'#f2d7ce');nuvem(d,126,42,'#ead4db')
        d.polygon([(0,117),(33,92),(65,112),(98,82),(137,108),(174,86),(224,114),(224,159),(0,159)],fill='#c897ac')
        for x,y,col in [(23,74,'#dfadbd'),(194,66,'#e2bfa8')]:
            d.rectangle((x-2,y+14,x+2,143),fill='#ede2c3');d.ellipse((x-17,y-16,x+17,y+18),fill='#866c8c');d.ellipse((x-14,y-13,x+14,y+15),fill=col)
            d.arc((x-10,y-9,x+10,y+11),0,290,fill='#f6e4d0',width=3);d.arc((x-4,y-3,x+4,y+5),0,300,fill='#b681a5',width=2)
        for x in [4,210]:
            d.rectangle((x,108,x+6,150),fill='#f0dec9')
            for y in range(110,150,10):d.polygon([(x,y),(x+6,y+4),(x+6,y+8),(x,y+4)],fill='#c3778d')
        for x,y,c in [(44,130,'#8b96ac'),(178,128,'#aa8cab'),(11,168,'#d1b39c'),(215,170,'#9ba695')]:d.ellipse((x-11,y-11,x+11,y+7),fill=c)
        for y in range(153,192,12):
            for x in range(0,224,14):d.rectangle((x,y,x+13,y+11),fill='#bf93a3' if (x//14+y//12)%2 else '#c9a2ae')
    elif tipo=='jardim-japones':
        faixas(d,['#8b9aa4','#a8b5b0','#b3bbaa','#8faaa0','#819482','#647e6e'])
        d.polygon([(0,107),(38,85),(75,99),(111,72),(163,101),(195,82),(224,103),(224,146),(0,146)],fill='#869e92')
        d.ellipse((78,105,206,155),fill='#6f999c');d.line((95,129,198,129),fill='#b4c5ae',width=2)
        d.arc((105,87,185,135),180,360,fill='#a56159',width=5);d.arc((105,96,185,140),180,360,fill='#a56159',width=3)
        for x in range(112,182,12):d.line((x,104,x,124),fill='#a56159',width=2)
        for x in [13,205]:
            d.line([(x,144),(x+4,68),(x-3,22)],fill='#5b5148',width=7)
            d.line((x,79,x+(-20 if x>100 else 31),40),fill='#5b5148',width=5)
            for dx,dy,w in [(-20,13,38),(-32,35,48),(-8,40,37),(5,4,31)]:
                d.ellipse((x+dx,dy,x+dx+w,dy+25),fill='#c99eaa');d.rectangle((x+dx+5,dy+4,x+dx+w-6,dy+14),fill='#e3bdc3')
        d.rectangle((36,115,39,146),fill='#5e655b');d.rectangle((29,111,46,116),fill='#69776c');d.polygon([(27,111),(37,105),(48,111)],fill='#68766b');d.rectangle((32,118,43,129),fill='#d8c7a2')
        for i in range(35):x,y=r.randrange(224),r.randrange(48,185);d.rectangle((x,y,x+2,y+1),fill='#e5c0c5')
    plataforma(d)
    im.convert('RGB').save(OUT/(tipo+'.png'),optimize=True)

def previews(destino):
    destino.mkdir(parents=True,exist_ok=True)
    itens=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'))['itens']
    cenas=[i for i in itens if i['categoria']=='cenarios'];board=Image.new('RGB',(1456,1344),'#25323e');d=ImageDraw.Draw(board)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    hero=Image.open(ROOT/'static/loja/herois/poses-v5/cavaleiro-m.png').convert('RGBA').crop((0,0,96,128)).resize((88,117),Image.Resampling.NEAREST)
    pet=Image.open(ROOT/'static/loja/pets/dragao.png').convert('RGBA').crop((0,0,48,48));cushion=Image.open(ROOT/'static/loja/cenario/almofada.png').convert('RGBA')
    for k,item in enumerate(cenas):
        im=Image.open(ROOT/'static'/item['sprite']).convert('RGBA');im.alpha_composite(cushion,(147,122));im.alpha_composite(hero,(63,33));im.alpha_composite(pet,(146,104))
        im.resize((672,576),Image.Resampling.NEAREST).save(destino/(item['id']+'-preview.png'))
        x=16+(k%3)*480;y=16+(k//3)*440
        d.text((x,y),item['nome'],font=font,fill='#f1ddb1');d.text((x,y+24),'Grátis · padrão' if item.get('padrao') else '300 cristais',font=font,fill='#c3c9be')
        board.paste(im.resize((448,384),Image.Resampling.NEAREST),(x,y+48))
    board.save(destino/'cenarios-v7-preview.png')
    print('Seis cenários 224×192 e sete composições PIL; prancha 1456×1344. Não são screenshots.')
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for tipo in CENAS:gerar(tipo)
    previews(ROOT.parent/'prints-loja/v7')
