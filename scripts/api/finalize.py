"""Fecha a coleta: confere integridade, gera SHA256SUMS, faz backup compactado e trava os brutos (somente leitura).

Uso: .venv/bin/python -I scripts/api/finalize.py <pasta em data/, ex.: api_pr_diffs>
Falha (exit 1) se algum arquivo do manifesto não existir ou não bater com o sha256 registrado.
"""
import datetime, hashlib, json, os, stat, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE = os.path.join(ROOT, "data", sys.argv[1])


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main():
    with open(os.path.join(BASE, "manifest.jsonl"), encoding="utf-8") as f:
        man = [json.loads(l) for l in f]
    ok = {}
    for r in man:
        if r.get("http") == 200:
            ok[r["arquivo"]] = r["sha256"]  # a última tentativa vale
    erros = [a for a, h in ok.items() if not os.path.exists(os.path.join(BASE, a)) or sha256(os.path.join(BASE, a)) != h]
    if erros:
        print(f"ERRO de integridade em {len(erros)} arquivos, ex.: {erros[:3]}")
        return 1
    with open(os.path.join(BASE, "SHA256SUMS"), "w") as f:
        for a in sorted(ok):
            f.write(f"{ok[a]}  {a}\n")
    os.makedirs(os.path.join(BASE, "backup"), exist_ok=True)
    nome = f"coleta_{datetime.date.today().isoformat()}.tar.gz"
    destino = os.path.join(BASE, "backup", nome)
    with tarfile.open(destino + ".tmp", "w:gz") as t:
        for item in ["raw", "manifest.jsonl", "sample", "SHA256SUMS", "README.md"]:
            if os.path.exists(os.path.join(BASE, item)):
                t.add(os.path.join(BASE, item), arcname=item)
    os.replace(destino + ".tmp", destino)
    with open(destino + ".sha256", "w") as f:
        f.write(f"{sha256(destino)}  {nome}\n")
    # somente leitura: brutos, manifesto, amostra e backup
    so_leitura = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    for raiz in ["raw", "sample", "backup"]:
        for d, _, arqs in os.walk(os.path.join(BASE, raiz)):
            for a in arqs:
                os.chmod(os.path.join(d, a), so_leitura)
    os.chmod(os.path.join(BASE, "manifest.jsonl"), so_leitura)
    print(f"ok: {len(ok)} brutos conferidos; SHA256SUMS e backup/{nome} gravados; arquivos travados (somente leitura)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
