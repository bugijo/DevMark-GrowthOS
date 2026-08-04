# ADR 0005 — Rate limiting compartilhado e proxies confiáveis

- **Status:** aceita para a Fase 3
- **Data:** 2026-07-16
- **Decisão relacionada:** hardening operacional da versão 1.0

## Contexto

A fundação limita login, convite e recuperação em memória. Esse adaptador é
adequado para uma instância local, mas cada réplica mantém sua própria janela e
um atacante pode distribuir tentativas entre processos. Além disso, usar
diretamente o endereço observado pela aplicação pode agrupar todos os usuários
sob o endereço do proxy ou, se headers encaminhados forem aceitos sem validação,
permitir que o cliente escolha o próprio IP aparente.

A versão 1.0 precisa funcionar sem Redis e sem novo serviço obrigatório. O
PostgreSQL já é a fonte transacional compartilhada e atende a escala do piloto.

## Decisão

Usar PostgreSQL como armazenamento compartilhado das janelas de rate limiting
da versão 1.0, atrás de um contrato interno `RateLimitStore`.

- Chaves de identidade, origem e token são transformadas por HMAC antes da
  persistência; e-mail e IP puros não são armazenados.
- O registro e a consulta do orçamento usam operação atômica e devolvem um
  `Retry-After` coerente entre processos.
- Janelas expiradas são removidas em lotes limitados. A tabela não é audit log e
  possui retenção curta.
- O adaptador em memória continua disponível para testes unitários isolados,
  mas produção recusa inicialização com esse backend.
- Falha do store em uma rota protegida falha fechado com erro temporário seguro;
  não libera tentativas ilimitadas.

Headers de origem encaminhados só serão considerados quando:

1. `TRUST_PROXY_HEADERS=true` estiver configurado;
2. o peer imediato pertencer a uma lista explícita de CIDRs confiáveis;
3. a cadeia tiver tamanho limitado e endereços válidos;
4. a aplicação selecionar o primeiro endereço não confiável da cadeia.

Por padrão, headers encaminhados são ignorados. Redes universais como
`0.0.0.0/0` e `::/0` são rejeitadas em produção. O proxy do frontend encaminha
somente headers permitidos e nunca replica cegamente valores fornecidos pelo
navegador.

## Motivos

- Mantém a topologia aprovada e não adiciona Redis antes de existir carga que o
  justifique.
- Faz múltiplas réplicas compartilharem o mesmo orçamento de abuso.
- Evita armazenar identificadores pessoais em claro na tabela operacional.
- Torna a confiança no proxy explícita, testável e negada por padrão.

## Consequências positivas

- Tentativas distribuídas não contornam o limite por processo.
- `Retry-After` permanece consistente entre instâncias.
- Spoof de `X-Forwarded-For` por cliente direto não muda a chave de origem.
- A decisão pode evoluir para Redis preservando o contrato e os casos de uso.

## Custos e mitigação

| Custo/risco | Mitigação |
| --- | --- |
| A tabela pode receber muitas escritas durante ataque | HMAC curto, chave primária indexada, transações pequenas, janela/cleanup limitados e monitoramento |
| Banco indisponível também afeta a proteção | Rotas autenticáveis já dependem do banco; falhar fechado e retornar erro temporário |
| Configuração incorreta do proxy pode agrupar usuários | confiança desativada por padrão, CIDRs explícitos, diagnóstico em `make doctor` e testes |
| IP é dado pessoal em alguns contextos | não persistir IP puro, retenção curta e finalidade exclusiva de segurança |

## Alternativas consideradas

### Manter somente memória

Rejeitada para o piloto real porque não funciona entre réplicas e perde estado a
cada reinício.

### Adicionar Redis obrigatório

Adiada. É uma solução adequada para volume maior, porém adicionaria serviço,
backup, monitoramento e operação antes de existir evidência de necessidade.

### Confiar sempre em `X-Forwarded-For`

Rejeitada. Um cliente direto poderia forjar a origem e contornar limites ou
atribuir tentativas a terceiros.

### Usar apenas o peer imediato

Permanece como padrão seguro quando a confiança em proxy está desligada. Em um
deploy atrás de proxy, entretanto, pode aplicar orçamento coletivo e precisa da
configuração explícita descrita nesta decisão.

## Verificação

- duas instâncias do store observam e bloqueiam a mesma janela;
- concorrência não perde incrementos nem ultrapassa silenciosamente o limite;
- valores persistidos não contêm e-mail, token ou IP em claro;
- janela expirada volta a permitir a operação e pode ser removida pelo cleanup;
- produção rejeita backend em memória e CIDR universal;
- header encaminhado de peer não confiável é ignorado;
- cadeia válida de proxy confiável resolve a origem esperada para IPv4 e IPv6;
- mensagens e logs não expõem a chave original.

## Critérios de reavaliação

Reavaliar o armazenamento quando medições mostrarem contenção relevante no
PostgreSQL, quando a aplicação adotar muitas réplicas ou quando uma plataforma
gerenciada já fornecer rate limiting consistente na borda. Uma troca deve
preservar HMAC, semântica de janela, `Retry-After`, negação por padrão e testes
entre instâncias.

