# Plano de execução — Sistema especialista Simplifica Conquista

Trabalho individual de Sistema Especialista para Web do IFBA, com **tema aprovado** e entrega em **20/11/2026**. A etapa atual é o desenvolvimento e a validação da solução. A redação do capítulo começa após a conclusão dessa etapa.

## 1. Materiais analisados e decisões de escopo

- O [arquivo de avaliação](documentos/IFBA-Especialistas-Avaliacao-v4-1.md) exige chat, LLM como motor de inferência, cache semântico, ferramentas MCP e um script separado de LLM-as-a-Judge. O código funcionando vale 3 pontos, o vídeo vale 2 e o capítulo vale 5. A implementação será autoral, conforme a regra sobre o ProgBot.
- O [tema aprovado](documentos/tema.md) abrange esclarecer dúvidas, orientar sobre serviços, auxiliar no cadastro e na abertura de solicitações e consultar o andamento por protocolo. O mini-mundo será um atendimento acadêmico com catálogo, regras, cidadãos, solicitações e protocolos integralmente fictícios, sem integração com sistemas municipais.
- A [aplicação de referência](documentos/aplicacao-referencia/README.md) usa Python assíncrono, chat de terminal, base JSON, Gemini, MCP via Streamable HTTP, ChromaDB, Sentence Transformers e um julgador separado. O projeto mantém essa stack de inferência e acrescenta uma interface web e Docker Compose.

## 2. Arquitetura proposta

| Componente | Implementação planejada |
| --- | --- |
| Chat web | FastAPI para a API e a entrega da interface, com HTML, CSS e JavaScript no navegador. O chat terá histórico por sessão, estado de carregamento, mensagens de erro e controles de confirmação ou cancelamento quando houver uma operação pendente. |
| Inferência | Python com `asyncio` e `google-genai` via Interactions API, como em [`llm.py`](documentos/aplicacao-referencia/llm.py). Começar com `gemini-3.5-flash-lite`. Configurar a chave e o modelo pelo ambiente do backend. |
| Ferramentas MCP | Manter a stack Python/MCP e Streamable HTTP em `/mcp`, conforme [`ferramentas.py`](documentos/aplicacao-referencia/ferramentas.py). Expor `cadastrar_cidadao`, `registrar_solicitacao` e `consultar_protocolo`. Validar em contêiner os imports do SDK e a versão do FastMCP listada pela referência. |
| Conhecimento e dados | Catálogo, FAQ e casos de avaliação em JSON. Cadastro e solicitações persistidos com `sqlite3` da biblioteca padrão. Preparar registros de demonstração reproduzíveis, com identificadores próprios para cidadãos e protocolos fictícios. |
| Cache semântico | ChromaDB persistente, Sentence Transformers e embeddings multilíngues `paraphrase-multilingual-MiniLM-L12-v2`, como em [`cache.py`](documentos/aplicacao-referencia/cache.py). Usar distância de cosseno, calibrar o limiar inicial de 0,20 com paráfrases em português e versionar a coleção pela base de conhecimento. |
| Julgador | Script separado, seguindo a divisão de [`julgamento.py`](documentos/aplicacao-referencia/julgamento.py), com `gemini-3.1-flash-lite` como modelo inicial. Rodar sob demanda no Compose e avaliar o mesmo fluxo de atendimento usado pelo chat web. |
| Docker Compose | Serviços `web` e `mcp` em rede privada, com apenas a porta do chat publicada localmente. Usar volumes nomeados para SQLite e ChromaDB, configuração via `.env.example` e verificações de saúde. O backend terá saída para o Gemini e, quando necessário, para baixar o modelo de embeddings. |

Fluxo principal do navegador ao armazenamento:

```text
Navegador → API do chat → regras de atendimento → Gemini
                               ├─ FAQ elegível → cache ChromaDB
                               └─ operação → servidor MCP → SQLite
```

## 3. Jornadas e regras de atendimento

| Jornada | Regra | Resultado esperado no chat |
| --- | --- | --- |
| Dúvida ou orientação | Consultar a FAQ e um catálogo pequeno, com serviços, locais e requisitos inventados para a demonstração. Pedir esclarecimento quando a demanda for ambígua e orientar sobre o escopo quando o assunto estiver fora do catálogo. | Resposta em português, coerente com a base fictícia. |
| Cadastro | Coletar ou oferecer dados de um personagem fictício, apresentar o resumo e exigir confirmação explícita antes de acionar o MCP. | Código de cadastro de demonstração. Um cadastro duplicado recupera o registro existente. |
| Abertura de solicitação | Validar o cadastro, o serviço e seus requisitos, mostrar o resumo e aguardar confirmação. Vincular a confirmação àquela operação para tratar reenvios. | Protocolo gerado pelo servidor MCP. Repetir a confirmação devolve o mesmo protocolo. Cancelar encerra o fluxo sem gravar. |
| Consulta de andamento | Validar o formato e consultar o MCP a cada pedido de status. | Estado atual do registro em SQLite ou mensagem clara para protocolo inválido, inexistente ou serviço indisponível. |

O Gemini interpreta a intenção, usa o contexto da sessão e propõe a resposta ou chamada de ferramenta. O backend valida a operação e controla as gravações. A confirmação de sucesso e o protocolo vêm do retorno estruturado do MCP. O cache atende apenas a FAQs estáveis e independentes do contexto. Mensagens transacionais, dados de cadastro, protocolos, consultas de status e erros ficam fora da busca e da gravação no cache.

A interface terá indicação visível de ambiente acadêmico e exemplos que permitam testar as jornadas com dados fictícios. A massa de testes, o conteúdo encaminhado ao julgador e os exemplos do README seguirão a mesma premissa.

## 4. Ordem de execução

| Etapa | Trabalho previsto | Evidência para concluir |
| --- | --- | --- |
| 1. Ambiente reproduzível | Preparar `Dockerfile`, `compose.yaml`, dependências e configuração. Validar os dois modelos Gemini com a chave disponível, o transporte MCP e o carregamento dos embeddings em contêiner. | Build concluída, serviços acessíveis e dependências verificadas. |
| 2. Domínio e ferramentas | Criar catálogo, FAQ e dados fictícios de teste. Implementar SQLite, validação de argumentos e as três ferramentas MCP. | Cadastro, abertura e consulta testados por MCP. Registros persistem após recriar o contêiner com o volume. |
| 3. Inferência e chat web | Implementar o fluxo conversacional, regras, API e interface. Integrar confirmação e cancelamento e tratar indisponibilidade de dependências. | Pelo navegador, uma pessoa consegue obter orientação, cadastrar um personagem, abrir uma solicitação e consultar o protocolo. |
| 4. Cache e julgador | Integrar o cache, calibrar a similaridade e criar uma suíte de avaliação com expectativas independentes da FAQ. Executar o julgador sob demanda no Compose. | A primeira pergunta elegível usa o LLM, uma paráfrase usa o cache e a consulta de status lê o SQLite. O julgador produz um relatório por cenário e rejeita respostas incorretas de controle. |
| 5. Aceite da solução | Executar o roteiro ponta a ponta em ambiente limpo e revisar a documentação. | README reproduzível, interface verificada e evidências de inferência, ferramentas MCP, cache e julgador disponíveis para a apresentação. |

O README deverá documentar a configuração de `GOOGLE_API_KEY`, a inicialização com `docker compose up --build`, o acesso local pelo navegador, a execução do julgador, a carga inicial e a limpeza dos dados de demonstração. Esses comandos são pontos de entrada planejados.

## 5. Critérios de aceite

- **Interface web.** Enviar mensagens, acompanhar o histórico da sessão e completar as quatro jornadas no navegador. Testar layout em tela estreita, navegação por teclado e feedback de carregamento ou erro.
- **Regras e MCP.** Conferir cadastro duplicado, cancelamento, confirmação repetida, protocolo existente, inválido ou inexistente e indisponibilidade do MCP. Verificar os efeitos diretamente no banco, inclusive após recriar o contêiner.
- **Cache.** Confirmar acerto por paráfrase em uma nova sessão, rejeição de uma pergunta semelhante com intenção diferente e leitura atualizada de status após alterar um registro fictício.
- **LLM-as-a-Judge.** Usar cenários de orientação, ações via MCP, cache e falhas. Registrar veredito e justificativa por caso e separar erros de execução. Verificar chamadas, gravações e protocolos com checagens determinísticas além do julgamento do texto.
- **Docker Compose.** Reproduzir a instalação e o roteiro do README com volumes novos. Conferir persistência após reiniciar e uso da chave Gemini apenas nos processos que precisarem dela.

## 6. Entregas após a validação da solução

O prazo da disciplina continua sendo **20/11/2026**. Com a solução validada, preparar o capítulo em LaTeX no modelo do Classroom, com os nomes exatos das seções do exemplo. A meta é de 3 páginas, com limite de 4. Gravar o vídeo com som e imagem em até 8 minutos, mostrando o tema, a inicialização com Docker Compose, o chat web, o LLM, o cache, as ferramentas MCP e a execução do julgador. Publicar o código e o vídeo no Zenodo conforme a orientação da disciplina e incluir os links na seção *Reproducibilidade e Reuso*.
