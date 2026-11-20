"""Números-chave da RQ1 por ferramenta (ciclo de vida, janela de 60 dias, hipóteses H1a e H1b) e do corpus.
Estimativa principal = média das médias por repo (sensibilidade = média por spec); IC 95% = percentis de 1.000 réplicas
bootstrap de repos (semente fixa).
Saídas: docs/key_numbers_final.json, data/derived/tables/*.csv. Uso: .venv/bin/python -I scripts/analysis/key_numbers.py
"""
import json, os, zlib
import duckdb
import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "specmine", "data")
U = os.path.join(ROOT, "data", "derived", "universe.parquet")
TAB = os.path.join(ROOT, "data", "derived", "tables")
CORTE = "2026-07-11T23:59:59Z"
SEED = 20261105
B = 1000
GRUPOS = ["openspec", "speckit", "outras_nomeadas", "sem_ferramenta"]
con = duckdb.connect()
NUM = {}  # números citados no paper que não estão nas tabelas (lidos pelo notebook numeros_do_paper.ipynb)


def rng_do(g):
    """Gerador próprio de cada grupo: o IC de um grupo não depende de quais outros grupos existem nem da ordem."""
    return np.random.default_rng([SEED, zlib.crc32(str(g).encode())])


def boot(df, cols, grupo_col="grupo"):
    """df: uma linha por spec com repo_name, grupo e indicadores 0/1 ou numéricos -> estimativas por grupo."""
    out = []
    for g, d in df.groupby(grupo_col):
        rng = rng_do(g)
        r = d.groupby("repo_name")[cols].agg(["sum", "count"])
        n_rep = len(r)
        idx = rng.integers(0, n_rep, size=(B, n_rep))
        for c in cols:
            s, n = r[(c, "sum")].to_numpy(float), r[(c, "count")].to_numpy(float)
            m = s / n
            est_repo, est_spec = m.mean(), s.sum() / n.sum()
            bm = m[idx].mean(axis=1)
            bs = s[idx].sum(axis=1) / n[idx].sum(axis=1)
            out.append(dict(grupo=g, metrica=c, por_repo=est_repo, ic_repo_lo=np.percentile(bm, 2.5),
                            ic_repo_hi=np.percentile(bm, 97.5), por_spec=est_spec,
                            ic_spec_lo=np.percentile(bs, 2.5), ic_spec_hi=np.percentile(bs, 97.5),
                            n_unidades=int(n.sum()), n_repos=n_rep))
    return pd.DataFrame(out)


def cliff(x, y):
    """Cliff's δ = P(X>Y) − P(X<Y), via U de Mann-Whitney."""
    return 2 * stats.mannwhitneyu(x, y).statistic / (len(x) * len(y)) - 1


def magnitude(d):
    d = abs(d)
    return "negligible" if d < .147 else "small" if d < .33 else "medium" if d < .474 else "large"


def _autoteste():
    rng = np.random.default_rng(1)
    x, y = rng.integers(0, 5, 40) / 4, rng.integers(0, 5, 30) / 4
    assert np.isclose(cliff(x, y), np.mean(np.sign(x[:, None] - y[None, :])))  # δ por força bruta


def veredito(lo, hi, limiar, lado):
    """IC inteiro do lado declarado -> satisfeito; inteiro do outro lado -> não satisfeito; senão inconclusivo."""
    if lado == "<":
        return "satisfeito" if hi < limiar else "nao_satisfeito" if lo >= limiar else "inconclusivo"
    return "satisfeito" if lo > limiar else "nao_satisfeito" if hi <= limiar else "inconclusivo"


VIVA = "openspec:living"


def so_viva(o, cols):
    """Spec viva do OpenSpec."""
    return boot(o[o.grupo == VIVA], cols)


def bloco_ciclo():
    u = con.execute(f"""select repo_name, grupo, papel, n_commits from '{U}' where u_ciclo""").df()
    u["editada"] = (u.n_commits >= 2).astype(int)
    o = u[u.grupo == "openspec"].copy()
    o["grupo"] = "openspec:" + o.papel
    return pd.concat([boot(u, ["editada"]), so_viva(o, ["editada"])]), pd.concat([u, o[o.grupo == VIVA]])


def bloco_janela():
    """Sensibilidade à exposição: entre specs com >=60 dias até o corte, editada nos 60 primeiros dias."""
    x = con.execute(f"""
    with s as (select file_url_sha16, repo_name, grupo, papel, primeiro_commit from '{U}' where u_ciclo
               and cast(primeiro_commit as timestamp) <= timestamp '2026-07-11 23:59:59' - interval 60 day),
    c as (select file_url_sha16, authored_at from '{D}/spec_file_commits.parquet' where authored_at <= '{CORTE}'
          and file_url_sha16 in (select file_url_sha16 from s))
    select s.*, (select count(*) from c where c.file_url_sha16=s.file_url_sha16
       and cast(c.authored_at as timestamp) > cast(s.primeiro_commit as timestamp)
       and cast(c.authored_at as timestamp) <= cast(s.primeiro_commit as timestamp) + interval 60 day) ed60
    from s""").df()
    x["editada_60d"] = (x.ed60 > 0).astype(int)
    o = x[x.grupo == "openspec"].copy()
    o["grupo"] = "openspec:" + o.papel
    return pd.concat([boot(x, ["editada_60d"]), so_viva(o, ["editada_60d"])])


def hipoteses(ciclo, u):
    """Vereditos de H1a e H1b pelas regras de docs/metodo.md §5b; Mann-Whitney + Cliff δ na H1b (a hipótese comparativa)."""
    linhas = []
    c = ciclo[ciclo.metrica == "editada"].set_index("grupo")
    for g in GRUPOS + ["openspec:living"]:
        r = c.loc[g]
        linhas.append(dict(hipotese="H1a", criterio="editada < 50%", grupo=g, estimativa=r.por_repo, ic_lo=r.ic_repo_lo,
                           ic_hi=r.ic_repo_hi, limiar=0.5, veredito=veredito(r.ic_repo_lo, r.ic_repo_hi, 0.5, "<")))
    pr = u.groupby(["grupo", "repo_name"]).editada.mean()
    viva, sk = pr.loc["openspec:living"], pr.loc["speckit"]
    v, s = c.loc["openspec:living"], c.loc["speckit"]
    for nome, x, y in [("todos", viva, sk)]:
        p = stats.mannwhitneyu(x, y, alternative="greater").pvalue
        d = cliff(x.to_numpy(), y.to_numpy())
        ok = "satisfeito" if v.ic_repo_lo > s.ic_repo_hi and p < .05 else "nao_satisfeito" if v.ic_repo_hi < s.ic_repo_lo else "inconclusivo"
        linhas.append(dict(hipotese="H1b", criterio=f"viva > Spec Kit ({nome})", grupo="openspec:living vs speckit",
                           estimativa=v.por_repo - s.por_repo, ic_lo=np.nan, ic_hi=np.nan, limiar=0.0, veredito=ok,
                           mw_p_unilateral=p, cliff_delta=d, magnitude=magnitude(d), n_a=len(x), n_b=len(y)))
    return pd.DataFrame(linhas)


def main():
    os.makedirs(TAB, exist_ok=True)
    _autoteste()
    ciclo, u = bloco_ciclo()
    janela = bloco_janela()
    hip = hipoteses(ciclo, u)
    for nome, df in [("ciclo", ciclo), ("ciclo_janela60", janela), ("hipoteses", hip)]:
        df.round(6).to_csv(os.path.join(TAB, f"{nome}.csv"), index=False)
    saida = {"semente": SEED, "replicas_bootstrap": B, "corte": CORTE,
             "funil": pd.read_csv(os.path.join(TAB, "funil.csv")).to_dict("records"),
             "ciclo": ciclo.round(6).to_dict("records"), "ciclo_janela60": janela.round(6).to_dict("records"),
             "hipoteses": hip.round(6).to_dict("records")}
    with open(os.path.join(ROOT, "docs", "key_numbers_final.json"), "w") as f:
        json.dump(saida, f, indent=1, ensure_ascii=False)
    pd.set_option("display.width", 230)
    fmt = lambda df: df.assign(repo=lambda x: (100 * x.por_repo).round(1).astype(str) + " [" + (100 * x.ic_repo_lo).round(1).astype(str)
                               + "–" + (100 * x.ic_repo_hi).round(1).astype(str) + "]", spec=lambda x: (100 * x.por_spec).round(1))
    print("== ciclo de vida (% por repo [IC], % por spec)\n", fmt(ciclo)[["grupo", "metrica", "repo", "spec", "n_repos"]].to_string(index=False))
    idade = con.execute(f"""select case when grupo = 'openspec' then 'openspec:' || papel else grupo end grupo,
        median(date_diff('day', cast(primeiro_commit as timestamp), timestamp '2026-07-11 23:59:59')) mediana_dias
        from '{U}' where u_ciclo group by 1 order by 1""").df()
    print("\n== idade até o corte (mediana, dias)\n", idade.to_string(index=False))
    NUM["idade_mediana_dias"] = {g: float(d) for g, d in zip(idade.grupo, idade.mediana_dias)}
    # ameaças à validade externa (Seção VI): período, idade dos repositórios e estrelas da camada de PRs
    anos, repos, novos = con.execute(f"""
        with r as (select distinct s.repo_name, s.repo_created_at from '{D}/spec_files.parquet' s join '{U}' u using(file_url_sha16)
                   where u.u_ciclo)
        select (select [min(substr(primeiro_commit, 1, 4)), max(substr(primeiro_commit, 1, 4))] from '{U}' where u_ciclo),
               count(distinct repo_name), count(distinct repo_name) filter (where repo_created_at >= '2025-01-01') from r""").fetchone()
    estrelas = con.execute(f"""select min(s.repo_stars) from (select distinct repo_name from '{D}/pull_requests.parquet') p
        join (select repo_name, min(repo_stars) repo_stars from '{D}/spec_files.parquet' group by 1) s using(repo_name)""").fetchone()[0]
    coleta = con.execute(f"""select [min(substr(commit_history_fetched_at, 1, 10)), max(substr(commit_history_fetched_at, 1, 10))],
        [min(substr(content_fetched_at, 1, 10)), max(substr(content_fetched_at, 1, 10))] from '{D}/spec_files.parquet'""").fetchone()
    # specs que saem do funil por "sem commit até o corte": o arquivo existe, mas o SpecMine não coletou o histórico dele
    vazio, sem_commit = con.execute(f"""select
        (select count(*) from '{D}/spec_files.parquet' where spec_tool <> 'caffeine' and commit_history_status = 'empty'),
        (select count(*) from '{U}' where not excl_caffeine and n_commits = 0)""").fetchone()
    assert vazio == sem_commit, (vazio, sem_commit)
    NUM["corpus"] = dict(primeiro_commit_anos=list(anos), repos=int(repos), repos_criados_2025_ou_depois=int(novos),
                         estrelas_min_camada_pr=int(estrelas), coleta_historico=list(coleta[0]), coleta_texto=list(coleta[1]),
                         historico_nao_coletado=int(vazio))
    os.makedirs(os.path.join(ROOT, "data", "derived", "numeros"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "derived", "numeros", "key_numbers.json"), "w") as f:
        json.dump(NUM, f, indent=1, ensure_ascii=False)
    print("\n== ciclo, janela fixa de 60 dias (exposição)\n", fmt(janela)[["grupo", "metrica", "repo", "n_repos"]].to_string(index=False))
    print("\n== hipóteses (regras de docs/metodo.md §5b)\n", hip.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
