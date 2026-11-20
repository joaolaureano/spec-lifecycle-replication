#!/usr/bin/env bash
# Reproduz TODOS os números do paper a partir das entradas congeladas e confere o determinismo: roda o pipeline
# duas vezes e compara a impressão digital das saídas (scripts/hash_saidas.py). Detalhes: docs/REPRODUZIR.md.
#
# Uso (da raiz do repositório):  bash scripts/reproduzir.sh [--desde-o-zenodo] [--uma-vez]
#   --desde-o-zenodo  refaz também data/derived/specs_text.parquet a partir do specs.jsonl.gz do Zenodo (lento)
#   --uma-vez         roda o pipeline só uma vez (sem a checagem de determinismo)
#
# NÃO roda (são geradores de uma vez só, cujas saídas estão congeladas e conferidas por SHA256SUMS):
#   coleta na API (scripts/api/fetch_pr.py, finalize.py), material de rotulagem (validation_build.py — reescreveria
#   rotulagem_pares.csv) e chamadas a LLM (llm_pares_v3.py). Ver docs/REPRODUZIR.md.
#   Dos geradores com semente, o sorteio dos pares é refeito dentro do pipeline (spec_rot_viabilidade.py), e o da ordem
#   cega da adjudicação no passo 3b (p4_adjudicacao.py --conferir); os dois falham se o sorteio mudar.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python -I"
OUT="data/derived/reproducao"
mkdir -p "$OUT"
DESDE_ZENODO=0; VEZES=2
for a in "$@"; do
  case "$a" in --desde-o-zenodo) DESDE_ZENODO=1 ;; --uma-vez) VEZES=1 ;; *) echo "opção desconhecida: $a"; exit 2 ;; esac
done

echo "== 1. entradas congeladas"
test "$(md5 -q data/specmine_zenodo/specmine.zip 2>/dev/null || md5sum data/specmine_zenodo/specmine.zip | cut -d' ' -f1)" \
  = "86c8fa6249bafd220eafbdf89ca7231f" && echo "SpecMine v1.0 (Zenodo 22102780): MD5 ok"
for d in api_pr_diffs api_pr_diffs_ext; do
  (cd "data/$d" && shasum -a 256 -c SHA256SUMS --quiet) && echo "data/$d: SHA256SUMS ok"
done

if [ "$DESDE_ZENODO" = 1 ]; then
  echo "== 0. texto das specs a partir do Zenodo"
  $PY scripts/build/specs_jsonl_to_parquet.py
fi

echo "== 1b. integridade de todas as entradas lidas (parquets = ZIP do Zenodo; texto, decisões e sorteios = manifesto)"
$PY scripts/conferir_entradas.py

rodar() {  # $1 = número da execução
  local L="$OUT/execucao_$1"; mkdir -p "$L"
  for etapa in "scripts/analysis/universe.py" \
               "scripts/analysis/spec_rot_viabilidade.py" \
               "scripts/analysis/p4_ligacao.py" \
               "scripts/analysis/key_numbers.py" \
               "scripts/analysis/p4_poder.py" \
               "scripts/analysis/p4_dono.py" \
               "scripts/analysis/validation_score.py" \
               "scripts/analysis/p4_fluxo.py"; do
    nome=$(echo "$etapa" | tr ' /' '__')
    echo "   [$1] $etapa"
    $PY $etapa > "$L/$nome.log" 2>&1 || { echo "FALHOU: $etapa (log em $L/$nome.log)"; exit 1; }
  done
  $PY scripts/hash_saidas.py "$OUT/saidas_$1.sha256"
}

for i in $(seq 1 $VEZES); do echo "== 2. pipeline, execução $i"; rodar "$i"; done

if [ "$VEZES" = 2 ]; then
  echo "== 3. determinismo"
  if diff "$OUT/saidas_1.sha256" "$OUT/saidas_2.sha256"; then
    echo "OK: $(wc -l < "$OUT/saidas_2.sha256" | tr -d ' ') saídas idênticas nas duas execuções"
  else
    echo "ERRO: as saídas diferem entre execuções (ver diff acima)"; exit 1
  fi
fi

echo "== 3b. sorteio refeito a partir da semente (não grava nada; falha se o sorteio mudar)"
$PY scripts/analysis/p4_adjudicacao.py --conferir    # RQ2: ordem cega A/B da adjudicação (semente adj-20261108)
# (o sorteio dos 289 pares da RQ2 é conferido dentro do pipeline, por spec_rot_viabilidade.py)

echo "== 4. números do paper: numeros_do_paper.ipynb (com paper/main.tex, confere cada valor no texto e que nenhum número do paper fica sem origem)"
$PY scripts/executar_notebook.py > "$OUT/notebook.log" 2>&1 || { echo "FALHOU: notebook (log em $OUT/notebook.log)"; exit 1; }
grep -v IPKernelApp "$OUT/notebook.log" | tail -5

echo "== 5. documento de ponta a ponta (docs/EXPLICACAO_E2E.md, todos os valores lidos das saídas)"
$PY scripts/gerar_explicacao.py
