# Método — o que foi feito (diário datado)

> **Leia primeiro.** Este documento é um **diário**: as seções §1 e §4 descrevem o piloto e foram superadas pelas datadas (§5b–§5h e §9). O paper tem uma RQ guarda-chuva com RQ1 (edição) e RQ2 (spec decay; arquivos `p4_*`). **Correção (19/nov):** o avaliador **não** viu rótulos de LLM no piloto (o esclarecimento de 10/nov, em §5d, já dizia que o LLM foi só apoio de linguagem); o que distingue o piloto é ter sido rotulado primeiro. Houve tradução automática, só para leitura, das specs em chinês, no piloto e nos pares novos, com rótulo 100% humano.

Cada parágrafo indica a seção do paper a que se destina. Números: `docs/key_numbers_final.json` e `data/derived/tables/`. As limitações principais estão no artigo (Threats to Validity).

## 0. Spec decay: definição e operacionalização (05/nov/2026; antes em `metodo.md` §0)
Base para a RQ2. Cada afirmação traz a fonte; marcado **[texto lido]** quando conferi a passagem no original, **[resumo]** quando só vi resumo/metadados.

### 0.1 O que a literatura diz

| Fonte | Termo | Definição | Situação |
|---|---|---|---|
| **Agarwal et al. 2026** (paper-base, arXiv:2608.25202, Finding 10 e §V-C) | *spec decay* × *implementation drift* | *Implementation drift*: o agente se afasta da spec **ao implementar**. *Spec decay*: "a spec fica desatualizada conforme o código muda" — "se a spec diz que a sessão expira em 30 min e o agente implementa 60, é drift; se uma mudança posterior define 60 como pretendido e a spec ainda diz 30, é decay". Afeta **specs vivas**, sobretudo quando mudanças alteram comportamento que **outras** specs descrevem. Também afirmam (inferência, não medida) que spec com mais detalhe de implementação decai mais cedo, e que **não verificaram** se alguma ferramenta checa spec × código depois da implementação | [texto lido] |
| **Aghajani et al. 2019** (ICSE, *Software Documentation Issues Unveiled*; 878 artefatos minerados, 824 rotulados, 485 sobre conteúdo; **lido no original em 08/nov**, §IV-A, p. 6 da versão do autor, `literatura/artigos/`) | *up-to-dateness* (documentação desatualizada) | "Um documento está desatualizado quando não está em sincronia com outras partes do sistema." Difere de correção e completude porque **a informação estava correta e completa antes de uma mudança ser introduzida**. Up-to-dateness = 39% dos problemas de conteúdo; em 21% deles, a inconsistência é entre o comportamento do sistema e sua descrição, "geralmente disparada por uma mudança no código que exigia mudar a documentação"; inclui documentação de código que não existe mais | [texto lido] |
| **Grabowski 2026** (arXiv:2606.27045, *Spec Growth Engine*; citado pelo paper-base) | *spec-code drift* | "o código evolui, a especificação não, e a divergência fica invisível até ser cara de reparar"; propõe bloquear merges quando spec e código divergem | [resumo] |
| **Böckeler 2025** (martinfowler.com; citada pelo paper-base) | *spec-first*, *spec-anchored*, *spec-as-source* | *spec-first*: a spec é escrita antes e usada na tarefa; *spec-anchored*: "a spec é mantida depois da tarefa, para evolução e manutenção"; *spec-as-source*: só a spec é editada. Considera o Spec Kit *spec-first* (spec por pedido de mudança, não por feature); **não menciona o OpenSpec**, que classificamos como *spec-anchored* pela definição dela e pelo mecanismo da documentação do OpenSpec (09/nov); muitas ferramentas deixam vaga a estratégia de manutenção da spec | [texto lido, via página] |
| **Tan, Wagner, Treude 2024** (EMSE; arXiv:2212.01479) | referência de código desatualizada | "referências a elementos de código que sobrevivem na documentação depois que todas as instâncias no código foram removidas"; >3.000 projetos GitHub; a maioria teve ao menos uma em algum momento da história | [resumo] |
| **Fluri et al. 2007; 2009** (WCRE; Software Quality J.) | co-evolução código–comentário | na maioria dos sistemas estudados, comentários mudam junto com o código relacionado (97% das mudanças de comentário na mesma revisão, em 2007; ~90% em 6 de 8 sistemas, em 2009) | [resumo] |
| **Wen et al. 2019** (ICPC, *A large-scale empirical study on code-comment inconsistencies*, 1.500 projetos Java) | inconsistência código–comentário | precedente de mineração em larga escala de inconsistências corrigidas | [metadados; texto inacessível (403)] |
| **Perry & Wolf 1992** (SIGSOFT SEN) | *architectural erosion* × *drift* | erosão = "violações da arquitetura"; drift = "insensibilidade em relação à arquitetura", que leva a inadaptabilidade e falta de coerência | [texto lido] — precedente conceitual de **dois modos** de divergência (violar × negligenciar), não equivalência direta |
| Literatura cinzenta SDD (blogs de fornecedores, 2025–26) | *spec drift* (às vezes *spec rot*) | uso inconsistente: em geral "spec e código desalinhados porque um mudou sem o outro", misturando os dois sentidos do paper-base | [resumo] — não usar como definição |

### 0.2 Definição adotada
**Spec decay** é a perda de correspondência entre uma spec que **deveria ser mantida** (*spec-anchored*; no OpenSpec, a spec viva de uma capacidade) e o comportamento do sistema, **causada por mudanças posteriores no código que não foram refletidas na spec**.
Fundamentos: o conceito e o nome vêm do paper-base. "Estava correta **e completa** antes de uma mudança" vem de Aghajani et al. (up-to-dateness; conferido no original em 08/nov). **Ressalva:** a up-to-dateness de Aghajani **não tem direção**. Ela inclui casos em que é o código que precisa mudar ("it is the code that needs to be updated to match the documentation"), além de copyright e links velhos. Por isso tomamos dele só o critério temporal: spec decay é a direção código → spec desse problema. A direção contrária é implementation drift. Isso sustenta o `omite`: para Aghajani, documentação que falta para uma feature nova é up-to-dateness, não completeness. a restrição a specs que deveriam ser mantidas vem da distinção *spec-first* × *spec-anchored* de Böckeler.

**Não é spec decay:**
- *Implementation drift* — o código nunca correspondeu à spec (problema na implementação, não depois dela).
- Specs que não foram feitas para durar (*spec-first*): changes arquivadas do OpenSpec (registros) e, segundo Böckeler, specs de feature do Spec Kit. Nelas, não ser atualizada é o desenho, não decay.
- Mudanças de código que não alteram o comportamento descrito (refatoração interna, correção que restaura o comportamento descrito).
- Atualizações feitas pelo próprio fluxo (arquivamento que mescla a change na spec viva) — isso é a spec sendo mantida.

### 0.3 Operacionalização em níveis (do conceito ao observável)
| Nível | O que é | Como medimos | O que sustenta |
|---|---|---|---|
| **N0 — conceito** | a spec correspondia ao sistema no seu assunto. Uma mudança posterior faz uma frase dela ficar falsa (`contradiz`) ou acrescenta comportamento do assunto dela que ela não menciona (`omite`). A spec não é atualizada | não observável em escala (exigiria entender spec e código) | — |
| **N1 — evento candidato** | arquivo de código ligado à capacidade é alterado **depois** da última edição da spec viva, por um PR que **não toca nenhuma spec da capacidade**. Na camada de PRs esse PR sempre toca alguma spec, em geral uma change de **outra** capacidade, então o evento está **dentro** do fluxo de outra capacidade, não "fora do fluxo" | ligação indireta spec viva ← changes da capacidade ← `tasks.md` (estrita); camada de PRs; `spec_rot_viabilidade.py` | condição **necessária**, não suficiente: "mudança no código ligado que não foi refletida" |
| **N2 — confirmação** | o PR do N1 deixou a spec falsa ou incompleta no assunto dela? Livro de códigos v3 (`prompt_llm2_pares.md`): preserva / outra_capacidade / omite / contradiz / nao_da_para_julgar | amostra julgada lendo o diff do PR e o texto da spec (humano = padrão-ouro; LLM às cegas) | **precisão de N1 como indicador de N0** → permite estimar quanto do N1 é decay |

| **N3 — complementar (opcional)** | a spec cita um elemento de código que não existe mais (operacionalização de Tan et al.) | caminhos citados no texto da spec × árvore do repositório | evidência forte e simples, mas só para specs que citam código no texto (~18% das specs OpenSpec) |

**Afirmação máxima que os dados podem sustentar** (refeita em 07/nov): "Em X% das specs vivas (média por repositório; OpenSpec, camada de PRs), um PR alterou o código ligado depois da última atualização da spec sem tocar nenhuma spec da capacidade. Numa amostra lida, em Y% desses pares (média por repositório) a spec ficou falsa ou incompleta no seu assunto (Y estrito: falsa em Y_e%)." **Não multiplicar X·Y:** as unidades diferem (specs × pares). Escopo declarado: OpenSpec, specs vivas, repositórios da camada de PRs (PRs que tocam alguma spec).

### 0.4 Terminologia no paper
Usar **spec decay** (termo do paper-base); citar *spec rot* e *spec drift* como sinônimos correntes, e **não** usar "drift" para este fenômeno, porque o paper-base reserva *drift* para o desvio na implementação.

## 1. Dados (→ Data)
- **SpecMine v1.0** (snapshot de jul/2026), Zenodo record 22102780 (MD5 `86c8fa6249bafd220eafbdf89ca7231f` conferido), 470.795 specs em 73.031 (nosso funil, `funil.csv`; o paper-base diz 73.030) repositórios; texto de todas as specs (`specs.jsonl.gz`).
- **Coleta da RQ2 (05/nov/2026)**: `GET /repos/{owner}/{repo}/pulls/{n}/files` (lista de arquivos com diff) para 60 PRs (`fetch_pr.py`; `data/api_pr_diffs/`): 58 respondidos, nenhum truncado. Na coleta: token só em memória, gravação atômica, manifesto com SHA-256, SHA256SUMS, backup e somente leitura; nenhum e-mail, assinatura ou token nos brutos (conferido por busca).

## 2. Universo de análise e dedup (→ Method: data preparation; Tabela 1)
Script `scripts/analysis/universe.py`. Nada é apagado: cada spec recebe flags, e cada análise usa o universo adequado.
- Excluídos: gerador caffeine (13.749 repos; 14.262 specs); commits posteriores a 2026-07-11 (6 commits, 2 specs); as 1.473 specs cujo histórico de commits o SpecMine não coletou (status `empty`). **Correção (19/nov):** as specs sem texto (2.488) **não** são excluídas; 1.156 delas ficam no universo, porque sem o texto não dá para marcá-las como cópia.
- **Universo de ciclo de vida (`u_ciclo`)** — análises de commits: sem conteúdo copiado em **≥5 repositórios** (682 conteúdos, ~6,6 mil arquivos: tutoriais e templates) e sem **repositórios "vendor"** (≥50% dos arquivos com conteúdo visto em ≥5 repos; 1.660 repos). 447.795 specs, 57.435 repos. Duplicatas dentro do repo permanecem: no OpenSpec, uma change arquivada e a spec viva podem ter o mesmo texto e são arquivos com história própria.
- **Papel corrigido:** 264 specs de change registradas como abertas cujo histórico contém o commit que criou a cópia arquivada de mesmo nome → "arquivada depois do censo" (o censo de arquivos do SpecMine é anterior à coleta do histórico).
- Funil completo: `data/derived/tables/funil.csv`.

## 3. Grupos de ferramenta e medidas (→ Method: measures)
- **Grupos:** OpenSpec; Spec Kit; outras ferramentas nomeadas (Conductor, Trae, Claude Code, …); sem ferramenta (caminhos genéricos: `adhoc_other`, `specs_generic`, `docs_embedded`, `root_bare`, `dot_specs`). Resultados sempre por grupo; no OpenSpec, a spec viva.
- **Ciclo de vida:** spec *editada* = ≥2 commits no caminho. Commit = commit que toca o caminho atual (o histórico não segue mudanças de caminho).

## 4. RQ2 — spec decay (→ Method: spec decay; ver §0)
Script `scripts/analysis/spec_rot_viabilidade.py`.
- **Ligação spec viva ↔ código (indireta, estrita):** spec viva `openspec/specs/<cap>/spec.md` ← specs de changes da mesma capacidade (`openspec/changes/[archive/]<c>/specs/<cap>/spec.md`) ← caminhos de código citados no `tasks.md` dessas changes (`spec_links`, rel = code, provenance = tasks), só caminhos com pasta e sem nomes genéricos (index, main, app, utils, helpers, types, constants, config); o arquivo do PR tem de ser exatamente o caminho citado.
- **Evento candidato (N1):** PR da camada de PRs do SpecMine (repos com ≥10 estrelas, PRs que tocam alguma spec), aceito **depois** do último commit da spec viva, que altera código ligado à capacidade e **não toca nenhuma spec dessa capacidade**. Como a spec viva não foi editada entre o PR e o snapshot, o texto do censo é o texto da época do PR. Nos 58 pares sorteados, 57 PRs tocam alguma spec, 53 envolvem uma change do OpenSpec e 46 criam/alteram a spec viva de **outra** capacidade: o evento é "mudança especificada em outra capacidade que alterou o código desta, sem atualizar a spec desta" (decay entre capacidades), não "mudança fora do fluxo".
- **Corte temporal (10/nov):** o PR também precisa ser aceito até 11/07/2026 23:59:59 UTC, data do snapshot das specs. Um PR aceito em 14/07/2026 gerava 158 pares candidatos posteriores ao snapshot; nenhum entrou na amostra. Com o corte, há 13.028 candidatos em 108 repositórios, e os 289 pares sorteados permanecem iguais. Sem o filtro de nomes genéricos, mas mantendo o corte temporal, haveria 14.735 candidatos em 111 repositórios (mais 1.707 pares).
- **Confirmação (N2):** 60 pares (1 por repo, ordem por hash com semente `p4-20261105`), 58 com resposta da API. Avaliador lê a spec viva e o diff dos arquivos ligados e responde: *sim* (o PR mudou comportamento descrito e a spec ficou com o antigo), *não muda comportamento*, *muda parte não coberta pela spec*, *não dá para julgar*. Y = sim / julgáveis, IC de Wilson. Critério fixado antes: Y ≥ 50% decay; 20–50% co-mudança com parte de decay; < 20% resultado negativo.

## 5. Estimação, pesos e incerteza (→ Method: analysis)
- **Corpus:** proporções = **média por repositório** (cada repositório pesa igual dentro do grupo); a média por spec é reportada como sensibilidade. IC 95% por **bootstrap de repositórios** (1.000 réplicas, percentis, semente `20261105`); variação < 0,1 pp ao trocar a semente.

## 5b. Regras de decisão estatística (fixadas em 05/nov, ANTES de recalcular; base: aula 10 — Análise Quantitativa; aula de Metodologia p.45–48)
Regra geral: um critério de limiar está **satisfeito** quando o IC 95% inteiro está do lado declarado, **não satisfeito** quando está inteiro do outro lado, **inconclusivo** quando cruza o limiar (equivale a testar H₀ "o limiar não é ultrapassado" ao nível 2,5% unilateral). Além da tendência central, reportar **dispersão** por repositório (mediana, p25, p75, % de repos em 0 e em 1) — aula 10 p.7–12.
- **H1a** (cada grupo: openspec, speckit, outras_nomeadas, sem_ferramenta, e openspec:living): H₀ p ≥ 50% de specs editadas (por repo); satisfeito se IC_hi < 50%.
- **H1b** (viva > Spec Kit): IC por repo disjuntos com a viva acima **e** Mann-Whitney unilateral (viva > Spec Kit) nas proporções por repositório, p < 0,05, com **Cliff's δ** (faixas da aula 10 p.20). ~~Sensibilidade: sem os repositórios que estão nos dois grupos~~ **[REMOVIDO em 08/nov]**.
- **Sem testes entre os 4 grupos** (revisto em 05/nov): Kruskal-Wallis/Dunn não respondem a nenhuma hipótese e, com ~58 mil repositórios, dão p ≈ 0 sempre; foram retirados. Se o texto comparar ferramentas, reporta-se só o Cliff δ do par citado.
- **H2** (RQ2): Y por repositório = sim ÷ julgáveis do repositório (repos sem par julgável saem); estimativa = média por repositório; IC por bootstrap de repositórios. H₀: Y ≥ 20% × H₁: Y < 20%. Leitura: IC inteiro < 20% → resultado negativo; inteiro ≥ 50% → decay; inteiro em [20%, 50%) → co-mudança com parte de decay; cruzando um limiar → inconclusivo. Wilson agrupado como sensibilidade. O piloto (58 pares, P001–P060) é reportado à parte.
- **Tamanho da amostra da RQ2 (m pares por repositório)** — simulação (`scripts/analysis/p4_poder.py`), sem usar rótulo nenhum além do Y do piloto: Y verdadeiro = 12,5% (piloto, LLM); heterogeneidade entre repositórios pelo ICC ρ ∈ {0; 0,1; 0,2; 0,3} (θ_repo ~ Beta com média Y e ρ = 1/(a+b+1)); m ∈ {1,…,6}, cada repositório recebe min(m, candidatos); 108 repositórios; 2.000 réplicas; em cada réplica, estimativa = média das proporções por repositório e IC = ± 1,96 · dp/√108 (aproximação normal do bootstrap); **poder = P(IC_hi < 20%)**. **Regra:** o menor m com poder ≥ 80% para todo ρ ≤ 0,3. ρ > 0,3 (decay como propriedade do projeto) e Y = 15% só como sensibilidade. **Regra de parada:** a amostra final é a desse m; não haverá nova ampliação, qualquer que seja o resultado.
- **Resultado (05/nov):** m = **3** → 289 pares em todos os 108 repositórios (84 com 3, 13 com 2, 11 com 1; P001–P060 = piloto, P061–P289 em `data/api_pr_diffs_ext/sample/pares.csv`). Poder mínimo (Y = 12,5%, ρ ≤ 0,3): m = 2 → 0,77; m = 3 → 0,82. Margem estreita: recálculo independente com 20 mil réplicas deu m = 2 → 0,78 (falha) e m = 3 → 0,82 (passa). Se Y verdadeiro ≈ 15%, nenhum m ≤ 6 chega a 80% (o resultado pode sair inconclusivo — declarar).
- **Livro de códigos v3 (05/nov, depois da 1ª rotulagem humana do piloto):** o livro v3, discutido com o avaliador humano, é uma árvore respondida na ordem: (1) o diff muda comportamento observável? não → `preserva`; (2) é do assunto desta spec? não → `outra_capacidade`; (3) alguma frase ficou falsa? sim → `contradiz`; não, mas a spec não menciona → `omite`; falta informação → `nao_da_para_julgar`. Marcas: `divergencia_previa` (código já contrariava a spec antes do PR; fora do Y) e `apoio_llm` (nenhum | traducao | analise). **Critério H2 sobre o Y amplo** (contradiz + omite), fiel à definição fixada antes; Y estrito (contradiz) como decomposição; a fração `outra_capacidade` mede o acoplamento entre capacidades (descritivo). O piloto foi rotulado primeiro; os pares P061–P289, depois, já com o v3 → sensibilidade só com eles. As specs com texto em chinês foram lidas com tradução automática (decisão humana) → sensibilidade sem elas.
- **Regra de dono da mudança (05/nov, combinada com o avaliador):** `outra_capacidade` só vale com evidência de **conteúdo**: uma spec de outra capacidade (no PR ou em qualquer lugar do repositório no censo, de qualquer data, viva ou de change) cujo texto descreve a mudança. Revisão feita depois da rotulagem, só nos pares `outra_capacidade`: candidatas = specs cujo `tasks.md` cita o mesmo arquivo ligado (`spec_links`) e specs com os termos das linhas alteradas; coluna `revisao_outra` = `confirmada` (com o nome em `outra_spec`) ou `sem_evidencia` → o par conta como `omite`. Conservadora a favor do decay; o PR ter tocado outra spec, sozinho, não basta (furos: PR que muda o código de Y sem tocar spec; *merge* que toca dezenas de specs).
- **`preserva` × `outra_capacidade` (06/nov):** para a spec do par as duas significam "continua verdadeira" e nenhuma entra no Y. Ficam separadas porque (1) `preserva` = nenhum comportamento observável mudou, enquanto `outra_capacidade` = mudou, mas é de outro assunto, uma afirmação verificável que, sem dono, vira `omite` (fundir esconderia essa checagem e subestimaria o decay); (2) a fração `outra_capacidade` é a medida do acoplamento entre capacidades. No artigo, `preserva` é descrita como "sem mudança de comportamento". **Figura de fluxo** (`scripts/analysis/p4_fluxo.py [piloto|completa]` → `data/derived/figures/p4_fluxo_*.{pdf,png,csv}`): rótulo humano → revisão de evidência → classe no Y, para mostrar ao leitor quantos `outra_capacidade` foram rebaixados a `omite`. Conta pares (o Y é por repositório; dizer na legenda). Recusa rodar com `outra_capacidade` sem `revisao_outra`.
- **IC com 0 positivos:** o bootstrap degenera em [0; 0]; nesse caso o IC usado é o de Wilson (correção técnica, declarada).
- **Reprodutibilidade:** duas execuções completas do pipeline → 43 saídas com hash idêntico.

## 5c. Revisão crítica de 07/nov — decisões fixadas ANTES do fim da rotulagem dos pares novos da RQ2
Fontes desta seção:
- revisão própria;
- um revisor independente (DeepSeek v4 Pro, sem a hipótese);
- diagnósticos sem rótulo.

Nenhum rótulo da RQ2 (humano dos 222 ou DeepSeek v3) foi visto.

**RQ2, o que é a análise principal e o que é sensibilidade:**
- **Y amplo (`contradiz` + `omite`) continua como critério da H2.** A razão é a definição adotada (`metodo.md` §0.2), que diz: "perda de correspondência [...] causada por mudanças posteriores no código". O Aghajani separa desatualização de completude justamente porque "a informação estava correta e completa antes de uma mudança". Além disso, o `omite` exige citar o trecho do escopo da spec dentro do qual o comportamento novo cai.
  - O revisor propôs trocar o desfecho principal para o Y estrito. **Recusado:** isso trocaria o critério já fixado.
  - O que foi aceito: o **Y estrito vai com o mesmo destaque**, com veredito pelas mesmas faixas. Se Y amplo e Y estrito caírem em faixas diferentes, o paper diz isso explicitamente, e a frase-resumo cita os dois.
- **O piloto continua na análise principal**, como foi fixado em 05/nov: os 280 pares, porque m = 3 depende dele para ter poder. Ficou fixada uma **regra de robustez**: se a sensibilidade só com os 222 pares fora do piloto cair em faixa diferente da principal, a conclusão é reportada como **não robusta ao piloto**: as duas faixas aparecem, sem veredito único, e o piloto não decide a H2 sozinho.
- **Taxa de resposta da amostra estendida:** dos 229 pares, 222 têm diff. Dos 149 PRs únicos, 144 deram HTTP 200, 3 deram 404 e 2 deram 422, e nenhum foi truncado; sem substituição. Somando o piloto (58 de 60): 280 de 289.
- **κ humano × LLM é calculado só nos 222 pares fora do piloto**, sobre o rótulo humano **bruto**, antes da revisão de dona.
- **Sensibilidades fixadas agora:**
  - (a) só os 222 pares fora do piloto;
  - (b) só o piloto;
  - (c) **sem a revisão de dona**, com o rótulo humano como está, em que `outra_capacidade` não conta no Y;
  - (d) `nao_da_para_julgar` imputado como não-decay e como decay, para dar os limites;
  - (e) **só PRs aceitos ≥ 60 dias antes do corte** do histórico. Dos 289 pares, 105 têm PR com menos de 30 dias até o corte e 163 com menos de 60. Abaixo disso, uma spec "não atualizada" pode ser só atraso. Com cerca de 120 pares, essa sensibilidade tem pouco poder; isso é declarado;
  - (f) sem as specs com texto em chinês (lidas com tradução);
  - (g) Wilson agrupado.
- **Reportar junto:** quantos `outra_capacidade` foram rebaixados a `omite`; quantos o humano vetou; a fração de `nao_da_para_julgar`; o número de PRs e de specs **únicos**, porque 82 pares repetem um PR do mesmo repositório e 33 repetem a spec.
- **O bootstrap continua por repositório, sem cluster por PR.** O revisor sugeriu cluster por PR. Recusado: os PRs estão aninhados nos repositórios, e reamostrar o nível de cima já carrega a dependência entre pares que repetem um PR.
- **Sem recálculo do poder.** A regra de parada fixou m = 3 qualquer que seja o resultado, e o poder calculado depois do fato não muda decisão nenhuma. O ICC observado entre repositórios é reportado como descrição, ao lado da premissa ρ ≤ 0,3. Se o resultado sair inconclusivo, vai reportado assim.
- **Não multiplicar X · Y.** X é a fração de specs vivas com evento N1, estimada por repositório. Y é a fração de pares julgáveis, por repositório. As unidades diferem, então os dois são reportados separados. A "afirmação máxima" da definição foi refeita.
- **A revisão de dona por LLM:**
  - só move rótulos **para** `omite`, o que é conservador para refutar a H2;
  - o humano tem veto;
  - o recall das candidatas é desconhecido, o que pode inflar o Y. Isso é declarado, e a sensibilidade (c) mostra o tamanho do efeito.
  - O registro inclui modelo (Claude Opus 5.5), data e critério, em `MODELO_E_PROMPTS.md`.

**RQ1:**
- **H1b continua**, porque deriva de Böckeler (spec-anchored × spec-first), mas a redação muda. A diferença pode refletir o **mecanismo da ferramenta** (o arquivamento mescla a change na spec viva), não manutenção voluntária. O revisor propôs rebaixar a H1b; recusado em parte: o mecanismo é a explicação prevista pela hipótese, não uma circularidade.
- A sensibilidade à exposição (janela fixa de 60 dias) mantém a ordem: viva 28,9 contra Spec Kit 22,7.
- **Multiplicidade:** não há correção. Os limiares das hipóteses são leituras de evidência pré-declaradas, não testes simultâneos, e o paper mostra todos os ICs. Só a H2 fica perto do limiar.
## 5d. RQ2 final (07/nov): rotulagem humana concluída
**Entrada:** `data/validation/rotulagem_pares_humano.csv`, a planilha final do avaliador.
- Formato: separada por `;`, CRLF, colunas `par;repo_name;pr_number;q_decay;outra_spec;obs`.
- Os 280 pares foram revisados de ponta a ponta. O avaliador declara que todas as decisões são dele (tradução automática só para ler as specs em chinês).
- **Esclarecimento do avaliador (10/nov):** no piloto, o uso de LLM foi apoio de linguagem, não elaboração da análise ou dos rótulos. A frase anterior do paper que atribuía a revisão dos rótulos à leitura da LLM estava incorreta. Este esclarecimento substitui a interpretação de ancoragem dos rótulos finais nas notas históricas da §5b; as comparações posteriores com LLM como segundo leitor permanecem etapas separadas.
- Integridade: só leitura, sha256 `923243ce…fed4`.
- A planilha antiga da v3 (só o piloto) **não é usada** em nada, por decisão do usuário.

**Desvios em relação ao que foi fixado, todos declarados:**
1. **`divergencia_previa` saiu da planilha.** A regra fixada em §5b ("fora do Y") foi aplicada aos pares em que o próprio avaliador escreveu na observação que o código já divergia antes do PR: P200, P244 e P246 (`divergencia_previa.csv`, com o trecho da observação). A sensibilidade "divergência prévia contada como rotulada" mede o efeito.
   - Ressalva: o recall é desconhecido, porque nem toda observação foi escrita pensando nisso.
   - **Confirmado pelo avaliador em 08/nov**, nos três pares.
2. **A revisão de dona foi refeita do zero nos 128 `outra_capacidade`**, incluindo o piloto. A revisão antiga do piloto vinha da planilha descartada. Detalhes em `llm/MODELO_E_PROMPTS.md`.
   - O rigor variou entre os 6 lotes paralelos. Para corrigir, **antes de calcular o Y** foi fixada uma passada única de força, `explicita` ou `componente`.
   - Na análise principal, "componente" conta como confirmada, porque foi o critério dado aos revisores.
   - A sensibilidade (h) faz "componente" virar `omite`, que é a leitura literal de "o texto descreve a mudança".
   - Specs de change e de qualquer data foram aceitas como evidência, como a regra permite. Em parte delas, a spec que descreve a mudança é posterior ao PR.
3. **Os pares da sensibilidade (f) foram definidos de forma mecânica:** "o texto da spec tem caracteres CJK" (53 pares; o avaliador usou tradução para ler todos eles).
4. **O veto humano é sensibilidade, não análise principal.** É a semântica já implementada desde 05/nov. Os 13 pares sem evidência aguardam o veto em `decisoes.csv`.

**Resultado** (`scripts/analysis/validation_score.py` → `data/validation/resultado_p4.csv`):
- **Contagens:** rótulo bruto com 125 preserva, 128 outra_capacidade, 11 omite, 9 contradiz e 7 não dá para julgar. Revisão de dona: 115 confirmadas e 13 sem evidência (viram `omite`). 3 pares com divergência prévia.
- **Amostra principal:** 270 pares julgáveis, 198 PRs únicos, 239 specs únicas, 105 repositórios.
- **Y amplo por repositório: 11,6% [IC 7,6–16,2] → resultado negativo.** Y estrito: 2,7% [0,8–5,2], também negativo.
- **Sensibilidades:** todas ficam com IC < 20%. O maior limite superior é 19,2%, em (h). Depois vem 18,7%, em (d2).
- **Robustez ao piloto:** o conjunto fora do piloto (222 pares; amplo 10,7% [6,6–15,0]) cai na mesma faixa → robusto.
- **ICC entre repositórios (descritivo):** amplo 0,07, estrito 0,12. Fica dentro da premissa do cálculo de poder (ρ ≤ 0,3).
- **κ humano bruto × DeepSeek v3 nos 222 pares fora do piloto:** 0,33 nas 5 categorias (acordo 58%) e **0,23 no Y amplo binário** (213 julgáveis).
  - Leitura: **o LLM não serve como 2º avaliador confiável nesta tarefa.** O resultado se apoia no humano, e o LLM entra como ameaça e descrição (Ahmed et al. 2025).
- **Reprodução:** `reproduzir.sh` dá 81 saídas idênticas em 2 execuções.

## 5e. Decisões de 08/nov
- **Veto humano na revisão de dona:** o avaliador revisou os 13 `sem_evidencia` (original em `originais_do_avaliador/revisao_veto.csv`; cópia normalizada e só leitura em `revisao_dono/veto_humano.csv`).
  - Vetou 12: 9 marcados "Sim" e 3 com "não se trata de novo comportamento omitido na spec".
  - Manteve 1 (P265), com a nota "possível contradiz". O par fica como `omite` e não foi promovido a `contradiz`.
  - **A análise principal passa a usar o veto**, porque o humano é o padrão-ouro e o revisor só propõe (Verifier-in-the-Loop, §5c). A regra sem veto vira sensibilidade.
  - O veredito não muda: negativo nas duas versões, 7,0% com o veto e 11,6% sem ele.
- **Adjudicação da RQ2 (opção a2, problemas #68), regras fixadas ANTES de ver as respostas:**
  - **Material:** `scripts/analysis/p4_adjudicacao.py` → `data/validation/adjudicacao_p4/`. São os pares em que o rótulo final do humano e o DeepSeek v3 (rodada 1) discordam em "decay sim/não", sem os "não dá para julgar" e sem os de divergência prévia. Deu 28 pares (25 fora do piloto): humano sim × DeepSeek não em 10; humano não × DeepSeek sim em 18.
  - **Formato:** o avaliador relê a spec e o diff e vê as duas leituras como A e B, em ordem sorteada por hash e sem autoria. A chave fica em `chave_NAO_ABRIR.csv`.
  - **Análise principal depois da adjudicação:** o rótulo adjudicado substitui o rótulo final nesses 28 pares. A versão anterior à adjudicação vira sensibilidade.
  - **O κ continua** o do rótulo bruto. A adjudicação não muda a concordância medida.
  - **Se o avaliador escolher `outra_capacidade`** num par que não tinha dona confirmada, a regra de dona se aplica: o revisor procura a spec dona e o avaliador tem veto.
  - **Declaração no paper:** "adjudicação pelo avaliador principal, informada pelo 2º avaliador". É mais fraca que um 2º humano independente, e isso será dito.
  - **Feita em 08/nov** (`adjudicacao_p4.csv`, backup e sha256 em `backup/`).
    - Dos 28 pares, 15 passaram a decay e 9 foram para `outra_capacidade`.
    - Dona conferida por Claude (`dona_adjudicacao.csv`): 7 explícitas, 1 só por componente (P140) e 1 sem dona (P228, palavras do próprio avaliador), que vira `omite`.
    - **Resultado:** Y amplo 10,3% [5,6–15,4] e estrito 5,4% [2,2–9,5], ambos negativos. Antes da adjudicação: 7,0% e 2,7%.
    - O ICC subiu para 0,34 (amplo) e 0,43 (estrito), acima da premissa ρ ≤ 0,3 do cálculo de amostra. O IC < 20% torna isso irrelevante para o veredito, mas a premissa fica declarada como não confirmada.

## 5f. Segundo canal de ligação spec ↔ código: `openspec_code_refs` (08/nov; regras fixadas ANTES de rodar no pipeline)
- **O que é:** a tabela do SpecMine v1.0 com 435.401 referências de `tasks.md` para código. O paper-base resolveu cada uma "against the repository's git tree at the anchoring commit", registrando se a tarefa estava marcada e se o arquivo existia. O próprio paper-base a chama de "a second channel from spec to code, independent of co-change" (`literatura/artigos/paper_2608.25202.txt`, Apêndice A).
  - O dataset **não diz** qual commit é a âncora nem como o casamento de caminhos foi feito (exato ou por nome). Isso fica como ressalva.
- **Por que entra:** a ameaça de construto "a ligação spec ↔ código é indireta (regra nossa sobre `spec_links`)" ganha uma checagem independente.
- **Já visto no planejamento** (consulta só de leitura, declarada aqui):
  - 596 de 619 caminhos ligados nos 280 pares aparecem na tabela para a mesma change e capacidade, e 584 existiam na âncora;
  - 279 de 280 pares têm ligação confirmada e existente;
  - 248 pares têm algum caminho de tarefa marcada;
  - os 12 pares vetados também estão confirmados, então essa tabela **não** resolve a dúvida de escopo deles.
- **Regras de interpretação:**
  1. Se ≥ 95% dos pares tiverem ligação confirmada, o paper diz que a ligação é confirmada pelo SpecMine; abaixo disso, reporta a fração e mantém a ameaça.
  2. Duas sensibilidades do Y: "só pares com algum caminho de tarefa marcada" e "só pares com todos os caminhos confirmados". Vão para a Tabela II ou para o texto, pelas mesmas faixas, e não trocam o resultado principal.
  3. X com a ligação ampla (caminhos resolvidos da tabela, incluindo nomes soltos) é só descritivo, reportado como faixa [estrita, ampla].
- **Script:** `scripts/analysis/p4_ligacao.py` → `data/derived/tables/p4_ligacao.csv` e `data/derived/p4_ligacao.txt`.

## 5g. "Lacuna de especificação" (08/nov; interpretação dada DEPOIS de ver os resultados, declarada)
- **O que são:** os 12 pares vetados. O avaliador julgou o comportamento mudado fora do escopo da spec do par, e o revisor não achou nenhuma spec no repositório que o descreva.
- **O que muda:** só o nome e a apresentação. São comportamentos **não documentados**, não descritos errado pela spec do par. A regra fixada antes ("sem dona → `omite`, salvo veto") e o veto continuam iguais.
- **Como o paper reporta:** as duas leituras. Com a lacuna separada (análise principal), Y amplo = 10,3% [5,6–15,4]. Com a lacuna contada como decay da spec do par, Y amplo = 14,9% [9,5–20,8], que é inconclusivo.
- **Pergunta em aberto:** uma spec deve responder por comportamento fora do escopo dela que nenhuma spec cobre? É de construto, e o paper a deixa explícita.

## 5h. Evidência documentada dos vetos (08/nov, noite; feita DEPOIS de ver os resultados, declarada)
- **O que foi feito:** para cada um dos 12 vetos, o avaliador registrou em `data/validation/revisao_dono/evidencia_veto/evidencia_veto.csv` (material: `evidencia_veto.html`, gerado por `scripts/analysis/p4_veto_evidencia.py`) o trecho literal da spec que delimita o escopo, o comportamento que o diff mudou, uma justificativa e se mantém o veto. A planilha está no manifesto `data/ENTRADAS.sha256`.
- **Resultado:** 11 mantidos e 1 retirado (**P224**, KatanA: o diff trata de um atalho de colagem com o editor focado, "exatamente o comportamento de entrada e autoria coberto por esta spec"). P224 volta à regra fixada antes (sem dona → `omite`).
- **Efeito:** Y amplo principal 10,3% → **10,6% [5,9–16,0]**, ainda negativo; Y estrito igual (5,4%); "lacunas = decay" igual (14,9%), porque já contava os 12 como `omite`. A sensibilidade "PRs com ≥60 dias" passa a inconclusiva por 0,1 ponto (problemas #87).
- **Direção:** a única mudança aumentou o Y, isto é, foi contra o resultado negativo. Mesmo assim, a releitura foi feita conhecendo os resultados, e o paper declara isso.

## 6. Validação das medidas (→ Method: validation; Threats)
- **LLM avaliador:** `deepseek-v4-pro` (API DeepSeek), temperatura 0,3, sem ferramentas, prompts e instruções em `data/validation/llm/MODELO_E_PROMPTS.md`.
- **RQ2, 2º avaliador (06/nov):** `scripts/analysis/llm_pares_v3.py` roda `deepseek-v4-pro` (temperatura 0,3) com o prompt v3 autocontido nos 280 pares (lotes de ≤180 mil caracteres; piloto em `llm/lotes_pares_piloto/`), grava em `llm/deepseek_v3/` e `llm/llm_pares_v3.csv` sem imprimir rótulos (a revisão de evidência e a rotulagem humana ficam cegas a eles).
- **Revisão de evidência (dono), preparada às cegas (06/nov):** `scripts/analysis/p4_dono.py` lista, para os 222 pares novos, specs de outra capacidade do mesmo repositório candidatas a dona: (A) changes cujo `tasks.md` cita o arquivo ligado, (B) specs tocadas pelo PR, (C) specs com termos raros das linhas alteradas (idf no repositório) → `data/validation/revisao_dono/`. Gerado antes de ver qualquer rótulo humano ou do LLM; o julgamento (a candidata descreve a mudança?) é feito só nos pares rotulados `outra_capacidade`.
- **Revisão independente:** o código e os resultados foram revisados sem fornecer a hipótese ao revisor.

## 7. Reprodutibilidade (→ Data availability)
- **Um comando (07/nov):** `bash scripts/reproduzir.sh`. Ele confere as entradas congeladas, roda o pipeline 2× e compara o conteúdo das saídas. Guia em `docs/REPRODUZIR.md`; versões exatas em `requirements.lock.txt`.
- Pipeline: `universe.py` → `spec_rot_viabilidade.py` → `p4_ligacao.py` → `key_numbers.py` → `p4_poder.py` → `p4_dono.py` → `validation_score.py` → `p4_fluxo.py`. O `validation_build.py` gerou o material de rotulagem uma vez e não é rodado de novo. Python 3.12.14, DuckDB 2.0.0, pandas 3.1.1.
- Duas execuções completas (05/nov, tarde) produzem tabelas, JSON e o sorteio da RQ2 com hash idêntico; o universo tem conteúdo idêntico (checksum por coluna). O sorteio da RQ2 é conferido contra a amostra travada a cada execução.
- Sementes fixas em todos os sorteios e no bootstrap.

## 8. Limitações (→ Threats to validity) — resumo
Histórico só do caminho atual (sem duração de changes); *squash* e *rebase* juntam edições; papéis do censo podem estar desatualizados além dos 264 corrigidos; `spec.md` mistura gêneros; corpus majoritariamente solo e de histórico curto (o recorte pós-2024 é do próprio dataset, não um achado).

## 9. Revisão de 19/nov/2026 (depois do repasse e da revisão da orientadora)
- **Estrutura do paper:** RQ guarda-chuva ("How do SDD specifications evolve after creation, and do they stay accurate as the code changes?") com RQ1 (edição) e RQ2 (spec decay). Pedido da orientadora: perguntas que não se respondem com sim/não, hipóteses com origem e regra explícitas, Figura 2 maior e Discussion em diálogo com a literatura.
- **Texto do paper corrigido, sem mudar método nem número:** "files whose commit history SpecMine did not collect (1,473)" (antes: "no commit by July 11"); origem do 12,5% declarada; "blind pairs" virou "pairs outside the pilot"; κ com os dois n (222 e 213); a frase do veto passou a dizer que a leitura com veto virou análise principal **depois** de ver os rótulos; uso de IA completo (tradução, rotulagem preliminar, crítica do desenho); Böckeler sem atribuir a ela a classificação do OpenSpec; ameaça do *squash* com a passagem do paper-base.
- **Pipeline:** `key_numbers.py` conta `historico_nao_coletado` e afirma que ele é igual à etapa do funil; `spec_rot_viabilidade.py` conta `candidatos_sem_spec` (11 de 13.028), que sustenta "nearly every candidate PR updated a spec"; a Figura 2 passou a ter duas colunas (`p4_fluxo.py`, `larga=True`); `scripts/paper/extrair_abstract.py` gera `dist/abstract.txt` a partir do `main.tex`.
- **Revisão do autor (20/nov):** a H1a ("menos de 50% editadas em cada grupo") saiu como hipótese, porque é previsível depois dos 81,5% do paper-base; a leitura "menos da metade" continua descritiva. A H1b passou a se chamar **H1**. A RQ2 foi reescrita ("When a pull request changes the code linked to a living spec but leaves the spec unchanged, how often does the spec become false or incomplete?"); entrou uma frase sobre por que a RQ1 importa; a lista dos nomes genéricos excluídos foi para uma nota de rodapé; a Figura 1 virou uma linha do tempo.
