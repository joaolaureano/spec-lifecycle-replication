"""RQ2 — Candidatas a dona da mudança, para a revisão de evidência (regra de dono, docs/metodo.md §5b).

Roda ANTES de ler os rótulos humanos e os do LLM: para cada par (piloto incluído), lista specs de OUTRA capacidade do mesmo
repositório que podem descrever a mudança: (A) changes cujo tasks.md cita o mesmo arquivo ligado; (B) specs tocadas
pelo PR; (C) specs com termos das linhas alteradas no diff ligado. O revisor lê revisao.txt e decide se alguma
descreve a mudança (data/validation/revisao_dono/decisoes.csv); só depois isso é aplicado aos pares rotulados outra_capacidade.
Uso: .venv/bin/python -I scripts/analysis/p4_dono.py
Saída: data/validation/revisao_dono/{candidatos.csv,revisao_NN.txt}
"""
import gzip, json, math, os, re
from collections import Counter
import duckdb
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "specmine", "data")
U = os.path.join(ROOT, "data", "derived", "universe.parquet")
TXT = os.path.join(ROOT, "data", "derived", "specs_text.parquet")
VAL = os.path.join(ROOT, "data", "validation")
OUT = os.path.join(VAL, "revisao_dono")
BASES = [os.path.join(ROOT, "data", b) for b in ("api_pr_diffs", "api_pr_diffs_ext")]
CAP = re.compile(r"/specs/(.+)/spec\.md$")
PALAVRA = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")
COMUNS = set("""return const function import export class async await string number boolean false true null undefined
self this print value values default public private static final void error errors throw catch result results
props state data type types interface struct return_value await_ length index items item array object config
options param params value_ string_ should expect describe test tests assert""".split())
POR_ARQ = 6  # pares por arquivo de revisão


def termos(patch):
    """Identificadores das linhas alteradas (+/-), sem palavras de linguagem."""
    linhas = [l[1:] for l in patch.split("\n") if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    return {t for l in linhas for t in PALAVRA.findall(l) if t.lower() not in COMUNS}


def main():
    pares = pd.read_csv(os.path.join(VAL, "gabarito_pares.csv"), dtype=str)
    pares = pares.sort_values("par")
    repos = tuple(pares.repo_name.unique())
    # order by: o texto da capacidade é a junção das suas specs; sem ordem fixa, o DuckDB variava a junção entre execuções
    specs = duckdb.sql(f"select repo_name, file_path, content from '{TXT}' where repo_name in {repos} "
                       "order by repo_name, file_path").df()
    specs["cap"] = specs.file_path.str.extract(CAP)[0]
    specs = specs.dropna(subset=["cap"])
    refs = duckdb.sql(f"""
        select distinct u.repo_name, regexp_extract(u.file_path, '/specs/(.+)/spec\\.md$', 1) cap, l.target
        from '{D}/spec_links.parquet' l join '{U}' u on u.file_url_sha16=l.spec_url_sha16
        where u.repo_name in {repos} and l.rel='code' and l.provenance='tasks'
          and regexp_matches(u.file_path, 'openspec/changes/.+/specs/.+/spec\\.md$')""").df()
    linhas_csv, blocos = [], []
    for r in pares.itertuples():
        bruto = next(x for b in BASES if os.path.exists(x := os.path.join(b, "raw", r.repo_name.replace("/", "__"),
                                                                            f"pr{r.pr_number}.json.gz")))
        with gzip.open(bruto, "rt", encoding="utf-8") as f:
            arqs = json.load(f)["files"]
        ligados = set(r.codigo_ligado.split(";"))
        patch = "\n".join(a.get("patch") or "" for a in arqs if a.get("filename") in ligados)
        do_repo = specs[(specs.repo_name == r.repo_name) & (specs.cap != r.cap)]
        a_ = set(refs[(refs.repo_name == r.repo_name) & refs.target.isin(ligados) & (refs.cap != r.cap)].cap)
        b_ = {m.group(1) for a in arqs if (m := CAP.search(a.get("filename", ""))) and m.group(1) != r.cap}
        tt = sorted(termos(patch))  # ordem fixa: a soma de floats abaixo não pode depender da ordem de um set
        # (C) termo raro no repositório pesa mais (idf entre as capacidades do repo)
        texto_cap = do_repo.groupby("cap").content.apply(lambda s: "\n".join(s.fillna("")))
        df = Counter(t for t in tt for c in texto_cap.index if t in texto_cap[c])
        n = max(len(texto_cap), 1)
        nota = {c: sum(math.log(1 + n / df[t]) for t in tt if t in texto_cap[c]) for c in texto_cap.index}
        # desempate pelo nome: sem ele, a ordem de set/dict (hash aleatório por processo) decidia quem entrava no corte
        c_ = {c for c, v in sorted(nota.items(), key=lambda x: (-x[1], x[0]))[:3] if v > 0}
        cands = sorted(a_ | b_ | c_, key=lambda c: (-(c in a_) - (c in b_), -nota.get(c, 0), c))[:5]
        linhas_csv.append(dict(par=r.par, cap=r.cap, n_termos=len(tt), A_tasks=";".join(sorted(a_)),
                               B_pr=";".join(sorted(b_)), C_termos=";".join(sorted(c_)), candidatas=";".join(cands)))
        alt = [l for l in patch.split("\n") if l[:1] in "+-" and not l.startswith(("+++", "---")) and l[1:].strip()]
        txt = [f"===== {r.par} | {r.repo_name} PR #{r.pr_number} | capacidade do par: {r.cap}",
               f"PR: {str(r.title)[:160]}", f"arquivos ligados: {r.codigo_ligado}",
               f"--- linhas alteradas ({len(alt)}; mostrando até 40)", *[l[:160] for l in alt[:40]]]
        for c in cands:
            orig = "+".join(k for k, s in (("tasks", a_), ("PR", b_), ("termos", c_)) if c in s)
            corpo = texto_cap.get(c, "")
            hits = [l.strip()[:200] for l in corpo.split("\n") if l.strip() and any(t in l for t in tt)]
            topo = [l.strip()[:200] for l in corpo.split("\n") if l.strip()][:3]
            txt += [f"--- candidata: {c} [{orig}]" + ("" if corpo else " (sem texto no censo)"),
                    *["  | " + l for l in topo], *["  > " + l for l in hits[:8]]]
        if not cands:
            txt.append("--- nenhuma candidata")
        blocos.append("\n".join(txt))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("revisao_"):
            os.remove(os.path.join(OUT, f))
    for i in range(0, len(blocos), POR_ARQ):
        open(os.path.join(OUT, f"revisao_{i // POR_ARQ + 1:02d}.txt"), "w", encoding="utf-8").write("\n\n".join(blocos[i:i + POR_ARQ]) + "\n")
    c = pd.DataFrame(linhas_csv)
    assert len(c) == len(pares) and c.par.is_unique
    c.to_csv(os.path.join(OUT, "candidatos.csv"), index=False)
    print(f"pares: {len(c)}; sem nenhuma candidata: {(c.candidatas == '').sum()}; com A: {(c.A_tasks != '').sum()}; "
          f"com B: {(c.B_pr != '').sum()}; com C: {(c.C_termos != '').sum()}; arquivos: {math.ceil(len(c) / POR_ARQ)}")


if __name__ == "__main__":
    main()
