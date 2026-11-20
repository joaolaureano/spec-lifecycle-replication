"""RQ2 — Material para documentar a evidência dos 12 vetos ("lacunas de especificação", metodo.md §5g).

Para cada par cujo rótulo final é outra_capacidade só por veto (p4_rotulos_finais.csv: dona_tipo == "veto"), mostra
a spec e o diff (o mesmo material de pares.html), a nota original do avaliador e a do revisor de dona. O avaliador
registra o trecho da spec que delimita o escopo e por que o comportamento mudado fica fora dele.
Gerador de uma vez só: não roda no reproduzir.sh e não sobrescreve a planilha preenchida.
Uso: .venv/bin/python -I scripts/analysis/p4_veto_evidencia.py
Saída: data/validation/revisao_dono/evidencia_veto/{evidencia_veto.html, evidencia_veto.csv (preencher)}
"""
import html, os, re
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "data", "validation")
OUT = os.path.join(V, "revisao_dono", "evidencia_veto")
INSTR = """Evidência dos vetos (lacunas de especificação). Em cada par você vetou o rebaixamento para "omite": julgou que o
comportamento mudado está FORA do escopo da spec do par, e o revisor não achou nenhuma outra spec que o descreva.
Para tornar o veto auditável, preencha evidencia_veto.csv:
  trecho_escopo  = trecho LITERAL da spec do par (Purpose ou requisito) que delimita o escopo dela
  comportamento  = em poucas palavras, o comportamento que o diff mudou
  justificativa  = uma frase: por que esse comportamento não é assunto desta spec
  mantem_veto    = sim | nao   (nao = na releitura você acha que É do escopo, e o par vira omite)"""


def main():
    planilha = os.path.join(OUT, "evidencia_veto.csv")
    if os.path.exists(planilha):
        raise SystemExit(f"{planilha} já existe: não sobrescrevo (pode estar preenchida)")
    r = pd.read_csv(os.path.join(V, "p4_rotulos_finais.csv"), dtype=str).fillna("")
    v = r[r.dona_tipo == "veto"].sort_values("par")
    assert len(v) == 12, len(v)
    h = pd.read_csv(os.path.join(V, "rotulagem_pares_humano.csv"), sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    d = pd.read_csv(os.path.join(V, "revisao_dono", "decisoes.csv"), dtype=str).fillna("")
    vh = pd.read_csv(os.path.join(V, "revisao_dono", "veto_humano.csv"), dtype=str).fillna("")
    v = v.merge(h[["par", "obs"]], on="par").merge(d[["par", "evidencia"]], on="par").merge(vh[["par", "nota_humano"]], on="par")
    pagina = open(os.path.join(V, "pares.html"), encoding="utf-8").read()
    secoes = dict(re.findall(r"<section><h2>(P\d{3}) \|.*?</h2>(.*?)</section>", pagina, re.S))
    cab = {k: c for c, k in re.findall(r"<section><h2>((P\d{3}) \|.*?)</h2>", pagina)}
    partes = [f"<section><h2>{html.escape(cab[x.par])}</h2>"
              f"<h3>Sua nota na rotulagem</h3><pre class=l>{html.escape(x.obs or '(vazia)')}</pre>"
              f"<h3>Revisor de dona (por que não achou dona)</h3><pre class=l>{html.escape(x.evidencia)}</pre>"
              f"<h3>Sua nota no veto</h3><pre class=l>{html.escape(x.nota_humano)}</pre>{secoes[x.par]}</section>"
              for x in v.itertuples()]
    os.makedirs(OUT, exist_ok=True)
    estilo = ("<style>body{font-family:sans-serif;max-width:1100px;margin:auto}pre{background:#f4f4f4;padding:8px;"
              "white-space:pre-wrap;font-size:12px}pre.l{background:#fff4d6;font-size:13px}"
              "section{border-top:2px solid #333;margin-top:28px}</style>")
    with open(os.path.join(OUT, "evidencia_veto.html"), "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset=utf-8><title>Evidência dos vetos</title>{estilo}"
                f"<pre>{html.escape(INSTR)}</pre>" + "".join(partes))
    # mesmo formato das planilhas do avaliador (Excel: ';', CRLF, BOM)
    v[["par", "repo_name"]].assign(trecho_escopo="", comportamento="", justificativa="", mantem_veto="").to_csv(
        planilha, sep=";", index=False, lineterminator="\r\n", encoding="utf-8-sig")
    print(f"{len(v)} pares: {', '.join(v.par)} -> {OUT}")


if __name__ == "__main__":
    main()
