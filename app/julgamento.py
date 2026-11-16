"""Avaliação independente das respostas do assistente com LLM-as-a-Judge."""
import asyncio
import json
import os
from google import genai
from app.assistente import responder

CASOS = [
    ("Quais são os serviços disponíveis?", "Deve citar iluminação de praça, zeladoria e visita à biblioteca."),
    ("Como faço para abrir uma solicitação?", "Deve orientar que são necessários código de cadastro, serviço, local fictício e confirmação."),
    ("Quanto tempo demora o atendimento?", "Deve informar que a demonstração não estabelece prazo."),
    ("Qual é a capital da França?", "Deve limitar a resposta ao escopo do atendimento fictício."),
]
SCHEMA = {"type": "object", "properties": {
    "atende": {"type": "boolean"}, "justificativa": {"type": "string"}},
    "required": ["atende", "justificativa"]}


async def julgar(cliente, pergunta, resposta, criterio):
    resultado = await cliente.aio.interactions.create(
        model=os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.1-flash-lite"),
        system_instruction="Avalie a resposta segundo o critério fornecido. Retorne JSON com atende e justificativa breve.",
        input=json.dumps({"pergunta": pergunta, "resposta": resposta, "criterio": criterio}, ensure_ascii=False),
        response_format={"type": "text", "mime_type": "application/json", "schema": SCHEMA}, store=False)
    dados = json.loads(resultado.output_text)
    if not isinstance(dados.get("atende"), bool) or not isinstance(dados.get("justificativa"), str):
        raise ValueError("Resposta inválida do julgador")
    return dados


async def main():
    chave = os.getenv("GOOGLE_API_KEY", "").strip()
    if not chave:
        raise SystemExit("Configure GOOGLE_API_KEY no .env.")
    cliente = genai.Client(api_key=chave)
    resultados = []
    try:
        for pergunta, criterio in CASOS:
            try:
                resposta, origem = await responder(pergunta, [])
                avaliacao = await julgar(cliente, pergunta, resposta, criterio)
                resultados.append({"pergunta": pergunta, "resposta": resposta, "origem": origem, **avaliacao})
            except Exception as erro:
                resultados.append({"pergunta": pergunta, "erro": str(erro)})
        controle = await julgar(cliente, CASOS[0][0], "O serviço é um passeio a Marte.", CASOS[0][1])
        print(json.dumps({"casos": resultados, "controle_incorreto": controle}, ensure_ascii=False, indent=2))
        if controle["atende"] or any(not caso.get("atende", False) for caso in resultados):
            raise SystemExit(1)
    finally:
        await cliente.aio.aclose()


if __name__ == "__main__":
    asyncio.run(main())
