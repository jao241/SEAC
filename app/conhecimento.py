import json
from pathlib import Path

CONHECIMENTO = json.loads(Path(__file__).with_name("conhecimento.json").read_text(encoding="utf-8"))
SERVICOS = {item["codigo"]: item for item in CONHECIMENTO["servicos"]}


def campo(valor, nome, limite=120):
    valor = " ".join(valor.strip().split())
    if not 2 <= len(valor) <= limite:
        raise ValueError(f"Informe {nome} com 2 a {limite} caracteres.")
    return valor
