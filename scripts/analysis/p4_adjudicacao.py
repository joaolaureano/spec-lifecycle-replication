"""RQ2 — Material da adjudicação.

Pares em que o rótulo final do humano (com revisão de dona, veto e divergência prévia; p4_rotulos_finais.csv) e o
DeepSeek v3 rodada 1 discordam em "decay sim/não" (Y amplo). "Não dá para julgar" de qualquer lado fica fora. O avaliador
relê cada par (spec + diff, o mesmo material de pares.html) e vê duas leituras, A e B, em ordem sorteada e sem dizer de
quem é cada uma. Depois decide o rótulo final pelo livro de códigos v3.
Gerador de uma vez só (como validation_build.py): não sobrescreve a planilha preenchida; no reproduzir.sh roda só o --conferir.
Uso: .venv/bin/python -I scripts/analysis/p4_adjudicacao.py [--conferir]  (--conferir: só confere a ordem A/B pela semente)
Saída: data/validation/adjudicacao_p4/{adjudicacao.html, adjudicacao_p4.csv (preencher), chave_NAO_ABRIR.csv}
"""
import hashlib, html, os, re, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "data", "validation")
OUT = os.path.join(V, "adjudicacao_p4")
AMPLO = {"contradiz", "omite"}
SEED = "adj-20261108"
INSTR = """Adjudicação da P4 (08/nov). Cada par abaixo teve duas leituras que discordam sobre "a spec ficou errada ou
incompleta por causa deste PR?" (decay sim × não). As leituras A e B estão em ordem sorteada; uma delas pode ser sua.
Releia a spec e o diff e decida o rótulo FINAL pela mesma árvore do livro de códigos v3:
  1. o diff muda comportamento observável? não -> preserva
  2. é do assunto desta spec? não -> outra_capacidade (escreva a spec dona em obs)
  3. alguma frase ficou falsa? sim -> contradiz; não, mas a spec não cobre o comportamento novo -> omite
  falta informação -> nao_da_para_julgar
Preencha adjudicacao_p4.csv: rotulo_final (um dos 5) e obs (por quê, em uma frase). Vale ficar com A, com B ou com outro."""


def humano_primeiro(par):
    return int(hashlib.md5(f"{SEED}|{par}".encode()).hexdigest(), 16) % 2 == 0


def conferir():
    """Refaz a ordem A/B a partir da semente e compara com chave_NAO_ABRIR.csv, sem gravar nada (roda no reproduzir.sh)."""
    k = pd.read_csv(os.path.join(OUT, "chave_NAO_ABRIR.csv"))
    p = pd.read_csv(os.path.join(OUT, "adjudicacao_p4.csv"), sep=";", encoding="utf-8-sig")
    if list(k.par) != list(p.par) or [("humano" if humano_primeiro(x) else "deepseek") for x in k.par] != list(k.A):
        raise SystemExit("ERRO: a ordem A/B da adjudicação não se repete a partir da semente")
    print(f"ordem cega da adjudicação idêntica à chave ({len(k)} pares; semente {SEED})")


def main():
    planilha = os.path.join(OUT, "adjudicacao_p4.csv")
    if os.path.exists(planilha):
        raise SystemExit(f"{planilha} já existe: não sobrescrevo (pode estar preenchida)")
    r = pd.read_csv(os.path.join(V, "p4_rotulos_finais.csv"), dtype=str).fillna("")
    h = pd.read_csv(os.path.join(V, "rotulagem_pares_humano.csv"), sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    ds = pd.read_csv(os.path.join(V, "llm", "llm_pares_v3.csv"), dtype=str).fillna("")
    j = r.merge(h[["par", "obs"]], on="par").merge(ds[["par", "q_decay", "divergencia_previa", "frase_spec", "justificativa"]]
                                                    .rename(columns={"q_decay": "ds", "divergencia_previa": "ds_div"}), on="par")
    j = j[(j.divergencia_previa != "sim") & (j.q != "nao_da_para_julgar") & (j.ds != "nao_da_para_julgar")]
    j["h_sim"] = j.q.isin(AMPLO)
    j["d_sim"] = j.ds.isin(AMPLO) & (j.ds_div != "sim")  # o DeepSeek também tira do Y o que já divergia antes
    d = j[j.h_sim != j.d_sim].sort_values("par").copy()
    secoes = dict(re.findall(r"<section><h2>(P\d{3}) \|.*?</h2>(.*?)</section>",
                             open(os.path.join(V, "pares.html"), encoding="utf-8").read(), re.S))
    cab = dict(re.findall(r"<section><h2>((P\d{3}) \|.*?)</h2>", open(os.path.join(V, "pares.html"), encoding="utf-8").read()))
    cab = {v: k for k, v in cab.items()}
    linhas, partes = [], []
    for x in d.itertuples():
        hum = f"{x.q}: {x.obs or '(sem observação)'}"
        llm = f"{x.ds}: {x.justificativa}" + (f' (frase da spec: "{x.frase_spec}")' if x.frase_spec else "")
        h1 = humano_primeiro(x.par)
        a, b = (hum, llm) if h1 else (llm, hum)
        linhas.append(dict(par=x.par, A="humano" if h1 else "deepseek", B="deepseek" if h1 else "humano"))
        partes.append(f"<section><h2>{html.escape(cab[x.par])}</h2><h3>Leitura A</h3><pre class=l>{html.escape(a)}</pre>"
                      f"<h3>Leitura B</h3><pre class=l>{html.escape(b)}</pre>{secoes[x.par]}</section>")
    os.makedirs(OUT, exist_ok=True)
    estilo = ("<style>body{font-family:sans-serif;max-width:1100px;margin:auto}pre{background:#f4f4f4;padding:8px;"
              "white-space:pre-wrap;font-size:12px}pre.l{background:#fff4d6;font-size:13px}"
              "section{border-top:2px solid #333;margin-top:28px}</style>")
    with open(os.path.join(OUT, "adjudicacao.html"), "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset=utf-8><title>Adjudicação P4</title>{estilo}<pre>{html.escape(INSTR)}</pre>"
                + "".join(partes))
    pd.DataFrame(linhas).to_csv(os.path.join(OUT, "chave_NAO_ABRIR.csv"), index=False)
    # mesmo formato da planilha de rotulagem do avaliador (Excel: ';', CRLF, BOM)
    d[["par"]].assign(rotulo_final="", obs="").to_csv(planilha, sep=";", index=False, lineterminator="\r\n",
                                                    encoding="utf-8-sig")
    print(f"pares em discordância: {len(d)} (humano sim × DeepSeek não: {int((d.h_sim & ~d.d_sim).sum())}; "
          f"humano não × DeepSeek sim: {int((~d.h_sim & d.d_sim).sum())}); fora do piloto: {int((d.par >= 'P061').sum())}")


if __name__ == "__main__":
    conferir() if "--conferir" in sys.argv else main()
