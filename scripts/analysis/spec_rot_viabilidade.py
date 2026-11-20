"""RQ2 (spec decay): candidatos, X e sorteio dos pares spec–PR, só com dados em disco.

Ligação indireta (OpenSpec): spec viva openspec/specs/<cap>/spec.md  <-  changes que tocaram <cap>
(openspec/changes/[archive/]<change>/specs/<cap>/spec.md)  <-  caminhos de código citados no tasks.md dessas changes
(spec_links rel='code', provenance='tasks').
Evento candidato a decay: PR (camada de PRs) que altera um arquivo de código ligado à capacidade e NÃO toca nenhuma
spec daquela capacidade (nem a viva, nem de change). Na camada de PRs todo PR toca alguma spec: na prática é uma
mudança dentro do fluxo de OUTRA capacidade (docs/metodo.md §0.3).
Uso: .venv/bin/python -I scripts/analysis/spec_rot_viabilidade.py
"""
import hashlib, json, os
import duckdb
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "specmine", "data")
U = os.path.join(ROOT, "data", "derived", "universe.parquet")
CORTE = "2026-07-11T23:59:59Z"
con = duckdb.connect()
con.execute(f"""
create temp table viva as
select file_url_sha16, repo_name, regexp_extract(file_path, 'openspec/specs/(.+)/spec\\.md$', 1) cap, ultimo_commit
from '{U}' where u_ciclo and grupo='openspec' and papel='living' and regexp_matches(file_path, 'openspec/specs/.+/spec\\.md$')""")
con.execute(f"""
create temp table refs as
select distinct u.repo_name, regexp_extract(u.file_path, '/specs/(.+)/spec\\.md$', 1) cap, l.target
from '{D}/spec_links.parquet' l join '{U}' u on u.file_url_sha16=l.spec_url_sha16
where u.u_ciclo and u.grupo='openspec' and u.papel in ('archived','change_proposal','archived_pos_censo')
  and l.rel='code' and l.provenance='tasks' and regexp_matches(u.file_path, 'openspec/changes/.+/specs/.+/spec\\.md$')
  and l.target like '%/%'""")
# ligação estrita: sem nomes genéricos (index, main, utils, config...); a tabela completa fica para medir o que o filtro tira
con.execute("""create temp table refs_com_genericos as select * from refs""")
con.execute("""delete from refs where regexp_matches(lower(target), '(^|/)(index|main|app|utils?|helpers?|types?|constants?|config)\\.[a-z]+$')""")
cob = con.execute("""
select count(*) specs_vivas, count(distinct repo_name) repos,
  sum((cap in (select cap from refs r where r.repo_name=viva.repo_name))::int) com_codigo_ligado
from viva""").df()
print("== cobertura da ligação indireta (spec viva -> código)\n", cob.to_string(index=False))
con.execute(f"""
create temp table pf as select repo_name, pr_number, file_path, is_code, is_spec from '{D}/pr_files.parquet'""")
con.execute(f"""
create temp table pr as select repo_name, pr_number, merged_at from '{D}/pull_requests.parquet'
where tool='openspec' and merged_at <= '{CORTE}'""")
def eventos(tab_refs):
    d = con.execute(f"""
with hit as (
  select v.file_url_sha16, v.repo_name, v.cap, v.ultimo_commit, pf.pr_number,
         string_agg(distinct pf.file_path, ';' order by pf.file_path) codigo_ligado
  from viva v join {tab_refs} r on r.repo_name=v.repo_name and r.cap=v.cap
  join pf on pf.repo_name=v.repo_name and pf.is_code=1 and pf.file_path=r.target
  group by 1,2,3,4,5)
select h.*, p.merged_at,
  exists (select 1 from pf s where s.repo_name=h.repo_name and s.pr_number=h.pr_number and s.is_spec=1
          and (s.file_path like '%/specs/' || h.cap || '/spec.md')) toca_spec_da_cap,
  exists (select 1 from pf s where s.repo_name=h.repo_name and s.pr_number=h.pr_number and s.is_spec=1) toca_alguma_spec
from hit h join pr p on p.repo_name=h.repo_name and p.pr_number=h.pr_number""").df()
    d["depois_da_ultima_edicao"] = d.merged_at.astype(str) > d.ultimo_commit.astype(str)
    return d


ev = eventos("refs")
print("\n== PRs que mexem em código ligado a uma capacidade (camada de PRs, OpenSpec)")
print(f"pares spec viva x PR: {len(ev)}; specs vivas: {ev.file_url_sha16.nunique()}; repos: {ev.repo_name.nunique()}")
print(ev.groupby(["toca_spec_da_cap", "depois_da_ultima_edicao"]).agg(
    pares=("pr_number", "size"), specs=("file_url_sha16", "nunique"), repos=("repo_name", "nunique")).to_string())
fora = ev[~ev.toca_spec_da_cap & ev.depois_da_ultima_edicao]
por_repo = fora.groupby("repo_name").file_url_sha16.nunique().describe()
print("\n== candidatos a decay (PR depois da última edição da spec, sem tocar nenhuma spec da capacidade)")
print(f"specs: {fora.file_url_sha16.nunique()} em {fora.repo_name.nunique()} repos; specs por repo:\n{por_repo.round(1).to_string()}")
print(f"desses PRs, quantos não tocam nenhuma spec: {(~fora.toca_alguma_spec).sum()} de {len(fora)} "
      "(a camada só tem PRs que tocam alguma spec — esperado ~0)")

# X da afirmação máxima (metodo.md §0.3): entre specs vivas com código ligado, nos repos da
# camada de PRs, fração com >=1 evento candidato; média por repo, IC por bootstrap de repos (como key_numbers.boot)
base = con.execute("""select v.repo_name, v.file_url_sha16 from viva v
  where v.repo_name in (select repo_name from pr) and v.cap in (select cap from refs r where r.repo_name=v.repo_name)""").df()
base["evento"] = base.file_url_sha16.isin(fora.file_url_sha16).astype(int)
m = base.groupby("repo_name").evento.mean().to_numpy()
rng = np.random.default_rng(20261105)
bm = m[rng.integers(0, len(m), (1000, len(m)))].mean(axis=1)
x_txt = (f"X: specs vivas com código ligado na camada de PRs com >=1 evento: {base.evento.sum()}/{len(base)} specs, "
         f"{len(m)} repos; por repo {100 * m.mean():.1f}% [IC {100 * np.percentile(bm, 2.5):.1f}–{100 * np.percentile(bm, 97.5):.1f}]; "
         f"por spec {100 * base.evento.mean():.1f}%")
print("\n== " + x_txt)

# Piloto: sorteio de 1 par (spec viva, PR) por repo, em N_PARES repos, para ler o diff do PR (scripts/api/fetch_pr.py)
SEED, N_PARES = "p4-20261105", 60
OUT = os.path.join(ROOT, "data", "api_pr_diffs", "sample")
os.makedirs(OUT, exist_ok=True)
fora = fora.assign(_h=[hashlib.md5(f"{SEED}|{r.file_url_sha16}|{r.pr_number}".encode()).hexdigest() for r in fora.itertuples()])
pares = (fora.sort_values("_h").groupby("repo_name", as_index=False).head(1)
         .sort_values("_h").head(N_PARES).reset_index(drop=True))
pares["par"] = [f"P{i + 1:03d}" for i in range(len(pares))]
cols = ["par", "repo_name", "pr_number", "file_url_sha16", "cap", "ultimo_commit", "merged_at", "codigo_ligado"]
novo = pares[cols].to_csv(index=False)
destino = os.path.join(OUT, "pares.csv")
if os.path.exists(destino):  # amostra já coletada e travada (somente leitura): só confere que o sorteio se repete
    if open(destino).read() != novo:
        raise SystemExit("ERRO: o sorteio mudou em relação à amostra travada em data/api_pr_diffs/sample/pares.csv")
    print(f"\npiloto: sorteio idêntico à amostra travada ({len(pares)} pares)")
else:
    with open(destino, "w") as f:
        f.write(novo)
    fora.drop(columns="_h").to_parquet(os.path.join(OUT, "candidatos.parquet"), index=False)
    print(f"\npiloto: {len(pares)} pares sorteados (1 por repo, semente {SEED}) -> data/api_pr_diffs/sample/pares.csv")

# Amostra ampliada: mesma ordem de sorteio; até M_POR_REPO pares por repo em TODOS os repos, mantendo os 60 do
# piloto. M_POR_REPO = 3 sai da regra fixada antes (docs/metodo.md §5b; scripts/analysis/p4_poder.py).
M_POR_REPO = 3
f = fora.sort_values("_h").assign(rk=lambda d: d.groupby("repo_name").cumcount() + 1)
r1 = f[f.rk == 1]
assert list(r1.head(N_PARES).pr_number) == list(pares.pr_number), "ampliação não preserva os 60 primeiros"
piloto = set(zip(r1.head(N_PARES).file_url_sha16, r1.head(N_PARES).pr_number))
ext = f[(f.rk <= M_POR_REPO) & ~pd.Series(list(zip(f.file_url_sha16, f.pr_number)), index=f.index).isin(piloto)]
ext = ext.sort_values(["rk", "_h"]).reset_index(drop=True)
ext["par"] = [f"P{N_PARES + i + 1:03d}" for i in range(len(ext))]
N_TOTAL = N_PARES + len(ext)
assert N_TOTAL == int(fora.groupby("repo_name").size().clip(upper=M_POR_REPO).sum())
OUT2 = os.path.join(ROOT, "data", "api_pr_diffs_ext", "sample")
os.makedirs(OUT2, exist_ok=True)
novo2, destino2 = ext[cols].to_csv(index=False), os.path.join(OUT2, "pares.csv")
if os.path.exists(destino2):
    if open(destino2).read() != novo2:
        raise SystemExit("ERRO: o sorteio ampliado mudou em relação a data/api_pr_diffs_ext/sample/pares.csv")
    print(f"amostra ampliada: sorteio idêntico à amostra gravada ({len(ext)} pares)")
else:
    with open(destino2, "w") as fh:
        fh.write(novo2)
    print(f"amostra ampliada: +{len(ext)} pares (P{N_PARES + 1:03d}–P{N_TOTAL:03d}) em {ext.repo_name.nunique()} repos "
          f"-> data/api_pr_diffs_ext/sample/pares.csv")

# Descrição da amostra da RQ2: defasagem PR -> corte do histórico e repetição de PR/spec no repo.
a = pd.concat([pares[cols], ext[cols]], ignore_index=True)
dias = (pd.Timestamp(CORTE) - pd.to_datetime(a.merged_at, utc=True)).dt.days
lag = (pd.to_datetime(a.merged_at, utc=True) - pd.to_datetime(a.ultimo_commit, utc=True)).dt.days
txt = "\n".join([
    x_txt,
    f"pares sorteados: {len(a)} em {a.repo_name.nunique()} repos; pares por repo: {a.groupby('repo_name').size().value_counts().sort_index().to_dict()}",
    f"dias do PR ao corte: mediana {dias.median():.0f}, p10 {dias.quantile(.1):.0f}; < 30 dias: {(dias < 30).sum()}; < 60 dias: {(dias < 60).sum()}",
    f"dias da última edição da spec ao PR: mediana {lag.median():.0f}",
    f"pares que repetem um PR já usado no mesmo repo: {int(a.duplicated(['repo_name', 'pr_number']).sum())}; "
    f"que repetem a spec: {int(a.duplicated(['repo_name', 'file_url_sha16']).sum())}; "
    f"PRs únicos: {len(a.drop_duplicates(['repo_name', 'pr_number']))}; specs únicas: {a.file_url_sha16.nunique()}"])
open(os.path.join(ROOT, "data", "derived", "p4_amostra.txt"), "w").write(txt + "\n")
print("\n== amostra da RQ2\n" + txt)

# números citados no paper (lidos pelo notebook numeros_do_paper.ipynb)
alt = eventos("refs_com_genericos")
alt = alt[~alt.toca_spec_da_cap & alt.depois_da_ultima_edicao]
num = dict(candidatos=len(fora), candidatos_repos=int(fora.repo_name.nunique()),
           sem_filtro_generico=len(alt), sem_filtro_generico_repos=int(alt.repo_name.nunique()),
           x_specs=int(base.evento.sum()), x_base=len(base), x_repos=len(m), x_por_repo=round(float(m.mean()), 6),
           x_ic=[round(float(np.percentile(bm, q)), 6) for q in (2.5, 97.5)],
           pares_sorteados=len(a), pares_repos=int(a.repo_name.nunique()),
           candidatos_sem_spec=int((~fora.toca_alguma_spec).sum()))
os.makedirs(os.path.join(ROOT, "data", "derived", "numeros"), exist_ok=True)
json.dump(num, open(os.path.join(ROOT, "data", "derived", "numeros", "spec_rot_viabilidade.json"), "w"), indent=1)
print(f"sem o filtro de nomes genéricos: {len(alt)} candidatos em {alt.repo_name.nunique()} repos "
      f"(o filtro tira {len(alt) - len(fora)} pares e {alt.repo_name.nunique() - fora.repo_name.nunique()} repos)")
