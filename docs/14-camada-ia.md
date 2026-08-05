# Camada de inteligência artificial

## Objetivo e limites

O Growth Agent gera alternativas estruturadas usando somente o cliente resolvido pela sessão.
Ele não publica, aprova, compra nem executa ações externas. Toda saída é um rascunho, e conteúdo
veterinário sensível continua exigindo revisão profissional.

Ordem de fallback: OpenRouter gratuito, Ollama local chamado pelo adapter Hermes e mock. O mock
permanece obrigatório, determinístico e cobre desenvolvimento, testes e E2E sem internet.

## Contrato encontrado no Hermes local

A auditoria somente de leitura foi feita em 4 de agosto de 2026 no projeto local `Hermes Mobile`,
commit `d547986` da branch `main`.

- Base documentada: `http://localhost:8787` (bind padrão `127.0.0.1`).
- Saúde pública: `GET /health`, resposta `{"data":{"ok":true,"service":"hermes-mobile-api"}}`.
- Chat existente: `POST /api/chat`, privado, com bearer de sessão local. Recebe `text`,
  `sessionId` opcional e `confirmationStatus` opcional. Ele persiste uma resposta fixa; não gera
  texto com modelo.
- Não existem `/v1/chat/completions`, compatibilidade OpenAI, seleção/listagem de modelos nem
  ligação com Ollama no código e na documentação auditados.
- O Hermes não estava em execução. Ollama não estava instalado, a porta `11434` estava fechada e
  `qwen3:4b-instruct` não pôde ser encontrado neste computador.

Por isso o `HermesProvider` do GrowthOS não chama o chat persistente do Hermes Mobile. Ele usa o
contrato HTTP nativo e opcional do Ollama:

- disponibilidade/modelos: `GET {HERMES_BASE_URL}/api/tags`;
- geração: `POST {HERMES_BASE_URL}/api/chat`;
- autenticação: nenhuma no padrão local; a URL não deve ser exposta em rede não confiável;
- modelo: campo `model`, padrão `qwen3:4b-instruct`;
- timeout e tentativas: `HERMES_TIMEOUT_SECONDS` e `HERMES_MAX_ATTEMPTS`.

Exemplo de request Ollama:

```json
{
  "model": "qwen3:4b-instruct",
  "stream": false,
  "format": "json",
  "messages": [
    {"role": "system", "content": "Retorne JSON estruturado."},
    {"role": "user", "content": "Contexto e tarefa do cliente autorizado"}
  ],
  "options": {"num_predict": 2000}
}
```

Exemplo de response esperado:

```json
{
  "model": "qwen3:4b-instruct",
  "message": {
    "role": "assistant",
    "content": "{\"alternatives\":[{\"title\":\"Título\",\"caption\":\"Legenda\"}]}"
  },
  "prompt_eval_count": 420,
  "eval_count": 180,
  "done": true
}
```

## Configuração

No ambiente local do piloto, a preferência externa nasce ativa, mas o OpenRouter só entra na cadeia
quando `OPENROUTER_API_KEY` também está preenchida. A chave existe somente no `.env` ignorado e
nunca é retornada, persistida ou enviada ao frontend. `OPENROUTER_MODEL=openrouter/free` permite
roteamento gratuito, mas disponibilidade, rate limit e gratuidade são decisões do serviço externo;
não há gasto ou upgrade automático.

O limite diário é por organização. Os limites de entrada e saída são aplicados antes da chamada e
no provider. Custo só é persistido quando informado de forma confiável; caso contrário fica nulo.

## API do GrowthOS

- `POST/GET /api/v1/businesses/{business_id}/ai/generations`;
- `GET /api/v1/ai/generations/{id}`;
- `POST /api/v1/ai/generations/{id}/regenerate`;
- `POST /api/v1/ai/generations/{id}/feedback`;
- `GET /api/v1/ai/status` e `GET /api/v1/ai/usage`.

As respostas registram provider, modelo, duração, tokens, fallback e sensibilidade. Prompts completos
não entram em logs. O snapshot de contexto é tenant-scoped e minimizado: contém Brand Kit sem
notas internas, serviços, públicos, objetivos e até três estratégias aprovadas do mesmo cliente.

## Riscos conhecidos

- o Hermes Mobile atual não é um gateway de modelos; chamar seu `/api/chat` seria um contrato errado;
- `qwen3:4b-instruct` precisa ser instalado e validado separadamente no Ollama;
- modelos gratuitos do OpenRouter podem mudar, ficar indisponíveis ou aplicar limites;
- JSON de modelo pode ser inválido e é rejeitado antes de persistir como alternativa;
- envio a provider externo implica transferência de contexto da marca e exige decisão operacional,
  base legal e revisão de privacidade antes de dados reais.

Recomendação: usar OpenRouter Free no piloto somente com chave local, aceite explícito do tratamento
externo e monitoramento dos limites. Instalar/testar Ollama quando houver hardware adequado e manter
o mock como último fallback verificável.
