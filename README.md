# Replication package: "Editing and Spec Decay in Spec-Driven Development"

This package reproduces every number, table, and figure of the paper from frozen inputs.
The method record (`docs/`) is in Portuguese. Code comments are also in Portuguese.

The paper asks one research question with two subquestions: RQ1 (editing) and RQ2 (spec decay). RQ2 files are named
`p4_*`.

## Contents
| Path | What it is |
|---|---|
| `numeros_do_paper.ipynb` | Every number in the paper, read from the pipeline outputs, with its source file. Open it to see the numbers; the pipeline re-executes it. |
| `pipeline.ipynb` | The whole pipeline, step by step, with a text (in Portuguese) explaining each step; it checks the inputs, runs every script once, re-draws the seeded samples, and confirms that the outputs are identical to the shipped ones. Already executed, so the output of each step is visible without running it. |
| `scripts/reproduzir.sh` | Runs the whole pipeline twice, checks that all outputs are identical (content hashes), re-draws every seeded sample (the blind A/B order of the adjudication; the RQ2 pairs are re-drawn inside the pipeline) and fails if any differs from the frozen one, then executes the notebook. |
| `scripts/conferir_entradas.py`, `data/ENTRADAS.sha256` | Integrity check of every input. The SpecMine parquets are checked against the Zenodo ZIP; the spec text is checked by a content hash; the labels and decisions are checked by sha256. |
| `scripts/analysis/` | Analysis (RQ1: `key_numbers.py`; RQ2 (spec decay): `spec_rot_viabilidade.py`, `p4_ligacao.py`, `p4_dono.py`, `validation_score.py`, `p4_fluxo.py`). |
| `scripts/api/`, `scripts/build/` | One-time collector of PR diffs (GitHub API) and the builder of the spec-text table from the Zenodo ZIP. |
| `data/api_pr_diffs/`, `data/api_pr_diffs_ext/` | Frozen GitHub API responses (PR file diffs for RQ2), with `SHA256SUMS`. E-mails, signatures, and avatars were removed before storage. |
| `data/validation/` | RQ2 (spec decay) labels and decisions: `rotulagem_pares_humano.csv` (human labels, 280 pairs), `revisao_dono/` (owner check, reviewer evidence, human vetoes), `adjudicacao_p4/` (adjudication of human/LLM disagreements), `divergencia_previa.csv`, `llm/` (DeepSeek outputs, prompts, and model registry `MODELO_E_PROMPTS.md`), `pares.html` (the exact material the rater read). |
| `data/derived/` | Outputs: tables, figures, RQ2 sample description. |
| `docs/` | Method and dated decisions (`metodo.md`), reproduction instructions (`REPRODUZIR.md`), and `EXPLICACAO_E2E.md`, the whole study end to end with every metric, formula, and value (generated from the outputs by `scripts/gerar_explicacao.py`). |

## Reproduce
**Requirements:** tested on macOS; Linux (and WSL on Windows) should work but was not tested. You need `bash`, `unzip`, `curl`, `shasum`, and `md5` (macOS) or `md5sum` (Linux); [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed); about 12 GB of free disk and 8 GB of RAM. Nothing else is downloaded or called: no GitHub API, no LLM.

1. Get this package and create the environment with the exact package versions:
   ```bash
   git clone https://github.com/joaolaureano/spec-lifecycle-replication && cd spec-lifecycle-replication
   uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.lock.txt
   ```
2. Download SpecMine v1.0 from Zenodo (https://doi.org/10.5281/zenodo.22102780; 5.4 GB, MD5 `86c8fa6249bafd220eafbdf89ca7231f`) and extract it:
   ```bash
   mkdir -p data/specmine_zenodo data/specmine/data data/specmine_zenodo/x
   curl -L -o data/specmine_zenodo/specmine.zip https://zenodo.org/api/records/22102780/files/specmine.zip/content
   unzip -j data/specmine_zenodo/specmine.zip 'specmine-zenodo/data/*.parquet' -d data/specmine/data
   unzip data/specmine_zenodo/specmine.zip 'specmine-zenodo/specs.jsonl.gz' -d data/specmine_zenodo/x
   ```
3. Run the pipeline, in either of two ways:
   - **Script:** `bash scripts/reproduzir.sh --desde-o-zenodo`. It rebuilds the spec text from the ZIP, checks all inputs, runs the pipeline twice (about 20 minutes), re-draws every seeded sample, and ends with `OK: 75 saídas idênticas nas duas execuções` and `N of N values found in paper/main.tex` and `numbers and verdicts in the paper without a source: 0`.
   - **Notebook, step by step:** open `pipeline.ipynb` in Jupyter (`.venv/bin/jupyter lab`) and run all cells. It runs each step once, with a text explaining it, and checks at the end that the outputs equal the shipped ones.
4. Open `numeros_do_paper.ipynb`: every number of the paper next to its source file, checked against `paper/main.tex`.

`paper/` holds the LaTeX source and figure of the paper; `paper.pdf` is the compiled paper.

## Notes
- **Hypotheses:** they were written after exploring the data. Decision rules and their dates are in `docs/metodo.md` (§5b–5g); there is no external pre-registration.
- **LLM use:** DeepSeek v4 Pro was the second rater; Claude Opus 5.5 was the owner-evidence reviewer and the programming assistant. LLMs also translated Chinese-language specs for reading (every label is a human decision), produced the preliminary pilot labels behind the 12.5% used only to size the RQ2 sample (those labels and the model were not kept), and critiqued the study design. Prompts, versions, and dates are in `data/validation/llm/MODELO_E_PROMPTS.md`. Re-running LLM calls is not needed and is not deterministic.
- **GitHub data:** the API collections contain public GitHub metadata (including logins), as SpecMine itself does. Results are reported only in aggregate.
