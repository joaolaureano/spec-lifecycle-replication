# A pesquisa de ponta a ponta: o que foi feito, como e com que resultado

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
- **H1a:** menos de 50% das specs são editadas, em cada grupo. Origem: o
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
2026-07-11 e o texto das specs em 2026-07-12. Tudo que é datado depois de
11/07/2026 23:59:59 UTC (commits e PRs) é ignorado; nenhuma das 280 specs da RQ2 mudou
entre as duas coletas (0 mudaram).

**Funil do corpus** (`tables/funil.csv`):

| Etapa | Specs | Repositórios | Sai |
|---|---|---|---|
| Todas as specs do SpecMine | 470.795 | 73.031 |  |
| Sem `caffeine.ai` (gerador que cria um repositório por app) | 456.533 | 59.282 | −14.262 specs, −13.749 repos |
| Com histórico de commits coletado pelo SpecMine | 455.060 | 59.095 | −1.473 specs, −187 repos |
| Sem conteúdo repetido em 5 ou mais repositórios (templates, tutoriais) | 448.504 | 57.668 | −6.556 specs, −1.427 repos |
| Sem repositórios com metade ou mais das specs copiadas ("vendor") | 447.795 | 57.435 | −709 specs, −233 repos |

Por que cada corte: o `caffeine.ai` daria a um único gerador peso desproporcional nas médias por repositório; nas
1.473 specs do 3º corte, o SpecMine não coletou o histórico de commits (status `empty`: o
arquivo tem commits no Git, e a ficha até guarda a data do último, mas a lista veio vazia), então não dá para saber se
foram editadas; cópias e "vendor" não são specs escritas pelo projeto e inflariam
"nunca editada". O corpus final é o universo de todas as análises.

**Grupos** (no universo): OpenSpec (todas as specs) 271.567 specs em 8.857 repos, OpenSpec living 72.499 specs em 6.063 repos, Spec Kit 53.633 specs em 10.474 repos, Outras ferramentas 18.093 specs em 2.781 repos, Sem ferramenta 104.502 specs em 36.891 repos.
"Sem ferramenta" são caminhos genéricos (`specs/`, `docs/…/spec.md` etc.).

**Características do corpus** (`numeros/key_numbers.json`): o 1º commit das specs vai de
2024 a 2026; 53.188 de
57.435 repositórios (92,6%) foram criados em 2025 ou
depois. A camada de PRs do SpecMine só cobre repositórios com pelo menos 10 estrelas (o menor valor observado é
10) e só PRs que tocam alguma spec.

**Coleta própria na API do GitHub** (congelada, com `SHA256SUMS`; e-mails, assinaturas e avatares removidos):
- RQ2: 289 pares sorteados, 207 PRs distintos;
  202 PRs com diff (HTTP 200), que cobrem 280 pares.

## 3. Duas escolhas que valem para tudo

**Média por repositório.** Specs do mesmo projeto não são independentes, e um projeto com centenas de specs decidiria
sozinho uma média por spec. A estimativa principal é

  Ŷ = (1/R) · Σ_r (k_r / n_r),

com R repositórios, n_r unidades (specs ou pares) no repositório r e k_r delas com a propriedade. A versão por
spec, Σk_r / Σn_r, aparece nas tabelas como sensibilidade.

**IC 95% por bootstrap de repositórios.** Sorteiam-se R repositórios com reposição, recalcula-se Ŷ, e repete-se
B = 1.000 vezes; o IC são os percentis 2,5 e 97,5 das réplicas. A semente é 20261105;
na RQ1 cada grupo tem um gerador próprio (semente combinada com o nome do grupo), para que o IC de um grupo
não dependa dos outros. O bootstrap por repositório respeita a dependência entre specs do mesmo projeto, que um IC
binomial comum ignoraria.

## 4. RQ1: a spec é editada depois de criada?

**Métrica.** Uma spec é *editada* se o seu caminho tem um 2º commit até o corte (n_commits ≥ 2). Unidade: spec;
estimativa: média por repositório (§3). Limitação de construção: o histórico segue o caminho atual, então renomeações
somem.

| Grupo | % editada por repo [IC 95%] | % por spec | Specs | Repos | H1a (< 50%) |
|---|---|---|---|---|---|
| OpenSpec (todas as specs) | 10,8 [10,4–11,2] | 13,6 | 271.567 | 8.857 | met |
| Outras ferramentas | 17,8 [16,5–19,1] | 19,9 | 18.093 | 2.781 | met |
| Sem ferramenta | 40,0 [39,6–40,5] | 30,3 | 104.502 | 36.891 | met |
| Spec Kit | 22,9 [22,2–23,5] | 21,8 | 53.633 | 10.474 | met |
| OpenSpec living | 28,4 [27,5–29,2] | 37,3 | 72.499 | 6.063 | met |

**H1a** é *met* em todos os grupos: o IC inteiro fica abaixo de 50%.

**H1b: living specs são mais editadas que as do Spec Kit?** Diferença das médias por repositório:
5,5 pontos percentuais (28,4% contra 22,9%).
A regra exige duas coisas: ICs 95% disjuntos **e** o teste de Mann–Whitney unilateral com p < 0,05.

- **Mann–Whitney U** compara duas distribuições sem supor normalidade. Aqui, as amostras são as proporções de specs
  editadas por repositório: n_a = 6.063 repositórios com living spec e n_b = 10.474 com Spec Kit.
  U = Σ_i Σ_j [1(x_i > y_j) + ½·1(x_i = y_j)], somado sobre todos os pares (repositório living i, repositório Spec Kit j).
  A hipótese alternativa unilateral é "living tende a ser maior". Resultado: p = 0 em ponto
  flutuante, isto é, menor que o menor número representável (o paper escreve p < 0,001). Por que este teste: proporções por repositório são limitadas a [0, 1],
  com muitos 0 e 1, e um teste t suporia normalidade que elas não têm.
- **Cliff's δ** mede o tamanho do efeito: δ = P(X > Y) − P(X < Y), a probabilidade de um repositório living ter
  proporção maior que um do Spec Kit menos a do contrário. Liga-se ao U por δ = 2U/(n_a·n_b) − 1 (o código confere essa
  identidade por força bruta). Resultado: **δ = 0,17**, magnitude **small** pelos limiares
  usuais (|δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; acima, grande). Por que reportar: com milhares de
  repositórios quase qualquer diferença dá p minúsculo; o δ diz se a diferença importa.
- **Veredito H1b: met**, com efeito pequeno.

**Sensibilidade à idade.** As specs do Spec Kit são mais velhas (mediana 101 dias até o corte,
contra 69 das living specs), então tiveram mais tempo para ser editadas. Janela fixa:
entre specs com pelo menos 60 dias de idade no corte, conta-se se houve 2º commit nos 60 primeiros dias.

| Grupo | % editada em 60 dias [IC] | Specs | Repos |
|---|---|---|---|
| OpenSpec (todas as specs) | 10,8 [10,2–11,2] | 147.250 | 5.675 |
| Outras ferramentas | 17,2 [15,7–18,6] | 11.940 | 2.198 |
| Sem ferramenta | 38,1 [37,5–38,6] | 64.127 | 26.251 |
| Spec Kit | 22,7 [21,9–23,6] | 37.160 | 8.445 |
| OpenSpec living | 28,9 [27,8–30,0] | 40.182 | 3.761 |

A ordem se mantém: living 28,9% contra Spec Kit 22,7%.

## 5. RQ2: o PR que muda código ligado deixa a spec errada?

**Ligação spec → código.** A living spec `openspec/specs/C/spec.md` liga-se aos arquivos de código citados nos
`tasks.md` das changes da mesma capacidade C (tabela `spec_links` do SpecMine). Para evitar ligações ambíguas, o caminho
precisa ter um diretório e não pode ter basename genérico (index, main, app, utils, helpers, types, constants, config, no singular ou no plural).

**Par candidato.** Uma living spec e um PR que (1) foi mergeado depois do último commit da spec e até o corte, (2) muda
algum arquivo de código ligado e (3) não toca nenhuma spec de C. Vários arquivos ligados no mesmo PR formam um par só.
Como a spec não mudou entre o PR e o corte, o texto coletado é o texto do momento do merge. Resultado:
13.028 pares em 108 repositórios; sem o filtro de nomes genéricos seriam
14.735 em 111 (o filtro tira 1.707
pares e 3 repositórios).

**X, a frequência do evento:** fração das living specs ligadas a código (nos repositórios da camada de PRs) que tiveram
pelo menos um PR desse tipo, em média por repositório: **28,3% [24,0–32,7]**
(1.785 de 3.995 specs, 190 repositórios; por spec, 44,7%).
Com a ligação resolvida pelo próprio SpecMine (`openspec_code_refs`, que também aceita nomes sem diretório):
36,5% [31,9–41,3] (2.474 de 4.456,
202 repositórios). Por que X: sem ele, o leitor não sabe se o Y descreve algo comum ou raro. X e Y
não se multiplicam, porque as unidades são diferentes (spec × par).

**Sorteio dos pares.** Ordem por md5("p4-20261105|spec|PR"). Piloto: 1 par por repositório, nos 60 de menor hash.
Ampliação: mesma ordem, até 3 pares por repositório, mantendo o piloto.
289 pares em 108 repositórios (11 repos com 1 par(es), 13 repos com 2 par(es), 84 repos com 3 par(es)).

**Tamanho da amostra (simulação de poder).** Modelo: cada repositório tem uma taxa de decay θ_r ~ Beta com média Y e
correlação intra-repositório ρ = 1/(a+b+1), ou seja, a + b = 1/ρ − 1; cada repositório recebe min(m, candidatos)
pares, cada um com decay ~ Bernoulli(θ_r). Estimativa = média das proporções por repositório; IC = ± 1,96·dp/√R.
Poder = P(limite superior do IC < 20%), em 2.000 réplicas, com Y do piloto
= 7/56 = 12,5%. Esse valor veio de uma **rotulagem preliminar do piloto por LLM**, com o codebook
anterior ao v3; esses rótulos e o modelo não foram guardados (registro em `docs/problemas.md` #41), então o
12,5% é uma premissa do desenho, não um número reproduzível. Os rótulos v3 do DeepSeek no mesmo piloto
dão 5/56 = 8,9%; com uma premissa menor, mostrar Y < 20% fica mais fácil e m = 3 só fica mais folgado. Regra fixada antes: o menor m com poder ≥ 80%
para todo ρ ≤ 0,3.

| m | ρ = 0,0 | ρ = 0,1 | ρ = 0,2 | ρ = 0,3 |
|---|---|---|---|---|
| 1 | 63,9 | 61,4 | 63,5 | 60,5 |
| 2 | 83,9 | 82,5 | 79,7 | 77,2 |
| 3 | 91,6 | 89,9 | 86,5 | 82,4 |
| 4 | 94,8 | 91,8 | 87,6 | 84,5 |
| 5 | 94,7 | 93,1 | 89,5 | 85,6 |
| 6 | 97,2 | 93,9 | 91,3 | 86,3 |

O menor m com poder ≥ 80% em todas as colunas é **m = 3**.

**Rotulagem (codebook).** Um avaliador humano leu os 280 pares com diff (spec inteira e diff dos arquivos
ligados) e respondeu, em ordem: (1) o diff muda comportamento observável? Se não, **preserves**. (2) Esse comportamento
é do assunto desta spec? Se não, **other capability**. (3) Alguma frase da spec ficou falsa? Se sim, **contradicts**;
se não, mas a spec não cobre o comportamento novo dentro do seu escopo, **omits**. Falta de informação: **cannot judge**.
Rótulos brutos: outra_capacidade 128, preserva 125, omite 11, contradiz 9, nao_da_para_julgar 7. Ficam fora do Y os 7
*cannot judge* e os 3 pares em que o código já contrariava a spec antes do PR:
**270 pares julgáveis** (198 PRs, 239 specs, 105 repositórios).

**Owner check.** *Other capability* só vale se outra spec do repositório descreve o comportamento (ou, mais frouxo, o
componente). Um LLM (Claude), cego aos rótulos do 2º avaliador, procurou specs candidatas. Dos 128
rótulos, 115 foram confirmados e 13 ficaram sem evidência; sem evidência, o
par conta como *omits*, salvo veto do humano. O humano vetou 12 e, depois de citar o trecho de
escopo de cada veto, retirou 1. No fim, 131 pares são *other
capability*: 111 com outra spec descrevendo o comportamento, 9 só pelo componente e
11 **lacunas de especificação** (fora do escopo e sem spec dona encontrada; nome dado depois de ver os dados).

**Segundo avaliador e adjudicação.** O DeepSeek v4 Pro aplicou o mesmo codebook aos 280 pares, sem ver os
rótulos humanos. Concordância medida pelo **κ de Cohen**, que desconta o acordo esperado por acaso:

  κ = (p_o − p_e) / (1 − p_e),  p_o = acordo observado,  p_e = Σ_k p_humano(k)·p_LLM(k).

Só nos pares fora do piloto (P061–P289), como fixado antes de ver os rótulos: κ = **0,33** nos 5
rótulos (n = 222, acordo bruto 58,1%) e **0,23** em decay sim/não
(n = 213; decay: humano 17, LLM 23). Abaixo de 0,4 é fraco.
Tabela cruzada (linhas = humano bruto; colunas = DeepSeek):

| humano_bruto | contradiz | nao_da_para_julgar | omite | outra_capacidade | preserva | total |
|---|---|---|---|---|---|---|
| contradiz | 5 | 0 | 0 | 0 | 2 | 7 |
| nao_da_para_julgar | 0 | 3 | 0 | 1 | 2 | 6 |
| omite | 0 | 1 | 1 | 7 | 2 | 11 |
| outra_capacidade | 2 | 2 | 2 | 77 | 4 | 87 |
| preserva | 6 | 0 | 7 | 55 | 43 | 111 |
| total | 13 | 6 | 10 | 140 | 53 | 222 |

Nos 28 pares em que humano e LLM discordaram sobre decay, o humano releu as duas leituras, sem saber de
quem era cada uma e em ordem sorteada (semente `adj-20261108`), e decidiu o rótulo final: 15
pares entraram em decay e 8 saíram. **Todo rótulo final é humano.**

**Y, a medida de decay.** Fração dos pares julgáveis com decay, em média por repositório:

  Y = (1/R) · Σ_r (d_r / n_r),

com d_r = pares *contradicts* ou *omits* (**Y amplo**, o critério da H2, porque decay é ficar falsa **ou** incompleta)
ou só *contradicts* (**Y estrito**). IC por bootstrap de repositórios (1.000 réplicas, semente 20261105); se o bootstrap
degenerar (nenhum positivo), usa-se Wilson. Também se reporta o Wilson agrupado (todos os pares juntos).

- **Y amplo = 10,6% [5,9–16,0]**: 26 de 270 pares, 105 repositórios; Wilson
  agrupado [6,7–13,7]. Leitura: **resultado negativo**.
- **Y estrito = 5,4% [2,2–9,5]**: 12 de 270; Wilson [2,6–7,6]. Leitura: **resultado negativo**.

**Todas as análises de sensibilidade** (`validation/resultado_p4.csv`; a Tabela II do paper mostra uma parte):

| Análise | Medida | Pares | Repos | Y [IC 95%] | Positivos | Leitura |
|---|---|---|---|---|---|---|
| principal | amplo (critério) | 270 | 105 | 10,6 [5,9–16,0] | 26 | resultado negativo |
| principal | estrito | 270 | 105 | 5,4 [2,2–9,5] | 12 | resultado negativo |
| (a) só os 222 pares fora do piloto | amplo (critério) | 213 | 103 | 10,2 [5,7–15,2] | 22 | resultado negativo |
| (a) só os 222 pares fora do piloto | estrito | 213 | 103 | 4,4 [1,5–7,9] | 9 | resultado negativo |
| (b) só o piloto | amplo (critério) | 57 | 57 | 7,0 [1,8–14,0] | 4 | resultado negativo |
| (b) só o piloto | estrito | 57 | 57 | 5,3 [0,0–12,3] | 3 | resultado negativo |
| (c) sem a revisão de dona | amplo (critério) | 270 | 105 | 6,7 [3,7–10,2] | 17 | resultado negativo |
| (c) sem a revisão de dona | estrito | 270 | 105 | 2,7 [0,8–5,2] | 6 | resultado negativo |
| (d1) não dá para julgar = não decay | amplo (critério) | 277 | 105 | 10,0 [5,4–14,9] | 26 | resultado negativo |
| (d1) não dá para julgar = não decay | estrito | 277 | 105 | 4,9 [1,9–8,4] | 12 | resultado negativo |
| (d2) não dá para julgar = decay | amplo (critério) | 277 | 105 | 12,4 [7,6–18,1] | 33 | resultado negativo |
| (d2) não dá para julgar = decay | estrito | 277 | 105 | 7,3 [3,5–11,7] | 19 | resultado negativo |
| (e) só PRs >= 60 dias antes do corte | amplo (critério) | 119 | 53 | 12,3 [4,7–20,1] | 11 | inconclusivo |
| (e) só PRs >= 60 dias antes do corte | estrito | 119 | 53 | 6,3 [0,0–13,2] | 5 | resultado negativo |
| (f) sem specs com texto em chinês | amplo (critério) | 220 | 89 | 11,8 [6,6–17,6] | 22 | resultado negativo |
| (f) sem specs com texto em chinês | estrito | 220 | 89 | 6,0 [2,2–10,5] | 11 | resultado negativo |
| (h) dona só por componente = omite | amplo (critério) | 270 | 105 | 13,5 [8,7–18,9] | 35 | resultado negativo |
| (h) dona só por componente = omite | estrito | 270 | 105 | 5,4 [2,2–9,5] | 12 | resultado negativo |
| antes da adjudicação | amplo (critério) | 270 | 105 | 7,3 [4,1–10,8] | 19 | resultado negativo |
| antes da adjudicação | estrito | 270 | 105 | 2,7 [0,8–5,2] | 6 | resultado negativo |
| regra de dona sem o veto humano (e sem adjudicação) | amplo (critério) | 270 | 105 | 11,6 [7,6–16,2] | 30 | resultado negativo |
| regra de dona sem o veto humano (e sem adjudicação) | estrito | 270 | 105 | 2,7 [0,8–5,2] | 6 | resultado negativo |
| final sem o veto humano | amplo (critério) | 270 | 105 | 14,9 [9,5–20,8] | 37 | inconclusivo |
| final sem o veto humano | estrito | 270 | 105 | 5,4 [2,2–9,5] | 12 | resultado negativo |
| final sem o veto e dona só por componente = omite | amplo (critério) | 270 | 105 | 17,8 [12,4–24,0] | 46 | inconclusivo |
| final sem o veto e dona só por componente = omite | estrito | 270 | 105 | 5,4 [2,2–9,5] | 12 | resultado negativo |
| divergência prévia contada como rotulada | amplo (critério) | 273 | 105 | 11,3 [6,7–16,5] | 29 | resultado negativo |
| divergência prévia contada como rotulada | estrito | 273 | 105 | 6,0 [2,5–10,2] | 15 | resultado negativo |
| só pares com todos os caminhos confirmados (openspec_code_refs) | amplo (critério) | 269 | 105 | 10,6 [5,9–16,0] | 26 | resultado negativo |
| só pares com todos os caminhos confirmados (openspec_code_refs) | estrito | 269 | 105 | 5,4 [2,2–9,5] | 12 | resultado negativo |
| só pares com caminho de tarefa marcada (openspec_code_refs) | amplo (critério) | 240 | 101 | 11,6 [6,8–17,2] | 24 | resultado negativo |
| só pares com caminho de tarefa marcada (openspec_code_refs) | estrito | 240 | 101 | 6,1 [2,3–10,6] | 11 | resultado negativo |

"(a) só os 222 pares fora do piloto" são os pares P061–P289 com diff (no paper, "excluding pilot pairs"); 213
deles são julgáveis. "(b) só o piloto" são os pares P001–P060 com diff.

O Y estrito é negativo em todas. O Y amplo cruza 20% só quando as 11 lacunas contam como decay
(14,9% [9,5–20,8]) e, por 0,1 ponto, nos PRs com 60 dias ou mais até o corte.

**Correlação intra-repositório (ICC(1), ANOVA de um fator, grupos desiguais):**

  ICC = (MSB − MSW) / (MSB + (k₀ − 1)·MSW),  k₀ = [N − Σ n_r²/N] / (R − 1),

com MSB e MSW os quadrados médios entre e dentro dos repositórios. Resultado: 0,32 (amplo) e
0,43 (estrito), acima do ρ ≤ 0,3 da simulação: o decay se concentra em alguns repositórios. O veredito
não muda porque o IC já exclui o limiar.

**Datas.** Em 2 dos 280 pares, o último commit da spec foi *autorado* antes do merge
e *commitado* depois, então o texto pode ser posterior ao PR; 1 deles conta como decay.
A ligação por `tasks.md` é confirmada pelo SpecMine em 279 dos 280 pares.

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
   OpenSpec é mais editada que a do Spec Kit (28,4% contra 22,9%),
   mas com efeito pequeno (δ = 0,17).
2. **Spec decay é raro, dentro do fluxo SDD.** PRs que mudam código ligado sem tocar a spec são comuns (X =
   28,3%), mas a spec fica falsa em 5,4% dos pares e falsa ou incompleta em 10,6%, ambos
   abaixo de 20%.
3. **O que segura o decay é o acoplamento entre capacidades.** Em 131 de 280 pares a mudança
   pertence a outra capacidade, e em 111 outra spec já a descreve: a spec é organizada por capacidade e o
   código por arquivo, e um arquivo serve a várias specs.
4. **A fronteira de escopo decide o resultado amplo.** As 11 lacunas, sem spec dona, levam o Y amplo a
   14,9% [9,5–20,8], inconclusivo. E o κ fraco (0,23) mostra o problema em
   aberto: quanto detalhe uma spec deve ter. O LLM chama de decay detalhes novos que a spec não menciona; o humano
   julga a spec ainda verdadeira no seu nível de abstração.

**Limites:** um só avaliador humano, que também adjudicou; owner check com recall desconhecido; RQ2 só com living specs do OpenSpec, repositórios com 10 estrelas ou mais e PRs que tocam alguma spec; corpus
jovem (92,6% dos repositórios de 2025 em diante); specs apagadas são
invisíveis; nada depois do corte é observado; o resultado é relacional, não causal.
