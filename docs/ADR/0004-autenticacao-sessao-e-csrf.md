# ADR 0004 — Sessão web com cookie HttpOnly e proteção CSRF

- Status: aceito
- Data: 2026-07-15
- Responsáveis: fundação do DevMark GrowthOS

## Contexto

O painel da agência e o portal do cliente são aplicações web que acessam dados de várias organizações. Guardar um token de sessão em `localStorage` facilitaria o primeiro protótipo, mas aumentaria o impacto de uma falha de XSS. Usar cookie de sessão reduz a exposição do token ao JavaScript, porém exige proteção explícita contra CSRF nas operações que alteram dados.

A versão 1.0 também precisa continuar utilizável por clientes de API e por testes automatizados sem criar uma implementação própria de criptografia ou de hash de senha.

## Decisão

1. Senhas serão transformadas com Argon2 por uma biblioteca mantida. A aplicação nunca armazenará nem registrará a senha original.
2. O backend emitirá um JWT de vida curta, assinado com segredo fornecido pelo ambiente, dentro de cookie `HttpOnly`.
3. O cookie usará `SameSite=Lax`; em produção também usará `Secure` e os atributos de domínio/caminho mínimos necessários.
4. Operações autenticadas que alteram estado e usam o cookie exigirão um token CSRF no padrão double-submit: valor em cookie legível pelo frontend e cópia no cabeçalho `X-CSRF-Token`.
5. Neste ciclo, a API autenticada usa somente cookie de sessão. Suporte futuro a `Authorization: Bearer` exigirá política e testes próprios; não está implícito neste ADR.
6. O backend validará a membership e o contexto da organização a cada requisição. Papel e organização não serão aceitos como autoridade apenas por estarem no token.
7. Logout removerá os cookies de sessão e CSRF. Expiração ou token inválido produzirá resposta `401` sem revelar detalhes internos.
8. Login terá limites independentes por identidade e origem. O adaptador local mantém memória limitada e usa um limiar de origem maior porque o proxy do frontend pode ser compartilhado; produção com múltiplas réplicas exige armazenamento compartilhado e configuração explícita da cadeia de proxies confiáveis.
9. Recuperação de senha e revogação por versão de sessão estão implementadas com token de uso único e estado persistido. MFA permanece no backlog da versão 1.0 e deverá usar bibliotecas mantidas e política própria.

## Consequências

### Positivas

- o token de sessão não fica acessível ao JavaScript normal da aplicação;
- a API preserva uma alternativa padrão para ferramentas e testes;
- papéis alterados passam a valer sem esperar a expiração do token;
- o mecanismo é compatível com frontend e backend em subdomínios da mesma marca.

### Custos e limites

- toda mutação do frontend precisa enviar o cabeçalho CSRF;
- CORS deve permitir somente origens configuradas e credenciais quando frontend e API estiverem separados;
- o backend não confia diretamente em `X-Forwarded-For`; a infraestrutura deve preservar a origem apenas por proxies confiáveis antes de ajustar o rate limit;
- JWT curto não substitui revogação central para cenários de alto risco;
- cookies seguros em produção dependem de HTTPS e configuração correta do proxy.

## Alternativas consideradas

### Token em `localStorage`

Rejeitado como padrão porque um XSS poderia ler e exfiltrar diretamente o token. Pode ser usado apenas por ferramentas não-web que protejam seu próprio armazenamento.

### Sessão opaca persistida no banco

É uma alternativa válida e facilita revogação imediata, mas adiciona persistência e limpeza de sessões ao primeiro fluxo. Poderá substituir o JWT curto sem mudar o contrato do frontend, pois o cookie permanece opaco para ele.

### Autenticação terceirizada obrigatória

Adiada. Reduz parte da manutenção de identidade, mas criaria uma dependência externa para executar o produto e conflitaria com a exigência de funcionamento local sem serviço pago.

## Verificação

- testes comprovam que o cookie é `HttpOnly` e removido no logout;
- mutação com cookie e sem CSRF recebe `403`;
- mutação com token CSRF correto é aceita conforme o papel;
- token válido sem membership da organização recebe negação;
- usuário de outra organização não acessa o recurso mesmo conhecendo seu UUID;
- nenhum segredo, hash ou token aparece em logs e respostas de erro.
