"""Funções comuns da coleta na API do GitHub (usadas por fetch_pr.py).

Segurança/robustez: token só em memória (nunca gravado nem impresso); repo validado por regex antes de virar URL ou
caminho; gravação atômica (temporário + fsync + os.replace); e-mails, assinaturas e avatares removidos antes de gravar.
"""
import datetime, os, re, time, urllib.error, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REMOVER = {"email", "signature", "payload", "avatar_url", "gravatar_id"}


def agora():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def limpar(o):
    if isinstance(o, dict):
        return {k: limpar(v) for k, v in o.items() if k not in REMOVER}
    if isinstance(o, list):
        return [limpar(v) for v in o]
    return o


def gravar_atomico(caminho, dados):
    tmp = caminho + ".tmp"
    with open(tmp, "wb") as f:
        f.write(dados)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


def get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "specmine-msr-sample"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def esperar_limite(status, h, tentativa):
    """403/429 por limite: dorme até o reset (primário) ou recua (secundário). Devolve True se deve tentar de novo."""
    if status not in (403, 429):
        return False
    if h.get("X-RateLimit-Remaining") == "0":
        pausa = max(int(h.get("X-RateLimit-Reset", time.time() + 60)) - time.time(), 0) + 5
    else:
        pausa = int(h.get("Retry-After", 60 * (tentativa + 1)))
    print(f"  limite da API ({status}); pausa de {int(pausa)} s", flush=True)
    time.sleep(pausa)
    return True
