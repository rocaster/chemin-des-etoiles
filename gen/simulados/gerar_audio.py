"""Sintese edge-tts fr-CA existente: sem .env, senhas ou chaves.
Uso no box: /workspace/ncl/.v/bin/python gen/simulados/gerar_audio.py
"""
import json, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parents[2]/"out"
if not root.exists(): root=Path(__file__).resolve().parents[2]
rows=json.loads((root/"data/simulados/tef.json").read_text())["sections"]["co"]
exe="/workspace/ncl/.tts/bin/edge-tts"
def gerar(item):
 p=root/"static"/item["audio"];p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.stat().st_size>1000:return p.name+" existente"
 voz="fr-CA-SylvieNeural" if int(item["id"][2:])%2 else "fr-CA-AntoineNeural"
 r=subprocess.run([exe,"--voice",voz,"--rate=-5%","--text",item["texte"]+" Question : "+item["question"],"--write-media",str(p)],capture_output=True,timeout=70)
 if r.returncode:raise RuntimeError("Falha de sintese em "+item["id"])
 return p.name+" OK"
with ThreadPoolExecutor(max_workers=4) as pool:
 for msg in pool.map(gerar,rows):print(msg,flush=True)
print("40 audios gerados",flush=True)
