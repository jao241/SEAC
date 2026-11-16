from fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from app import dominio

mcp = FastMCP("Simplifica Conquista")


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return PlainTextResponse("ok")


@mcp.tool
def cadastrar_cidadao(nome: str, identificador: str) -> dict:
    """Cadastra um cidadão fictício, ou retorna o cadastro existente."""
    try:
        return {"ok": True, **dominio.cadastrar(nome, identificador)}
    except ValueError as erro:
        return {"ok": False, "erro": str(erro)}


@mcp.tool
def registrar_solicitacao(cidadao: str, servico: str, local: str, operacao: str) -> dict:
    """Registra uma solicitação fictícia com uma chave única de operação."""
    try:
        return {"ok": True, **dominio.registrar(cidadao, servico, local, operacao)}
    except ValueError as erro:
        return {"ok": False, "erro": str(erro)}


@mcp.tool
def consultar_protocolo(protocolo: str) -> dict:
    """Consulta o andamento atual de uma solicitação fictícia."""
    try:
        return {"ok": True, **dominio.consultar(protocolo)}
    except ValueError as erro:
        return {"ok": False, "erro": str(erro)}


if __name__ == "__main__":
    dominio.iniciar()
    mcp.run(transport="http", host="0.0.0.0", port=8000)
