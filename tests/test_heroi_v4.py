"""Contrato dos pets v4: arte determinística, integração e compra sem rede."""
import json
import pytest
from PIL import Image
from test_loja import ctx,post,A,ROOT
from gen.loja import gerar_pets as G

@pytest.mark.parametrize('tipo',G.PETS)
def test_sprite_v4_contrato_rgba_tamanho_transparencia(tipo):
    im=Image.open(ROOT/f'static/loja/pets/{tipo}.png')
    assert im.mode=='RGBA' and im.size==(384,48)
    for n in range(8):
        f=im.crop((48*n,0,48*(n+1),48))
        assert f.tobytes()==G.quadro_pet(tipo,n).tobytes()
        pixels=[f.getpixel((x,y)) for y in range(48) for x in range(48)]
        assert sum(c[3]==0 for c in pixels)>600
        assert sum(v>0 for v in f.getchannel('A').crop((0,40,48,44)).tobytes())>5
        assert len({c for c in pixels if c[3]==255})>=12
        assert not any(c[:3]==(0,0,0) and c[3] for c in pixels)

@pytest.mark.parametrize('tipo',G.PETS)
def test_sprite_v4_oito_quadros_distintos_e_articulacao(tipo):
    frames=[G.quadro_pet(tipo,n) for n in range(8)]
    assert len({f.tobytes() for f in frames})==8
    # Oito quadros: cabeça e apêndices se movem, não só o sprite inteiro.
    assert frames[0].tobytes()!=frames[1].tobytes()
    assert frames[0].crop((0,0,48,33)).tobytes()!=frames[2].crop((0,0,48,33)).tobytes()

@pytest.mark.parametrize('tipo',G.PETS)
def test_cada_pet_comprar_equipar_exibir_retirar_mantem_almofada(ctx,tipo):
    _,cliente=ctx;c,t=cliente()
    assert 'pet-vazio' in c.get('/heroi').text
    compra=post(c,t,item='pet-'+tipo)
    assert compra.status_code==200 and compra.json['estado']['cristais']==600
    assert post(c,t,'/loja/equipar',item='pet-'+tipo).status_code==200
    heroi=c.get('/heroi');loja=c.get('/loja?categoria=pets')
    assert 'pet-vazio' not in heroi.text
    for pagina in (heroi,loja):
        assert pagina.status_code==200
        assert 'loja/pets/'+tipo+'.png' in pagina.text
    r=c.get('/static/loja/pets/'+tipo+'.png')
    assert r.status_code==200 and r.mimetype=='image/png'
    assert post(c,t,'/loja/retirar',categoria='pets').status_code==200
    assert 'pet-vazio' in c.get('/heroi').text
    assert A._PERFIS_TESTE['teste:teste']['xp']==135

def test_identidade_nomes_precos_caminhos_preservados():
    itens=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'))['itens']
    pets=[i for i in itens if i['categoria']=='pets']
    assert [(i['id'],i['nome'],i['preco']) for i in pets]==[('pet-'+t,n,400) for t,n in zip(G.PETS,G.NOMES)]
    assert set(json.loads((ROOT/'static/loja/pets-design.json').read_text(encoding='utf-8')))==set(G.PETS)
    assert json.loads((ROOT/'static/loja/pets-estilo.json').read_text(encoding='utf-8'))==G.STYLE

def test_silhuetas_nao_sao_base_recolorida():
    silhuetas=[G.quadro_pet(t,0).getchannel('A').tobytes() for t in G.PETS]
    assert len(set(silhuetas))==10
    # Diferença em relação à área ocupada, não aos 2.304 pixels (incluindo fundo).
    # Mesmo os dois corpos arredondados (tigre/coruja) divergem >12% da união.
    for i,a in enumerate(silhuetas):
        for b in silhuetas[i+1:]:
            diferenca=sum((x>0)!=(y>0) for x,y in zip(a,b))
            uniao=sum(x>0 or y>0 for x,y in zip(a,b))
            assert diferenca/uniao>0.12

def test_gerador_reproduz_pngs_e_prancha_grande(tmp_path,monkeypatch):
    novo=tmp_path/'out';novo.mkdir();monkeypatch.setattr(G,'ROOT',novo)
    G.gerar()
    for t in G.PETS:
        assert (novo/f'static/loja/pets/{t}.png').read_bytes()==(ROOT/f'static/loja/pets/{t}.png').read_bytes()
    board=Image.open(tmp_path/'prints-loja/arte-pets-preview.png')
    assert board.size==(2400,1180)
    assert board.mode=='RGB'

@pytest.mark.parametrize('tipo,frame',[('cachorro',0),('dragao',8),('gato',-1)])
def test_nao_inventa_especie_nem_quadro(tipo,frame):
    with pytest.raises(ValueError):G.quadro_pet(tipo,frame)
