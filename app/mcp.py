import os

import httpx
from fastmcp import FastMCP
from starlette.responses import PlainTextResponse

DOMINIO_URL = os.getenv("DOMINIO_URL", "http://dominio:8001")
mcp = FastMCP("Simplifica Conquista")


async def chamar_dominio(metodo, caminho, *, json=None, params=None):
    try:
        async with httpx.AsyncClient(base_url=DOMINIO_URL, timeout=15) as cliente:
            resposta = await cliente.request(metodo, caminho, json=json, params=params)
            if resposta.status_code != 400:
                resposta.raise_for_status()
            return resposta.json()
    except httpx.HTTPError as erro:
        raise RuntimeError("A API de domínio não conseguiu concluir a operação.") from erro


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return PlainTextResponse("ok")


@mcp.tool
async def cadastrar_cidadao(nome: str, identificador: str) -> dict:
    """Cadastra um cidadão fictício, ou retorna o cadastro existente."""
    return await chamar_dominio("POST", "/cidadaos", json={"nome": nome, "identificador": identificador})


@mcp.tool
async def registrar_solicitacao(cidadao: str, servico: str, local: str, operacao: str) -> dict:
    """Registra uma solicitação fictícia com uma chave única de operação."""
    dados = {"cidadao": cidadao, "servico": servico, "local": local, "operacao": operacao}
    return await chamar_dominio("POST", "/solicitacoes", json=dados)


@mcp.tool
async def consultar_protocolo(protocolo: str) -> dict:
    """Consulta o andamento atual de uma solicitação fictícia."""
    return await chamar_dominio("GET", "/protocolos", params={"protocolo": protocolo})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
