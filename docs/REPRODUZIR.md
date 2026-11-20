# Como reproduzir todos os números

Qualquer pessoa com este diretório consegue refazer cada número do paper e conferir que o resultado não muda entre execuções.

## 1. Ambiente (uma vez)
```bash
uv venv --python 3.12 .venv                       # Python 3.12 (usado: 3.12.14)
uv pip install --python .venv/bin/python -r requirements.lock.txt   # versões exatas (duckdb 2.0.0, pandas 3.1.1, ...)
```
- Rode sempre `.venv/bin/python -I`. O `-I` isola o Python do diretório atual, e é a regra do projeto ao ler arquivos baixados.
- Também é preciso `shasum` e `md5` (macOS) ou `md5sum` (Linux). `pdftotext` (poppler) só serve para a literatura.

## 2. Rodar
```bash
bash scripts/reproduzir.sh                  # confere entradas, roda o pipeline 2× e compara hashes (~15 min; ~7 por execução, a maior parte no key_numbers)
bash scripts/reproduzir.sh --uma-vez        # só uma execução
bash scripts/reproduzir.sh --desde-o-zenodo # também refaz o texto das specs a partir do Zenodo (lento)
```
- **Saída esperada no fim:** `OK: N saídas idênticas nas duas execuções` e, do notebook, `N of N values found in paper/main.tex` e `numbers and verdicts in the paper without a source: 0`. A segunda linha vem de uma varredura do texto inteiro do paper: todo algarismo, todo número por extenso e todo veredito (*met*, *inconclusive*, *negative result*) precisa estar dentro de um valor conferido pelo notebook (saída do pipeline, parâmetro lido do script, registro do LLM ou trecho de um trabalho citado) ou numa lista declarada de usos estruturais (por exemplo, os passos (1)–(3) do codebook).
- **Logs e impressões digitais:** `data/derived/reproducao/`.
- **Passo a passo:** `pipeline.ipynb` roda as mesmas etapas uma vez, com um texto explicando cada uma, e confere no fim que as saídas não mudaram (`.venv/bin/python -I scripts/executar_notebook.py pipeline.ipynb`, ou abra no Jupyter e rode tudo).
- **Números do paper:** `numeros_do_paper.ipynb` mostra cada um, com o arquivo de origem (`docs/key_numbers_final.json`, `data/derived/tables/`, `data/derived/numeros/`, `data/validation/resultado_*.csv`). O script o executa no fim e grava as saídas nele; com `paper/main.tex` presente, ele falha se algum número não estiver no texto.

## 3. Ordem do pipeline (o que o script roda)
| Etapa | Script | Produz |
|---|---|---|
| universo e dedup | `scripts/analysis/universe.py` | `data/derived/universe.parquet`, funil |
| RQ2: evento N1, X, sorteio conferido | `scripts/analysis/spec_rot_viabilidade.py` | `data/derived/p4_amostra.txt`; **falha** se o sorteio mudar |
| RQ2: 2º canal de ligação (`openspec_code_refs`) e X amplo | `scripts/analysis/p4_ligacao.py` | `data/derived/tables/p4_ligacao.csv`, `data/derived/p4_ligacao.txt` |
| RQ1, hipótese H1 e números do corpus | `scripts/analysis/key_numbers.py` | `docs/key_numbers_final.json`, `data/derived/tables/*` |
| RQ2: tamanho da amostra | `scripts/analysis/p4_poder.py` | `data/derived/tables/p4_poder.csv` |
| RQ2: candidatas a dona | `scripts/analysis/p4_dono.py` | `data/validation/revisao_dono/` |
| RQ2: Y, sensibilidades e concordância | `scripts/analysis/validation_score.py` | `data/validation/resultado_*.csv`, `p4_rotulos_finais.csv` |
| figura da RQ2 | `scripts/analysis/p4_fluxo.py` | `data/derived/figures/` |
| sorteio da adjudicação pela semente (uma vez, depois das 2 execuções) | `p4_adjudicacao.py --conferir` | nada; **falha** se a ordem A/B da adjudicação (`adj-20261108`) mudar |
| documento de ponta a ponta | `scripts/gerar_explicacao.py` | `docs/EXPLICACAO_E2E.md` (todos os valores lidos das saídas) |

Parquet é comparado pelo **conteúdo**, não pelos bytes: o DuckDB com várias threads pode gravar os mesmos dados em bytes diferentes. Ver `scripts/hash_saidas.py`.

## 4. Entradas congeladas (o script não refaz; só confere)
| Entrada | Como foi gerada | Conferência |
|---|---|---|
| SpecMine v1.0 | Zenodo record 22102780 (`data/specmine_zenodo/specmine.zip`); Parquet idêntico no HF | MD5 `86c8fa6249bafd220eafbdf89ca7231f` |
| Coleta na API do GitHub (diffs dos PRs) | `scripts/api/{fetch_pr,finalize}.py` (funções em `github_api.py`) | `api_pr_diffs`, `api_pr_diffs_ext`: `SHA256SUMS`; o sorteio dos pares é refeito dentro do pipeline |
| Material de rotulagem | `scripts/analysis/validation_build.py` | gerado uma vez; **não rodar de novo durante a rotulagem** (reescreve `rotulagem_pares.csv`, mantendo os rótulos) |
| Rótulos humanos | rotulagem manual: `data/validation/rotulagem_pares_humano.csv` (`;`, só leitura) | sha256 `923243ce…fed4` |
| Adjudicação | `p4_adjudicacao.py` (gerado uma vez) → `data/validation/adjudicacao_p4/`; planilha preenchida pelo avaliador | só o `--conferir` roda no `reproduzir.sh` (ordem A/B pela semente) |
| Revisão de dona | Claude Opus 5.5 sobre `revisao_dono/material/`; decisões em `revisao_dono/decisoes.csv`; divergência prévia em `divergencia_previa.csv` (das notas do avaliador) | `validation_score.py` recusa `outra_capacidade` sem decisão |
| Rótulos de LLM | `llm_pares_v3.py` (API DeepSeek) e o registro em `data/validation/llm/MODELO_E_PROMPTS.md` | rodar de novo custa dinheiro e não é determinístico |

Para refazer uma coleta do zero, é preciso estar logado no `gh` (`gh auth login`). Os scripts leem o token com `gh auth token`, só em memória; nunca o gravam nem o imprimem. Para o LLM, a chave vai só no ambiente da sessão (`DEEPSEEK_API_KEY`). As respostas de hoje podem diferir das de nov/2026 (repositórios apagados), e por isso os brutos congelados são a referência.

## 4b. Integridade das entradas
`scripts/conferir_entradas.py` roda antes do pipeline e confere três coisas:
- os parquets de `data/specmine/data/` são idênticos aos de dentro do ZIP do Zenodo, cujo MD5 é conferido antes;
- o **conteúdo** de `data/derived/specs_text.parquet`;
- os bytes de todas as decisões humanas e de LLM, do gabarito dos pares e dos arquivos de sorteio, contra `data/ENTRADAS.sha256`.

A igualdade entre as duas execuções prova determinismo; esta etapa prova que as entradas são as registradas. O `--desde-o-zenodo` refaz o texto das specs a partir do ZIP, e a conferência de conteúdo continua valendo.

## 5. Regras que mantêm isto reproduzível
- Sementes fixas em todo sorteio e bootstrap; todas estão no código.
- Nada é calculado à mão fora de um script. Diagnóstico novo entra num script do pipeline antes de virar número no texto.
- As amostras sorteadas são travadas: o script falha se o sorteio mudar (os pares da RQ2 dentro do pipeline; a ordem da adjudicação no passo 3b).
- Cada dado bruto tem SHA256SUMS e é somente leitura.
