"""Rotas e regras dos simulados: somente Flask test client, sem .env/Cosmos real."""
import sys,os,json,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]/"out"
if not (ROOT/"app.py").exists():ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
with patch("dotenv.load_dotenv",return_value=False):import app as A
import simulados as S
ok=0

def chk(msg,cond):
 global ok
 if not cond:raise AssertionError(msg)
 ok+=1;print("OK",msg)
A.USUARIOS_TESTE.add("teste")
A.get_users_container=lambda:(_ for _ in ()).throw(AssertionError("Cosmos real proibido"))
A.app.config["TESTING"]=True
now=[1800000000000];A.app.config["SIMULADOS_AGORA"]=lambda:now[0]
c=A.app.test_client()
with patch.dict(os.environ,{"NCL_SENHA_TESTE":""}):c.post("/login",data={"usuario":"teste","senha":"qualquer"})
chk("anonimo precisa login",A.app.test_client().get("/simulados/tef").status_code==302)
for ex,n in (("tef",40),("tcf",39)):
 b=S.banque(ex)
 for sec in ("co","ce"):
  rows=b["sections"][sec]
  chk(ex+sec+" contagem completa",len(rows)==n)
  chk(ex+sec+" quatro alternativas e uma resposta",all(len(x["choix"])==4 and len(set(x["choix"]))==4 and x["correct"] in range(4) for x in rows))
  if ex=="tcf":chk("TCF dificuldade progressiva "+sec,["A1","A2","B1","B2","C1","C2"]==list(dict.fromkeys(x["niveau"] for x in rows)))
 chk(ex+" landing renderiza",c.get("/simulados/"+ex).status_code==200)
chk("mapa tem placas e links",all(x in c.get("/mapa").get_data(as_text=True) for x in ('sim-placas','/simulados/tef','/simulados/tcf')))
chk("exame invalido rejeitado",c.get("/simulados/xxx").status_code==404)
chk("secao invalida rejeitada",c.post("/simulados/tef/iniciar",json={"secao":"xxx"}).status_code==400)
for ex in ("tef","tcf"):
 for sec in ("co","ce","ee","eo","completo"):
  r=c.post(f"/simulados/{ex}/iniciar",json={"secao":sec,"novo":True})
  chk(ex+sec+" inicia",r.status_code==200)
  cfg=c.get(f"/simulados/{ex}/estado").get_json()
  esperado={"tef":{"co":2400,"ce":3600,"ee":3600,"eo":900,"completo":10500},"tcf":{"co":2100,"ce":3600,"ee":3600,"eo":720,"completo":10020}}[ex][sec]
  chk(ex+sec+" duracao real",sum(t["segundos"] for t in cfg["plano"])==esperado)
  deadline=cfg["deadline"];now[0]+=10000
  rec=c.get(f"/simulados/{ex}/estado").get_json()
  chk("recarregar nao reinicia "+ex+sec,rec["deadline"]==deadline and rec["etapa_inicio"]==cfg["etapa_inicio"])
  chk("pagina prova renderiza "+ex+sec,c.get(f"/simulados/{ex}/prova").status_code==200)
# Sequencias orais exatas e preparacao.
chk("TEF oral 5+10",[x["segundos"] for x in S.etapas("tef","eo")]==[300,600])
chk("TCF oral 2 + prep2 + 3:30 + 4:30",[x["segundos"] for x in S.etapas("tcf","eo")]==[120,120,210,270])
c.post("/simulados/tef/iniciar",json={"secao":"completo","novo":True})
cfg=c.get("/simulados/tef/estado").get_json();original_deadline=cfg["deadline"]
chk("gabarito nao exposto",all("correct" not in x and "texte" not in x for x in cfg["itens"]))
chk("audio MP3 servido",c.get('/static/'+cfg['itens'][0]['audio']).status_code==200)
with tempfile.TemporaryDirectory(prefix="simulados-js-") as pasta:
 arquivo=Path(pasta)/"co.json";arquivo.write_text(json.dumps(cfg), encoding='utf-8')
 r=subprocess.run(["node",str(Path(__file__).with_name("simulados.js")),str(arquivo),str(ROOT)],text=True,capture_output=True)
 print(r.stdout)
 if r.returncode:print(r.stderr)
 chk("JS timers/audio/navegacao/autosubmit",r.returncode==0)
# Prova completa, finalizacao por timeout e sem XP.
while True:
 cfg=c.get("/simulados/tef/estado").get_json();sid=cfg["etapa"]["id"]
 body={"tentativa":cfg["id"],"indice":cfg["indice"]}
 if sid in {"co","ce"}:body["respostas"]={x["id"]:x["correct"] for x in S.banque("tef")["sections"][sid]}
 if sid in S.ECRITS:body["textos"]={x["id"]:"bonjour "*x["min"] for x in S.ECRITS[sid]}
 if sid in S.ORAUX:body["transcript"]=[{"papel":"candidato","texto":"Combien coûte cet atelier?","modo":"voz"}]
 now[0]=cfg["deadline"]
 r=c.post("/simulados/tef/entregar",json=body);j=r.get_json()
 chk("envio automatico em zero "+sid,r.status_code==200)
 if j.get("concluido"):break
 chk("proxima etapa usa deadline anterior",j["config"]["etapa_inicio"]==now[0])
 retry=c.post("/simulados/tef/entregar",json=body).get_json()
 chk("entrega duplicada nao avanca duas etapas",retry.get("config",{}).get("indice")==j["config"]["indice"])
with c.session_transaction() as sess:uid="teste:"+sess["teste"]
p=A._PERFIS_TESTE[uid];final=p["simulados_historico"][-1]
chk("historico salvo no perfil",len(final["resultados"])==6 and p["simulados_ativo"] is None)
chk("compreensao corrige acertos",all(r["acertos"]==40 and r["estimativa"]["nclc"]=="10+" and r["penalidade_por_erro"]==0 for r in final["resultados"] if r["etapa"] in {"co","ce"}))
chk("sem nota oficial e sem XP",all(r["nota_oficial"] is None for r in final["resultados"]) and final["xp"]==0 and p["xp"]==0)
chk("EE apenas contagem e sem nota",all(r["tarefas"][0]["faixa_ok"] for r in final["resultados"] if "tarefas" in r))
chk("oral transcript e perguntas",all(r["perguntas"]==1 and r["palavras"]>0 for r in final["resultados"] if "transcript" in r))
chk("resultados renderizam",c.get(j["url"]).status_code==200)
chk("resposta final idempotente",c.post("/simulados/tef/entregar",json=body).get_json().get("concluido") is True)
# Errados/brancos nao descontam; historico conserva somente cinco.
for _ in range(6):
 c.post("/simulados/tcf/iniciar",json={"secao":"co","novo":True})
 cfg=c.get("/simulados/tcf/estado").get_json()
 c.post("/simulados/tcf/entregar",json={"tentativa":cfg["id"],"indice":0,"respostas":{}})
chk("historico limitado a 5",len(A._PERFIS_TESTE[uid]["simulados_historico"])==5)
z=A._PERFIS_TESTE[uid]["simulados_historico"][-1]["resultados"][0]
chk("brancos = zero acertos, sem pontos negativos",z["acertos"]==0 and z["penalidade_por_erro"]==0)
# Mesmo fluxo pelo adaptador real de contas, mas com container Cosmos em memoria.
from cosmos_fake import CosmosFake
fake=CosmosFake();A.get_users_container=lambda:fake
uid_normal="conta-simulado"
A.contas().criar(uid_normal,"qa_simulados","hash-fake","qa_simulados@example.com",{"id":uid_normal,"avatar":"mago-m","nome":"Alex","nome_personagem":"Alex","onboarding_versao":1,"nivelamento_concluido_em":"feito","onboarding_concluido_em":"feito","moldura":1,"xp":42},"nonce-fake",__import__("time").time())
A.contas().confirmar(uid_normal,"nonce-fake")
cn=A.app.test_client()
with cn.session_transaction() as ses:ses["uid"]=uid_normal
cn.post("/simulados/tef/iniciar",json={"secao":"ce"})
cf=cn.get("/simulados/tef/estado").get_json()
j=cn.post("/simulados/tef/entregar",json={"tentativa":cf["id"],"indice":0}).get_json()
pn=A.contas().read_item(uid_normal)
chk("salva resultado na conta Cosmos simulada",len(pn["simulados_historico"])==1 and pn["simulados_ativo"] is None)
chk("preserva XP e hash do perfil Cosmos",pn["xp"]==42 and fake.docs[uid_normal]["senha_hash"]=="hash-fake")
chk("resultado isolado por usuario",c.get(j["url"]).status_code==404)
chk("sem Cosmos real",A._client is None)
# Markup real do Flask exercitado em DOM simulado; NAO e screenshot/validacao visual.
ui=A.app.test_client()
with patch.dict(os.environ,{"NCL_SENHA_TESTE":""}):ui.post("/login",data={"usuario":"teste","senha":"qualquer"})
fixtures={"tef_inicio":ui.get("/simulados/tef").get_data(as_text=True),"tcf_inicio":ui.get("/simulados/tcf").get_data(as_text=True)}
for sec in ("co","ee","eo"):
 ui.post("/simulados/tcf/iniciar",json={"secao":sec,"novo":True})
 fixtures[sec]=ui.get("/simulados/tcf/prova").get_data(as_text=True)
 if sec=="co":fixtures["ativo"]=ui.get("/simulados/tcf").get_data(as_text=True)
ui.post("/simulados/tcf/iniciar",json={"secao":"co","novo":True})
uf=ui.get("/simulados/tcf/estado").get_json()
uj=ui.post("/simulados/tcf/entregar",json={"tentativa":uf["id"],"indice":0}).get_json()
fixtures["resultados"]=ui.get(uj["url"]).get_data(as_text=True)
with tempfile.TemporaryDirectory(prefix="simulados-ui-") as pasta:
 arquivo=Path(pasta)/"html.json";arquivo.write_text(json.dumps(fixtures), encoding='utf-8')
 r=subprocess.run(["node",str(Path(__file__).with_name("simulados-ui.js")),str(arquivo),str(ROOT)],text=True,capture_output=True)
 print(r.stdout)
 if r.returncode:print(r.stderr)
 chk("UI v2 no DOM real do template (nao validacao visual)",r.returncode==0)
print(f"\n{ok} OK, 0 falhas")
