"""RQ2 — Figura de fluxo (Sankey): rótulo humano -> revisão de dona, veto e adjudicação -> classe usada no Y.

Mostra, para o leitor do artigo, que outra_capacidade não é aceita na palavra do rotulador: sem evidência de
conteúdo vira omite (docs/metodo.md §5b). Contagens são de PARES; o Y do artigo é a média por repositório.
Uso: .venv/bin/python -I scripts/analysis/p4_fluxo.py
Saída: data/derived/figures/p4_fluxo_completa.{png,csv} (a figura e as contagens) e paper/figs/p4_flow.png
(rótulos em inglês, largura das duas colunas: figure* no paper).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG = os.path.join(ROOT, "data", "derived", "figures")
# cor = classe final no Y
COR = {"não decay": "#2a78d6", "decay (Y amplo)": "#eb6834", "excluído": "#9a9a94"}
NOME = {"outra_capacidade": "outra capacidade", "nao_da_para_julgar": "não dá para julgar"}
ETAPAS = [  # (coluna, nós na ordem de cima para baixo)
    ("rótulo humano", ["preserva", "outra_capacidade", "omite", "contradiz", "nao_da_para_julgar"]),
    ("dona, veto e adjudicação", ["preserva", "outra_capacidade", "omite", "contradiz", "divergência prévia",
                                  "nao_da_para_julgar"]),
    ("classe no Y", ["não decay", "decay (Y amplo)", "excluído"]),
]


def caminhos(rot):
    """e0 = rótulo humano bruto; e1 = rótulo depois da revisão de dona, do veto e da adjudicação (coluna q de
    p4_rotulos_finais.csv, gravada por validation_score.py); e2 = classe no Y."""
    r = rot.copy()
    r["e0"] = r.bruto
    r["e1"] = r.q.where(r.divergencia_previa != "sim", "divergência prévia")
    r["e2"] = r.e1.map({"preserva": "não decay", "outra_capacidade": "não decay", "omite": "decay (Y amplo)",
                        "contradiz": "decay (Y amplo)", "divergência prévia": "excluído", "nao_da_para_julgar": "excluído"})
    assert r.e2.notna().all(), f"categoria fora do livro de códigos: {set(r.e1[r.e2.isna()])}"
    return r


def banda(ax, x0, y0a, y0b, x1, y1a, y1b, cor):
    m = (x0 + x1) / 2
    v = [(x0, y0a), (m, y0a), (m, y1a), (x1, y1a), (x1, y1b), (m, y1b), (m, y0b), (x0, y0b), (x0, y0a)]
    c = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(v, c), fc=cor, ec="none", alpha=.35))


# rótulos em inglês: a figura vai ao paper (paper/figs/p4_flow.png)
EN = {"preserva": "preserves", "outra_capacidade": "other capability", "omite": "omits", "contradiz": "contradicts",
      "nao_da_para_julgar": "cannot judge", "divergência prévia": "prior divergence", "não decay": "no decay",
      "decay (Y amplo)": "decay (broad Y)", "excluído": "excluded"}
CAB = ["human label", "after owner check,\nveto, adjudication", "class in Y"]


def espacar(ys, dmin):
    """Afasta rótulos verticais que ficariam a menos de dmin (de cima para baixo), sem mudar a ordem."""
    out = []
    for y in sorted(ys, reverse=True):
        out.append(min(y, out[-1] - dmin) if out else y)
    return dict(zip(sorted(ys, reverse=True), out))


def desenhar(r, saida, larga=False):
    # uma coluna do IEEE (3,5 pol.) ou as duas (7 pol., figure* no paper); a fonte fica legível sem reescala
    n, gap, w, xs = len(r), .035 * len(r), .05 if larga else .07, [0, 1, 2]
    fig, ax = plt.subplots(figsize=(7.0, 1.9) if larga else (3.5, 2.35))
    f_cab, f_rot, d_rot = (8.5, 7.5, .12) if larga else (6.5, 6, .075)
    pos = []  # pos[k][nó] = (y_base, altura) na etapa k
    for k, (_, nos) in enumerate(ETAPAS):
        cont = r[f"e{k}"].value_counts()
        y, p = n + gap * (len(nos) - 1), {}
        for no in nos:
            h = int(cont.get(no, 0))
            if h:
                y -= h
                p[no] = [y, h]
                y -= gap
        pos.append(p)
    for k in range(2):  # faixas entre etapas, empilhadas na ordem dos nós (sem cruzar sem necessidade)
        topo_src = {no: b + h for no, (b, h) in pos[k].items()}
        topo_dst = {no: b + h for no, (b, h) in pos[k + 1].items()}
        fl = r.groupby(list(dict.fromkeys([f"e{k}", f"e{k+1}", "e2"]))).size().reset_index(name="v")
        ordem = {no: i for i, no in enumerate(ETAPAS[k][1])}, {no: i for i, no in enumerate(ETAPAS[k + 1][1])}
        fl = fl.sort_values(by=[f"e{k}", f"e{k+1}"], key=lambda s: s.map(ordem[0] if s.name == f"e{k}" else ordem[1]))
        for _, f in fl.iterrows():
            a, b, v = f[f"e{k}"], f[f"e{k+1}"], f.v
            banda(ax, xs[k] + w, topo_src[a], topo_src[a] - v, xs[k + 1], topo_dst[b], topo_dst[b] - v, COR[f.e2])
            topo_src[a] -= v
            topo_dst[b] -= v
    topo, y_min = n + gap * 6, -.12 * n
    for k, nos in enumerate(pos):
        ax.text(xs[k] + w / 2, topo, CAB[k], ha="center", va="bottom", fontsize=f_cab, color="#3d3d3a", weight="bold")
        ys = espacar([b + h / 2 for b, h in nos.values()], d_rot * n)
        y_min = min(y_min, min(ys.values()) - .06 * n)
        for no, (b, h) in nos.items():
            # só a última etapa tem cor de classe; antes dela um nó pode misturar classes (other capability)
            ax.add_patch(Rectangle((xs[k], b), w, h, fc=COR[no] if k == 2 else "#3d3d3a", ec="white", lw=1))
            direita = k > 0
            ax.text(xs[k] + (w + .025 if direita else -.025), ys[b + h / 2], f"{EN.get(no, no)} ({h})",
                    ha="left" if direita else "right", va="center", fontsize=f_rot, color="#1a1a19",
                    bbox=dict(fc="white", ec="none", alpha=.8, pad=.3) if k == 1 else None)
    ax.set_xlim(*((-.42, 2.42) if larga else (-.62, 2.6)))
    ax.set_ylim(y_min, topo + (.17 if larga else .1) * n)
    ax.axis("off")
    fig.tight_layout(pad=.1)
    fig.savefig(f"{saida}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    rot = pd.read_csv(os.path.join(ROOT, "data", "validation", "p4_rotulos_finais.csv"), dtype=str).fillna("")
    r = caminhos(rot)
    assert len(r) == r.e1.size == r.e2.size  # autoteste: o fluxo conserva pares
    os.makedirs(FIG, exist_ok=True)
    saida = os.path.join(FIG, "p4_fluxo_completa")
    r.groupby(["e0", "e1", "e2"]).size().reset_index(name="pares").to_csv(f"{saida}.csv", index=False)
    desenhar(r, saida)
    os.makedirs(os.path.join(ROOT, "paper", "figs"), exist_ok=True)  # o pacote de replicação não traz paper/
    desenhar(r, os.path.join(ROOT, "paper", "figs", "p4_flow"), larga=True)
    print(open(f"{saida}.csv").read())


if __name__ == "__main__":
    main()
