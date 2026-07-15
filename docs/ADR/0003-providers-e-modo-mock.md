# ADR 0003 — Providers e modo mock

- **Status:** Aceita
- **Data:** 2026-07-15
- **Decisão relacionada:** geração de conteúdo, imagens, Hermes e integrações

## Contexto

O GrowthOS precisa gerar estratégia, calendário, textos e referências visuais, mas não pode depender de uma única API nem exigir pagamento para iniciar, testar ou demonstrar o fluxo vertical.

SDKs externos têm contratos, custos, disponibilidade e políticas diferentes. Se o domínio chamar diretamente um fornecedor, trocar de modelo ou testar falhas exigirá alterar regras de negócio. Também existe risco de enviar dados de um cliente a um terceiro não autorizado.

## Decisão

Adotaremos portas e adaptadores para todas as capacidades externas. O domínio conhece interfaces internas e resultados normalizados; cada fornecedor fica em um adaptador de infraestrutura.

O modo mock será obrigatório, determinístico e padrão em desenvolvimento, testes e demonstração. A aplicação deve executar o fluxo vertical sem rede, Hermes ou chave paga.

## Contratos iniciais

- `TextProvider`: estratégia, ideias, legendas, roteiro e transformação textual.
- `ImageProvider`: imagem-base ou referência visual, sem delegar texto final da peça.
- `NotificationProvider`: e-mail e futuros canais.
- `StorageProvider`: objetos e URLs assinadas.
- `HermesProvider`: execução local e roteamento opcional.
- Portas de redes sociais e anúncios podem existir como contratos/stubs, mas escrita real fica desabilitada na versão 1.0.

Entradas e saídas usam schemas próprios do GrowthOS. Erros são classificados em validação, autenticação, limite, timeout, indisponibilidade e erro permanente. O domínio não recebe exceções ou tipos do SDK externo.

## Provider mock

O mock deve:

- implementar exatamente os contratos usados pela aplicação;
- gerar resultados previsíveis por fixture/seed e entrada normalizada;
- devolver dados suficientes para estratégia, calendário, conteúdo e ativo visual do primeiro fluxo;
- permitir cenários configuráveis de timeout, falha e resposta inválida;
- marcar provider e resultado como mock;
- não acessar rede, ler chave real ou criar custo;
- respeitar organização e nunca misturar fixtures entre tenants;
- evitar aleatoriedade ou relógio não controlados nos testes;
- não inventar métricas, publicação, entrega ou aprovação.

O mock não será implementado como condicionais dentro do domínio. Ele é um adaptador selecionado pelo mesmo mecanismo dos providers reais.

## Seleção e roteamento

Uma fábrica/registro seleciona o adaptador por capacidade e configuração. O Growth Agent poderá rotear tarefas conforme:

- modo do ambiente;
- autorização da organização;
- sensibilidade da tarefa;
- qualidade necessária;
- disponibilidade;
- custo e limite definidos.

Ordem inicial:

1. em modo mock, sempre usar mock;
2. se Hermes estiver habilitado e a tarefa local for permitida, usá-lo;
3. usar provider remoto somente quando explicitamente habilitado;
4. fallback só para provider autorizado para a mesma finalidade;
5. se não houver fallback permitido, falhar de forma clara e preservando o fluxo existente.

Provider não pode aprovar, publicar, enviar campanha, alterar orçamento ou decidir permissões. Toda saída de IA nasce como rascunho sujeito a validação e revisão humana.

## Configuração e segurança

- Configuração armazena capacidades, modelo, limites, status e referência ao segredo.
- Segredo real vem de ambiente/cofre, é criptografado quando persistido e nunca retorna integralmente.
- Configuração específica possui `organization_id` e não pode ser usada por outro tenant.
- Logs registram correlação, provider, modelo, duração, status e custo confirmado; não registram segredo ou prompt pessoal completo.
- Alterar, testar, habilitar ou desabilitar provider gera audit log.
- Envio de dados segue minimização e finalidade autorizada.

## Resiliência

- Timeout por operação e limite de payload.
- Retry somente para erro transitório e com número finito de tentativas.
- Circuit breaker quando falhas recorrentes justificarem.
- Idempotência para notificações e futuras escritas externas.
- Resposta do provider é validada antes de persistir.
- Falha de provider opcional não impede autenticação, organização, Brand Kit ou aprovação.
- Jobs falhos ficam visíveis e não entram em repetição infinita.

## Política de autonomia

Na versão 1.0, providers podem ler apenas o contexto mínimo autorizado e gerar rascunhos. Envio para revisão, aprovação e registro de publicação dependem de pessoa autorizada.

Publicação social, resposta a mensagens, Meta Ads, Google Ads, WhatsApp real, campanhas em massa e gasto automático permanecem fora de escopo. Escrita automática controlada exige versão futura, política por cliente, limites, reversão, alertas, auditoria e bloqueio de emergência.

## Consequências

### Positivas

- Desenvolvimento e CI funcionam sem internet ou custo variável.
- Trocar provider não altera o domínio.
- Falhas e timeouts são reproduzíveis.
- Hermes continua opcional.
- A política de dados por organização fica explícita.

### Custos e cuidados

- Contratos internos precisam ser mantidos e versionados.
- Cada adaptador exige teste de contrato.
- Resultado mock não mede qualidade ou desempenho de provider real.
- Recursos exclusivos de um fornecedor devem ser normalizados ou expostos como capacidade opcional, sem contaminar o núcleo.

## Alternativas consideradas

### Integrar diretamente um único SDK

Rejeitada por acoplamento, dificuldade de teste, indisponibilidade e risco de custo.

### Exigir Hermes em todos os ambientes

Rejeitada porque o sistema deve funcionar sem Hermes e porque a instalação inicial precisa ser simples.

### Usar respostas fixas no frontend

Rejeitada: criaria telas falsas sem backend, banco, versões, notificações e audit log reais.

### Fazer chamadas reais nos testes

Rejeitada para a suíte padrão por custo, instabilidade, privacidade e falta de determinismo. Testes de homologação de provider real serão separados e opt-in.

## Critérios de aceite

1. **ADR3-01:** aplicação e testes executam sem chave paga ou acesso de rede externo.
2. **ADR3-02:** mock e adaptadores reais implementam contratos internos comuns.
3. **ADR3-03:** resultado mock é determinístico e claramente identificado.
4. **ADR3-04:** seleção de provider ocorre na infraestrutura, não nas regras de domínio.
5. **ADR3-05:** Hermes indisponível não derruba o fluxo principal.
6. **ADR3-06:** timeout, indisponibilidade e resposta inválida possuem testes.
7. **ADR3-07:** segredo e prompt sensível não aparecem em logs ou respostas.
8. **ADR3-08:** provider recebe somente dados da organização e finalidade autorizadas.
9. **ADR3-09:** saída de IA permanece rascunho até revisão humana.
10. **ADR3-10:** nenhum adaptador real de publicação, anúncios ou WhatsApp é habilitado na versão 1.0.
