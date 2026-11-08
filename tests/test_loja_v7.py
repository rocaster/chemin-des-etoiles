"""Molduras por LVL, placas só no mundo e preços v7; CosmosFake/UTF-8."""
import ast,copy,json,re,subprocess,os
from pathlib import Path
import pytest
from test_loja import ctx,A,post,ROOT,estado_cosmetico,abastecer
from loja import ITENS,vitrine_molduras
IDS=['madeira','pedra','bronze','prata','ouro','diamante']
XP=[0,45,135,270,405,585]
PRECOS={'personagem':150,'particulas':250,'titulos':90,'pets':400,'cenarios':300}

def vitrine(h):return h.split('<section id="molduras"',1)[1].split('</section>',1)[0]
def perfil(fake,teste):return A._PERFIS_TESTE['teste:teste'] if teste else fake.docs['real']

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('xp',[0,44,45,134,135,269,270,404,405,584,585,640])
def test_limites_e_todas_molduras_sem_preco_ou_compra(ctx,teste,xp):
    fake,f=ctx;c,_=f(teste)
    if teste:perfil(fake,teste)['xp']=xp
    else:fake.alterar('real',xp=xp)
    lvl=A.borda_por_xp(xp)+1
    for path in ['/heroi','/loja','/loja?categoria=pets','/loja?categoria=particulas','/loja?categoria=titulos']:
        r=c.get(path);assert r.status_code==200;h=vitrine(r.text)
        assert h.count('data-moldura=')==6 and h.count('data-estado="ativa"')==1
        assert h.count('data-estado="bloqueada"')==6-lvl
        assert h.count('data-estado="conquistada"')==lvl-1
        assert '<form' not in h and '<button' not in h and 'class="preco"' not in h
        assert 'nunca por cristais' in h and 'automaticamente' in h
        for i,(iid,minimo) in enumerate(zip(IDS,XP),1):
            assert f'data-moldura="{iid}" data-nivel="{i}"' in h
            assert f'LVL {i} · {minimo} XP' in h
            assert c.get(f'/static/mapa/bordas/borda-{iid}@2x.png').status_code==200
    assert [(b['id'],b['xp']) for b in A.BORDAS_MAPA]==list(zip(IDS,XP))

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('iid',IDS)
@pytest.mark.parametrize('acao',['comprar','equipar','retirar'])
def test_servidor_rejeita_moldura_por_cristais_ou_selecao_manual(ctx,teste,iid,acao):
    fake,f=ctx;c,t=f(teste);antes=copy.deepcopy(perfil(fake,teste))
    r=post(c,t,f'/loja/{acao}',item='moldura-'+iid,categoria='molduras',preco=0,nivel=999,xp=999999)
    assert r.status_code==403 and 'nível' in r.json['erro']
    assert perfil(fake,teste)==antes

@pytest.mark.parametrize('teste',[True,False])
def test_cliente_nao_desbloqueia_por_inventario_ou_nivel_forjado(ctx,teste):
    fake,f=ctx;c,t=f(teste)
    e=estado_cosmetico(None,True);e['comprados']=['moldura-diamante'];e['equipados']={'molduras':'moldura-diamante'}
    if teste:perfil(fake,teste).update(xp=0,cosmeticos=e)
    else:fake.alterar('real',xp=0,cosmeticos=e)
    h=vitrine(c.get('/heroi?nivel=6&xp=999999').text)
    assert 'data-moldura="diamante" data-nivel="6" data-estado="bloqueada"' in h
    assert 'data-moldura="madeira" data-nivel="1" data-estado="ativa"' in h
    assert post(c,t,item='paleta-rubi',categoria='molduras').status_code==403

@pytest.mark.parametrize('vista',['mundo','regiao'])
@pytest.mark.parametrize('parada',[1,12,25])
def test_simulado_visibilidade_inicial_por_vista(ctx,vista,parada):
    _,f=ctx;c,_=f();h=c.get(f'/mapa?vista={vista}&parada={parada}').text
    nav=re.search(r'<nav[^>]+id="simulado-entradas"[^>]*>',h)[0]
    assert (' hidden' in nav)==(vista!='mundo')
    assert 'body:not(.vista-mundo) .simulado-placas' in h
    assert 'simulado-entradas").hidden = m !== "vista-mundo"' in h

def test_precos_e_balanceamento_aprovados_sem_alterar_ganhos():
    from economia import creditar_estado,ORDEM
    assert len(ITENS)==29 and sum(not v.get('padrao') for v in ITENS.values())==28
    assert all(v['preco']==(0 if v.get('padrao') else PRECOS[v['categoria']]) for v in ITENS.values())
    assert sum(v['preco'] for v in ITENS.values())==7860
    eventos=[{'id':pid,'sem_erros':True} for pid in ORDEM['ordem']]
    assert creditar_estado(None,eventos)['cristais']==1220
    assert 400+250+150+90==890
    # O maior número de itens distintos pelo custo mínimo possível é oito.
    acumulado=0;quantidade=0
    for preco in sorted(v['preco'] for v in ITENS.values() if not v.get('padrao')):
        if acumulado+preco>1220:break
        acumulado+=preco;quantidade+=1
    assert quantidade==8 and acumulado==1060

def test_hotfix_utf8_preservado_e_text_io_explicito():
    for nome in ['xp.py','simulados.py']:
        assert "read_text(encoding='utf-8')" in (ROOT/nome).read_text(encoding='utf-8')
    arquivos=json.loads((ROOT/'docs/python-utf8-v7.json').read_text(encoding='utf-8'))
    falhas=[]
    for nome in arquivos:
        for n in ast.walk(ast.parse((ROOT/nome).read_text(encoding='utf-8'))):
            if not isinstance(n,ast.Call):continue
            if isinstance(n.func,ast.Attribute) and n.func.attr in {'read_text','write_text'}:
                assert any(k.arg=='encoding' and isinstance(k.value,ast.Constant) and k.value.value=='utf-8' for k in n.keywords),(nome,n.lineno)
            if isinstance(n.func,ast.Name) and n.func.id=='open':
                mode=n.args[1].value if len(n.args)>1 and isinstance(n.args[1],ast.Constant) else 'r'
                if isinstance(mode,str) and 'b' not in mode:
                    assert any(k.arg=='encoding' and isinstance(k.value,ast.Constant) and k.value.value=='utf-8' for k in n.keywords),(nome,n.lineno)

def test_dom_entrada_saida_area_e_transicao(ctx,tmp_path):
    _,f=ctx;c,_=f();p=tmp_path/'vistas.json'
    p.write_text(json.dumps({v:c.get('/mapa?vista='+v).text for v in ['mundo','regiao']},ensure_ascii=False),encoding='utf-8')
    env=dict(os.environ);env['NODE_PATH']=str(ROOT.parent/'gen/formatos/teste/node_modules')
    run=subprocess.run(['node',str(ROOT/'gen/loja/v7-dom.js'),str(p)],text=True,encoding='utf-8',capture_output=True,env=env)
    assert run.returncode==0,run.stdout+run.stderr
    assert '26 checks OK' in run.stdout

CENAS=['floresta','taverna','ceu-estrelado','praia-tropical','mundo-doces','jardim-japones']

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('cena',CENAS)
def test_cenarios_compra_equipar_persistir_so_refugio(ctx,teste,cena):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste);iid='cenario-'+cena;antes=perfil(fake,teste)['xp']
    for _ in range(2):assert post(c,t,item=iid).json['estado']['cristais']==700
    assert post(c,t,'/loja/equipar',item=iid).json['estado']['equipados']['cenarios']==iid
    c2,_=f(teste);h=c2.get('/heroi').text
    assert f"loja/cenario/{cena}.png" in h
    assert 'loja/cenario/'+cena+'.png' in c2.get('/loja?categoria=cenarios').text
    for path in ['/personagem','/mapa','/parada/1/4']:
        assert f'loja/cenario/{cena}.png' not in c2.get(path).text
    assert perfil(fake,teste)['xp']==antes
    assert post(c,t,'/loja/retirar',categoria='cenarios').status_code==200
    assert 'loja/cenario/refugio.png' in c.get('/heroi').text
    assert perfil(fake,teste)['cosmeticos']['cristais']==700

@pytest.mark.parametrize('teste',[True,False])
def test_refugio_gratis_posse_permanente_implicita_e_equipamento(ctx,teste):
    from loja import itens_equipados
    fake,f=ctx;c,t=f(teste)
    for _ in range(2):
        j=post(c,t,item='cenario-refugio').json
        assert j['estado']['cristais']==(1000 if teste else 0)
        assert itens_equipados(j['estado'])['cenarios']['id']=='cenario-refugio'
    assert post(c,t,'/loja/equipar',item='cenario-refugio').status_code==200
    html=c.get('/loja?categoria=cenarios').text
    card=html.split('data-item="cenario-refugio"')[1].split('</article>')[0]
    assert 'Grátis · sempre seu' in card and 'Comprar' not in card and 'Equipado' in card
    assert post(c,t,'/loja/retirar',categoria='cenarios').status_code==200
    assert 'loja/cenario/refugio.png' in c.get('/heroi').text

def test_arte_cenarios_dimensoes_composicao_e_original_intacto():
    from PIL import Image
    import hashlib
    im=Image.open(ROOT/'static/loja/cenario/refugio.png');assert im.size==(224,192)
    hashes=[]
    for cena in CENAS:
        p=ROOT/f'static/loja/cenario/{cena}.png';c=Image.open(p)
        assert c.size==(224,192)
        assert c.getpixel((110,148))==Image.open(ROOT/'static/loja/cenario/floresta.png').getpixel((110,148))
        hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
    assert len(set(hashes))==6
    assert 'cenario-praia-bretanha' not in ITENS and 'cenario-torre-castelo' not in ITENS

@pytest.mark.parametrize('teste',[True,False])
@pytest.mark.parametrize('nome,normalizado',[("  L'étoile-7  ","L'étoile-7"),('Lua de Mel','Lua de Mel'),('Éclair','Éclair'),('E\u0301toile','Étoile'),('ABCDEFGHIJKLMNOP','ABCDEFGHIJKLMNOP')])
def test_renomear_gratis_validar_persistir_mostrar_todos_perfis(ctx,teste,nome,normalizado):
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste);post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    antes=copy.deepcopy(perfil(fake,teste));r=post(c,t,'/loja/pet/nome',item='pet-dragao',nome=nome)
    assert r.status_code==200 and r.json['estado']['nomes_pets']=={'pet-dragao':normalizado}
    assert r.json['estado']['cristais']==600 and perfil(fake,teste)['xp']==antes['xp']
    c2,_=f(teste)
    for url in ['/heroi','/loja?categoria=pets','/parada/1/4']:
        html=c2.get(url).text
        from html import unescape
        assert normalizado in unescape(html)
    assert post(c,t,'/loja/pet/nome',item='pet-dragao',resetar=True).json['estado']['nomes_pets']=={}
    assert 'Dragão bebê' in c.get('/heroi').text
    assert perfil(fake,teste)['cosmeticos']['cristais']==600

@pytest.mark.parametrize('nome',['','  ','a'*17,'---','<b>Lua</b>','Lua\nNova','Lua\tNova','Lua🐉','Lua_2','merda','mérde','putain','SH1T','p0rr4','f u c k',None,42,[],{}])
def test_nome_invalido_profanidade_sem_mudar_saldo_ou_nome(ctx,nome):
    fake,f=ctx;c,t=f();post(c,t,item='pet-dragao');antes=copy.deepcopy(perfil(fake,True))
    r=post(c,t,'/loja/pet/nome',item='pet-dragao',nome=nome)
    assert r.status_code==400 and perfil(fake,True)==antes

def test_renomear_csrf_posse_id_metodo_e_form_reset(ctx):
    _,f=ctx;c,t=f();url='/loja/pet/nome'
    assert c.get(url).status_code==405
    assert c.post(url,json={'item':'pet-dragao','nome':'Lua'}).status_code==403
    assert post(c,t,url,item='pet-dragao',nome='Lua').status_code==403
    assert post(c,t,url,item='cenario-floresta',nome='Lua').status_code==404
    post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    r=c.post(url,data={'csrf':t,'item':'pet-dragao','nome':'Lune'})
    assert r.status_code==303 and r.location.endswith('/heroi#nome-pet')
    r=c.post(url,data={'csrf':t,'item':'pet-dragao','resetar':'1'})
    assert r.status_code==303 and 'Dragão bebê' in c.get('/heroi').text

def test_nome_escapado_mesmo_se_documento_foi_alterado_externamente(ctx):
    _,f=ctx;c,t=f();post(c,t,item='pet-dragao');post(c,t,'/loja/equipar',item='pet-dragao')
    perfil(None,True)['cosmeticos']['nomes_pets']={'pet-dragao':'<b>Lua</b>'}
    for url in ['/heroi','/loja?categoria=pets','/parada/1/4']:
        h=c.get(url).text;assert '<b>Lua</b>' not in h and '&lt;b&gt;Lua&lt;/b&gt;' in h

@pytest.mark.parametrize('teste',[True,False])
def test_dois_nomes_e_ganho_concorrentes_preservam_ledger(ctx,teste):
    from concurrent.futures import ThreadPoolExecutor
    fake,f=ctx
    if not teste:abastecer(fake)
    c,t=f(teste)
    for pet in ['pet-dragao','pet-lobo']:assert post(c,t,item=pet).status_code==200
    def acao(n):
        cc,tt=f(teste)
        if n==2:return cc.post('/parada/1/1/concluir',json={'acertos':5,'erros':1,'fala_pendente':False,'duracao_s':100}).status_code
        return post(cc,tt,'/loja/pet/nome',item=['pet-dragao','pet-lobo'][n],nome=['Foguinho','Lune'][n]).status_code
    with ThreadPoolExecutor(max_workers=3) as pool:assert list(pool.map(acao,range(3)))==[200,200,200]
    c.get('/heroi');d=perfil(fake,teste)
    assert d['cosmeticos']['nomes_pets']=={'pet-dragao':'Foguinho','pet-lobo':'Lune'}
    assert d['cosmeticos']['cristais']==218 and d['xp']==160
