"""Arte UI v2: mesma reducao 400x225/64 cores/NEAREST x4 das paradas.
Fonte original gerada por GenerateImage usando nivelamento/mesa-fundo.png
como referencia de estilo. Nao gera imagens e nao acessa servicos ou .env.
"""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
fonte=Path(__file__).with_name("escrivaninha-v2-raw.jpg")
APP=ROOT/"out" if (ROOT/"out/templates").exists() else ROOT
saida=APP/"static/simulados/escrivaninha-v2.webp"
im=Image.open(fonte).convert("RGB").resize((400,225),Image.Resampling.BOX)
im=im.quantize(colors=64,method=Image.Quantize.MAXCOVERAGE,dither=Image.Dither.NONE).convert("RGB")
im=im.resize((1600,900),Image.Resampling.NEAREST)
im.save(saida,"WEBP",lossless=True,method=6)
meta={"origem":"GenerateImage, arte original solicitada por Alex", "referencia":"out/static/nivelamento/mesa-fundo.png (inalterada)", "fonte":"gen/simulados/escrivaninha-v2-raw.jpg", "pipeline":"gen/formatos/arte_formatos.py: BOX 400x225, 64 cores MAXCOVERAGE sem dither, NEAREST x4; exportacao WebP lossless", "asset":"out/static/simulados/escrivaninha-v2.webp", "tamanho":list(im.size), "bytes":saida.stat().st_size, "sha256":hashlib.sha256(saida.read_bytes()).hexdigest(), "descricao":"Mesa de escriba top-down; vela, pena, tinteiro, livros e mapa integrados a arte. Pergaminho central limpo para HTML, luz quente e sombras. Sem elementos CSS fingindo objetos."}
Path(__file__).with_name("arte-ui-v2.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
print(saida,saida.stat().st_size,"bytes")
