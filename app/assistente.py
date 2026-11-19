import asyncio
import hashlib
import json
import logging
import os
import re
import unicodedata

from fastmcp import Client
from google import genai
from app.conhecimento import CONHECIMENTO

LOG = logging.getLogger(__name__)
MODELO = os.getenv("GEMINI_ASSISTANT_MODEL", "gemini-3.5-flash-lite")
MCP_URL = os.getenv("MCP_URL", "http://mcp:8000/mcp")
INSTRUCOES = """Você é um assistente de atendimento de uma plataforma acadêmica fictícia.
Responda em português com clareza e use somente a base de conhecimento fornecida.
Os serviços, cadastros e protocolos são fictícios. Não invente prazos, requisitos ou estados.
Use as ferramentas quando o usuário quiser cadastrar, registrar solicitação ou consultar um protocolo.
Para cadastro, solicite nome e identificador fictícios. Para solicitação, solicite código do cadastro, código do serviço e local fictício. Para consulta, solicite o protocolo.
Não invente dados. Quando faltarem dados, peça-os ao usuário. Os códigos dos serviços constam na base.
Cadastro e solicitação exigem confirmação na interface após a preparação. Nunca afirme que foram concluídos antes do resultado confirmado.
Quando uma ferramenta retornar erro, explique a falha com clareza.
Para perguntas fora do domínio, explique brevemente o escopo do atendimento.
Base de conhecimento: """ + json.dumps(CONHECIMENTO, ensure_ascii=False)


FERRAMENTAS = [
    {"type": "function", "name": "consultar_protocolo",
     "description": "Consulta no MCP o estado atual de um protocolo fictício informado pelo usuário.",
     "parameters": {"type": "object", "properties": {"protocolo": {"type": "string"}},
                    "required": ["protocolo"]}},
    {"type": "function", "name": "preparar_cadastro",
     "description": "Prepara a confirmação de um cadastro fictício com nome e identificador fornecidos pelo usuário.",
     "parameters": {"type": "object", "properties": {"nome": {"type": "string"}, "identificador": {"type": "string"}},
                    "required": ["nome", "identificador"]}},
    {"type": "function", "name": "preparar_solicitacao",
     "description": "Prepara a confirmação de solicitação fictícia com cadastro, serviço e local fornecidos pelo usuário.",
     "parameters": {"type": "object", "properties": {"cidadao": {"type": "string"}, "servico": {"type": "string"}, "local": {"type": "string"}},
                    "required": ["cidadao", "servico", "local"]}}
]


async def ferramenta(nome, argumentos):
    async with Client(MCP_URL, timeout=20) as cliente:
        resultado = await cliente.call_tool(nome, argumentos)
        if resultado.is_error:
            raise RuntimeError("Erro na ferramenta MCP")
        return resultado.data


class Cache:
    def __init__(self):
        self.modelo = None
        self.colecao = None
        self.lock = asyncio.Lock()

    def inicializar(self):
        if self.colecao is not None:
            return
        import chromadb
        from sentence_transformers import SentenceTransformer
        self.modelo = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
        versao = hashlib.sha256((json.dumps(CONHECIMENTO, sort_keys=True) + INSTRUCOES).encode()).hexdigest()[:12]
        colecao = chromadb.PersistentClient(path="/data/chroma").get_or_create_collection(
            "conversas-" + versao, configuration={"hnsw": {"space": "cosine"}})
        # Converte entradas anteriores e remove os históricos armazenados.
        antigas = colecao.get(include=["documents", "metadatas", "embeddings"])
        for indice, metadados in enumerate(antigas["metadatas"]):
            if "historico" not in metadados:
                continue
            pergunta = antigas["documents"][indice]
            identificador = id_pergunta(pergunta)
            antigo_id = antigas["ids"][indice]
            if antigo_id == identificador or not colecao.get(ids=[identificador])["ids"]:
                colecao.upsert(
                    ids=[identificador],
                    embeddings=[antigas["embeddings"][indice].tolist()],
                    documents=[pergunta],
                    metadatas=[{"resposta": metadados["resposta"]}],
                )
            if antigo_id != identificador:
                colecao.delete(ids=[antigo_id])
        self.colecao = colecao

    def buscar(self, pergunta):
        self.inicializar()
        if self.colecao.count() == 0:
            return []
        vetor = self.modelo.encode(pergunta, normalize_embeddings=True).tolist()
        resultado = self.colecao.query(
            query_embeddings=[vetor], n_results=1,
            include=["documents", "metadatas", "distances"],
        )
        candidatos = []
        for documento, metadados, distancia in zip(
            resultado["documents"][0], resultado["metadatas"][0], resultado["distances"][0]
        ):
            if distancia <= 0.35:
                candidatos.append({
                    "pergunta": documento,
                    "resposta": metadados["resposta"],
                    "distancia": distancia,
                })
        return candidatos

    def gravar(self, pergunta, resposta):
        self.inicializar()
        vetor = self.modelo.encode(pergunta, normalize_embeddings=True).tolist()
        self.colecao.upsert(
            ids=[id_pergunta(pergunta)], embeddings=[vetor], documents=[pergunta],
            metadatas=[{"resposta": resposta}],
        )

    async def executar(self, metodo, *args):
        async with self.lock:
            try:
                return await asyncio.to_thread(metodo, *args)
            except Exception:
                LOG.exception("Cache semântico indisponível")
                return None


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def id_pergunta(pergunta):
    palavras = re.findall(r"[a-z0-9]+", normalizar(pergunta))
    return hashlib.sha256(" ".join(palavras).encode()).hexdigest()


cache = Cache()


async def responder(pergunta, historico, preparar_acao=None):
    candidatos = await cache.executar(cache.buscar, pergunta)
    if candidatos:
        return candidatos[0]["resposta"], "cache"

    chave = os.getenv("GOOGLE_API_KEY", "").strip()
    if not chave:
        raise RuntimeError("Configure GOOGLE_API_KEY no arquivo .env para conversar com o assistente.")
    cliente = genai.Client(api_key=chave)
    mensagens = historico[-12:] + [{"type": "user_input", "content": [{"type": "text", "text": pergunta}]}]
    try:
        usou_ferramenta = False
        for _ in range(5):
            resposta = await asyncio.wait_for(cliente.aio.interactions.create(
                model=MODELO, input=mensagens, system_instruction=INSTRUCOES,
                tools=FERRAMENTAS, store=False), timeout=45)
            chamadas = [passo for passo in resposta.steps if passo.type == "function_call"]
            if not chamadas:
                texto = resposta.output_text
                if not texto:
                    raise RuntimeError("O modelo retornou uma resposta vazia.")
                if not usou_ferramenta:
                    await cache.executar(cache.gravar, pergunta, texto)
                return texto, "mcp" if usou_ferramenta else "llm"

            usou_ferramenta = True
            mensagens.extend(passo.model_dump(exclude_none=True) for passo in resposta.steps)
            for chamada in chamadas:
                try:
                    if chamada.name == "consultar_protocolo":
                        resultado = await ferramenta("consultar_protocolo", chamada.arguments)
                    elif chamada.name in ("preparar_cadastro", "preparar_solicitacao") and preparar_acao:
                        tipo = "cadastro" if chamada.name == "preparar_cadastro" else "solicitacao"
                        resultado = await preparar_acao(tipo, chamada.arguments)
                    else:
                        resultado = {"ok": False, "erro": "Operação indisponível nesta execução."}
                except Exception:
                    LOG.exception("Falha ao executar ferramenta %s", chamada.name)
                    resultado = {"ok": False, "erro": "Não foi possível executar a ferramenta. Tente novamente."}
                mensagens.append({"type": "function_result", "name": chamada.name, "call_id": chamada.id,
                                  "result": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]})
                if resultado.get("aguardando_confirmacao"):
                    return "Confira os dados abaixo e confirme para concluir a operação.", "mcp"
        raise RuntimeError("Limite de chamadas de ferramentas atingido.")
    finally:
        await cliente.aio.aclose()
