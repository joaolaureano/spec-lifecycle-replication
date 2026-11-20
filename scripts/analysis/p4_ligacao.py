"""RQ2 — Segundo canal de ligação spec ↔ código: openspec_code_refs do SpecMine (regras em docs/metodo.md §5f).

(1) Confirma, nos 280 pares, se cada caminho ligado aparece num tasks.md de uma change da mesma capacidade.
(2) Refaz o X de spec_rot_viabilidade.py com a ligação ampla (resolved_path com exists_at_anchor=1), só descritivo.
Mapeamento change -> capacidade: pasta da change = diretório do artifact_path; capacidades = specs do universo
(grupo openspec) em '<pasta>/specs/<cap>/spec.md'.
Uso: .venv/bin/python -I scripts/analysis/p4_ligacao.py
Saída: data/derived/tables/p4_ligacao.csv e data/derived/p4_ligacao.txt
"""
import json, os
import duckdb
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "specmine", "data")
U = os.path.join(ROOT, "data", "derived", "universe.parquet")
VAL = os.path.join(ROOT, "data", "validation")
con = duckdb.connect()
# diretório do artifact_path vale também para TASKS.md (108 linhas): o mapeamento é pela pasta, não pelo nome
con.execute(f"""
create temp table cref as
select c.repo_name, m.cap, c.code_path, c.resolved_path, c.task_done, c.exists_at_anchor
from '{D}/openspec_code_refs.parquet' c
join (select distinct repo_name, regexp_extract(file_path, '^(.*?)/specs/(.+)/spec\\.md$', 1) pasta,
             regexp_extract(file_path, '^(.*?)/specs/(.+)/spec\\.md$', 2) cap
      from '{U}' where grupo='openspec' and regexp_matches(file_path, '^.*?/specs/.+/spec\\.md$')) m
  on m.repo_name=c.repo_name and m.pasta=regexp_replace(c.artifact_path, '/[^/]+$', '')""")

# vários matches para um caminho contam uma vez (any)
pares = pd.read_csv(os.path.join(VAL, "gabarito_pares.csv"), dtype=str)[["par", "repo_name", "cap", "codigo_ligado"]]
cam = pares.assign(caminho=pares.codigo_ligado.str.split(";")).explode("caminho").drop(columns="codigo_ligado")
con.register("cam", cam)
pc = con.execute("""
select k.par, k.caminho,
  count(c.repo_name) > 0 confirmado,
  coalesce(bool_or(c.exists_at_anchor = 1), false) existe,
  coalesce(bool_or(c.task_done = 1), false) feita
from cam k left join cref c on c.repo_name=k.repo_name and c.cap=k.cap
  and (c.resolved_path=k.caminho or c.code_path=k.caminho)
group by 1, 2 order by 1, 2""").df()
t = pc.groupby("par").agg(n_caminhos=("caminho", "size"), confirmados=("confirmado", "sum"), existem=("existe", "sum"),
                          tarefa_feita=("feita", "sum")).reset_index().sort_values("par")
t["todos_confirmados"] = (t.confirmados == t.n_caminhos).astype(int)
t["algum_feito"] = (t.tarefa_feita > 0).astype(int)
conf_exist = int((pc.confirmado & pc.existe).groupby(pc.par).any().sum())
assert len(t) == 280 and t.par.is_unique
# números da consulta exploratória declarados em docs/metodo.md §5f antes de entrar no pipeline
assert (len(pc), pc.confirmado.sum(), pc.existe.sum(), pc.feita.sum()) == (619, 596, 584, 510), \
    (len(pc), pc.confirmado.sum(), pc.existe.sum(), pc.feita.sum())
assert conf_exist == 279 and t.algum_feito.sum() == 248, (conf_exist, t.algum_feito.sum())
os.makedirs(os.path.join(ROOT, "data", "derived", "tables"), exist_ok=True)
t.to_csv(os.path.join(ROOT, "data", "derived", "tables", "p4_ligacao.csv"), index=False)

# (2) X: mesma lógica e bootstrap de spec_rot_viabilidade.py, trocando só a tabela de ligação (refs)
con.execute(f"""
create temp table viva as
select file_url_sha16, repo_name, regexp_extract(file_path, 'openspec/specs/(.+)/spec\\.md$', 1) cap, ultimo_commit
from '{U}' where u_ciclo and grupo='openspec' and papel='living' and regexp_matches(file_path, 'openspec/specs/.+/spec\\.md$')""")
con.execute(f"""
create temp table refs_estrita as
select distinct u.repo_name, regexp_extract(u.file_path, '/specs/(.+)/spec\\.md$', 1) cap, l.target
from '{D}/spec_links.parquet' l join '{U}' u on u.file_url_sha16=l.spec_url_sha16
where u.u_ciclo and u.grupo='openspec' and u.papel in ('archived','change_proposal','archived_pos_censo')
  and l.rel='code' and l.provenance='tasks' and regexp_matches(u.file_path, 'openspec/changes/.+/specs/.+/spec\\.md$')
  and l.target like '%/%' and not regexp_matches(lower(l.target), '(^|/)(index|main|app|utils?|helpers?|types?|constants?|config)\\.[a-z]+$')""")
# mesmo universo e mesmos papéis da versão estrita: a diferença entre os dois X vem só da fonte da ligação
con.execute(f"""
create temp table refs_ampla as
select distinct c.repo_name, regexp_extract(u.file_path, '/specs/(.+)/spec\\.md$', 1) cap, c.resolved_path target
from '{D}/openspec_code_refs.parquet' c join '{U}' u on u.repo_name=c.repo_name
  and regexp_extract(u.file_path, '^(.*)/specs/[^/]+/spec\\.md$', 1)=regexp_replace(c.artifact_path, '/[^/]+$', '')
where u.u_ciclo and u.grupo='openspec' and u.papel in ('archived','change_proposal','archived_pos_censo')
  and regexp_matches(u.file_path, 'openspec/changes/.+/specs/.+/spec\\.md$')
  and c.exists_at_anchor=1 and c.resolved_path is not null""")
con.execute(f"create temp table pf as select repo_name, pr_number, file_path, is_code, is_spec from '{D}/pr_files.parquet'")
con.execute(f"""create temp table pr as select repo_name, pr_number, merged_at
from '{D}/pull_requests.parquet'
where tool='openspec' and merged_at <= '2026-07-11T23:59:59Z'""")


def x(refs):
    ev = con.execute(f"""
    with hit as (
      select distinct v.file_url_sha16, v.repo_name, v.cap, v.ultimo_commit, pf.pr_number
      from viva v join {refs} r on r.repo_name=v.repo_name and r.cap=v.cap
      join pf on pf.repo_name=v.repo_name and pf.is_code=1 and pf.file_path=r.target)
    select h.*, p.merged_at,
      exists (select 1 from pf s where s.repo_name=h.repo_name and s.pr_number=h.pr_number and s.is_spec=1
              and (s.file_path like '%/specs/' || h.cap || '/spec.md')) toca_spec_da_cap
    from hit h join pr p on p.repo_name=h.repo_name and p.pr_number=h.pr_number""").df()
    fora = ev[~ev.toca_spec_da_cap & (ev.merged_at.astype(str) > ev.ultimo_commit.astype(str))]
    base = con.execute(f"""select v.repo_name, v.file_url_sha16 from viva v
      where v.repo_name in (select repo_name from pr) and v.cap in (select cap from {refs} r where r.repo_name=v.repo_name)
      order by 1, 2""").df()
    base["evento"] = base.file_url_sha16.isin(fora.file_url_sha16).astype(int)
    m = base.groupby("repo_name").evento.mean().to_numpy()
    rng = np.random.default_rng(20261105)
    bm = m[rng.integers(0, len(m), (1000, len(m)))].mean(axis=1)
    num = dict(specs=int(base.evento.sum()), base=len(base), repos=len(m), por_repo=round(float(m.mean()), 6),
               ic=[round(float(np.percentile(bm, q)), 6) for q in (2.5, 97.5)])
    return (f"{base.evento.sum()}/{len(base)} specs vivas ligadas, {len(m)} repos; por repo {100 * m.mean():.1f}% "
            f"[IC {100 * np.percentile(bm, 2.5):.1f}–{100 * np.percentile(bm, 97.5):.1f}] ({len(m)} repos); "
            f"por spec {100 * base.evento.mean():.1f}%"), num


(x_estrita, _), (x_ampla, n_ampla) = x("refs_estrita"), x("refs_ampla")
# a versão estrita tem de reproduzir o X já publicado em p4_amostra.txt
assert x_estrita.startswith("1785/3995") and "por repo 28.3% [IC 24.0–32.7]" in x_estrita, x_estrita
pct = lambda k: f"{k} ({100 * k / len(t):.1f}%)"
txt = "\n".join([
    f"ligação nos {len(t)} pares (openspec_code_refs, mesma change e capacidade): caminhos {len(pc)}; "
    f"confirmados {pc.confirmado.sum()}; existentes na âncora {pc.existe.sum()}; de tarefa marcada {pc.feita.sum()}",
    f"pares com >=1 caminho confirmado e existente: {pct(conf_exist)}; com todos os caminhos confirmados: "
    f"{pct(int(t.todos_confirmados.sum()))}; com algum caminho de tarefa marcada: {pct(int(t.algum_feito.sum()))}",
    f"X estrito (spec_links): {x_estrita}",
    f"X amplo (openspec_code_refs, resolved_path existente): {x_ampla}"])
open(os.path.join(ROOT, "data", "derived", "p4_ligacao.txt"), "w").write(txt + "\n")
print(txt)
os.makedirs(os.path.join(ROOT, "data", "derived", "numeros"), exist_ok=True)
json.dump(dict(x_amplo=n_ampla), open(os.path.join(ROOT, "data", "derived", "numeros", "p4_ligacao.json"), "w"), indent=1)
