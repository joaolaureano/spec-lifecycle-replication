"""Confere a integridade de TODAS as entradas que o pipeline lê.

- Parquets do SpecMine (data/specmine/data/): sha256 de cada arquivo = sha256 do mesmo arquivo dentro do ZIP do Zenodo
  (cujo MD5 o reproduzir.sh confere antes).
- Texto das specs (data/derived/specs_text.parquet): hash do CONTEÚDO (md5 de cada linha, em ordem de chave), porque um
  parquet refeito com --desde-o-zenodo tem os mesmos dados em bytes diferentes.
- Decisões humanas e de LLM, gabaritos e arquivos de sorteio: sha256 dos bytes.
Os valores esperados ficam em data/ENTRADAS.sha256 (gerado uma vez com --gerar, depois de conferido).
Uso: .venv/bin/python -I scripts/conferir_entradas.py [--gerar]
"""
import hashlib, os, sys, zipfile
import duckdb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFESTO = os.path.join(ROOT, "data", "ENTRADAS.sha256")
ZIP = os.path.join(ROOT, "data", "specmine_zenodo", "specmine.zip")
TEXTO = "data/derived/specs_text.parquet"
ARQUIVOS = [  # lidos pelo pipeline e não regenerados por ele
    "data/api_pr_diffs/sample/pares.csv", "data/api_pr_diffs_ext/sample/pares.csv",
    "data/validation/rotulagem_pares_humano.csv",
    "data/validation/gabarito_pares.csv",
    "data/validation/divergencia_previa.csv",
    "data/validation/revisao_dono/decisoes.csv", "data/validation/revisao_dono/veto_humano.csv",
    "data/validation/revisao_dono/evidencia_veto/evidencia_veto.csv",
    "data/validation/adjudicacao_p4/adjudicacao_p4.csv", "data/validation/adjudicacao_p4/dona_adjudicacao.csv",
    "data/validation/llm/llm_pares_v3.csv",
]


def sha256(f):
    h = hashlib.sha256()
    for bloco in iter(lambda: f.read(1 << 20), b""):
        h.update(bloco)
    return h.hexdigest()


def hash_texto():
    return duckdb.sql(f"""select md5(string_agg(md5(file_url_sha16 || coalesce(content, '')), '' order by file_url_sha16))
                          from '{os.path.join(ROOT, TEXTO)}'""").fetchall()[0][0]


def main():
    falhas = 0
    with zipfile.ZipFile(ZIP) as z:
        membros = {os.path.basename(i.filename): i for i in z.infolist() if i.filename.endswith(".parquet")}
        locais = sorted(os.listdir(os.path.join(ROOT, "data", "specmine", "data")))
        assert set(locais) == set(membros), f"parquets diferentes do ZIP: {set(locais) ^ set(membros)}"
        for nome in locais:
            with open(os.path.join(ROOT, "data", "specmine", "data", nome), "rb") as a, z.open(membros[nome]) as b:
                if sha256(a) != sha256(b):
                    print(f"DIFERE DO ZIP: data/specmine/data/{nome}")
                    falhas += 1
    atual = {p: sha256(open(os.path.join(ROOT, p), "rb")) for p in ARQUIVOS}
    atual[TEXTO] = hash_texto()
    if "--gerar" in sys.argv:
        with open(MANIFESTO, "w") as f:
            f.writelines(f"{v}  {k}\n" for k, v in sorted(atual.items()))
        print(f"manifesto gravado: {len(atual)} entradas")
        return
    esperado = dict(reversed(l.split(None, 1)) for l in open(MANIFESTO).read().splitlines())
    esperado = {k.strip(): v for k, v in esperado.items()}
    assert set(esperado) == set(atual), f"manifesto e lista divergem: {set(esperado) ^ set(atual)}"
    for k in sorted(atual):
        if atual[k] != esperado[k]:
            print(f"ALTERADO: {k}")
            falhas += 1
    if falhas:
        sys.exit(f"ERRO: {falhas} entrada(s) não conferem")
    print(f"ok: {len(locais)} parquets iguais ao ZIP do Zenodo e {len(atual)} entradas iguais ao manifesto")


if __name__ == "__main__":
    main()
