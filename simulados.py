"""Simulados nao oficiais: regras editoriais e persistencia no perfil existente, XP zero."""
import json, re, time, uuid
from pathlib import Path
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

DISCLAIMER = "Simulado não oficial para prática, sem vínculo com CCI Paris Île-de-France, France Éducation international ou IRCC. Escalas/NCLC são estimativas não oficiais, não um resultado de exame."
ROOT = Path(__file__).resolve().parent
PLANOS = {
 "tef": [("co", "CO",2400),("ce","CE",3600),("eea","EE · section A",1500),("eeb","EE · section B",2100),("eoa","EO · section A",300),("eob","EO · section B",600)],
 "tcf": [("co","CO",2100),("ce","CE",3600),("ee","EE · tâches 1–3",3600),("eo1","EO · entretien",120),("prep","EO · préparation tâche 2",120),("eo2","EO · interaction",210),("eo3","EO · point de vue",270)]}
FAIXAS={"tef":{"co":[(145,4),(181,5),(217,6),(249,7),(280,8),(298,9),(316,10)],"ce":[(121,4),(151,5),(181,6),(207,7),(233,8),(248,9),(263,10)]},"tcf":{"co":[(331,4),(369,5),(398,6),(458,7),(503,8),(523,9),(549,10)],"ce":[(342,4),(375,5),(406,6),(453,7),(499,8),(524,9),(549,10)]}}
AD = "ATELIER PHOTO À MONTRÉAL — Six rencontres, le mardi à 18 h 30, à la bibliothèque Rosemont. Tarif total: 85 dollars; matériel prêté. Inscription sur place ou en ligne. Débutants bienvenus; sortie pratique le dernier samedi."
ECRITS={
 "eea":[{"id":"a","titre":"Section A — fait divers","min":80,"max":None,"consigne":"Continuez cet article en ajoutant les événements, les circonstances et la fin de l'histoire (au moins 80 mots).","documents":["Un mardi matin, une employée d'une épicerie de Trois-Rivières a trouvé une enveloppe ancienne derrière une étagère. Son contenu a attiré l'attention de tout le quartier..."]}],
 "eeb":[{"id":"b","titre":"Section B — argumentation","min":200,"max":None,"consigne":"Un journal local affirme: « Les rues du centre-ville devraient être réservées aux piétons tous les week-ends. » Écrivez au journal pour défendre votre opinion avec des arguments et des exemples (au moins 200 mots).","documents":[]}],
 "ee":[{"id":"1","titre":"Tâche 1 — message","min":60,"max":120,"consigne":"Vous invitez un collègue nouvellement installé à une activité de quartier. Décrivez le lieu, l'horaire et ce que vous proposez de faire ensemble.","documents":[]},
 {"id":"2","titre":"Tâche 2 — récit","min":120,"max":150,"consigne":"Sur le site de votre association, racontez votre première expérience de bénévolat au Canada. Expliquez ce que vous avez fait, une difficulté rencontrée et ce que vous en avez retenu.","documents":[]},
 {"id":"3","titre":"Tâche 3 — synthèse et opinion","min":120,"max":180,"consigne":"Présentez brièvement les deux points de vue, puis donnez votre avis argumenté sur les ateliers numériques en bibliothèque.","documents":["Point de vue A: Des ateliers numériques gratuits aident les habitants à effectuer leurs démarches et réduisent leur isolement. La bibliothèque doit élargir ces activités.","Point de vue B: Les activités numériques ne doivent pas prendre toute la place. Les lecteurs ont aussi besoin de calme, de livres et d'un accompagnement qui ne dépende pas des écrans."]}]}
ORAUX={
 "eoa":("Vous appelez l'organisateur de cet atelier. Posez des questions pour obtenir des renseignements.",AD,"Bonjour, vous appelez pour l'atelier photo? Je vous écoute."),
 "eob":("Convainquez votre ami de participer à cet atelier. Répondez à ses objections.",AD,"Je ne suis pas très convaincu. Pourquoi est-ce que je devrais participer?"),
 "eo1":("Répondez aux questions de l'examinateur sur vous, votre travail, votre quotidien et vos projets. Aucune préparation.","Entretien dirigé — répondez en français.","Bonjour. Présentez-vous et parlez-moi de votre quotidien."),
 "prep":("Préparez vos questions pour l'interaction. Ces deux minutes font partie de l'épreuve orale; pas de dialogue pendant la préparation.",AD,"Préparez vos questions. L'interaction commencera après deux minutes."),
 "eo2":("Vous souhaitez participer à cet atelier. Interrogez l'organisateur: tarif, horaires, équipement, inscription...",AD,"Bonjour! Qu'aimeriez-vous savoir sur notre atelier?"),
 "eo3":("Défendez votre point de vue: les bibliothèques devraient-elles proposer davantage d'activités numériques? Donnez des raisons et des exemples. Aucune préparation.","L'examinateur peut demander des précisions.","Selon vous, faut-il développer les activités numériques en bibliothèque?")}


def banque(examen):
 if examen not in PLANOS: abort(404)
 return json.loads((ROOT/"data"/"simulados"/(examen+".json")).read_text(encoding='utf-8'))


def agora():
 return int(current_app.config.get("SIMULADOS_AGORA",lambda:time.time()*1000)())


def palavras(texto):
 return len(re.findall(r"(?:[^\W_]|['’-])+",texto or ""))


def estimar(examen,secao,acertos,total):
 # MODELO LINEAR DIDATICO, nao tabela de conversao oficial de itens/IRT.
 p=acertos/total
 antigo=round(p*(360 if secao=="co" else 300)) if examen=="tef" else None
 escala=round(p*699) if examen=="tef" else round(100+p*599)
 valor=antigo if antigo is not None else escala
 faixa=max([n for lim,n in FAIXAS[examen][secao] if valor>=lim] or [0])
 return {"escala":escala,"ancien":antigo,"nclc":"10+" if faixa==10 else str(faixa) if faixa else "abaixo de 4",
         "aviso":"Estimativa não oficial por proporção linear de acertos; itens não calibrados. Não prevê uma nota real nem comprova NCLC."}


def etapas(examen,secao):
 return [{"id":i,"titulo":t,"segundos":s} for i,t,s in PLANOS[examen] if secao=="completo" or i.startswith(secao) or (secao=="eo" and i=="prep")]


def dados_publicos(ativo):
 plano=ativo["plano"];i=ativo["indice"];etapa=plano[i];sid=etapa["id"]
 dados={k:v for k,v in ativo.items() if k not in {"parciais"}}
 dados.update(etapa=etapa,server_now=agora(),disclaimer=DISCLAIMER)
 if sid in {"co","ce"}:
  dados["itens"]=[{k:v for k,v in x.items() if k!="correct" and (sid=="ce" or k!="texte")} for x in banque(ativo["examen"])["sections"][sid]]
 if sid in ECRITS: dados["tarefas"]=ECRITS[sid]
 if sid in ORAUX:
  consigne,document,ouverture=ORAUX[sid]
  dados["oral"]={"consigne":consigne,"document":document,"ouverture":ouverture,"preparacao":sid=="prep"}
 return dados


def resultado_etapa(examen,etapa,corpo,inicio,fim,esgotado):
 sid=etapa["id"];resultado={"etapa":sid,"titulo":etapa["titulo"],"tempo_esgotado":esgotado,"duracao_s":min(etapa["segundos"],max(0,round((fim-inicio)/1000))),"nota_oficial":None}
 if sid in {"co","ce"}:
  itens=banque(examen)["sections"][sid];recebidas=corpo.get("respostas",{})
  if not isinstance(recebidas,dict):recebidas={}
  respostas={x["id"]:recebidas.get(x["id"]) if type(recebidas.get(x["id"])) is int and recebidas[x["id"]] in range(4) else None for x in itens}
  certas=sum(respostas[x["id"]]==x["correct"] for x in itens)
  resultado.update(acertos=certas,total=len(itens),respostas=respostas,estimativa=estimar(examen,sid,certas,len(itens)),penalidade_por_erro=0)
 elif sid in ECRITS:
  textos=corpo.get("textos",{}) if isinstance(corpo.get("textos"),dict) else {}
  checklist=corpo.get("checklist",[]) if isinstance(corpo.get("checklist"),list) else []
  resultado["tarefas"]=[]
  for t in ECRITS[sid]:
   texto=str(textos.get(t["id"],""))[:6000];n=palavras(texto)
   resultado["tarefas"].append({"id":t["id"],"texto":texto,"palavras":n,"min":t["min"],"max":t["max"],"faixa_ok":n>=t["min"] and (t["max"] is None or n<=t["max"])})
  resultado["checklist"]=[str(x)[:90] for x in checklist[:6]]
  resultado["aviso"]="Somente contagem e autoavaliação; sem correção humana, nota ou NCLC."
  if examen=="tcf":resultado["faixas_a_confirmar"]=True
 elif sid!="prep":
  turns=corpo.get("transcript",[]) if isinstance(corpo.get("transcript"),list) else []
  limite=5000;limpos=[]
  for t in turns[-40:]:
   if not isinstance(t,dict) or limite<=0:continue
   texto=str(t.get("texto",""))[:min(5000,limite)];limite-=len(texto)
   limpos.append({"papel":"candidato" if t.get("papel")=="candidato" else "examinador","texto":texto,"modo":"voz" if t.get("modo")=="voz" else "texto"})
  candidato=[t["texto"] for t in limpos if t["papel"]=="candidato"]
  resultado.update(transcript=limpos,transcript_truncado=len(turns)>40 or sum(len(str(t.get("texto",""))) for t in turns if isinstance(t,dict))>5000,palavras=sum(palavras(t) for t in candidato),intervencoes=len(candidato),perguntas=sum(bool(re.search(r"\?|\b(combien|quand|comment|pourquoi|quel|quelle|où|est-ce)\b",t.lower())) for t in candidato),aviso="Feedback indicativo: quantidade de fala/perguntas, não qualidade, fluência ou nota oficial. Texto digitado não equivale a desempenho oral.")
 return resultado


def registrar_simulados(app,usuarios,perfil_atual):
 bp=Blueprint("simulados",__name__)
 def perfil():
  p=perfil_atual()
  if p is None:abort(401)
  return p
 def corpo():
  d=request.get_json(silent=True)
  return d if isinstance(d,dict) else {}
 def ativo_ou_erro(examen,p):
  a=p.get("simulados_ativo")
  if not a or a.get("examen")!=examen:abort(409)
  return a
 @bp.route("/simulados/<examen>")
 def inicio(examen):
  banque(examen);p=perfil()
  return render_template("simulados.html",modo="inicio",examen=examen,disclaimer=DISCLAIMER,historico=(p.get("simulados_historico") or [])[-5:],ativo=p.get("simulados_ativo"))
 @bp.route("/simulados/<examen>/iniciar",methods=["POST"])
 def iniciar(examen):
  banque(examen);p=perfil();d=corpo();secao=d.get("secao","completo")
  if secao not in {"co","ce","ee","eo","completo"}:return jsonify(erro="Seção inválida."),400
  anterior=p.get("simulados_ativo")
  if anterior and not d.get("novo"):
   return jsonify(url=url_for("simulados.prova",examen=anterior["examen"]),retomada=True)
  plano=etapas(examen,secao);ag=agora()
  p["simulados_ativo"]={"id":uuid.uuid4().hex,"examen":examen,"secao":secao,"plano":plano,"indice":0,"inicio":ag,"etapa_inicio":ag,"deadline":ag+plano[0]["segundos"]*1000,"parciais":[]}
  usuarios().upsert_item(p)
  return jsonify(url=url_for("simulados.prova",examen=examen))
 @bp.route("/simulados/<examen>/prova")
 def prova(examen):
  banque(examen);p=perfil();a=p.get("simulados_ativo")
  if not a or a.get("examen")!=examen:return redirect(url_for("simulados.inicio",examen=examen))
  return render_template("simulados.html",modo="prova",examen=examen,config=dados_publicos(a),disclaimer=DISCLAIMER)
 @bp.route("/simulados/<examen>/estado")
 def estado(examen):
  banque(examen);return jsonify(dados_publicos(ativo_ou_erro(examen,perfil())))
 @bp.route("/simulados/<examen>/entregar",methods=["POST"])
 def entregar(examen):
  banque(examen);p=perfil();d=corpo();a=p.get("simulados_ativo")
  if not a:
   concluida=next((h for h in p.get("simulados_historico",[]) if h["id"]==d.get("tentativa")),None)
   if concluida:return jsonify(url=url_for("simulados.resultados",tentativa=concluida["id"]),concluido=True)
   abort(409)
  if a["examen"]!=examen or d.get("tentativa")!=a["id"]:abort(409)
  if d.get("indice")!=a["indice"]:
   return (jsonify(config=dados_publicos(a)),200) if type(d.get("indice")) is int and d["indice"]<a["indice"] else (jsonify(erro="Etapa inválida."),409)
  ag=agora();esgotado=ag>=a["deadline"];et=a["plano"][a["indice"]]
  a["parciais"].append(resultado_etapa(examen,et,d,a["etapa_inicio"],ag,esgotado))
  anterior_deadline=a["deadline"];a["indice"]+=1
  if a["indice"]>=len(a["plano"]):
   final={"id":a["id"],"examen":examen,"secao":a["secao"],"inicio":a["inicio"],"fim":ag,"resultados":a["parciais"],"xp":0,"disclaimer":DISCLAIMER}
   p["simulados_historico"]=([h for h in p.get("simulados_historico",[]) if h["id"]!=a["id"]]+[final])[-5:]
   p["simulados_ativo"]=None;usuarios().upsert_item(p)
   return jsonify(concluido=True,url=url_for("simulados.resultados",tentativa=a["id"]))
  a["etapa_inicio"]=anterior_deadline if esgotado else ag
  a["deadline"]=a["etapa_inicio"]+a["plano"][a["indice"]]["segundos"]*1000
  p["simulados_ativo"]=a;usuarios().upsert_item(p)
  return jsonify(config=dados_publicos(a))
 @bp.route("/simulados/resultados/<tentativa>")
 def resultados(tentativa):
  p=perfil();r=next((h for h in p.get("simulados_historico",[]) if h["id"]==tentativa),None)
  if not r:abort(404)
  return render_template("simulados.html",modo="resultados",examen=r["examen"],resultado=r,disclaimer=DISCLAIMER)
 app.register_blueprint(bp)
