"""Universo de análise: uma linha por spec, com flags de exclusão/dedup (nada é apagado).

u_ciclo (o universo de todas as análises): sem caffeine, com commits até o corte, sem conteúdo copiado em >=5 repos
e sem repos "vendor". Duplicatas DENTRO do repo ficam (ex.: change arquivada e spec viva podem ter o mesmo texto e
são arquivos com história própria).
Papel corrigido: spec de change "aberta" cujo histórico contém o commit que criou a cópia arquivada de mesmo
nome (changes/archive/<data>-<nome>/...) -> 'archived_pos_censo'.
Saídas: data/derived/universe.parquet, data/derived/tables/funil.csv
Uso: .venv/bin/python -I scripts/analysis/universe.py
"""
import os
import duckdb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "specmine", "data")
OUT = os.path.join(ROOT, "data", "derived")
CORTE = "2026-07-11T23:59:59Z"
COPIA_MIN_REPOS = 5
VENDOR_FRAC = 0.5
SEM_FERRAMENTA = ("adhoc_other", "specs_generic", "docs_embedded", "root_bare", "dot_specs")

os.makedirs(os.path.join(OUT, "tables"), exist_ok=True)
con = duckdb.connect()
con.execute(f"""
create temp table sf as
select s.file_url_sha16, s.repo_name, s.file_path, s.spec_tool, s.spec_role, s.file_content_sha,
       case when s.spec_tool='openspec' then 'openspec' when s.spec_tool='speckit' then 'speckit'
            when s.spec_tool='caffeine' then 'caffeine'
            when s.spec_tool in {SEM_FERRAMENTA} then 'sem_ferramenta' else 'outras_nomeadas' end grupo
from '{D}/spec_files.parquet' s
""")
con.execute(f"""
create temp table cm as
select file_url_sha16, count(*) n_commits, min(authored_at) primeiro_commit, max(authored_at) ultimo_commit
from '{D}/spec_file_commits.parquet' where authored_at <= '{CORTE}' group by 1
""")
con.execute("""
create temp table h as select file_content_sha, count(distinct repo_name) n_repos_mesmo_conteudo
from sf where grupo <> 'caffeine' and file_content_sha is not null group by 1
""")
con.execute(f"""
create temp table rv as
select sf.repo_name, avg((h.n_repos_mesmo_conteudo >= {COPIA_MIN_REPOS})::int) frac_copiado
from sf join h using(file_content_sha) where grupo <> 'caffeine' group by 1
""")
# papel desatualizado: change aberta cuja cópia arquivada de mesmo nome nasceu num commit do histórico dela
con.execute(f"""
create temp table stale as
with ch as (select file_url_sha16, repo_name,
              regexp_extract(file_path, 'openspec/changes/([^/]+)/(specs/.+)$', 1) nome,
              regexp_extract(file_path, 'openspec/changes/([^/]+)/(specs/.+)$', 2) resto
            from sf where spec_tool='openspec' and spec_role='change_proposal'
              and regexp_matches(file_path, 'openspec/changes/[^/]+/specs/') and file_path not like '%/changes/archive/%'),
ar as (select s.repo_name,
              regexp_extract(s.file_path, 'openspec/changes/archive/[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}-([^/]+)/(specs/.+)$', 1) nome,
              regexp_extract(s.file_path, 'openspec/changes/archive/[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}-([^/]+)/(specs/.+)$', 2) resto,
              c.commit_sha
       from sf s join '{D}/spec_file_commits.parquet' c using(file_url_sha16)
       where s.spec_tool='openspec' and s.spec_role='archived' and c.seq_from_oldest=1),
hist as (select file_url_sha16, commit_sha from '{D}/spec_file_commits.parquet')
select distinct ch.file_url_sha16
from ch join ar on ar.repo_name=ch.repo_name and ar.nome=ch.nome and ar.resto=ch.resto and ar.nome <> ''
join hist on hist.file_url_sha16=ch.file_url_sha16 and hist.commit_sha=ar.commit_sha
""")
con.execute(f"""
create temp table u as
select sf.*,
  (grupo='caffeine') excl_caffeine,
  coalesce(h.n_repos_mesmo_conteudo, 0) n_repos_mesmo_conteudo,
  (coalesce(h.n_repos_mesmo_conteudo, 0) >= {COPIA_MIN_REPOS}) copiado_5mais_repos,
  (coalesce(rv.frac_copiado, 0) >= {VENDOR_FRAC}) repo_vendor,
  coalesce(cm.n_commits, 0) n_commits, cm.primeiro_commit, cm.ultimo_commit,
  case when st.file_url_sha16 is not null then 'archived_pos_censo' else spec_role end papel
from sf left join h using(file_content_sha) left join rv using(repo_name)
left join cm using(file_url_sha16) left join stale st using(file_url_sha16)
""")
con.execute("""
create temp table uf as
select *,
  (not excl_caffeine and n_commits >= 1 and not copiado_5mais_repos and not repo_vendor) u_ciclo
from u
""")
con.execute(f"copy (select * from uf order by file_url_sha16) to '{OUT}/universe.parquet' (format parquet)")

funil = con.execute("""
select 'todas as specs' etapa, count(*) specs, count(distinct repo_name) repos from uf
union all select 'sem caffeine', count(*), count(distinct repo_name) from uf where not excl_caffeine
union all select 'sem caffeine, com commit até o corte', count(*), count(distinct repo_name) from uf where not excl_caffeine and n_commits >= 1
union all select '... sem conteúdo copiado em >=5 repos', count(*), count(distinct repo_name) from uf where not excl_caffeine and n_commits >= 1 and not copiado_5mais_repos
union all select 'u_ciclo: ... e sem repos vendor', count(*), count(distinct repo_name) from uf where u_ciclo
""").df()
funil.to_csv(os.path.join(OUT, "tables", "funil.csv"), index=False)
print(funil.to_string(index=False))
print(con.execute("""select grupo, count(*) specs, sum(u_ciclo::int) u_ciclo,
  count(distinct case when u_ciclo then repo_name end) repos_ciclo from uf group by 1 order by specs desc""").df().to_string(index=False))
print(con.execute("""select spec_role, papel, count(*) n from uf where spec_tool='openspec' and spec_role<>papel group by 1,2""").df().to_string(index=False))
