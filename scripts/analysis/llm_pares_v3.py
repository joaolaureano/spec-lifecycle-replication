"""RQ2 — DeepSeek como 2º avaliador dos 280 pares com o prompt v3 (data/validation/llm/prompt_llm2_pares.md).

Os rótulos vão direto para arquivo e NUNCA são impressos: a revisão de evidência (revisao_outra) e a rotulagem humana
seguem cegas a eles. Retomável: lote com resposta válida não é refeito. Chave só em memória (DEEPSEEK_API_KEY).
Uso: .venv/bin/python -I scripts/analysis/llm_pares_v3.py
Saída: data/validation/llm/deepseek_v3/<lote>.csv, llm_pares_v3.csv e LOG.txt (só contagens).
"""
import concurrent.futures as cf, csv, io, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LLM = os.path.join(ROOT, "data", "validation", "llm")
OUT = os.path.join(LLM, "deepseek_v3")
MODELO, TEMP, LIMITE = "deepseek-v4-pro", 0.3, 180_000
SISTEMA = "Você é um avaliador cuidadoso de engenharia de software. Responda somente no formato pedido."
CAB = ["par", "q_decay", "divergencia_previa", "outra_spec", "confianca", "frase_spec", "justificativa"]
VALORES = {"q_decay": {"preserva", "outra_capacidade", "omite", "contradiz", "nao_da_para_julgar"},
           "divergencia_previa": {"sim", "nao"}, "confianca": {"alta", "media", "baixa"}}


def lotes_piloto():
    """P001–P060 em lotes com as mesmas regras de validation_build.lotes (par nunca dividido; par grande cortado)."""
    d = os.path.join(LLM, "lotes_pares_piloto")
    if os.path.isdir(d) and os.listdir(d):
        return
    os.makedirs(d, exist_ok=True)
    txt = open(os.path.join(LLM, "pares.txt"), encoding="utf-8").read()
    blocos = [b for b in re.split(r"\n(?====== P\d{3} \|)", txt)[1:] if b[6:10] < "P061"]
    n, atual = 0, ""
    for b in blocos:
        if atual and len(atual) + len(b) > LIMITE:
            n += 1
            open(os.path.join(d, f"piloto_{n:02d}.txt"), "w", encoding="utf-8").write(atual)
            atual = ""
        atual += b.rstrip("\n")[:LIMITE] + "\n\n"
    if atual:
        n += 1
        open(os.path.join(d, f"piloto_{n:02d}.txt"), "w", encoding="utf-8").write(atual)


def validar(texto, esperados):
    """Devolve as linhas se o CSV cobre exatamente os pares do lote com valores do livro de códigos; senão None."""
    t = re.sub(r"^```\w*\n|```\s*$", "", texto.strip())
    try:
        linhas = list(csv.DictReader(io.StringIO(t)))
    except csv.Error:
        return None
    if not linhas or list(linhas[0].keys()) != CAB or [l["par"] for l in linhas] != esperados:
        return None
    if any(l[c] not in v for l in linhas for c, v in VALORES.items()):
        return None
    return linhas


def chamar(prompt):
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", method="POST",
                                 headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                          "Content-Type": "application/json"},
                                 data=json.dumps({"model": MODELO, "temperature": TEMP, "stream": True, "messages": [
                                     {"role": "system", "content": SISTEMA}, {"role": "user", "content": prompt}]}).encode())
    partes = []  # streaming: sem ele a conexão caía (IncompleteRead) nas respostas longas
    with urllib.request.urlopen(req, timeout=600) as r:
        for linha in r:
            linha = linha.decode().strip()
            if linha.startswith("data: ") and linha != "data: [DONE]":
                partes.append(json.loads(linha[6:])["choices"][0]["delta"].get("content") or "")
    return "".join(partes)


def rodar(caminho, instr):
    nome = os.path.splitext(os.path.basename(caminho))[0]
    saida = os.path.join(OUT, f"{nome}.csv")
    lote = open(caminho, encoding="utf-8").read()
    esperados = re.findall(r"^===== (P\d{3}) \|", lote, flags=re.M)
    if os.path.exists(saida) and validar(open(saida, encoding="utf-8").read(), esperados):
        return nome, len(esperados), "já feito"
    for tentativa in range(3):
        try:
            resp = chamar(instr + "\n\n===== ARQUIVO ANEXADO =====\n" + lote)
        except Exception as e:  # rede/limite: espera e tenta de novo (a mensagem não contém a chave)
            erro = type(e).__name__
            time.sleep(30 * (tentativa + 1))
            continue
        if validar(resp, esperados):
            tmp = saida + ".tmp"
            open(tmp, "w", encoding="utf-8").write(resp.strip() + "\n")
            os.replace(tmp, saida)
            return nome, len(esperados), f"ok (tentativa {tentativa + 1})"
        erro = "resposta fora do formato"
        open(os.path.join(OUT, f"{nome}.invalida.txt"), "w", encoding="utf-8").write(resp)  # para depurar sem imprimir
    return nome, len(esperados), f"FALHOU: {erro}"


def main():
    assert os.environ.get("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY ausente"
    lotes_piloto()
    os.makedirs(OUT, exist_ok=True)
    instr = open(os.path.join(LLM, "prompt_llm2_pares.md"), encoding="utf-8").read()
    arqs = sorted(os.path.join(LLM, d, f) for d in ("lotes_pares_piloto", "lotes_pares_novos")
                  for f in os.listdir(os.path.join(LLM, d)) if f.endswith(".txt"))
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda a: rodar(a, instr), arqs))
    tabela = [l for a in arqs if os.path.exists(p := os.path.join(OUT, os.path.splitext(os.path.basename(a))[0] + ".csv"))
              for l in validar(open(p, encoding="utf-8").read(), re.findall(r"^===== (P\d{3}) \|", open(a, encoding="utf-8").read(), flags=re.M)) or []]
    with open(os.path.join(LLM, "llm_pares_v3.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, CAB)
        w.writeheader()
        w.writerows(sorted(tabela, key=lambda l: l["par"]))
    log = [f"{datetime.now(timezone.utc).isoformat()} modelo={MODELO} temperatura={TEMP} lotes={len(arqs)} pares={len(tabela)}"]
    log += [f"{n}: {k} pares, {s}" for n, k, s in res]
    open(os.path.join(OUT, "LOG.txt"), "a", encoding="utf-8").write("\n".join(log) + "\n")
    print("\n".join(log))  # só contagens e status; nenhum rótulo
    sys.exit(0 if len(tabela) == 280 else 1)


if __name__ == "__main__":
    main()
