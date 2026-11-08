"""Novas poses/rigs v5; originais e economia continuam protegidos."""
import hashlib,json
from pathlib import Path
import pytest
from PIL import Image
from test_loja import ctx,A,ROOT
from gen.loja import animacao_v5 as V
from herois import sheet_heroi,PALETAS
from loja import estado_cosmetico

@pytest.mark.parametrize('tipo',V.PETS+V.HEROIS)
def test_oito_quadros_transparentes_distintos_sem_recorte(tipo):
    hero=tipo in V.HEROIS
    path=ROOT/'static'/sheet_heroi(tipo) if hero else ROOT/f'static/loja/pets/{tipo}.png'
    im=Image.open(path);w,h=(96,128) if hero else (48,48)
    assert im.mode=='RGBA' and im.size==(w*8,h)
    frames=[im.crop((w*n,0,w*(n+1),h)) for n in range(8)]
    assert len({f.tobytes() for f in frames})==8
    for f in frames:
        bb=f.getbbox();assert bb[0]>0 and bb[1]>0 and bb[2]<w and bb[3]<h
        assert set(f.getchannel('A').tobytes())=={0,255}
        assert f.getpixel((0,0))==(0,0,0,0)

@pytest.mark.parametrize('tipo',V.PETS+V.HEROIS)
def test_partes_separadas_e_editaveis(tipo):
    rig=V.rigs()[tipo];parts=V.separar(tipo)
    assert 'corpo' in parts and 'cabeca' in parts and len(parts)>=4
    for nome,im in parts.items():
        assert im.getbbox() is not None
        saved=Image.open(V.FONTES/f'partes/{tipo}/{nome}.png')
        assert saved.tobytes()==im.tobytes()
    roles={p['papel'] for p in rig['partes']}
    assert {'cabeca','item','braco'}<=roles if tipo in V.HEROIS else 'asa' in roles or 'cauda' in roles

@pytest.mark.parametrize('tipo',V.PETS+V.HEROIS)
def test_animacao_nao_e_so_bob_do_sprite_inteiro(tipo):
    parts=V.separar(tipo);rig=V.rigs()[tipo]
    role=next(p for p in rig['partes'] if p['papel'] in {'cauda','asa','item'})
    layer=parts[role['nome']]
    turned=V.transformar(layer,12,role['pivo'])
    assert layer.getchannel('A').tobytes()!=turned.getchannel('A').tobytes()
    a=V.quadro_trabalho(tipo,0);b=V.quadro_trabalho(tipo,2)
    # Pés permanecem ancorados enquanto braços/asas/cabeça mudam.
    foot=min(rig['linha_pes'],parts['corpo'].getbbox()[3]-1)
    anchors=[(x,foot) for x in range(a.width) if parts['corpo'].getpixel((x,foot))[3]]
    assert len(anchors)>=2
    assert all(a.getpixel(xy)==b.getpixel(xy) for xy in anchors)
    assert a.crop((0,0,a.width,a.height//2)).tobytes()!=b.crop((0,0,b.width,b.height//2)).tobytes()

@pytest.mark.parametrize('tipo',V.HEROIS)
@pytest.mark.parametrize('paleta',PALETAS)
def test_todas_as_classes_e_paletas_em_heroi_e_shop(ctx,tipo,paleta):
    _,cliente=ctx;c,t=cliente();perfil=A._PERFIS_TESTE['teste:teste'];perfil['avatar']=tipo
    if paleta:
        estado=estado_cosmetico(None,True);estado['comprados']=['paleta-'+paleta];estado['equipados']={'personagem':'paleta-'+paleta};perfil['cosmeticos']=estado
    path=sheet_heroi(tipo,paleta)
    assert c.get('/static/'+path).status_code==200
    assert path in c.get('/heroi').text
    shop=c.get('/loja').text
    assert all(sheet_heroi(tipo,p) in shop for p in PALETAS[1:])
    assert 'poses-v5' not in c.get('/personagem').text

@pytest.mark.parametrize('tipo',V.HEROIS)
def test_recolor_somente_tecido_preserva_itens_cabelo_pele(tipo):
    original=V.base(tipo);mask=V.mascara_tecido(tipo,original)
    assert mask.getbbox() is not None
    for paleta in PALETAS[1:]:
        cor=V.recolorir(tipo,original,paleta);assert cor.tobytes()!=original.tobytes()
        for y in range(original.height):
            for x in range(original.width):
                if not mask.getpixel((x,y)):assert cor.getpixel((x,y))==original.getpixel((x,y))

def test_origem_nova_sem_sprites_ou_geradores_antigos_de_pets():
    m=json.loads((V.FONTES/'proveniencia.json').read_text(encoding='utf-8'))
    assert m['pets_sem_imagens_referencia'] and not m['pets_geradores_anteriores_reutilizados']
    assert len(m['arquivos'])==18
    for tipo,meta in m['arquivos'].items():
        assert hashlib.sha256((V.FONTES/meta['arquivo']).read_bytes()).hexdigest()==meta['sha256']
    source=(ROOT/'gen/loja/gerar_pets.py').read_text(encoding='utf-8')
    assert 'class Pixel' not in source and 'quadro_pet(tipo,frame)' not in source

def test_css_passos_sem_frame_vazio_e_reduced_motion():
    css=(ROOT/'static/loja/animacoes-v5.css').read_text(encoding='utf-8')
    assert 'steps(8,end)' in css and '114.285714%' in css and '800% 100%' in css
    assert 'prefers-reduced-motion:reduce' in css and 'animation:none!important' in css
    assert 'background-position:0 0!important' in css
    assert '@keyframes hero-respira' not in (ROOT/'static/loja/heroi-v2.css').read_text(encoding='utf-8')

def test_so_cavaleiros_tem_espada_e_legado_somente_masculino():
    assert set(p.name.split('-')[0] for p in (ROOT/'static/loja/herois/espada').glob('*.png'))=={'cavaleiro'}
    assert len(list((ROOT/'static/loja/herois/espada').glob('cavaleiro-m*.png')))==8
    # Props sem espada são classes distintas, não variantes do cavaleiro.
    for tipo in V.HEROIS:
        assert V.rigs()[tipo]['tipo']=='heroi'
        assert (V.rigs()[tipo]['item_classe']=='espada')==tipo.startswith('cavaleiro-')
        assert 'cabeca' in V.separar(tipo) and 'braco_item' in V.separar(tipo)
