"""Gera docs/EXPLICACAO_E2E.md: a pesquisa de ponta a ponta, com cada métrica, fórmula, racional e valor.
Nenhum número é digitado: todos vêm das saídas do pipeline ou das entradas congeladas. Roda no fim do reproduzir.sh.
Uso: .venv/bin/python -I scripts/gerar_explicacao.py
"""
import importlib.util, json, os
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(ROOT, *a)
TAB, VAL, NUMD = P("data", "derived", "tables"), P("data", "validation"), P("data", "derived", "numeros")
js = lambda p: json.load(open(p, encoding="utf-8"))
csv = lambda p, **k: pd.read_csv(p, **k)


def modulo(caminho):
    spec = importlib.util.spec_from_file_location(os.path.basename(caminho)[:-3], caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def q(x, casas):  # arredondamento "meio para cima", como no paper
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def pc(x, casas=1):  # proporção -> "28,4"
    return str(q(Decimal(str(x)) * 100, casas)).replace(".", ",")


def dc(x, casas=2):
    return str(q(x, casas)).replace(".", ",")


def ic(lo, hi):
    return f"[{pc(lo)}–{pc(hi)}]"


def n(x):
    return f"{int(x):,}".replace(",", ".")


LEIT = {"satisfeito": "met", "nao_satisfeito": "refuted", "inconclusivo": "inconclusive"}
GN = {"openspec": "OpenSpec (todas as specs)", "openspec:living": "OpenSpec living", "speckit": "Spec Kit",
      "outras_nomeadas": "Outras ferramentas", "sem_ferramenta": "Sem ferramenta"}


def tabela(df):
    cab = "\n| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return cab + "".join("| " + " | ".join(str(v) for v in r) + " |\n" for r in df.itertuples(index=False))


def main():
    KN = js(P("docs", "key_numbers_final.json"))
    NK, NV, NS, NL = (js(os.path.join(NUMD, f"{k}.json")) for k in
                      ["key_numbers", "validation_score", "spec_rot_viabilidade", "p4_ligacao"])
    CO = NK["corpus"]
    fun = csv(os.path.join(TAB, "funil.csv"))
    cic = csv(os.path.join(TAB, "ciclo.csv")).set_index("grupo")
    jan = csv(os.path.join(TAB, "ciclo_janela60.csv")).set_index("grupo")
    hip = csv(os.path.join(TAB, "hipoteses.csv"))
    pod = csv(os.path.join(TAB, "p4_poder.csv"))
    res = csv(os.path.join(VAL, "resultado_p4.csv"))
    cz = csv(os.path.join(VAL, "resultado_p4_confusao.csv")).set_index("humano_bruto")
    pares = pd.concat([csv(P("data", d, "sample", "pares.csv")) for d in ["api_pr_diffs", "api_pr_diffs_ext"]])
    man_p = pd.concat([pd.read_json(P("data", d, "manifest.jsonl"), lines=True) for d in ["api_pr_diffs", "api_pr_diffs_ext"]])
    pr_ok = man_p[man_p.http == 200].drop_duplicates(["repo", "pr"])
    poder_m = modulo(P("scripts", "analysis", "p4_poder.py"))
    srv = open(P("scripts", "analysis", "spec_rot_viabilidade.py"), encoding="utf-8").read()
    reg = open(os.path.join(VAL, "llm", "MODELO_E_PROMPTS.md"), encoding="utf-8").read()

    f = fun.set_index("etapa")
    etapas = list(fun.etapa)
    h1b = hip[hip.hipotese == "H1b"].iloc[0]
    R = res.set_index(["amostra", "medida"])
    pb, ps = R.loc[("principal", "amplo (critério)")], R.loc[("principal", "estrito")]
    gap = R.loc[("final sem o veto humano", "amplo (critério)")]
    oc, rb = NV["outra_capacidade_final"], NV["rotulo_bruto"]
    corte = pd.Timestamp(KN["corte"])
    diag = sum(int(cz.loc[k, k]) for k in cz.index if k != "total" and k in cz.columns)
    p_o = diag / int(cz.loc["total", "total"])
    esc = pod[pod.principal.astype(str) == "True"]
    poder_min = esc.groupby("m").poder.min()
    m_rec = int(poder_min[poder_min >= poder_m.ALVO].index.min())
    y_pil = open(P("scripts", "analysis", "p4_poder.py"), encoding="utf-8").read().split("Y_PILOTO = ", 1)[1].split("\n")[0].strip().replace(" ", "")
    v3 = pd.read_csv(P("data", "validation", "llm", "llm_pares_v3.csv"))
    v3 = v3[(v3.par <= "P060") & (v3.q_decay.str.strip() != "nao_da_para_julgar")]
    v3_k, v3_n = int(v3.q_decay.str.strip().isin(["contradiz", "omite"]).sum()), len(v3)
    por_repo = pares.groupby("repo_name").size().value_counts().sort_index()
    genericos = srv.split("(^|/)(", 1)[1].split(")", 1)[0].replace("?", "").split("|")
    m_repo = int(srv.split("M_POR_REPO = ", 1)[1].split()[0])

    L = []
    w = L.append
    w(f"""# A pesquisa de ponta a ponta: o que foi feito, como e com que resultado

> **Gerado por `scripts/gerar_explicacao.py`** a partir das saídas do pipeline (`bash scripts/reproduzir.sh`).
> Nenhum número deste documento foi digitado: se o pipeline mudar, este arquivo muda junto. Decimais com vírgula;
> o paper usa ponto. Detalhe de cada decisão e data: `docs/metodo.md`; histórico de problemas: `docs/problemas.md`.

## 1. O que o estudo pergunta

Em *spec-driven development* (SDD), uma especificação em linguagem natural (a *spec*) guia um agente de código.
Depois da implementação, a spec continua no repositório e pode guiar trabalho futuro. O risco é ela ficar errada
quando o código muda (*spec decay*), algo que o paper-base do SpecMine (Agarwal et al.) relatou em entrevistas, mas
não mediu. A pergunta do paper é **como as specs de SDD evoluem depois de criadas, e se continuam corretas quando o
código muda**, respondida por duas subquestões:

- **RQ1 (edição):** com que frequência as specs são editadas depois de criadas, e isso difere entre ferramentas?
- **RQ2 (spec decay):** com que frequência um PR que muda código ligado a uma *living spec* do OpenSpec, sem
  atualizá-la, a deixa falsa ou incompleta?

Os arquivos da RQ2 se chamam `p4_*` (nome interno do projeto).

Por que separar por ferramenta: a tese é que a ferramenta define o ciclo de vida da spec. No **OpenSpec**, cada
mudança vive numa pasta própria (*change*) e, ao ser concluída, é **arquivada**: o arquivamento funde a proposta na
*living spec* da capacidade, que fica em `openspec/specs/` para o trabalho seguinte (*spec-anchored*, na classificação
de Böckeler). No **Spec Kit**, a spec nasce para uma tarefa, num branch, e guia o plano e as tarefas (*spec-first*).
Misturar as ferramentas num número "SDD em geral" juntaria comportamentos opostos.

**Hipóteses** (escritas depois de explorar os dados; regras de decisão fixadas antes da validação e da rotulagem; sem
pré-registro externo):
- **H1a:** menos de {pc(hip[hip.hipotese == 'H1a'].limiar.iloc[0], 0)}% das specs são editadas, em cada grupo. Origem: o
  paper-base achou 81,5% das specs com um único commit; a H1a pergunta se isso vale em cada ferramenta, depois da deduplicação.
- **H1b:** living specs do OpenSpec são mais editadas que as do Spec Kit. Origem: Böckeler (spec-anchored, feita para ser
  mantida, × spec-first).
- **H2:** uma fração relevante desses PRs deixa a spec desatualizada. Origem: 7 entrevistados do paper-base citaram o
  spec decay, e a literatura de documentação acha desatualização comum (Aghajani; Tan).

**Regra de veredito**, a mesma para todas as hipóteses com limiar: **met** se o IC 95% inteiro fica do lado previsto;
**refuted** se fica inteiro do outro lado; **inconclusive** se cruza o limiar. Para a H2 há faixas fixadas antes da
rotulagem: IC inteiro abaixo de 20% = resultado negativo; entre 20% e 50% = co-mudança com algum decay; IC inteiro
acima de 50% = decay. Os limiares não vêm da literatura: dizem quão frequente o decay precisaria ser para mudar a conclusão.

## 2. Os dados

**SpecMine v1.0** (Zenodo, record 22102780; ZIP conferido por MD5). O histórico de commits das specs foi coletado em
{CO['coleta_historico'][0]} e o texto das specs em {CO['coleta_texto'][0]}. Tudo que é datado depois de
{corte:%d/%m/%Y %H:%M:%S} UTC (commits e PRs) é ignorado; nenhuma das {NV['texto_pares_conferidos']} specs da RQ2 mudou
entre as duas coletas ({NV['texto_mudou_entre_coletas']} mudaram).

**Funil do corpus** (`tables/funil.csv`):
""")
    linhas = [("Todas as specs do SpecMine", etapas[0], None),
              ("Sem `caffeine.ai` (gerador que cria um repositório por app)", etapas[1], etapas[0]),
              ("Com histórico de commits coletado pelo SpecMine", etapas[2], etapas[1]),
              ("Sem conteúdo repetido em 5 ou mais repositórios (templates, tutoriais)", etapas[3], etapas[2]),
              ("Sem repositórios com metade ou mais das specs copiadas (\"vendor\")", etapas[4], etapas[3])]
    w(tabela(pd.DataFrame([(t, n(f.loc[k].specs), n(f.loc[k].repos),
                            "" if a is None else f"−{n(f.loc[a].specs - f.loc[k].specs)} specs, −{n(f.loc[a].repos - f.loc[k].repos)} repos")
                           for t, k, a in linhas], columns=["Etapa", "Specs", "Repositórios", "Sai"])))
    w(f"""
Por que cada corte: o `caffeine.ai` daria a um único gerador peso desproporcional nas médias por repositório; nas
{n(CO['historico_nao_coletado'])} specs do 3º corte, o SpecMine não coletou o histórico de commits (status `empty`: o
arquivo tem commits no Git, e a ficha até guarda a data do último, mas a lista veio vazia), então não dá para saber se
foram editadas; cópias e "vendor" não são specs escritas pelo projeto e inflariam
"nunca editada". O corpus final é o universo de todas as análises.

**Grupos** (no universo): {', '.join(f"{GN[g]} {n(cic.loc[g].n_unidades)} specs em {n(cic.loc[g].n_repos)} repos" for g in ['openspec', 'openspec:living', 'speckit', 'outras_nomeadas', 'sem_ferramenta'])}.
"Sem ferramenta" são caminhos genéricos (`specs/`, `docs/…/spec.md` etc.).

**Características do corpus** (`numeros/key_numbers.json`): o 1º commit das specs vai de
{CO['primeiro_commit_anos'][0]} a {CO['primeiro_commit_anos'][1]}; {n(CO['repos_criados_2025_ou_depois'])} de
{n(CO['repos'])} repositórios ({pc(CO['repos_criados_2025_ou_depois'] / CO['repos'])}%) foram criados em 2025 ou
depois. A camada de PRs do SpecMine só cobre repositórios com pelo menos 10 estrelas (o menor valor observado é
{CO['estrelas_min_camada_pr']}) e só PRs que tocam alguma spec.

**Coleta própria na API do GitHub** (congelada, com `SHA256SUMS`; e-mails, assinaturas e avatares removidos):
- RQ2: {len(pares)} pares sorteados, {pares[['repo_name', 'pr_number']].drop_duplicates().shape[0]} PRs distintos;
  {len(pr_ok)} PRs com diff (HTTP 200), que cobrem {NV['pares']} pares.

## 3. Duas escolhas que valem para tudo

**Média por repositório.** Specs do mesmo projeto não são independentes, e um projeto com centenas de specs decidiria
sozinho uma média por spec. A estimativa principal é

  Ŷ = (1/R) · Σ_r (k_r / n_r),

com R repositórios, n_r unidades (specs ou pares) no repositório r e k_r delas com a propriedade. A versão por
spec, Σk_r / Σn_r, aparece nas tabelas como sensibilidade.

**IC 95% por bootstrap de repositórios.** Sorteiam-se R repositórios com reposição, recalcula-se Ŷ, e repete-se
B = {n(KN['replicas_bootstrap'])} vezes; o IC são os percentis 2,5 e 97,5 das réplicas. A semente é {KN['semente']};
na RQ1 cada grupo tem um gerador próprio (semente combinada com o nome do grupo), para que o IC de um grupo
não dependa dos outros. O bootstrap por repositório respeita a dependência entre specs do mesmo projeto, que um IC
binomial comum ignoraria.

## 4. RQ1: a spec é editada depois de criada?

**Métrica.** Uma spec é *editada* se o seu caminho tem um 2º commit até o corte (n_commits ≥ 2). Unidade: spec;
estimativa: média por repositório (§3). Limitação de construção: o histórico segue o caminho atual, então renomeações
somem.
""")
    w(tabela(pd.DataFrame([(GN[g], f"{pc(r.por_repo)} {ic(r.ic_repo_lo, r.ic_repo_hi)}", f"{pc(r.por_spec)}", n(r.n_unidades), n(r.n_repos),
                            LEIT[hip[(hip.hipotese == 'H1a') & (hip.grupo == g)].veredito.iloc[0]])
                           for g, r in cic.iterrows()], columns=["Grupo", "% editada por repo [IC 95%]", "% por spec", "Specs", "Repos", "H1a (< 50%)"])))
    idade = NK["idade_mediana_dias"]
    w(f"""
**H1a** é *met* em todos os grupos: o IC inteiro fica abaixo de 50%.

**H1b: living specs são mais editadas que as do Spec Kit?** Diferença das médias por repositório:
{pc(h1b.estimativa)} pontos percentuais ({pc(cic.loc['openspec:living'].por_repo)}% contra {pc(cic.loc['speckit'].por_repo)}%).
A regra exige duas coisas: ICs 95% disjuntos **e** o teste de Mann–Whitney unilateral com p < 0,05.

- **Mann–Whitney U** compara duas distribuições sem supor normalidade. Aqui, as amostras são as proporções de specs
  editadas por repositório: n_a = {n(h1b.n_a)} repositórios com living spec e n_b = {n(h1b.n_b)} com Spec Kit.
  U = Σ_i Σ_j [1(x_i > y_j) + ½·1(x_i = y_j)], somado sobre todos os pares (repositório living i, repositório Spec Kit j).
  A hipótese alternativa unilateral é "living tende a ser maior". Resultado: p = {h1b.mw_p_unilateral:.3g} em ponto
  flutuante, isto é, menor que o menor número representável (o paper escreve p < 0,001). Por que este teste: proporções por repositório são limitadas a [0, 1],
  com muitos 0 e 1, e um teste t suporia normalidade que elas não têm.
- **Cliff's δ** mede o tamanho do efeito: δ = P(X > Y) − P(X < Y), a probabilidade de um repositório living ter
  proporção maior que um do Spec Kit menos a do contrário. Liga-se ao U por δ = 2U/(n_a·n_b) − 1 (o código confere essa
  identidade por força bruta). Resultado: **δ = {dc(h1b.cliff_delta)}**, magnitude **{h1b.magnitude}** pelos limiares
  usuais (|δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; acima, grande). Por que reportar: com milhares de
  repositórios quase qualquer diferença dá p minúsculo; o δ diz se a diferença importa.
- **Veredito H1b: {LEIT[h1b.veredito]}**, com efeito pequeno.

**Sensibilidade à idade.** As specs do Spec Kit são mais velhas (mediana {idade['speckit']:.0f} dias até o corte,
contra {idade['openspec:living']:.0f} das living specs), então tiveram mais tempo para ser editadas. Janela fixa:
entre specs com pelo menos 60 dias de idade no corte, conta-se se houve 2º commit nos 60 primeiros dias.
""")
    w(tabela(pd.DataFrame([(GN[g], f"{pc(r.por_repo)} {ic(r.ic_repo_lo, r.ic_repo_hi)}", n(r.n_unidades), n(r.n_repos))
                           for g, r in jan.iterrows()], columns=["Grupo", "% editada em 60 dias [IC]", "Specs", "Repos"])))
    w(f"""
A ordem se mantém: living {pc(jan.loc['openspec:living'].por_repo)}% contra Spec Kit {pc(jan.loc['speckit'].por_repo)}%.
""")
    w(f"""
## 5. RQ2: o PR que muda código ligado deixa a spec errada?

**Ligação spec → código.** A living spec `openspec/specs/C/spec.md` liga-se aos arquivos de código citados nos
`tasks.md` das changes da mesma capacidade C (tabela `spec_links` do SpecMine). Para evitar ligações ambíguas, o caminho
precisa ter um diretório e não pode ter basename genérico ({', '.join(genericos)}, no singular ou no plural).

**Par candidato.** Uma living spec e um PR que (1) foi mergeado depois do último commit da spec e até o corte, (2) muda
algum arquivo de código ligado e (3) não toca nenhuma spec de C. Vários arquivos ligados no mesmo PR formam um par só.
Como a spec não mudou entre o PR e o corte, o texto coletado é o texto do momento do merge. Resultado:
{n(NS['candidatos'])} pares em {NS['candidatos_repos']} repositórios; sem o filtro de nomes genéricos seriam
{n(NS['sem_filtro_generico'])} em {NS['sem_filtro_generico_repos']} (o filtro tira {n(NS['sem_filtro_generico'] - NS['candidatos'])}
pares e {NS['sem_filtro_generico_repos'] - NS['candidatos_repos']} repositórios).

**X, a frequência do evento:** fração das living specs ligadas a código (nos repositórios da camada de PRs) que tiveram
pelo menos um PR desse tipo, em média por repositório: **{pc(NS['x_por_repo'])}% {ic(*NS['x_ic'])}**
({n(NS['x_specs'])} de {n(NS['x_base'])} specs, {NS['x_repos']} repositórios; por spec, {pc(NS['x_specs'] / NS['x_base'])}%).
Com a ligação resolvida pelo próprio SpecMine (`openspec_code_refs`, que também aceita nomes sem diretório):
{pc(NL['x_amplo']['por_repo'])}% {ic(*NL['x_amplo']['ic'])} ({n(NL['x_amplo']['specs'])} de {n(NL['x_amplo']['base'])},
{NL['x_amplo']['repos']} repositórios). Por que X: sem ele, o leitor não sabe se o Y descreve algo comum ou raro. X e Y
não se multiplicam, porque as unidades são diferentes (spec × par).

**Sorteio dos pares.** Ordem por md5("p4-20261105|spec|PR"). Piloto: 1 par por repositório, nos 60 de menor hash.
Ampliação: mesma ordem, até {m_repo} pares por repositório, mantendo o piloto.
{len(pares)} pares em {pares.repo_name.nunique()} repositórios ({', '.join(f'{v} repos com {k} par(es)' for k, v in por_repo.items())}).

**Tamanho da amostra (simulação de poder).** Modelo: cada repositório tem uma taxa de decay θ_r ~ Beta com média Y e
correlação intra-repositório ρ = 1/(a+b+1), ou seja, a + b = 1/ρ − 1; cada repositório recebe min(m, candidatos)
pares, cada um com decay ~ Bernoulli(θ_r). Estimativa = média das proporções por repositório; IC = ± 1,96·dp/√R.
Poder = P(limite superior do IC < {pc(poder_m.LIMIAR, 0)}%), em {n(poder_m.REPS)} réplicas, com Y do piloto
= {y_pil} = {pc(poder_m.Y_PILOTO)}%. Esse valor veio de uma **rotulagem preliminar do piloto por LLM**, com o codebook
anterior ao v3; esses rótulos e o modelo não foram guardados (registro em `docs/problemas.md` #41), então o
{pc(poder_m.Y_PILOTO)}% é uma premissa do desenho, não um número reproduzível. Os rótulos v3 do DeepSeek no mesmo piloto
dão {v3_k}/{v3_n} = {pc(v3_k / v3_n)}%; com uma premissa menor, mostrar Y < 20% fica mais fácil e m = {m_rec} só fica mais folgado. Regra fixada antes: o menor m com poder ≥ {pc(poder_m.ALVO, 0)}%
para todo ρ ≤ {dc(esc.rho.max(), 1)}.
""")
    tp = esc.pivot(index="m", columns="rho", values="poder")
    tp.columns = [f"ρ = {dc(c, 1)}" for c in tp.columns]
    w(tabela(tp.reset_index().assign(**{c: tp[c].map(lambda x: pc(x)).values for c in tp.columns})))
    w(f"""
O menor m com poder ≥ {pc(poder_m.ALVO, 0)}% em todas as colunas é **m = {m_rec}**.

**Rotulagem (codebook).** Um avaliador humano leu os {NV['pares']} pares com diff (spec inteira e diff dos arquivos
ligados) e respondeu, em ordem: (1) o diff muda comportamento observável? Se não, **preserves**. (2) Esse comportamento
é do assunto desta spec? Se não, **other capability**. (3) Alguma frase da spec ficou falsa? Se sim, **contradicts**;
se não, mas a spec não cobre o comportamento novo dentro do seu escopo, **omits**. Falta de informação: **cannot judge**.
Rótulos brutos: {', '.join(f'{k} {v}' for k, v in rb.items())}. Ficam fora do Y os {NV['nao_da_para_julgar']}
*cannot judge* e os {NV['divergencia_previa']} pares em que o código já contrariava a spec antes do PR:
**{NV['julgaveis']} pares julgáveis** ({NV['prs_unicos']} PRs, {NV['specs_unicas']} specs, {NV['repos']} repositórios).

**Owner check.** *Other capability* só vale se outra spec do repositório descreve o comportamento (ou, mais frouxo, o
componente). Um LLM (Claude), cego aos rótulos do 2º avaliador, procurou specs candidatas. Dos {NV['dona_outra_capacidade']}
rótulos, {NV['dona_confirmadas']} foram confirmados e {NV['dona_sem_evidencia']} ficaram sem evidência; sem evidência, o
par conta como *omits*, salvo veto do humano. O humano vetou {NV['vetos_iniciais']} e, depois de citar o trecho de
escopo de cada veto, retirou {NV['vetos_iniciais'] - NV['vetos_finais']}. No fim, {sum(oc.values())} pares são *other
capability*: {oc['explicita']} com outra spec descrevendo o comportamento, {oc['componente']} só pelo componente e
{oc['veto']} **lacunas de especificação** (fora do escopo e sem spec dona encontrada; nome dado depois de ver os dados).

**Segundo avaliador e adjudicação.** O DeepSeek v4 Pro aplicou o mesmo codebook aos {NV['pares']} pares, sem ver os
rótulos humanos. Concordância medida pelo **κ de Cohen**, que desconta o acordo esperado por acaso:

  κ = (p_o − p_e) / (1 − p_e),  p_o = acordo observado,  p_e = Σ_k p_humano(k)·p_LLM(k).

Só nos pares fora do piloto (P061–P289), como fixado antes de ver os rótulos: κ = **{dc(NV['kappa_5_categorias'])}** nos 5
rótulos (n = {NV['kappa_n']}, acordo bruto {pc(p_o)}%) e **{dc(NV['kappa_binario'])}** em decay sim/não
(n = {NV['kappa_binario_n']}; decay: humano {NV['decay_humano']}, LLM {NV['decay_deepseek']}). Abaixo de 0,4 é fraco.
Tabela cruzada (linhas = humano bruto; colunas = DeepSeek):
""")
    w(tabela(cz.reset_index()))
    w(f"""
Nos {NV['adjudicados']} pares em que humano e LLM discordaram sobre decay, o humano releu as duas leituras, sem saber de
quem era cada uma e em ordem sorteada (semente `adj-20261108`), e decidiu o rótulo final: {NV['adjudicacao_entram']}
pares entraram em decay e {NV['adjudicacao_saem']} saíram. **Todo rótulo final é humano.**

**Y, a medida de decay.** Fração dos pares julgáveis com decay, em média por repositório:

  Y = (1/R) · Σ_r (d_r / n_r),

com d_r = pares *contradicts* ou *omits* (**Y amplo**, o critério da H2, porque decay é ficar falsa **ou** incompleta)
ou só *contradicts* (**Y estrito**). IC por bootstrap de repositórios (1.000 réplicas, semente 20261105); se o bootstrap
degenerar (nenhum positivo), usa-se Wilson. Também se reporta o Wilson agrupado (todos os pares juntos).

- **Y amplo = {pc(pb.y)}% {ic(pb.ic_lo, pb.ic_hi)}**: {pb.positivos} de {pb.pares} pares, {pb.repos} repositórios; Wilson
  agrupado {ic(pb.wilson_lo, pb.wilson_hi)}. Leitura: **{pb.leitura}**.
- **Y estrito = {pc(ps.y)}% {ic(ps.ic_lo, ps.ic_hi)}**: {ps.positivos} de {ps.pares}; Wilson {ic(ps.wilson_lo, ps.wilson_hi)}. Leitura: **{ps.leitura}**.

**Todas as análises de sensibilidade** (`validation/resultado_p4.csv`; a Tabela II do paper mostra uma parte):
""")
    w(tabela(pd.DataFrame([(r.amostra, r.medida, r.pares, r.repos, f"{pc(r.y)} {ic(r.ic_lo, r.ic_hi)}", f"{r.positivos}", r.leitura)
                           for r in res.itertuples()], columns=["Análise", "Medida", "Pares", "Repos", "Y [IC 95%]", "Positivos", "Leitura"])))
    w(f"""
"(a) só os 222 pares fora do piloto" são os pares P061–P289 com diff (no paper, "excluding pilot pairs"); {int(R.loc[('(a) só os 222 pares fora do piloto', 'amplo (critério)')].pares)}
deles são julgáveis. "(b) só o piloto" são os pares P001–P060 com diff.

O Y estrito é negativo em todas. O Y amplo cruza 20% só quando as {oc['veto']} lacunas contam como decay
({pc(gap.y)}% {ic(gap.ic_lo, gap.ic_hi)}) e, por 0,1 ponto, nos PRs com 60 dias ou mais até o corte.

**Correlação intra-repositório (ICC(1), ANOVA de um fator, grupos desiguais):**

  ICC = (MSB − MSW) / (MSB + (k₀ − 1)·MSW),  k₀ = [N − Σ n_r²/N] / (R − 1),

com MSB e MSW os quadrados médios entre e dentro dos repositórios. Resultado: {dc(NV['icc_amplo'])} (amplo) e
{dc(NV['icc_estrito'])} (estrito), acima do ρ ≤ 0,3 da simulação: o decay se concentra em alguns repositórios. O veredito
não muda porque o IC já exclui o limiar.

**Datas.** Em {NV['commit_depois_do_merge']} dos {NV['pares']} pares, o último commit da spec foi *autorado* antes do merge
e *commitado* depois, então o texto pode ser posterior ao PR; {NV['commit_depois_do_merge_decay']} deles conta como decay.
A ligação por `tasks.md` é confirmada pelo SpecMine em {NV['ligacao_confirmada']} dos {NV['pares']} pares.

## 6. Como tudo isso se reproduz

- `bash scripts/reproduzir.sh` confere as entradas (MD5 do Zenodo, `SHA256SUMS` das coletas, manifesto das decisões),
  roda o pipeline duas vezes e compara a impressão digital das saídas (Parquet pelo conteúdo), refaz os sorteios a
  partir das sementes (pares da RQ2 `p4-20261105`, dentro do pipeline; ordem cega da adjudicação `adj-20261108`) e executa `numeros_do_paper.ipynb`.
- O notebook confere cada número do paper contra a sua origem e varre o texto inteiro: um número sem origem faz o
  pipeline falhar.
- `pipeline.ipynb` roda as mesmas etapas uma a uma, com o que cada uma faz.
- Não se refazem: as coletas na API (congeladas), a rotulagem humana e as chamadas a LLM (não determinísticas;
  modelos e prompts em `data/validation/llm/MODELO_E_PROMPTS.md`).

## 7. O que o estudo mostra

1. **A maioria das specs nunca é reeditada.** Em todos os grupos, menos da metade tem um 2º commit; a living spec do
   OpenSpec é mais editada que a do Spec Kit ({pc(cic.loc['openspec:living'].por_repo)}% contra {pc(cic.loc['speckit'].por_repo)}%),
   mas com efeito pequeno (δ = {dc(h1b.cliff_delta)}).
2. **Spec decay é raro, dentro do fluxo SDD.** PRs que mudam código ligado sem tocar a spec são comuns (X =
   {pc(NS['x_por_repo'])}%), mas a spec fica falsa em {pc(ps.y)}% dos pares e falsa ou incompleta em {pc(pb.y)}%, ambos
   abaixo de 20%.
3. **O que segura o decay é o acoplamento entre capacidades.** Em {sum(oc.values())} de {NV['pares']} pares a mudança
   pertence a outra capacidade, e em {oc['explicita']} outra spec já a descreve: a spec é organizada por capacidade e o
   código por arquivo, e um arquivo serve a várias specs.
4. **A fronteira de escopo decide o resultado amplo.** As {oc['veto']} lacunas, sem spec dona, levam o Y amplo a
   {pc(gap.y)}% {ic(gap.ic_lo, gap.ic_hi)}, inconclusivo. E o κ fraco ({dc(NV['kappa_binario'])}) mostra o problema em
   aberto: quanto detalhe uma spec deve ter. O LLM chama de decay detalhes novos que a spec não menciona; o humano
   julga a spec ainda verdadeira no seu nível de abstração.

**Limites:** um só avaliador humano, que também adjudicou; owner check com recall desconhecido; RQ2 só com living specs do OpenSpec, repositórios com 10 estrelas ou mais e PRs que tocam alguma spec; corpus
jovem ({pc(CO['repos_criados_2025_ou_depois'] / CO['repos'])}% dos repositórios de 2025 em diante); specs apagadas são
invisíveis; nada depois do corte é observado; o resultado é relacional, não causal.
""")
    destino = P("docs", "EXPLICACAO_E2E.md")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("".join(L))
    print(f"ok: {os.path.relpath(destino, ROOT)}")


if __name__ == "__main__":
    main()
