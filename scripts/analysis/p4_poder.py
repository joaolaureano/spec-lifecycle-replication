"""RQ2: quantos pares por repositório (m) julgar — simulação de poder, regra fixada em docs/metodo.md §5b.

Y verdadeiro = piloto; θ_repo ~ Beta(média Y, ICC ρ); cada repo recebe min(m, candidatos) pares Bernoulli(θ_repo);
estimativa = média das proporções por repo; IC = ± 1,96·dp/√R (aproximação normal do bootstrap de repos).
Poder = P(IC_hi < 20%). Regra: menor m com poder >= 80% para todo ρ <= 0,3.
Saída: data/derived/tables/p4_poder.csv
Uso: .venv/bin/python -I scripts/analysis/p4_poder.py
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAND = os.path.join(ROOT, "data", "api_pr_diffs", "sample", "candidatos.parquet")
TAB = os.path.join(ROOT, "data", "derived", "tables")
SEED, REPS, LIMIAR, ALVO = 20261105, 2000, 0.20, 0.80
# Premissa do desenho (05/nov): rotulagem preliminar dos 58 pares do piloto por LLM, com o codebook anterior ao v3
# (7 decay em 56 julgáveis). Esses rótulos e o modelo não foram guardados (registro: docs/problemas.md #41); os
# rótulos v3 do mesmo piloto (llm_pares_v3.csv) dão 5/56, o que só tornaria m = 3 mais folgado.
Y_PILOTO = 7 / 56
CENARIOS = [(Y_PILOTO, r) for r in (0.0, 0.1, 0.2, 0.3)] + [(Y_PILOTO, 0.5), (0.15, 0.0), (0.15, 0.1), (0.15, 0.2)]


def poder(cand, m, y, rho, rng):
    n = np.minimum(cand, m)
    if rho == 0:
        theta = np.full((REPS, len(n)), y)
    else:
        s = 1 / rho - 1  # a + b
        theta = rng.beta(y * s, (1 - y) * s, size=(REPS, len(n)))
    p = rng.binomial(n, theta) / n
    est = p.mean(axis=1)
    hi = est + 1.96 * p.std(axis=1, ddof=1) / np.sqrt(len(n))
    return (hi < LIMIAR).mean(), est.mean(), int(n.sum())


def main():
    pool = pd.read_parquet(CAND)
    pool = pool[pd.to_datetime(pool.merged_at, utc=True) <= pd.Timestamp("2026-07-11T23:59:59Z")]
    cand = pool.groupby("repo_name").size().sort_index().to_numpy()
    rng = np.random.default_rng(SEED)
    linhas = []
    for y, rho in CENARIOS:
        for m in range(1, 7):
            pw, media, pares = poder(cand, m, y, rho, rng)
            linhas.append(dict(y=round(y, 4), rho=rho, m=m, pares=pares, poder=round(pw, 4), media_est=round(media, 4),
                               principal=rho <= 0.3 and y == Y_PILOTO))
    t = pd.DataFrame(linhas)
    t.to_csv(os.path.join(TAB, "p4_poder.csv"), index=False)
    ok = t[t.principal].groupby("m").poder.min()
    m_rec = int(ok[ok >= ALVO].index.min()) if (ok >= ALVO).any() else None
    print(f"repos: {len(cand)}; candidatos por repo: mediana {np.median(cand):.0f}, com 1 só: {(cand == 1).sum()}")
    print(t.pivot_table(index=["y", "rho"], columns="m", values="poder").to_string())
    print("pares por m:", t.drop_duplicates("m").set_index("m").pares.to_dict())
    print(f"poder mínimo (ρ<=0,3, Y piloto) por m: {ok.round(3).to_dict()}\nRECOMENDAÇÃO: m = {m_rec}")


if __name__ == "__main__":
    main()
