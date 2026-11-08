"""Regressão da correção de Alex: só cavaleiro masculino pode ser derivado."""
from pathlib import Path
import pytest
from PIL import Image,ImageChops
from test_loja import ctx,A,ROOT
from herois import AVATARES,PALETAS,sprite_heroi,pode_piscar

OUTROS=sorted(AVATARES-{'cavaleiro-m'})

@pytest.mark.parametrize('avatar',OUTROS)
@pytest.mark.parametrize('paleta',PALETAS)
@pytest.mark.parametrize('fechado',[False,True])
def test_outros_sete_servem_bytes_dos_originais(ctx,avatar,paleta,fechado):
    _,f=ctx;c,t=f()
    if paleta:
        original=f'loja/paletas/{avatar}-{paleta}.png'
    else:
        original=f'fogueira/sprite-{avatar}-'+('fechado' if fechado else 'aberto')+'.png'
    caminho=sprite_heroi(avatar,paleta,fechado)
    assert caminho==original and 'herois/espada' not in caminho
    assert c.get('/static/'+caminho).data==(ROOT/'static'/original).read_bytes()

@pytest.mark.parametrize('paleta',PALETAS)
@pytest.mark.parametrize('fechado',[False,True])
def test_somente_cavaleiro_m_usa_espada_derivada(ctx,paleta,fechado):
    _,f=ctx;c,t=f()
    caminho=sprite_heroi('cavaleiro-m',paleta,fechado)
    assert caminho.startswith('loja/herois/espada/cavaleiro-m')
    im=Image.open(ROOT/'static'/caminho).convert('RGBA')
    original=Image.open(ROOT/'static'/(f'loja/paletas/cavaleiro-m-{paleta}.png' if paleta else 'fogueira/sprite-cavaleiro-m-aberto.png')).convert('RGBA')
    assert im.size==original.size
    assert ImageChops.difference(im,original).convert('RGB').getbbox() is not None
    assert c.get('/static/'+caminho).status_code==200
    # Aço da lâmina igual em todas as paletas e nos olhos fechados.
    base=Image.open(ROOT/'static/loja/herois/espada/cavaleiro-m.png').convert('RGBA')
    assert im.getpixel((52*4,30*4))==base.getpixel((52*4,30*4))


def test_pasta_so_contem_os_oito_arquivos_do_cavaleiro_m():
    nomes={p.name for p in (ROOT/'static/loja/herois/espada').glob('*.png')}
    esperados={Path(sprite_heroi('cavaleiro-m',p,f)).name for p in PALETAS for f in (False,True)}
    assert nomes==esperados and len(nomes)==8


def test_gerador_recusa_alterar_os_demais():
    from gen.loja.gerar_herois_espada import ESPADAS,derivar
    assert set(ESPADAS)=={'cavaleiro-m'}
    for avatar in OUTROS:
        with pytest.raises(ValueError):derivar(Image.new('RGBA',(48,48)),avatar)


def test_limpeza_nao_remove_cavaleiro_ou_qualquer_outro_arquivo(tmp_path):
    from gen.loja.limpar_derivados_obsoletos import limpar,OBSOLETOS
    for nome in OBSOLETOS:(tmp_path/nome).write_bytes(b'obsoleto')
    (tmp_path/'cavaleiro-m.png').write_bytes(b'manter')
    (tmp_path/'outro-arquivo.png').write_bytes(b'manter')
    originais=tmp_path/'fogueira';originais.mkdir();(originais/'sprite-cavaleiro-f-aberto.png').write_bytes(b'original')
    assert len(limpar(tmp_path))==56 and limpar(tmp_path)==[]
    assert (tmp_path/'cavaleiro-m.png').read_bytes()==b'manter'
    assert (tmp_path/'outro-arquivo.png').read_bytes()==b'manter'
    assert (originais/'sprite-cavaleiro-f-aberto.png').read_bytes()==b'original'


def test_piscada_nunca_inventa_quadros_dos_demais():
    for avatar in OUTROS:
        assert pode_piscar(avatar)
        for paleta in PALETAS[1:]:
            assert not pode_piscar(avatar,paleta)
            assert sprite_heroi(avatar,paleta,True)==sprite_heroi(avatar,paleta,False)
    assert all(pode_piscar('cavaleiro-m',p) for p in PALETAS)

@pytest.mark.parametrize('avatar',OUTROS)
def test_nenhuma_url_antiga_de_espada_dos_outros_e_servida(ctx,avatar):
    _,f=ctx;c,t=f()
    for paleta in ('','-esmeralda','-ametista','-rubi'):
        for quadro in ('','-fechado'):
            assert c.get(f'/static/loja/herois/espada/{avatar}{paleta}{quadro}.png').status_code==404
