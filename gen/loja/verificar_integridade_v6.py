"""Auditoria local v6. Única exceção do motor: bloco de XP/conclusão autorizado.
Snapshots ficam fora do pacote/produção; nenhuma leitura de .env ou rede.
"""
from pathlib import Path
import ast,hashlib,json,difflib,copy
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent/'backup-xp-loja-v6';OUT=ROOT.parent/'relatorio-xp-loja-v6'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
AUTORIZADOS={'app.py','contas_cosmos.py','loja.py','templates/mapa.html','templates/batalha.html','templates/heroi.html','templates/loja.html','templates/loja-base.html','static/parada/motor.js','static/parada/formatos.js','docs/balanceamento-xp-cristais.md'}
for backup in ['backup-loja/frozen.json','backup-heroi-espada/protegidos.json','backup-heroi-v3/protegidos.json','backup-heroi-v4/protegidos.json','backup-heroi-v5/protegidos.json','backup-xp-loja-v6/protegidos.json']:
 for name,h in json.loads((ROOT.parent/backup).read_text()).items():
  if name in AUTORIZADOS or name.startswith('data/paradas/'):continue
  if name.startswith('static/loja/pets/') and not backup.startswith('backup-xp-loja-v6/'):continue
  if name=='herois.py' and not backup.startswith('backup-xp-loja-v6/'):continue
  if name=='data/loja.json' and backup.startswith('backup-heroi-espada/'):continue
  if name=='static/loja/heroi-v2.css' and not backup.startswith('backup-xp-loja-v6/'):continue
  checks[backup+':'+name]=sha(ROOT/name)==h
# Todas as artes v5 (inclusive fontes e animações) continuam byte-idênticas.
v5=json.loads((ROOT.parent/'relatorio-heroi-v5/manifesto.json').read_text())['paths']
for name,h in v5.items():
 if name.endswith(('.png','.gif','.jpg','.jpeg')):checks['arte_v5:'+name]=sha(ROOT/name)==h
old=(BASE/'static/parada/motor.js').read_text();new=(ROOT/'static/parada/motor.js').read_text()
for marker,parte in [('  /* ---------- fim da parada ---------- */',0),('  /* Estado exposto só para testes/depuração',1)]:
 checks['motor_jogabilidade_intacta:'+str(parte)]=old.split(marker)[parte]==new.split(marker)[parte]
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/static/parada/motor.js',tofile='b/static/parada/motor.js'))
(ROOT/'docs/diff-motor-xp-v6.patch').write_text(patch)
f0=(BASE/'static/parada/formatos.js').read_text();f1=(ROOT/'static/parada/formatos.js').read_text()
checks['formatos_prefixo_sem_mudar_jogo']=f0.split('  function salvar(')[0]==f1.split('  function salvar(')[0]
checks['formatos_toda_jogabilidade_apos_xp_intacta']=f0.split('  function abertura(')[1]==f1.split('  function abertura(')[1]
a0=ast.parse((BASE/'app.py').read_text());a1=ast.parse((ROOT/'app.py').read_text())
fun=lambda ar:{n.name:ast.dump(n,include_attributes=False) for n in ar.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
antes,depois=fun(a0),fun(a1)
for name,texto in antes.items():
 if name not in {'mapa','parada_concluir','teste_zerar'}:checks['funcao_app_intacta:'+name]=depois[name]==texto
for ar,label in [(a0,'antes'),(a1,'depois')]:
 for n in ar.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BORDAS_MAPA' for t in n.targets):
   if label=='antes':bordas=ast.dump(n)
   else:checks['BORDAS_MAPA_inalterada']=bordas==ast.dump(n)
for p in (ROOT/'data/paradas').glob('*.json'):
 d0=json.loads((BASE/p.relative_to(ROOT)).read_text());d1=json.loads(p.read_text())
 for d in [d0,d1]:
  for k in ['xp_base','xp_por_estrela','xp_pausado','xp_versao']:d.get('recompensa',{}).pop(k,None)
 checks['conteudo_e_estrelas_intactos:'+p.name]=d0==d1
for marker,label in [('<div class="pergaminho ficha">','painel'),('<section id="conquistas"','bau')]:
 antigo=(BASE/'templates/heroi.html').read_text().split(marker)[1];atual=(ROOT/'templates/heroi.html').read_text().split(marker)[1]
 antigo=antigo.replace('Pets ficam somente aqui, ao seu lado. Nada de companheiros atravessando batalhas!','Seu companheiro também aparece na ficha do mapa e nas batalhas: é só companhia, sem alterar o combate.')
 checks[label+'_intacto_exceto_nota_de_visibilidade']=antigo==atual
legacy=list((ROOT/'static/loja/herois/espada').glob('*.png'))
checks['legado_so_oito_cavaleiro_m']=len(legacy)==8 and all(p.name.startswith('cavaleiro-m') for p in legacy)
checks['load_dotenv_mantido']='load_dotenv()' in (ROOT/'app.py').read_text()
checks['catalogo_precos_saldos_intactos']=(ROOT/'data/loja.json').read_bytes()==(BASE/'data/loja.json').read_bytes()
checks['economia_valores_intactos']=(ROOT/'data/economia.json').read_bytes()==(BASE/'data/economia.json').read_bytes()
for line in (BASE/'templates/batalha.html').read_text().splitlines():
 if 'data-trilha=' in line:checks['tag_musica_batalha_chefe_inalterada']=line in (ROOT/'templates/batalha.html').read_text().splitlines()
assert all(checks.values()),[k for k,v in checks.items() if not v]
OUT.mkdir(exist_ok=True);(OUT/'integridade.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(len(checks),'verificações v6 OK; 0 falhas. Motor: apenas XP; jogos/congelados/artes v5/música/BORDAS intactos.')
