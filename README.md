# Simplifica Conquista

Ambiente inicial para o sistema especialista acadêmico. Esta etapa fornece os serviços web e MCP e uma verificação das dependências.

Copie `.env.example` para `.env` e configure `GOOGLE_API_KEY`. Instale Docker e Docker Compose e execute:

```sh
docker compose up --build -d
docker compose exec web python -m app.verificar
```

O serviço web responde em http://localhost:8080/health. A verificação conecta ao MCP, baixa o modelo de embeddings na primeira execução e testa os dois modelos Gemini quando a chave estiver configurada. O download e as chamadas Gemini exigem acesso à internet. Os volumes preservam os dados e o modelo baixado. Para parar os serviços, use `docker compose down`.
