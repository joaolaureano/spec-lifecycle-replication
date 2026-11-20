"""RQ2 (spec decay): monta o material de leitura dos pares (spec viva, PR) — gerador de uma vez só, fora do reproduzir.sh.

Saídas em data/validation/: pares.html (o que o avaliador leu), rotulagem_pares.csv (planilha; nunca apaga rótulo),
gabarito_pares.csv, llm/pares.txt e llm/lotes_pares_novos/ (material do 2º avaliador).
Uso: .venv/bin/python -I scripts/analysis/validation_build.py
"""
import gzip, html, json, os, re, sys
import duckdb
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TXT = os.path.join(ROOT, "data", "derived", "specs_text.parquet")
D = os.path.join(ROOT, "data", "specmine", "data")
OUT = os.path.join(ROOT, "data", "validation")
MAX_LINHAS_SPEC, MAX_ARQS = 3000, 3000  # tudo visível: spec inteira e lista inteira de arquivos

PERG_PAR = """P4 (spec decay). Cada par traz uma spec VIVA do OpenSpec (texto atual; ela não foi editada desde antes do PR)
e um PR, aceito DEPOIS da última edição dela, que alterou arquivo(s) de código ligado(s) a essa capacidade sem tocar a spec.
Livro de códigos v3 (05/nov). Julgue SÓ pela spec e pelo diff do código ligado (arquivos marcados); o tamanho do PR
não é critério. Pergunta: depois desse PR, a spec continua dizendo a verdade? Responda NA ORDEM:
  1. O diff muda algum comportamento observável (o que o sistema faz, aceita, devolve ou grava)?
     não -> preserva (refatoração, renomeação, teste, estilo, log, correção que só faz o código cumprir a spec)
  2. Esse comportamento é do assunto desta spec (Purpose e requisitos da capacidade)?
     não, é de outra capacidade -> outra_capacidade (se souber qual, escreva o nome em outra_spec). Depois, um revisor
       procura no repositório uma spec cujo TEXTO descreva a mudança; sem essa evidência, o par conta como omite.
  3. Alguma frase da spec ficou falsa?
     sim -> contradiz (cite a frase em obs)
     não, mas a spec não menciona o comportamento novo -> omite (cite em obs o trecho do escopo)
  Falta informação em qualquer passo (diff truncado ou ausente, binário, spec vaga demais) -> nao_da_para_julgar.
q_decay: preserva | outra_capacidade | contradiz | omite | nao_da_para_julgar
divergencia_previa: sim = o código JÁ contrariava a spec antes deste PR (visível nas linhas de contexto ou removidas);
  não entra no Y; deixe vazio caso contrário.
obs: livre."""


def bloco(titulo, corpo):
    return f"<section><h2>{html.escape(titulo)}</h2>{corpo}</section>"


def lotes(usados, pt, limite=180_000):
    """Lotes de até ~180 mil caracteres, só com os pares novos (P061+), para LLMs externos isolados: só os blocos dos
    pares, sem instruções (as regras vão no prompt, data/validation/llm/prompt_llm2_pares.md). Um par nunca é dividido;
    um par maior que o limite é cortado no fim."""
    d = os.path.join(OUT, "llm", "lotes_pares_novos")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    n, atual = 0, ""
    for par, b in zip(usados, pt):
        if par < "P061":
            continue
        b = "===== " + b[len("===== "):]
        if atual and len(atual) + len(b) > limite:
            n += 1
            open(os.path.join(d, f"novos_{n:02d}.txt"), "w", encoding="utf-8").write(atual)
            atual = ""
        atual += b[:limite] + "\n"
    if atual:
        n += 1
        open(os.path.join(d, f"novos_{n:02d}.txt"), "w", encoding="utf-8").write(atual)


def pares():
    """Página e planilha dos pares (spec viva, PR). Não sobrescreve rotulagem já começada."""
    bases = [os.path.join(ROOT, "data", b) for b in ("api_pr_diffs", "api_pr_diffs_ext")]
    p = pd.concat([pd.read_csv(os.path.join(b, "sample", "pares.csv")) for b in bases if os.path.exists(os.path.join(b, "sample", "pares.csv"))])
    txt = duckdb.sql(f"select file_url_sha16, content from '{TXT}'").df().set_index("file_url_sha16").content
    titulos = duckdb.sql(f"select repo_name, pr_number, title from '{D}/pull_requests.parquet' where tool='openspec'").df()
    p = p.merge(titulos.drop_duplicates(["repo_name", "pr_number"]), on=["repo_name", "pr_number"], how="left")
    ph, pt, usados = [], [], []
    for r in p.itertuples():
        brutos = [os.path.join(b, "raw", r.repo_name.replace("/", "__"), f"pr{r.pr_number}.json.gz") for b in bases]
        bruto = next((x for x in brutos if os.path.exists(x)), None)
        if bruto is None:
            continue  # PR sem resposta da API (perda reportada no manifesto)
        with gzip.open(bruto, "rt", encoding="utf-8") as f:
            arqs = json.load(f)["files"]
        ligados = set(str(r.codigo_ligado).split(";"))
        lista = "\n".join(f"{a.get('status'):9} +{a.get('additions', 0):<5} -{a.get('deletions', 0):<5} {a.get('filename')}"
                          + ("   <== código ligado à spec" if a.get("filename") in ligados else "") for a in arqs[:MAX_ARQS])
        diffs = "\n\n".join(f"### {a['filename']}\n" + "\n".join((a.get("patch") or "(sem diff: binário ou grande demais)")
                                                                .split("\n")[:300]) for a in arqs if a.get("filename") in ligados)
        linhas = (txt.get(r.file_url_sha16) or "").split("\n")
        spec = "\n".join(linhas[:MAX_LINHAS_SPEC])
        cab = f"{r.par} | repo {r.repo_name} | PR #{r.pr_number}: {str(r.title)[:200]} | capacidade: {r.cap}"
        ph.append(bloco(cab, f"<h3>Spec viva</h3><pre>{html.escape(spec)}</pre><h3>Arquivos do PR ({len(arqs)})</h3>"
                             f"<pre>{html.escape(lista)}</pre><h3>Diff do código ligado</h3><pre>{html.escape(diffs)}</pre>"))
        pt.append(f"===== {cab}\n--- SPEC VIVA\n{spec}\n--- ARQUIVOS DO PR ({len(arqs)})\n{lista}\n--- DIFF DO CÓDIGO LIGADO\n{diffs}\n")
        usados.append(r.par)
    lotes(usados, pt)
    estilo = "<style>body{font-family:sans-serif;max-width:1100px;margin:auto}pre{background:#f4f4f4;padding:8px;white-space:pre-wrap;font-size:12px}section{border-top:2px solid #333;margin-top:28px}</style>"
    with open(os.path.join(OUT, "pares.html"), "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset=utf-8><title>Validação — P4 pares</title>{estilo}<pre>{html.escape(PERG_PAR)}</pre>" + "".join(ph))
    with open(os.path.join(OUT, "llm", "pares.txt"), "w", encoding="utf-8") as f:
        f.write(PERG_PAR + "\n\n" + "\n".join(pt))
    rot = os.path.join(OUT, "rotulagem_pares.csv")
    novos = p[p.par.isin(usados)][["par", "repo_name", "pr_number"]].assign(v1="", revisar="", q_decay="", outra_spec="",
                                                                              revisao_outra="", divergencia_previa="", obs="")
    if os.path.exists(rot):  # nunca apaga rótulo: só acrescenta os pares que ainda não estão na planilha
        velho = pd.read_csv(rot, dtype=str, keep_default_na=False)
        novos = pd.concat([velho, novos[~novos.par.isin(velho.par)].astype(str)])
    novos.sort_values("par").to_csv(rot, index=False)
    p[p.par.isin(usados)].to_csv(os.path.join(OUT, "gabarito_pares.csv"), index=False)
    print(f"pares: {len(usados)} de {len(p)} (os demais sem resposta da API)")


if __name__ == "__main__":
    pares()
