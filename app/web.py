import asyncio
import secrets
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.assistente import ferramenta, responder
from app.dominio import CONHECIMENTO, SERVICOS, campo

app = FastAPI(title="Simplifica Conquista")
app.mount("/static", StaticFiles(directory=Path(__file__).with_name("static")), name="static")
pendentes = {}


class Mensagem(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    historico: list[dict] = Field(default_factory=list, max_length=12)


class Acao(BaseModel):
    tipo: str
    dados: dict


class Confirmacao(BaseModel):
    token: str


@app.get("/")
async def inicio():
    return FileResponse(Path(__file__).with_name("static") / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/servicos")
async def servicos():
    return CONHECIMENTO["servicos"]


@app.post("/api/chat")
async def chat(entrada: Mensagem):
    historico = []
    for item in entrada.historico:
        if item.get("papel") not in ("usuario", "assistente") or not isinstance(item.get("texto"), str):
            raise HTTPException(400, "Histórico inválido.")
        historico.append({"type": "user_input" if item["papel"] == "usuario" else "model_output",
                          "content": [{"type": "text", "text": item["texto"][:2000]}]})
    try:
        propostas = []

        async def preparar_conversa(tipo, dados):
            if propostas:
                return {"ok": False, "erro": "Conclua a confirmação pendente antes de iniciar outra operação."}
            proposta = await preparar(Acao(tipo=tipo, dados=dados))
            propostas.append(proposta)
            return {"ok": True, "aguardando_confirmacao": True, "resumo": proposta["resumo"]}

        texto, origem = await responder(entrada.mensagem.strip(), historico, preparar_conversa)
        return {"resposta": texto, "origem": origem, "confirmacao": propostas[0] if propostas else None}
    except Exception:
        raise HTTPException(503, "Não foi possível obter uma resposta. Verifique a configuração do Gemini e tente novamente.")


@app.post("/api/acao")
async def preparar(entrada: Acao):
    dados = entrada.dados
    try:
        if entrada.tipo == "consulta":
            resultado = await ferramenta("consultar_protocolo", {"protocolo": str(dados.get("protocolo", ""))})
            return {"resultado": resultado}
        if entrada.tipo == "cadastro":
            argumentos = {"nome": campo(str(dados.get("nome", "")), "o nome"),
                          "identificador": campo(str(dados.get("identificador", "")), "o identificador", 60)}
            nome = "cadastrar_cidadao"
            resumo = f"Cadastro de {argumentos['nome']}, identificador {argumentos['identificador']}"
        elif entrada.tipo == "solicitacao":
            codigo = str(dados.get("servico", ""))
            if codigo not in SERVICOS:
                raise ValueError("Selecione um serviço válido.")
            argumentos = {"cidadao": campo(str(dados.get("cidadao", "")), "o código de cadastro", 30).upper(),
                          "servico": codigo, "local": campo(str(dados.get("local", "")), "o local"),
                          "operacao": str(uuid4())}
            nome = "registrar_solicitacao"
            resumo = f"{SERVICOS[codigo]['nome']} em {argumentos['local']}, cadastro {argumentos['cidadao']}"
        else:
            raise ValueError("Ação inválida.")
    except ValueError as erro:
        raise HTTPException(400, str(erro))
    except Exception:
        raise HTTPException(503, "Serviço de ferramentas indisponível.")
    agora = time.monotonic()
    for token, registro in list(pendentes.items()):
        if registro["expira"] < agora:
            del pendentes[token]
    token = secrets.token_urlsafe(32)
    pendentes[token] = {"nome": nome, "argumentos": argumentos, "expira": agora + 1800, "lock": asyncio.Lock()}
    return {"token": token, "resumo": resumo}


@app.post("/api/confirmar")
async def confirmar(entrada: Confirmacao):
    registro = pendentes.get(entrada.token)
    if not registro or registro["expira"] < time.monotonic():
        raise HTTPException(400, "Confirmação expirada. Prepare a operação novamente.")
    async with registro["lock"]:
        if "resultado" not in registro:
            try:
                registro["resultado"] = await ferramenta(registro["nome"], registro["argumentos"])
            except Exception:
                raise HTTPException(503, "Não foi possível concluir a operação. Tente confirmar novamente.")
        return {"resultado": registro["resultado"]}


@app.post("/api/cancelar")
async def cancelar(entrada: Confirmacao):
    pendentes.pop(entrada.token, None)
    return {"cancelado": True}
