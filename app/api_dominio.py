from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import dominio


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    dominio.iniciar()
    yield


app = FastAPI(title="Domínio do Simplifica Conquista", lifespan=ciclo_de_vida)


class Cadastro(BaseModel):
    nome: str
    identificador: str


class Solicitacao(BaseModel):
    cidadao: str
    servico: str
    local: str
    operacao: str


@app.exception_handler(ValueError)
async def erro_de_dominio(request: Request, erro: ValueError):
    return JSONResponse(status_code=400, content={"ok": False, "erro": str(erro)})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/cidadaos")
def cadastrar(entrada: Cadastro):
    return {"ok": True, **dominio.cadastrar(entrada.nome, entrada.identificador)}


@app.post("/solicitacoes")
def registrar(entrada: Solicitacao):
    resultado = dominio.registrar(entrada.cidadao, entrada.servico, entrada.local, entrada.operacao)
    return {"ok": True, **resultado}


@app.get("/protocolos")
def consultar(protocolo: str):
    return {"ok": True, **dominio.consultar(protocolo)}
