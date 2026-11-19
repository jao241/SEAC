# ChatBot inspirado no Simplifica Conquista

Sistema especialista acadêmico para atendimento em um domínio fictício. O chat usa Gemini para orientar sobre serviços. As ferramentas MCP encaminham cadastro, registro e consulta por HTTP para uma API de domínio, que aplica as regras de atendimento e acessa o SQLite. O cache semântico combina Sentence Transformers e ChromaDB.

## Iniciar

É necessário ter Docker e Docker Compose, acesso à internet e uma chave do Gemini.

1. Copie `.env.example` para `.env` e preencha `GOOGLE_API_KEY`.
2. Execute `docker compose up --build -d`.
3. Acesse [http://localhost:8080](http://localhost:8080).

Na primeira execução, o modelo de embeddings é baixado para um volume Docker. Os modelos de assistente e julgador podem ser alterados no arquivo `.env`. O servidor MCP e a API de domínio ficam na rede interna do Compose. O volume SQLite é montado no serviço `dominio`.

## Usar a demonstração

No chat, pergunte sobre a plataforma e os serviços, solicite um cadastro ou uma solicitação e informe um protocolo para consultar o andamento. O assistente solicitará os dados necessários e acionará as ferramentas MCP. Os botões laterais também permitem executar essas operações. Utilize apenas nomes, identificadores e locais fictícios. Para cadastro e registro, confira o resumo e confirme antes de gravar. Na conversa, use os botões de confirmação ou cancelamento apresentados abaixo do resumo. Guarde o código de cadastro para abrir uma solicitação e o protocolo para consultá-la.

O cache armazena perguntas e respostas que não utilizaram ferramentas MCP. Para cada mensagem, a busca semântica procura a pergunta mais próxima no cache e retorna a resposta diretamente quando a distância de cosseno é de até 0,35. Caso não encontre uma resposta dentro do limite, a mensagem segue para o Gemini, que pode acionar ferramentas MCP. O cache armazena apenas a pergunta e a resposta e também funciona durante uma conversa.

## Verificação e avaliação

```sh
docker compose exec web python -m app.verificar
docker compose exec web python -m app.julgamento
```

O julgador executa cenários de orientação, avalia as respostas com outro modelo e inclui uma resposta incorreta de controle. O resultado é impresso em JSON, com veredito, justificativa e eventuais erros por caso. A execução usa a chave Gemini configurada.

Para parar os serviços, execute `docker compose down`. Os volumes de SQLite, cache e embeddings permanecem. Para reiniciar toda a demonstração e apagar esses dados, execute `docker compose down -v`.

Os serviços, requisitos, cadastros e protocolos são fictícios e a aplicação não possui integração com o simplifica conquista.
