"""Regressão v6: endpoints reais Flask + CosmosFake/ETag, sem rede/.env."""
import copy,json,re,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from test_loja import A,ctx,post,abastecer,estado_cosmetico,ContasCosmos,erro,ITENS
from xp import XP_POR_ID,ORDEM,CONFIG,normalizar,valor_xp
from economia import ETAPAS,CONFIG as EC,creditar_estado
ROOT=Path(__file__).resolve().parents[1]
ENTRADA=dict(acertos=5,erros=1,fala_pendente=False,duracao_s=120)

def conta(c,n,**extra):return c.post(f'/parada/1/{n}/concluir',json={**ENTRADA,**extra})
def doc(fake,teste):return A._PERFIS_TESTE['teste:teste'] if teste else fake.docs['real']

def test_tabela_completa_e_quarenta_recompensas():
    assert len(XP_POR_ID)==40 and sum(XP_POR_ID.values())==640
    for pid in ORDEM:
        d=json.loads((ROOT/'data/paradas'/f'{pid}.json').read_text(encoding='utf-8'));r=d['recompensa']
        assert r['xp_base']==CONFIG['primeira_conclusao'][d.get('formato','missao')]
        assert r['xp_por_estrela']==0 and r['xp_versao']==6
    assert CONFIG['primeira_conclusao']['simulado']==0

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('n',range(1,41))
def test_cada_etapa_primeira_repeticao_xp_e_cristais(ctx,teste,n):
    fake,f=ctx;c,_=f(teste);d0=copy.deepcopy(doc(fake,teste));pid=ORDEM[n-1]
    r=conta(c,n,xp=999999,cristais=999999,primeira=True)
    assert r.status_code==200;r=r.json;esperado=XP_POR_ID[pid]
    assert r['xp']==r['xp_ganho']==r['xp_creditado_etapa']==esperado
    assert r['xp_total']==135+esperado
    estado=creditar_estado(d0.get('cosmeticos'),[{'id':pid,'sem_erros':False}],teste)
    assert r['cristais_total']==estado['cristais'] and not r['cristais_pendentes']
    for _ in range(2):
        j=conta(c,n).json
        assert j['ok'] and j['xp_ganho']==j['xp']==j['cristais_ganhos']==0
        assert j['xp_creditado_etapa']==esperado and j['xp_total']==135+esperado
        assert j['cristais_total']==estado['cristais']
    d=doc(fake,teste);assert d['paradas_progresso'][pid]['tentativas']==3
    assert d['paradas_progresso'][pid]['xp']==esperado

@pytest.mark.parametrize('teste',[True,False])
def test_mapa_inteiro_640_e_1220_cristais(ctx,teste):
    fake,f=ctx;c,_=f(teste);d=doc(fake,teste)
    if teste:d['xp']=0
    else:fake.alterar('real',xp=0)
    respostas=[conta(c,n,erros=0).json for n in range(1,41)]
    assert all(j['ok'] for j in respostas)
    assert sum(j['xp_ganho'] for j in respostas)==640
    assert sum(j['cristais_ganhos'] for j in respostas)==1220
    assert respostas[-1]['xp_total']==640
    assert respostas[-1]['cristais_total']==(1000 if teste else 0)+1220
    for n in range(1,41):assert conta(c,n,erros=0).json['xp_ganho']==0
    assert doc(fake,teste)['xp']==640
    assert len(doc(fake,teste)['cosmeticos']['etapas_creditadas'])==40
    assert doc(fake,teste)['borda_mapa']=='diamante'

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('categoria',['personagem','particulas','titulos','pets'])
def test_compra_equipamento_persistencia_e_retirada_todas_categorias(ctx,teste,categoria):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste);iid=next(k for k,v in ITENS.items() if v['categoria']==categoria)
    item=ITENS[iid];antes=doc(fake,teste)['xp']
    assert post(c,t,'/loja/equipar',item=iid).status_code==403
    for _ in range(3):
        j=post(c,t,item=iid,preco=0).json
        assert j['estado']['cristais']==1000-item['preco']
        assert j['estado']['comprados'].count(iid)==1
    for _ in range(2):assert post(c,t,'/loja/equipar',item=iid).json['estado']['equipados'][categoria]==iid
    c2,t2=f(teste)
    for rota in ['/heroi','/loja','/mapa','/parada/1/4']:
        h=c2.get(rota).text
        if categoria=='personagem':assert '-esmeralda.png' in h
        if categoria=='pets':assert item['sprite'] in h
        if categoria=='titulos':assert item['nome_fr_f'] in h
        if categoria=='particulas':assert (f"fx-{item['efeito']}" in h)==(rota in ['/heroi','/loja'])
    assert 'loja/herois/poses-v5/' not in c2.get('/personagem').text
    assert doc(fake,teste)['xp']==antes
    for _ in range(2):assert post(c2,t2,'/loja/retirar',categoria=categoria).json['estado']['equipados']=={}
    assert post(c2,t2,item=iid).json['estado']['cristais']==1000-item['preco']
    assert doc(fake,teste)['xp']==antes

@pytest.mark.parametrize('teste',[True,False])
def test_credito_recuperado_apos_falha_entre_progresso_e_ledger(ctx,teste,monkeypatch):
    fake,f=ctx;c,_=f(teste)
    import economia
    original=economia.creditar
    monkeypatch.setattr(economia,'creditar',lambda *a,**kw: (_ for _ in ()).throw(economia.ContasIndisponiveis()))
    j=conta(c,1).json;assert j['ok'] and j['cristais_pendentes']
    assert doc(fake,teste)['xp']==160
    monkeypatch.setattr(economia,'creditar',original)
    assert c.get('/heroi').status_code==200
    assert doc(fake,teste)['cosmeticos']['cristais']==(1000 if teste else 0)+18
    assert conta(c,1).json['cristais_ganhos']==0

@pytest.mark.parametrize('teste',[True,False])
def test_paralelismo_mesma_etapa_uma_vez(ctx,teste):
    fake,f=ctx;f(teste)
    def chamada(_):
        c=A.app.test_client()
        with c.session_transaction() as s:s['teste' if teste else 'uid']='teste' if teste else 'real'
        return conta(c,1).json
    with ThreadPoolExecutor(max_workers=8) as pool:js=list(pool.map(chamada,range(24)))
    assert all(j['ok'] for j in js)
    assert sum(j['xp_ganho'] for j in js)==25
    assert sum(j['cristais_ganhos'] for j in js)==18
    assert doc(fake,teste)['xp']==160
    assert doc(fake,teste)['paradas_progresso'][ORDEM[0]]['tentativas']==24

@pytest.mark.parametrize('teste',[True,False])
def test_paralelismo_quarenta_etapas_nao_perde_progresso(ctx,teste):
    fake,f=ctx;f(teste)
    def chamada(n):
        c=A.app.test_client()
        with c.session_transaction() as s:s['teste' if teste else 'uid']='teste' if teste else 'real'
        return conta(c,n,erros=0).json
    with ThreadPoolExecutor(max_workers=6) as pool:js=list(pool.map(chamada,range(1,41)))
    assert all(j['ok'] for j in js)
    assert sum(j['xp_ganho'] for j in js)==640
    c,_=f(teste);assert c.get('/heroi').status_code==200
    d=doc(fake,teste);assert d['xp']==775
    assert set(d['paradas_progresso'])==set(ORDEM)
    assert d['cosmeticos']['cristais']==(1000 if teste else 0)+1220

@pytest.mark.parametrize('teste',[True,False])
def test_upsert_generico_atrasado_nao_desfaz_xp_nem_compra(ctx,teste):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste)
    with c:
        c.get('/mapa');u=A.usuarios();stale=u.read_item('teste:teste' if teste else 'real')
        assert conta(c,1).json['xp_ganho']==25
        assert post(c,t,item='titulo-voz').status_code==200
        stale['nome_personagem']='Novo nome';u.upsert_item(stale)
    d=doc(fake,teste);assert d['xp']==160 and ORDEM[0] in d['paradas_progresso']
    assert 'titulo-voz' in d['cosmeticos']['comprados'] and d['nome_personagem']=='Novo nome'
    if not teste:assert d['senha_hash']==d['nonce']=='preservar'

def test_conflito_etag_reprocessa_com_estado_novo(ctx):
    fake,f=ctx;c,_=f(False);bar=threading.Barrier(2);lock=threading.Lock();vezes=0
    def corrida(item,body):
        nonlocal vezes
        with lock:vezes+=1;n=vezes
        if n<=2:bar.wait(timeout=8)
    fake.before_replace=corrida
    def chamada(_):
        cc=A.app.test_client()
        with cc.session_transaction() as s:s['uid']='real'
        return conta(cc,1).json
    with ThreadPoolExecutor(max_workers=2) as pool:js=list(pool.map(chamada,range(2)))
    assert sorted(j['xp_ganho'] for j in js)==[0,25]
    assert sum(j['cristais_ganhos'] for j in js)==18
    assert fake.docs['real']['xp']==160 and vezes>=3

@pytest.mark.parametrize('rota',['/mapa','/heroi','/loja'])
def test_migracao_somente_servidor_e_idempotente(ctx,rota):
    fake,f=ctx;c,_=f(False)
    progresso={ORDEM[n-1]:{'concluida_em':'legado','xp':0,'acertos':5,'erros':1} for n in range(12,41)}
    fake.alterar('real',xp=135,paradas_progresso=progresso)
    assert c.get(rota).status_code==200
    esperado=135+sum(XP_POR_ID[ORDEM[n-1]] for n in range(12,41))
    assert fake.docs['real']['xp']==esperado
    for _ in range(3):assert c.get(rota).status_code==200
    assert fake.docs['real']['xp']==esperado
    h=c.get('/mapa').text
    assert 'let xpServidor = '+str(esperado) in h
    assert 'Math.max(xpServidor || 0, xpLocal())' not in h
    assert 'Number.isFinite(xpServidor)' in h

@pytest.mark.parametrize('perfil,esperado',[
 ({'xp':25,'paradas_progresso':{ORDEM[1]:{'concluida_em':'ok','xp':25}}},25),
 ({'xp':7,'paradas_progresso':{'forjado':{'concluida_em':'ok','xp':99999}}},7),
 ({'xp':0,'paradas_progresso':{ORDEM[1]:{'concluida_em':'ok','xp':0}}},20),
 ({'xp':135,'paradas_progresso':[]},135)])
def test_migracao_preserva_legitimo_nao_importa_local_ou_desconhecidos(perfil,esperado):
    novo=normalizar(perfil);assert novo['xp']==esperado and normalizar(novo)==novo

@pytest.mark.parametrize('rec,esperado',[({},0),({'xp_base':0},0),({'xp_base':25,'xp_pausado':True},0),({'xp_base':20},20)])
def test_valores_zero_pausa_ausente(rec,esperado):
    assert valor_xp({'formato':'desconhecido','recompensa':rec})==esperado

@pytest.mark.parametrize('avatar',[f'{c}-{g}' for c in ['cavaleiro','arqueiro','mago','bardo'] for g in ['m','f']])
def test_derivados_mapa_batalha_preservam_12_quadros_e_paletas(ctx,avatar):
    from PIL import Image,ImageChops
    from gen.loja.gerar_aparencia_v6 import tecido
    from aparencia import apresentar
    fake,f=ctx;c,t=f();A._PERFIS_TESTE['teste:teste']['avatar']=avatar
    original=Image.open(ROOT/f'static/batalha/heroi-{avatar}.png').convert('RGBA')
    for paleta in ['esmeralda','ametista','rubi']:
        post(c,t,item=f'paleta-{paleta}');post(c,t,'/loja/equipar',item=f'paleta-{paleta}')
        for rota,trecho in [('/heroi','loja/herois/poses-v5/'),('/loja','loja/herois/poses-v5/'),('/mapa','loja/mapa/'),('/parada/1/4','loja/batalha/')]:
            h=c.get(rota).text;assert f'{trecho}{avatar}-{paleta}.png' in h
            if rota=='/parada/1/4':assert f'loja/herois/poses-v5/{avatar}-{paleta}.png' in h and 'perfil-batalha-retrato' in h
        novo=Image.open(ROOT/f'static/loja/batalha/{avatar}-{paleta}.png').convert('RGBA')
        assert novo.size==original.size==(6144,400)
        assert novo.getchannel('A').tobytes()==original.getchannel('A').tobytes()
        pequeno=original.resize((1536,100),Image.Resampling.NEAREST)
        novo_p=novo.resize((1536,100),Image.Resampling.NEAREST);mudados=0
        for y in range(100):
            for x in range(1536):
                if novo_p.getpixel((x,y))!=pequeno.getpixel((x,y)):
                    mudados+=1;assert tecido(avatar,x%128,y,pequeno.getpixel((x,y)),quadro=x//128)
        assert mudados>0
        if avatar.startswith('mago-'):
            assert novo_p.crop((0,0,128,69)).tobytes()==pequeno.crop((0,0,128,69)).tobytes(), 'Cabeça/cabelos/chapéu/magia do mago não são tecido livre'
    assert 'loja/batalha/' not in c.get('/personagem').text

def test_reset_teste_intencional_nao_e_bloqueado_pelo_merge_seguro(ctx):
    fake,f=ctx;c,t=f();post(c,t,item='titulo-voz');conta(c,1)
    saldo=doc(fake,True)['cosmeticos']['cristais']
    assert c.post('/teste/zerar').json['ok']
    d=doc(fake,True);assert d['xp']==d['xp_mapa_contabilizado']==0
    assert not d.get('paradas_progresso') and d['cosmeticos']['cristais']==saldo
    assert conta(c,1).json['xp_ganho']==25
    assert doc(fake,True)['cosmeticos']['cristais']==saldo
    real,_=f(False);assert real.post('/teste/zerar').status_code==404

def test_sessao_teste_sobrevive_reinicio_sem_saldo_inutilizavel(ctx):
    fake,f=ctx;c,t=f();antes=copy.copy(fake.calls);A._PERFIS_TESTE.clear()
    assert post(c,t,item='titulo-voz').json['estado']['cristais']==910
    assert c.get('/heroi').status_code==200
    assert conta(c,1).json['xp_ganho']==25
    assert fake.calls==antes
