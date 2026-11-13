"""Verifica MCP, embeddings e, quando configurado, os modelos Gemini."""
import asyncio
import os

from fastmcp import Client
from google import genai
from sentence_transformers import SentenceTransformer


async def main():
    async with Client(os.environ["MCP_URL"]) as cliente:
        ferramentas = await cliente.list_tools()
        print(f"MCP conectado: {len(ferramentas)} ferramentas")
    modelo = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print(f"Embeddings carregados: {len(modelo.encode('Olá'))} dimensões")
    chave = os.getenv("GOOGLE_API_KEY")
    if not chave:
        print("Gemini não verificado: GOOGLE_API_KEY ausente.")
        return
    cliente = genai.Client(api_key=chave)
    try:
        for variavel in ("GEMINI_ASSISTANT_MODEL", "GEMINI_JUDGE_MODEL"):
            nome = os.environ[variavel]
            resposta = await cliente.aio.interactions.create(model=nome, input="Responda apenas OK.", store=False)
            if not resposta.output_text:
                raise RuntimeError(f"Modelo {nome} retornou resposta vazia")
            print(f"Modelo {nome}: resposta recebida")
    finally:
        await cliente.aio.aclose()


if __name__ == "__main__":
    asyncio.run(main())
