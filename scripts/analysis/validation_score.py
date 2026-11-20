"""Pontua a RQ2 (spec decay): Y, sensibilidades, ICC e acordo humano × LLM, a partir dos rótulos e decisões em
data/validation/.
Uso: .venv/bin/python -I scripts/analysis/validation_score.py
"""
import json, os
import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "data", "validation")
NUM = {}  # números citados no paper que não estão nas tabelas (lidos pelo notebook numeros_do_paper.ipynb)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - m, c + m)


def ler(nome):
    p = os.path.join(V, nome)
    return pd.read_csv(p, dtype=str).fillna("") if os.path.exists(p) else None


def main():
    pd.set_option("display.width", 200)
    p4()
    os.makedirs(os.path.join(ROOT, "data", "derived", "numeros"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "derived", "numeros", "validation_score.json"), "w") as f:
        json.dump(NUM, f, indent=1, ensure_ascii=False)


CORTE = pd.Timestamp("2026-07-11T23:59:59Z")  # o mesmo corte do histórico de spec_rot_viabilidade.py
AMPLO, ESTRITO = {"contradiz", "omite"}, {"contradiz"}


def faixa(lo, hi):
    """Leitura da H2 pelas faixas fixadas antes (docs/metodo.md §5b), aplicada ao IC."""
    return ("resultado negativo" if hi < .2 else "decay" if lo >= .5 else
            "co-mudança com parte de decay" if lo >= .2 and hi < .5 else "inconclusivo")


def y_repo(d, pos):
    """Y = média das proporções por repositório nos pares julgáveis; IC por bootstrap de repositórios; Wilson agrupado."""
    julg = d[d.q != "nao_da_para_julgar"]
    s = julg.q.isin(pos)
    lo, hi = wilson(int(s.sum()), len(julg))
    pr = julg.assign(s=s).groupby("repo_name").s.mean().to_numpy(float)
    bm = pr[np.random.default_rng(20261105).integers(0, len(pr), (1000, len(pr)))].mean(axis=1)
    y, blo, bhi = pr.mean(), np.percentile(bm, 2.5), np.percentile(bm, 97.5)
    if blo == bhi:  # 0 (ou só) positivos: o bootstrap degenera em [y, y]; usa Wilson como IC
        blo, bhi = lo, hi
    return dict(y=y, ic_lo=blo, ic_hi=bhi, leitura=faixa(blo, bhi), repos=len(pr), pares=len(julg),
                positivos=int(s.sum()), wilson_lo=lo, wilson_hi=hi)


def icc(y, g):
    """ICC(1) por ANOVA de um fator, grupos desiguais (descrição da heterogeneidade entre repositórios)."""
    d = pd.DataFrame(dict(y=np.asarray(y, float), g=np.asarray(g)))
    n, m, N, k = d.groupby("g").size(), d.groupby("g").y.mean(), len(d), d.g.nunique()
    msb = (n * (m - d.y.mean()) ** 2).sum() / (k - 1)
    msw = ((d.y - d.g.map(m)) ** 2).sum() / (N - k)
    k0 = (N - (n ** 2).sum() / N) / (k - 1)
    return (msb - msw) / (msb + (k0 - 1) * msw)


def rotulos_p4():
    """Rótulo humano final (livro v3) + revisão de dona + divergência prévia -> classe no Y.
    - outra_capacidade sem evidência de conteúdo (revisao_dono/decisoes.csv) conta como omite (§5b), salvo veto do
      avaliador humano (revisao_dono/veto_humano.csv): o humano é o padrão-ouro e o revisor só propõe;
    - divergência prévia (o código já contrariava a spec antes do PR) fica fora do Y (§5b). A coluna saiu da planilha
      final; os pares vêm das notas do próprio avaliador (divergencia_previa.csv), com sensibilidade sem a exclusão.
    Grava p4_rotulos_finais.csv (lido por p4_fluxo.py)."""
    h = pd.read_csv(os.path.join(V, "rotulagem_pares_humano.csv"), sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    g = ler("gabarito_pares.csv")
    assert len(h) == len(g) == 280 and set(h.par) == set(g.par) and h.q_decay.str.strip().ne("").all()
    r = h[["par", "q_decay", "outra_spec"]].merge(g[["par", "repo_name", "pr_number", "file_url_sha16", "merged_at"]], on="par")
    r["bruto"] = r.q_decay.str.strip()
    assert set(r.bruto) <= {"preserva", "outra_capacidade", "omite", "contradiz", "nao_da_para_julgar"}, set(r.bruto)
    dono = ler(os.path.join("revisao_dono", "decisoes.csv"))
    veto = ler(os.path.join("revisao_dono", "veto_humano.csv"))
    assert set(veto.par) == set(dono.par[dono.revisao_outra == "sem_evidencia"]), "veto deve cobrir os sem_evidencia"
    # evidência documentada dos vetos (metodo.md §5g): quando preenchida, "mantem_veto = nao" retira o veto
    ev = os.path.join(V, "revisao_dono", "evidencia_veto", "evidencia_veto.csv")
    if os.path.exists(ev):
        e = pd.read_csv(ev, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
        e["mantem_veto"] = e.mantem_veto.str.strip().str.lower()
        if e.mantem_veto.ne("").any():
            assert e.mantem_veto.isin(["sim", "nao", "não"]).all(), "mantem_veto deve ser sim ou nao em todas as linhas"
            veto.loc[veto.par.isin(e.par[e.mantem_veto != "sim"]), "veto"] = "nao"
    r = r.merge(dono[["par", "revisao_outra", "forca"]], on="par", how="left").merge(
        veto[["par", "veto"]], on="par", how="left").fillna("")
    oc = r.bruto == "outra_capacidade"
    assert r.loc[oc, "revisao_outra"].isin(["confirmada", "sem_evidencia"]).all(), "outra_capacidade sem revisão de dona"
    r["q_regra"] = r.bruto.mask(oc & (r.revisao_outra == "sem_evidencia"), "omite")  # regra sem veto (sensibilidade)
    r["q_pre_adj"] = r.q_regra.mask(oc & (r.veto == "sim"), "outra_capacidade")  # antes da adjudicação (sensibilidade)
    # adjudicação (metodo.md §5e): nos pares em que humano e DeepSeek discordavam, o rótulo relido substitui;
    # outra_capacidade adjudicada só vale com dona (dona_adjudicacao.csv, ou a revisão/veto anteriores); senão, omite
    adj = pd.read_csv(os.path.join(V, "adjudicacao_p4", "adjudicacao_p4.csv"), sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    adj["final"] = adj.rotulo_final.str.strip().str.lower()
    assert adj.par.is_unique and adj.final.isin(["preserva", "outra_capacidade", "contradiz", "omite", "nao_da_para_julgar"]).all()
    dadj = ler(os.path.join("adjudicacao_p4", "dona_adjudicacao.csv"))
    tem_dona = set(dadj.par[dadj.revisao_outra == "confirmada"]) | set(r.par[oc & ((r.revisao_outra == "confirmada") | (r.veto == "sim"))])
    oa = adj.final == "outra_capacidade"
    assert set(adj.par[oa]) <= tem_dona | set(dadj.par), "outra_capacidade adjudicada sem revisão de dona"
    adj.loc[oa & ~adj.par.isin(tem_dona), "final"] = "omite"
    r = r.merge(adj[["par", "final"]].rename(columns={"final": "adjudicado"}), on="par", how="left").fillna("")
    r["q"] = r.q_pre_adj.mask(r.adjudicado != "", r.adjudicado)
    r["dona_componente"] = (r.forca == "componente") | r.par.isin(dadj.par[dadj.forca == "componente"])
    # de onde vem a "outra capacidade" final: spec dona com texto explícito, dona só
    # pelo componente, ou só o veto humano (sem spec dona identificada)
    fa = dadj.set_index("par").forca
    r["dona_tipo"] = np.select(
        [r.q != "outra_capacidade", r.par.isin(fa.index), r.revisao_outra == "confirmada", r.veto == "sim"],
        ["", r.par.map(fa).fillna(""), r.forca, "veto"], default="?")
    assert not (r.dona_tipo == "?").any(), "outra_capacidade final sem origem de dona"
    r["divergencia_previa"] = np.where(r.par.isin(ler("divergencia_previa.csv").par), "sim", "")
    r["dias_ao_corte"] = (CORTE - pd.to_datetime(r.merged_at, utc=True)).dt.days
    txt = duckdb.sql(f"select file_url_sha16, content from '{os.path.join(ROOT, 'data', 'derived', 'specs_text.parquet')}'"
                     ).df().set_index("file_url_sha16").content
    # (f): no piloto, os 14 pares com spec em chinês foram julgados com tradução; nos novos, não há registro -> todos fora
    r["spec_chines"] = r.file_url_sha16.map(txt).fillna("").str.contains(r"[一-鿿]")
    r.drop(columns=["q_decay"]).to_csv(os.path.join(V, "p4_rotulos_finais.csv"), index=False)
    return r


def p4():
    """RQ2: Y = fração dos pares julgáveis em que o PR tornou a spec errada, média por repositório.
    Critério H2 sobre o Y amplo (contradiz + omite); Y estrito (contradiz) com o mesmo destaque (§5c).
    Faixas fixadas antes: IC < 20% negativo; >= 50% decay; [20%, 50%) co-mudança com parte de decay."""
    assert icc([1, 1, 0, 0], [0, 0, 1, 1]) == 1  # autoteste: grupos puros -> ICC 1
    r = rotulos_p4()
    # segundo canal de ligação (metodo.md §5f): confirmação de cada par por openspec_code_refs (p4_ligacao.py)
    lig = pd.read_csv(os.path.join(ROOT, "data", "derived", "tables", "p4_ligacao.csv"), dtype={"par": str})
    assert set(lig.par) == set(r.par), "p4_ligacao.csv não cobre os 280 pares"
    r = r.merge(lig[["par", "todos_confirmados", "algum_feito"]], on="par")
    base = r[r.divergencia_previa != "sim"]
    oc = base.bruto == "outra_capacidade"
    cortes = {
        "principal": base,
        "(a) só os 222 pares fora do piloto": base[base.par >= "P061"],
        "(b) só o piloto": base[base.par <= "P060"],
        "(c) sem a revisão de dona": base.assign(q=base.bruto),
        "(d1) não dá para julgar = não decay": base.assign(q=base.q.replace("nao_da_para_julgar", "preserva")),
        "(d2) não dá para julgar = decay": base.assign(q=base.q.replace("nao_da_para_julgar", "contradiz")),
        "(e) só PRs >= 60 dias antes do corte": base[base.dias_ao_corte >= 60],
        "(f) sem specs com texto em chinês": base[~base.spec_chines],
        # régua literal: "o texto descreve a mudança" -> dona só por componente (decisoes.csv: forca) não basta
        "(h) dona só por componente = omite": base.assign(q=base.q.mask((base.q == "outra_capacidade") & base.dona_componente, "omite")),
        "antes da adjudicação": base.assign(q=base.q_pre_adj),
        "regra de dona sem o veto humano (e sem adjudicação)": base.assign(q=base.q_regra),
        # o veto aplicado ao resultado FINAL; e o mais estrito, sem veto e sem dona por componente
        "final sem o veto humano": base.assign(q=base.q.mask(base.dona_tipo == "veto", "omite")),
        "final sem o veto e dona só por componente = omite": base.assign(
            q=base.q.mask(base.dona_tipo.isin(["veto", "componente"]), "omite")),
        "divergência prévia contada como rotulada": r,
        "só pares com todos os caminhos confirmados (openspec_code_refs)": base[base.todos_confirmados == 1],
        "só pares com caminho de tarefa marcada (openspec_code_refs)": base[base.algum_feito == 1],
    }
    print(f"\n== RQ2 — humano v3 (280 pares): rótulo bruto {r.bruto.value_counts().to_dict()}")
    print(f"   revisão de dona: {int(oc.sum())} outra_capacidade; confirmadas {int((oc & (base.revisao_outra == 'confirmada')).sum())}; "
          f"sem evidência {int((oc & (base.revisao_outra == 'sem_evidencia')).sum())}, das quais o humano vetou "
          f"{int((oc & (base.veto == 'sim')).sum())} e manteve como omite {int((oc & (base.revisao_outra == 'sem_evidencia') & (base.veto != 'sim')).sum())}")
    print(f"   outra capacidade no rótulo final, por origem da dona: {base.dona_tipo[base.dona_tipo != ''].value_counts().to_dict()}")
    print(f"   divergência prévia (fora do Y): {sorted(r.par[r.divergencia_previa == 'sim'])}; não dá para julgar: "
          f"{int((base.q == 'nao_da_para_julgar').sum())}/{len(base)}")
    jb = base[base.q != "nao_da_para_julgar"]
    print(f"   principal: {len(jb)} pares julgáveis, {jb.drop_duplicates(['repo_name', 'pr_number']).shape[0]} PRs únicos, "
          f"{jb.file_url_sha16.nunique()} specs únicas, {jb.repo_name.nunique()} repos; ICC entre repos (descritivo): "
          f"amplo {icc(jb.q.isin(AMPLO), jb.repo_name):.3f}, estrito {icc(jb.q.isin(ESTRITO), jb.repo_name):.3f} (premissa do poder: ρ ≤ 0,3)")
    pre, fin = jb.q_pre_adj.isin(AMPLO), jb.q.isin(AMPLO)
    print(f"   adjudicação (julgáveis, Y amplo): {int((~pre & fin).sum())} entram no decay, {int((pre & ~fin).sum())} saem")
    vetos = ler(os.path.join("revisao_dono", "veto_humano.csv"))
    NUM.update(pares=len(r), rotulo_bruto={k: int(v) for k, v in r.bruto.value_counts().items()},
               dona_outra_capacidade=int(oc.sum()), dona_confirmadas=int((oc & (base.revisao_outra == "confirmada")).sum()),
               dona_sem_evidencia=int((oc & (base.revisao_outra == "sem_evidencia")).sum()),
               vetos_iniciais=int((vetos.veto == "sim").sum()), vetos_finais=int((oc & (base.veto == "sim")).sum()),
               outra_capacidade_final={k: int(v) for k, v in base.dona_tipo[base.dona_tipo != ""].value_counts().items()},
               divergencia_previa=int((r.divergencia_previa == "sim").sum()),
               nao_da_para_julgar=int((base.q == "nao_da_para_julgar").sum()), julgaveis=len(jb),
               prs_unicos=int(jb.drop_duplicates(["repo_name", "pr_number"]).shape[0]),
               specs_unicas=int(jb.file_url_sha16.nunique()), repos=int(jb.repo_name.nunique()),
               icc_amplo=round(icc(jb.q.isin(AMPLO), jb.repo_name), 6), icc_estrito=round(icc(jb.q.isin(ESTRITO), jb.repo_name), 6),
               adjudicados=int((base.adjudicado != "").sum()), adjudicacao_entram=int((~pre & fin).sum()),
               adjudicacao_saem=int((pre & ~fin).sum()), ligacao_confirmada=int(r.todos_confirmados.sum()))
    # datas por authored_at; o commit da spec pode ter entrado (committed_at) depois do merge do PR
    sfc = os.path.join(ROOT, "data", "specmine", "data", "spec_file_commits.parquet")
    ult = duckdb.sql(f"""select file_url_sha16, max(cast(committed_at as timestamptz)) committed from '{sfc}'
                        where authored_at <= '2026-07-11T23:59:59Z' group by 1""").df()
    t = r.merge(ult, on="file_url_sha16")
    tarde = t[t.committed > pd.to_datetime(t.merged_at, utc=True)].par
    NUM.update(commit_depois_do_merge=len(tarde), commit_depois_do_merge_decay=int((base.par.isin(tarde) & base.q.isin(AMPLO)).sum()))
    print(f"   último committed_at da spec depois do merge do PR: {sorted(tarde)} de {len(t)} pares; "
          f"decay (amplo) no final: {sorted(base.par[base.par.isin(tarde) & base.q.isin(AMPLO)])}")
    # o texto lido vem da coleta de conteúdo (12/jul), um dia depois do histórico (11/jul): nenhuma spec dos pares pode ter
    # mudado entre as duas; spec sem data conta como mudada
    sf = os.path.join(ROOT, "data", "specmine", "data", "spec_files.parquet")
    dt = r[["file_url_sha16"]].merge(duckdb.sql(f"""select s.file_url_sha16, s.file_last_commit_at, h.ult from '{sf}' s
        join (select file_url_sha16, max(authored_at) ult from '{sfc}' group by 1) h using(file_url_sha16)""").df(), on="file_url_sha16")
    mudou = dt.file_last_commit_at.isna() | (dt.file_last_commit_at > dt.ult) | (dt.file_last_commit_at > "2026-07-11T23:59:59Z")
    NUM.update(texto_pares_conferidos=len(dt), texto_mudou_entre_coletas=int(mudou.sum()))
    print(f"   specs dos pares com commit depois do histórico ou do corte: {int(mudou.sum())} de {len(dt)}")
    linhas = []
    for nome, d in cortes.items():
        for medida, pos in [("amplo (critério)", AMPLO), ("estrito", ESTRITO)]:
            e = y_repo(d, pos)
            linhas.append(dict(amostra=nome, medida=medida, **e))
            print(f"   [{nome} | {medida}] Y por repo = {e['y']:.3f} [IC {e['ic_lo']:.3f}–{e['ic_hi']:.3f}] ({e['repos']} repos, "
                  f"{e['pares']} pares) -> {e['leitura']}; Wilson agrupado {e['positivos']}/{e['pares']} [{e['wilson_lo']:.3f}–{e['wilson_hi']:.3f}]")
    res = pd.DataFrame(linhas)
    res.round(6).to_csv(os.path.join(V, "resultado_p4.csv"), index=False)
    for medida in ["amplo (critério)", "estrito"]:  # regra de robustez ao piloto (§5c)
        f = res[res.medida == medida].set_index("amostra").leitura
        ok = f["principal"] == f["(a) só os 222 pares fora do piloto"]
        print(f"   robustez ao piloto [{medida}]: principal '{f['principal']}' × fora do piloto '{f['(a) só os 222 pares fora do piloto']}' -> "
              + ("robusto" if ok else "NÃO robusto: reportar as duas faixas, sem veredito único"))
    # κ humano × DeepSeek v3 (rodada 1): só nos 222 pares fora do piloto (P061–P289) e sobre o rótulo humano BRUTO,
    # como fixado em §5c antes de ver os rótulos. O avaliador não viu rótulos de LLM no piloto (esclarecimento de 19/nov)
    ds = ler(os.path.join("llm", "llm_pares_v3.csv"))[["par", "q_decay"]].rename(columns={"q_decay": "ds"})
    j = r.merge(ds, on="par")
    j["ds"] = j.ds.str.strip()
    for nome, d in [("fora do piloto P061–P289", j[j.par >= "P061"])]:
        b = d[(d.bruto != "nao_da_para_julgar") & (d.ds != "nao_da_para_julgar")]
        print(f"   κ humano (bruto) × DeepSeek v3 [{nome}]: 5 categorias {cohen_kappa_score(d.bruto, d.ds):.3f} "
              f"(n={len(d)}, acordo {(d.bruto == d.ds).mean():.3f}); Y amplo binário "
              f"{cohen_kappa_score(b.bruto.isin(AMPLO), b.ds.isin(AMPLO)):.3f} (n={len(b)}; positivos "
              f"{int(b.bruto.isin(AMPLO).sum())} × {int(b.ds.isin(AMPLO).sum())})")
        NUM.update(kappa_5_categorias=round(cohen_kappa_score(d.bruto, d.ds), 6), kappa_n=len(d),
                   kappa_binario=round(cohen_kappa_score(b.bruto.isin(AMPLO), b.ds.isin(AMPLO)), 6), kappa_binario_n=len(b),
                   decay_humano=int(b.bruto.isin(AMPLO).sum()), decay_deepseek=int(b.ds.isin(AMPLO).sum()))
    cz = j[j.par >= "P061"]
    tab = pd.crosstab(cz.bruto.rename("humano_bruto"), cz.ds.rename("deepseek"), margins=True, margins_name="total")
    tab.to_csv(os.path.join(V, "resultado_p4_confusao.csv"))
    print("   tabela cruzada nos 222 pares fora do piloto (linhas = humano bruto; colunas = DeepSeek v3):\n" + tab.to_string())


if __name__ == "__main__":
    main()
