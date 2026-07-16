# Integrações e provedores

## Objetivo

Integrações externas devem ficar atrás de contratos estáveis. Regras de conteúdo, aprovação e auditoria não podem depender diretamente de OpenAI, Hermes, Meta, Google ou qualquer fornecedor específico.

A versão 1.0 funciona integralmente com providers mock e sem API paga. Providers reais são opcionais e só podem ser ativados por configuração explícita e segura.

## Arquitetura de portas e adaptadores

O domínio chama interfaces próprias; adaptadores traduzem essas chamadas para serviços externos. A seleção ocorre em uma fábrica ou registro de providers, nunca por condicionais espalhadas pelas regras de negócio.

Contratos iniciais:

- `TextProvider`: ideias, legendas, roteiros, estratégia e transformações textuais.
- `ImageProvider`: imagem-base, ilustração ou referência visual.
- `NotificationProvider`: e-mail e, futuramente, outros canais.
- `StorageProvider`: upload, leitura autorizada e URLs assinadas.
- `HermesProvider`: tarefas locais, roteamento e orquestração opcional.
- `SocialProvider` e `AdsProvider`: apenas contratos ou stubs nesta fase; escrita real desabilitada.

Todo contrato deve receber contexto explícito da organização, identificador de correlação, finalidade e limites da tarefa, e devolver um resultado normalizado com provider, modelo, duração, status e erro seguro. O provider nunca decide permissão, aprovação ou mudança de estado do domínio.

## Providers da versão 1.0

### Mock obrigatório

O mock é o padrão de desenvolvimento, testes, demonstração e instalação sem credenciais. Ele deve:

- implementar o mesmo contrato do provider real;
- retornar dados determinísticos a partir de fixtures ou seed controlada;
- produzir estratégia, calendário, conteúdo e ativo visual de demonstração suficientes para o fluxo vertical;
- permitir simular sucesso, timeout, indisponibilidade e resposta inválida;
- identificar o resultado como mock, sem inventar métricas ou afirmar que houve chamada externa;
- não acessar rede nem exigir segredo;
- respeitar contexto e isolamento por organização;
- gerar metadados úteis para teste e audit log sem guardar prompt sensível em excesso.

Um teste deve conseguir fixar a resposta sem depender de relógio, internet ou comportamento aleatório.

### Hermes opcional

O `HermesProvider` pode executar classificação, resumo, organização, etiquetas, rascunhos, reaproveitamento e tarefas repetitivas. A aplicação continua funcional se Hermes estiver indisponível. Memórias só podem ser persistidas quando autorizadas, isoladas por organização e adequadas à LGPD.

### Provider remoto configurável

Providers remotos podem ser usados para estratégia, texto final, revisão de qualidade, raciocínio complexo e conteúdo sensível. A ativação exige configuração válida, orçamento e política definidos. Ausência de chave deve provocar fallback permitido para mock ou erro orientativo, nunca falha de inicialização de toda a plataforma.

## Roteamento pelo Growth Agent

O Growth Agent escolhe um provider conforme tipo da tarefa, qualidade necessária, sensibilidade, custo permitido e disponibilidade. Na primeira versão, esse roteamento deve ser simples, previsível e configurável.

Regras mínimas:

1. verificar permissão e organização antes de montar o contexto;
2. preferir mock quando `PROVIDER_MODE=mock`;
3. usar Hermes para tarefas locais autorizadas quando saudável;
4. usar provider remoto apenas se habilitado e necessário;
5. aplicar timeout, limite de tentativas e orçamento;
6. normalizar e validar a resposta antes de persistir;
7. exigir revisão humana; resultado de IA nasce como rascunho;
8. registrar provider, status e custo conhecido, sem inventar custo ausente.

Fallback não pode trocar silenciosamente a finalidade ou enviar dados a um terceiro não autorizado. O usuário deve conseguir identificar quando um resultado foi mock ou quando houve degradação.

## Configuração e segredos

- `provider_configs` pertence a uma organização quando a configuração for específica do cliente.
- Guardar nome, capacidades, modelo, limites, status e referência do segredo; não guardar segredo em texto aberto no repositório.
- Variáveis de ambiente são aceitas no desenvolvimento; produção deve usar um cofre ou secret manager.
- Segredos são mascarados na API, interface, logs e erros.
- O backend acessa tokens; o frontend não recebe credencial sem necessidade técnica comprovada.
- Rotação, revogação, teste de conexão e alteração de configuração entram no audit log.
- Escopos devem ser mínimos e credenciais de ambientes diferentes não podem ser compartilhadas.

## Resiliência e observabilidade

- Timeout explícito por operação.
- Retry apenas para erros transitórios, com limite e atraso crescente.
- Sem retry automático para erro de validação, autenticação ou operação financeira.
- Circuit breaker para provider instável quando necessário.
- Chave de idempotência em operações de escrita.
- Jobs guardam tentativas, status e erro sanitizado.
- Logs estruturados usam correlação, provider e organização, sem prompt completo ou segredo.
- Métricas distinguem sucesso, falha, timeout, fallback, latência e custo confirmado.

## Centro de Integrações

O alvo da versão 1.0 apresenta configurações disponíveis e seu estado, mesmo quando conectores reais ainda estão desativados. Para cada integração, prever:

- status e modo (`mock`, `read_only`, `disabled` ou `enabled`);
- conta e empresa vinculadas, quando houver;
- permissões concedidas;
- última sincronização e último erro;
- validade do token;
- ações de conectar, reconectar, testar e desconectar;
- logs e recursos habilitados.

Botões de conectores fora do escopo devem aparecer como indisponíveis ou futuros; não devem sugerir uma conexão inexistente.

## Política de autonomia externa

### Nível 1 — leitura automática autorizada

Pode ler métricas, comentários, campanhas, perfis e status somente após conexão e consentimento válidos, usando escopos mínimos.

### Nível 2 — escrita com aprovação

Publicar, responder, alterar perfil, criar/editar/pausar campanha, mudar orçamento e enviar mensagens em massa exigem aprovação explícita. Na versão 1.0 os adaptadores reais dessas ações permanecem desabilitados.

### Nível 3 — escrita automática controlada

Fica reservada a versões futuras e requer política explícita por cliente, limite financeiro, janela de operação, reversão, alertas, audit log e bloqueio de emergência.

Nenhum provider pode promover uma ação para outro nível de autonomia.

## Fases

- **Versão 1.0:** contratos, mock, configuração segura, Hermes opcional, notificação interna, e-mail por adaptador, upload e registro manual.
- **Versão 2.0:** Meta orgânico, Google Business Profile, YouTube básico, métricas e publicação programada com aprovação.
- **Versão 2.5:** WhatsApp Business oficial, Telegram, CRM e relacionamento consentido.
- **Versão 3.0:** Meta Ads e Google Ads, com limites e aprovação obrigatória.
- **Versão 4.0:** automações controladas, reversíveis e explicáveis.

## Critérios de aceite

1. **IP-01:** a aplicação sobe e executa o fluxo vertical com modo mock e sem chaves pagas.
2. **IP-02:** trocar o provider configurado não exige alterar regras de domínio.
3. **IP-03:** respostas mock são determinísticas, identificadas e validadas pelo mesmo schema do provider real.
4. **IP-04:** testes simulam sucesso, timeout, indisponibilidade e resposta inválida.
5. **IP-05:** falha de Hermes não impede login, cadastro, aprovação ou uso do mock.
6. **IP-06:** segredo não aparece em resposta da API, interface, log, audit log ou mensagem de erro.
7. **IP-07:** configuração de uma organização não pode ser lida ou usada por outra.
8. **IP-08:** timeout e tentativas terminam em status conhecido e erro orientativo.
9. **IP-09:** resultados de IA são persistidos como rascunho e não aprovam nem publicam conteúdo.
10. **IP-10:** conectores Meta, Google Ads e WhatsApp reais permanecem desabilitados na versão 1.0.
11. **IP-11:** nenhuma operação externa altera orçamento ou gera gasto automaticamente.
12. **IP-12:** alteração, teste e desconexão de provider geram audit log sem expor credenciais.

## Fora do escopo da versão 1.0

- publicação direta em Instagram e Facebook;
- Meta Ads e Google Ads reais;
- WhatsApp Business oficial;
- sincronização automática de métricas sociais;
- resposta automática a mensagens;
- geração automática de vídeo;
- cobrança por consumo;
- autonomia total ou otimização financeira automática.

