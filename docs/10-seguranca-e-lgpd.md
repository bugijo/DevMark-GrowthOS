# Segurança e LGPD

## Objetivo e princípios

O GrowthOS trata dados de várias empresas, pessoas usuárias e materiais de marketing. Segurança e privacidade são requisitos do domínio, não uma camada adicionada depois.

Princípios obrigatórios:

- negar por padrão e conceder o menor privilégio necessário;
- validar autenticação, autorização e organização no backend;
- minimizar coleta, exposição, retenção e envio a providers;
- manter ações relevantes auditáveis;
- nunca guardar segredos no código ou no Git;
- não usar dados de um cliente para outro sem autorização explícita;
- exigir revisão humana para conteúdo veterinário ou de saúde;
- não armazenar prontuário ou informação clínica sensível no conteúdo de marketing.

## Fronteiras e ameaças prioritárias

As ameaças mais críticas da versão 1.0 são acesso cruzado entre organizações, elevação de papel, sequestro de sessão, vazamento de segredos, upload malicioso, injeção, conteúdo sensível enviado a providers e decisão de aprovação aplicada à versão errada.

Cada endpoint e job deve considerar pelo menos:

1. quem é o usuário ou serviço;
2. a qual organização ele está associado;
3. qual empresa e recurso pode acessar;
4. qual papel e ação estão autorizados;
5. se a entrada é válida e pertence ao mesmo tenant;
6. qual evento precisa ser auditado;
7. quais dados podem aparecer em log ou ser enviados a terceiros.

## Autenticação e sessão

- Usar biblioteca mantida para hash de senha, autenticação e sessão; não implementar criptografia própria.
- Armazenar apenas hash forte de senha, nunca senha reversível.
- Aplicar política mínima de senha e permitir recuperação com token aleatório, de uso único e curta duração.
- Cookies, quando usados, devem ser `HttpOnly`, `Secure` em produção e com `SameSite` adequado.
- Tokens não devem ficar em URL, log, audit log ou armazenamento inseguro do navegador.
- Invalidar sessões após troca de senha, revogação ou evento de segurança compatível.
- Limitar tentativas em login, convite e recuperação, com resposta que não permita enumerar contas.
- Convites expiram, têm uso único e vinculam e-mail, organização e papel autorizado.

## Autorização e isolamento multiempresa

- `organization_id` é obrigatório em toda entidade multiempresa e faz parte das consultas no backend.
- O contexto da organização vem da sessão e de uma `membership` ativa; um valor do frontend é apenas uma solicitação, nunca prova de autorização.
- O papel é verificado por ação, não apenas por tela.
- `CLIENT_OWNER`, `CLIENT_REVIEWER` e `VIEWER` ficam limitados à própria empresa quando necessário.
- Acesso da agência a vários clientes exige associações explícitas. Não existe bypass implícito por pertencer à equipe.
- `SUPER_ADMIN` é excepcional, restrito, observável e auditado.
- Chaves estrangeiras e índices compostos devem reduzir referências acidentais entre tenants.
- Jobs carregam e validam o contexto da organização novamente ao executar.
- Testes negativos de acesso cruzado são obrigatórios em cada recurso multiempresa.

O [ADR 0002 — Isolamento multiempresa](./ADR/0002-isolamento-multiempresa.md) registra a decisão detalhada.

## Validação e proteção da aplicação

- Validar payloads com schemas e rejeitar campos desconhecidos ou incompatíveis quando apropriado.
- Usar consultas parametrizadas/ORM e nunca concatenar entrada em SQL.
- Escapar saída e sanitizar HTML permitido para reduzir XSS.
- Aplicar proteção contra CSRF quando a forma de sessão exigir.
- Definir CORS por ambiente e origem autorizada, sem curingas com credenciais em produção.
- Proteger rotas administrativas e documentação sensível.
- Configurar cabeçalhos de segurança, limites de corpo e timeouts.
- Mensagens externas devem ser simples; detalhes internos ficam em logs seguros.
- Auditar dependências e corrigir vulnerabilidades críticas antes da entrega.
- Aplicar rate limiting por identidade e origem nas rotas de maior risco.

## Upload e armazenamento

- Validar tipo real, extensão, tamanho e dimensões.
- Gerar nome interno; não confiar no nome fornecido pelo usuário.
- Impedir execução de arquivos e servir conteúdo em domínio ou política apropriada.
- Sanitizar SVG ou rejeitá-lo; remover metadados desnecessários.
- Usar URLs assinadas e de curta validade para arquivos privados.
- Registrar organização, autor, hash, tipo, tamanho e finalidade.
- Prever varredura antimalware em produção.
- Aplicar exclusão lógica e política de retenção compatível com vínculos de auditoria.

## Segredos e integrações

- Desenvolvimento lê segredos do ambiente; `.env` real não entra no repositório.
- Produção usa secret manager ou mecanismo equivalente, com rotação e acesso mínimo.
- Chaves, tokens e senhas são mascarados em respostas e logs.
- Tokens de integração ficam criptografados em repouso e não são enviados ao frontend sem necessidade.
- Conectar, testar, rotacionar, revogar e desconectar integrações gera audit log.
- O provider mock é o padrão seguro sem credenciais e não acessa rede.
- Fallback para terceiro real só ocorre quando esse terceiro e a finalidade estão autorizados.

## Audit log e logs técnicos

O audit log registra quem fez o quê, quando, em qual organização, sobre qual recurso e com qual resultado. Ele deve cobrir login relevante, mudanças de papel, Brand Kit, versões, revisões, aprovações, providers, integrações e registro manual de publicação.

Não registrar:

- senha, token, cookie ou chave;
- prompt completo contendo dados pessoais quando metadados forem suficientes;
- conteúdo clínico ou dado pessoal desnecessário;
- corpo completo de arquivo;
- cabeçalhos de autenticação.

Logs técnicos devem ser estruturados, ter identificador de correlação, retenção definida e acesso restrito. Usuários comuns não podem alterar o audit log.

## LGPD por ciclo de vida

### Inventário e base legal

Antes de produção, cada categoria deve ter finalidade, base legal, origem, destinatários, retenção e responsável definidos. Os papéis de controlador e operador entre DevMark IA e cada cliente devem constar em contrato e registro de tratamento; este documento não substitui avaliação jurídica.

Categorias iniciais:

- conta: nome, e-mail, papel e registros de acesso;
- negócio e marca: dados públicos ou fornecidos pelo cliente;
- aprovação: identidade do revisor, decisão e comentário;
- conteúdo e arquivos: material de marketing e referências;
- notificações: endereço, preferência e histórico de entrega;
- telemetria: eventos técnicos mínimos para segurança e operação.

### Minimização e finalidade

- Coletar somente o necessário para operar a funcionalidade declarada.
- Não reutilizar dados de marketing para treinamento ou sugestão cruzada sem autorização específica.
- Não enviar ao provider campos que ele não precisa.
- Preferir identificadores internos e conteúdo anonimizado ou reduzido quando possível.
- Não coletar dados clínicos de animais, tutores ou pacientes nesta plataforma.

### Consentimento e comunicação

Consentimento deve ser específico quando for a base aplicável, registrando texto, versão, data e revogação. Mensagens em massa e canais futuros devem respeitar consentimento, opt-out, preferências e políticas da plataforma. Notificações estritamente operacionais devem ser diferenciadas de marketing.

### Direitos do titular

O processo operacional deve permitir localizar, confirmar, corrigir, exportar, anonimizar ou excluir dados conforme obrigação e base aplicável. Solicitações exigem verificação de identidade, protocolo, prazo e audit log. Dados sujeitos a retenção legal ou defesa de direitos podem ser bloqueados em vez de apagados, com justificativa.

### Retenção e descarte

Prazos devem ser configurados e documentados por categoria. Conta encerrada não significa exclusão imediata indiscriminada: dados ativos são removidos ou anonimizados, backups expiram conforme ciclo e registros necessários são preservados com acesso reduzido. O descarte deve ser verificável.

## IA, conteúdo veterinário e privacidade

- Resultado de IA é rascunho e sempre passa por revisão humana.
- Conteúdo de saúde exige revisão profissional antes da aprovação final.
- Prompts e respostas devem ser tratados como dados da organização.
- Instruções contidas em arquivos ou conteúdo do cliente não podem substituir regras de sistema ou autorização.
- Providers reais devem ter avaliação de privacidade, contrato e região de tratamento conhecidos antes da ativação.
- Não prometer diagnóstico, cura, resultado garantido ou orientação clínica automática.

## Continuidade e incidentes

- Backups criptografados, com retenção e acesso restritos.
- Testes periódicos de restauração; backup sem teste não é evidência de recuperação.
- Procedimento de incidente com contenção, preservação de evidência, avaliação de impacto, comunicação interna e notificações legais quando aplicáveis.
- Revogação rápida de sessão e credencial comprometida.
- Runbooks devem informar responsáveis, contatos e critérios de escalonamento.

## Critérios de aceite

1. **SEG-01:** usuário sem sessão não acessa rota protegida.
2. **SEG-02:** papel sem permissão recebe negação no backend, mesmo chamando a API diretamente.
3. **SEG-03:** usuário de uma organização não lista, lê, altera ou infere recursos de outra.
4. **SEG-04:** cada entidade multiempresa criada recebe organização validada pela sessão.
5. **SEG-05:** tentativas de login e recuperação possuem limitação e não enumeram contas.
6. **SEG-06:** nenhum segredo real está versionado ou aparece em respostas e logs.
7. **SEG-07:** uploads inválidos são rejeitados e arquivos privados exigem autorização.
8. **SEG-08:** entradas maliciosas cobertas por testes não resultam em SQL injection, XSS ou acesso indevido.
9. **SEG-09:** alteração de papel, aprovação e configuração de provider geram audit log íntegro.
10. **SEG-10:** logs e audit log mascaram credenciais e dados pessoais desnecessários.
11. **SEG-11:** existe processo documentado para exportação, correção e exclusão de dados.
12. **SEG-12:** retenção e backup são configuráveis e a restauração é testável.
13. **SEG-13:** conteúdo veterinário sensível não avança sem revisão profissional registrada.
14. **SEG-14:** o sistema funciona em modo mock sem transmitir dados a API paga.
15. **SEG-15:** dependências críticas conhecidas não permanecem sem correção ou aceite formal de risco.

## Fora do escopo da versão 1.0

- prontuário médico ou veterinário;
- armazenamento de exames, diagnósticos ou prescrições;
- autenticação biométrica e aplicativo móvel nativo;
- certificação ISO 27001, SOC 2 ou selo de conformidade;
- DLP e SIEM corporativos completos;
- conectores reais de anúncios ou WhatsApp;
- parecer jurídico definitivo sobre cada operação de tratamento.
