"""Executa um notebook e grava as saídas nele (padrão: numeros_do_paper.ipynb, usado por scripts/reproduzir.sh).
Falha se alguma célula falhar, inclusive a conferência contra paper/main.tex quando o paper existe.
Uso: .venv/bin/python -I scripts/executar_notebook.py [notebook.ipynb]   (pipeline.ipynb roda o pipeline inteiro)
"""
import os, sys
import nbformat
from nbclient import NotebookClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NB = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "numeros_do_paper.ipynb")
nb = nbformat.read(NB, as_version=4)
NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": ROOT}}).execute()
nbformat.write(nb, NB)
final = [c for c in nb.cells if c.cell_type == "code"][-1]
print("".join(o.get("text", "") for o in final.get("outputs", []) if o.get("output_type") == "stream"), end="")
print(f"ok: {sum(c.cell_type == 'code' for c in nb.cells)} células executadas -> {os.path.basename(NB)}")
