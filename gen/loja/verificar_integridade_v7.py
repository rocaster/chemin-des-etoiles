"""Auditoria v7b por snapshots locais conhecidos; sem rede ou leitura de .env."""
from pathlib import Path
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent/'backup-xp-loja-v7';OUT=ROOT.parent/'relatorio-xp-loja-v7c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
baseline=json.loads((BASE/'baseline-hotfix.json').read_text(encoding='utf-8'))
# Restrição ainda mais forte que v6: motor/formatos/paradas/BORDAS/rotas,
# sprites originais e sprites v5 permanecem byte-idênticos ao hotfix aprovado.
for name,h in baseline.items():
    if name in {'aparencia.py','data/economia.json'}:continue
    congelado=(name in {'app.py','contas_cosmos.py','xp.py','simulados.py','aparencia.py','herois.py','economia.py','data/economia.json','data/xp.json','templates/personagem.html','templates/nivelamento.html','templates/missao.html','templates/batalha.html'}
        or name.startswith(('static/fogueira/','static/mapa/','static/batalha/','static/parada/','static/missao/','static/nivelamento/','static/audio/','data/paradas/'))
        or name.startswith('static/loja/') and name!='static/loja/perfil-v6.css')
    if congelado:checks['baseline_hotfix:'+name]=sha(ROOT/name)==h
v5=json.loads((ROOT.parent/'relatorio-heroi-v5/manifesto.json').read_text(encoding='utf-8'))['paths']
for name,h in v5.items():
    if name.endswith(('.png','.gif','.jpg','.jpeg')):checks['arte_v5:'+name]=sha(ROOT/name)==h
mapa=(ROOT/'templates/mapa.html').read_text(encoding='utf-8')
revertido=mapa.replace('    .simulado-placas[hidden], body:not(.vista-mundo) .simulado-placas { display:none!important; }\n','',1)
revertido=revertido.replace('<nav class="sim-placas simulado-placas" id="simulado-entradas" aria-label="Simulados não oficiais"{% if vista != \'mundo\' %} hidden{% endif %}>','<nav class="sim-placas" aria-label="Simulados não oficiais">',1)
revertido=revertido.replace('      document.getElementById("simulado-entradas").hidden = m !== "vista-mundo";\n','',1)
checks['mapa_diff_exclusivamente_visibilidade_placas']=revertido==(BASE/'templates/mapa.html').read_text(encoding='utf-8')
# Outra garantia das constantes e funções congeladas, sem importar o app.
a=ast.parse((ROOT/'app.py').read_text(encoding='utf-8'));b=ast.parse((BASE/'app.py').read_text(encoding='utf-8'))
for name in ['BORDAS_MAPA']:
    bloco=lambda ar:next(ast.dump(n) for n in ar.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    checks[name+'_inalterada']=bloco(a)==bloco(b)
checks['load_dotenv_mantido']='load_dotenv()' in (ROOT/'app.py').read_text(encoding='utf-8')
checks['derivados_legados_so_cavaleiro_m']=len(list((ROOT/'static/loja/herois/espada').glob('*.png')))==8 and all(p.name.startswith('cavaleiro-m') for p in (ROOT/'static/loja/herois/espada').glob('*.png'))
dados=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'));itens=dados['itens'];precos={'personagem':150,'particulas':250,'titulos':90,'pets':400,'cenarios':300}
checks['catalogo_somente_precos_aprovados']=all(i['preco']==(0 if i.get('padrao') else precos[i['categoria']]) for i in itens)
checks['catalogo_28_pagos_total_7860']=sum(not i.get('padrao') for i in itens)==28 and sum(i['preco'] for i in itens)==7860
checks['saldo_inicial_inalterado']=dados['saldo_inicial']==json.loads((BASE/'data/loja.json').read_text(encoding='utf-8'))['saldo_inicial']
checks['seis_cenarios_finais_corretos']={i['id'] for i in itens if i['categoria']=='cenarios' and not i.get('padrao')}=={'cenario-'+s for s in ['floresta','taverna','ceu-estrelado','praia-tropical','mundo-doces','jardim-japones']}
checks['molduras_fora_catalogo']=not any(i['categoria']=='molduras' for i in itens)
# v7b: congelados/dados/frames/artes permanecem iguais à v7 aprovada.
pre=json.loads((ROOT.parent/'backup-xp-loja-v7b/baseline-v7.json').read_text(encoding='utf-8'))
for name,h in pre.items():
    if name in {'aparencia.py','data/loja.json','data/economia.json'}:continue
    if (name.startswith(('data/','static/')) and name!='static/loja/perfil-v6.css') or name in {'app.py','contas_cosmos.py','xp.py','simulados.py','aparencia.py','herois.py','economia.py','templates/mapa.html','templates/batalha.html','templates/personagem.html','templates/nivelamento.html','templates/missao.html'}:
        checks['v7b_somente_apresentacao:'+name]=sha(ROOT/name)==h
atual=ast.parse((ROOT/'loja.py').read_text(encoding='utf-8'));antigo=ast.parse((ROOT.parent/'backup-xp-loja-v7b/loja.py').read_text(encoding='utf-8'))
fun=lambda ar:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ar) if isinstance(n,ast.FunctionDef)}
f0,f1=fun(antigo),fun(atual)
for name,dump in f0.items():
    if name not in {'registrar_loja','aparencia_do_perfil','preparar','inicio'}:checks['loja_logica_inalterada:'+name]=f1[name]==dump
checks['sem_camada_global']="loja-efeito.html" not in (ROOT/'templates/loja-base.html').read_text(encoding='utf-8')
# v7c: autorizados somente metadados FR/PT dos quatro títulos e três bônus.
B7C=ROOT.parent/'backup-xp-loja-v7c'
antes=json.loads((B7C/'data/loja.json').read_text(encoding='utf-8'));depois=json.loads((ROOT/'data/loja.json').read_text(encoding='utf-8'))
for catalogo in [antes,depois]:
    for item in catalogo['itens']:
        if item['categoria']=='titulos':
            for chave in ['nome_fr','nome_fr_f','nome_pt_f','descricao']:item.pop(chave,None)
checks['v7c_catalogo_so_traducao_descricao']=antes==depois
antes=json.loads((B7C/'data/economia.json').read_text(encoding='utf-8'));depois=json.loads((ROOT/'data/economia.json').read_text(encoding='utf-8'))
for dado in [antes,depois]:
    for chave in ['bonus_area','bonus_boss','bonus_mapa']:dado.pop(chave,None)
checks['v7c_economia_so_tres_bonus']=antes==depois
orig=(B7C/'aparencia.py').read_text(encoding='utf-8');at=(ROOT/'aparencia.py').read_text(encoding='utf-8')
at=at.replace('from titulos import titulo_fr\n','').replace("titulo=titulo_fr(equipados.get('titulos'),avatar),pet=","titulo=equipados.get('titulos',{}).get('nome',''),pet=")
checks['v7c_aparencia_so_resolvedor_titulo']=orig==at
assert all(checks.values()),[k for k,v in checks.items() if not v]
OUT.mkdir(exist_ok=True);(OUT/'integridade.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(checks),'verificações v7c OK; 0 falhas. Hotfix UTF-8, congelados, XP, ledger, preços, sprites e BORDAS preservados; títulos e três bônus autorizados.')
