"""Impressão digital das saídas do pipeline (usada por scripts/reproduzir.sh).

CSV/JSON/TXT: sha256 dos bytes. Parquet: sha256 do CONTEÚDO (linhas ordenadas por todas as colunas), porque o
DuckDB com várias threads pode gravar os mesmos dados em bytes diferentes.
Uso: .venv/bin/python -I scripts/hash_saidas.py <arquivo_saida>
"""
import glob, hashlib, os, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAIDAS = ["data/derived/universe.parquet", "data/derived/tables/*", "docs/key_numbers_final.json",
          "data/validation/resultado_*.csv", "data/validation/p4_rotulos_finais.csv", "data/validation/revisao_dono/*", "data/derived/figures/*.csv",
          "data/derived/p4_*.txt", "data/derived/numeros/*.json"]


def digest(p):
    if p.endswith(".parquet"):
        d = pd.read_parquet(p)
        d = d.astype(str).sort_values(list(d.columns)).reset_index(drop=True)
        return hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


if __name__ == "__main__":
    arqs = sorted({f for g in SAIDAS for f in glob.glob(os.path.join(ROOT, g)) if os.path.isfile(f)})
    assert arqs, "nenhuma saída encontrada"
    with open(sys.argv[1], "w") as f:
        for a in arqs:
            f.write(f"{digest(a)}  {os.path.relpath(a, ROOT)}\n")
    print(f"{len(arqs)} saídas")
