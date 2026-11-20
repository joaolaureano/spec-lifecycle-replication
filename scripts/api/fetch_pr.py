"""RQ2 (spec decay): busca na API do GitHub a lista de arquivos de cada PR sorteado, com o diff (`patch`) de cada arquivo.

Protocolo (funções em github_api.py): token só em memória, repo/PR validados por regex,
gravação atômica em data/api_pr_diffs/raw/<owner>__<repo>/pr<N>.json.gz, manifesto só com acréscimos (sha256),
e-mails/assinaturas/avatares removidos, retomável.
Entrada: data/api_pr_diffs/sample/pares.csv (gerado por scripts/analysis/spec_rot_viabilidade.py).
Uso: .venv/bin/python -I scripts/api/fetch_pr.py
"""
import csv, gzip, hashlib, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from github_api import agora, esperar_limite, get, gravar_atomico, limpar, RE_REPO, ROOT

BASE = os.path.join(ROOT, "data", "api_pr_diffs")
RAW = os.path.join(BASE, "raw")
MANIFEST = os.path.join(BASE, "manifest.jsonl")
LISTA = os.path.join(BASE, "sample", "pares.csv")
RE_PR = re.compile(r"^[0-9]{1,7}$")
MAX_PAGINAS = 30  # 100 arquivos por página; a API para em 3.000


def registrar(linha):
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def buscar(repo, pr, token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr}/files?per_page=100"
    arquivos, paginas, status = [], 0, None
    while url and paginas < MAX_PAGINAS:
        for tentativa in range(4):
            try:
                status, h, raw = get(url, token)
            except OSError as e:
                status, h, raw = -1, {}, str(e).encode()
            if esperar_limite(status, h, tentativa):
                continue
            if status == -1 or status >= 500:
                time.sleep(5 * (tentativa + 1))
                continue
            break
        if status != 200:
            return status, None
        arquivos.extend(json.loads(raw))
        paginas += 1
        m = re.search(r'<([^>]+)>;\s*rel="next"', h.get("Link", "") or "")
        url = m.group(1) if m and m.group(1).startswith("https://api.github.com/") else None
    return 200, limpar({"repo": repo, "pr": int(pr), "files": arquivos,
                        "_coleta": {"paginas": paginas, "truncado": bool(url), "coletado_em": agora()}})


def main():
    global BASE, RAW, MANIFEST, LISTA
    if "--base" in sys.argv:
        BASE = os.path.join(ROOT, "data", sys.argv[sys.argv.index("--base") + 1])
        RAW, MANIFEST, LISTA = os.path.join(BASE, "raw"), os.path.join(BASE, "manifest.jsonl"), os.path.join(BASE, "sample", "pares.csv")
    original = os.path.join(ROOT, "data", "api_pr_diffs", "raw")
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    os.makedirs(RAW, exist_ok=True)
    feitos = set()
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            feitos = {(r["repo"], str(r["pr"])) for r in map(json.loads, f) if r["http"] in (200, 404, 410, 422, 451)}
    with open(LISTA, newline="") as f:
        prs = sorted({(r["repo_name"], r["pr_number"]) for r in csv.DictReader(f)})
    ok = 0
    for repo, pr in prs:
        if (repo, pr) in feitos or os.path.exists(os.path.join(original, repo.replace("/", "__"), f"pr{pr}.json.gz")):
            continue  # já coletado (nesta base ou na coleta original)
        if not RE_REPO.match(repo) or ".." in repo or not RE_PR.match(pr):
            registrar({"repo": repo, "pr": pr, "http": 0, "status": "entrada_invalida"})
            continue
        status, corpo = buscar(repo, pr, token)
        linha = {"repo": repo, "pr": int(pr), "http": status, "coletado_em": agora()}
        if status == 200:
            d = os.path.join(RAW, repo.replace("/", "__"))
            os.makedirs(d, exist_ok=True)
            destino = os.path.join(d, f"pr{int(pr)}.json.gz")
            dados = gzip.compress(json.dumps(corpo, ensure_ascii=False).encode("utf-8"), mtime=0)
            gravar_atomico(destino, dados)
            linha.update(n_arquivos=len(corpo["files"]), truncado=corpo["_coleta"]["truncado"],
                         sha256=hashlib.sha256(dados).hexdigest(), arquivo=os.path.relpath(destino, BASE))
            ok += 1
        registrar(linha)
        time.sleep(0.2)
    print(f"fim: {ok} PRs gravados nesta execução (de {len(prs)} na lista)")


if __name__ == "__main__":
    sys.exit(main())
