# Gate de privacidade e ativação comercial — DevMarkia

**Estado em 2026-10-09: BLOQUEADO para intake público e dados reais.** Este
checklist organiza uma revisão técnica e jurídica; não declara conformidade nem
substitui parecer de profissional especializado.

## Evidência técnica observada

- O código local do GrowthOS inclui pipeline de leads e `0018_sales_leads`.
- `PUBLIC_QUOTE_INTAKE_ENABLED` tem default `false`; a configuração também
  exige organização de destino, aviso HTTPS/versionado e aprovações jurídica e
  de segurança antes de aceitar a flag.
- A rota pública minimiza a resposta, exige consentimento, usa idempotência,
  honeypot e rate limit em memória por processo; os testes verificam
  duplicação, ausência de PII em logs/resposta, consentimento e `Retry-After`.
- O CRM interno aplica capabilities e consultas por `organization_id`; briefing
  e proposta são determinísticos e não enviados.
- Retenção `sales_leads` é por organização, auditada e com dry-run como padrão.
- A exportação autenticada existente cobre a conta do usuário, não a localização
  e exportação de leads recebidos anonimamente. A exclusão desses leads só está
  coberta por retenção administrativa, não por pedido individual verificado.
- O limitador fica em memória; não coordena múltiplas réplicas. Criptografia do
  volume PostgreSQL, do armazenamento de mídia e dos backups precisa ser
  comprovada no ambiente real; a configuração local não é evidência suficiente.
- O stack local observado respondeu saudável, mas executava revisão Alembic
  `0017_ai_lifecycle`; o OpenAPI ativo não continha as rotas de vendas. O código
  local `0018_sales_leads` ainda não está implantado nesse stack.
- A infraestrutura local tem serviços PostgreSQL/MinIO e scripts de backup e
  restauração isolada. Não foi localizado backup elegível no diretório de
  backups do GrowthOS, então nenhuma restauração real pôde ser demonstrada.

## Gate obrigatório antes de aceitar leads reais

### Revisão jurídica / privacidade

- [ ] Definir controlador, operadores, finalidade e base legal por campo e por
  etapa; consentimento não deve ser assumido como base única ou automaticamente
  adequado.
- [ ] Publicar aviso claro no ponto de coleta: controlador, dados, finalidade,
  compartilhamentos, retenção, direitos, canal de contato e consequências da
  recusa; manter versão e evidência de apresentação/aceite.
- [ ] Confirmar canal acessível para titular/encarregado e processo de protocolo,
  verificação proporcional de identidade, resposta e exceções de retenção.
- [ ] Definir prazo e justificativa de retenção de lead não convertido; revisar
  preservação por obrigação legal/defesa de direitos antes de eliminar.
- [ ] Aprovar contrato, papéis controlador/operador, instruções e incidentes.
- [ ] Analisar o registro das operações e, se aplicável, necessidade de RIPD.

### Revisão de segurança / operação

- [ ] Implementar fluxo verificável de acesso/exportação/correção/exclusão para
  leads anônimos. Não resolver por busca de e-mail sem prova de controle do
  endereço; avaliar desafio de uso único com expiração, anti-enumeração, rate
  limit e retenção legal.
- [ ] Substituir ou complementar o limitador em memória por armazenamento
  compartilhado e atômico antes de qualquer implantação com múltiplas réplicas.
- [ ] Demonstrar criptografia em repouso para volumes, backups e objetos, gestão
  de chaves, permissões, rotação e restauração. Não inferir isso do protocolo
  TLS nem do filesystem.
- [ ] Executar migrations somente em PostgreSQL isolado com dados fictícios;
  provar backup + restore em projeto Docker descartável, verificar checksums,
  revisão Alembic e contagens. Não usar produção para o teste.
- [ ] Confirmar proxy confiável e extração de IP; rejeitar spoofing de headers;
  rever limite de corpo, timeouts, CORS, CSRF, alertas e resposta a abuso.
- [ ] Rever logs, auditoria, telemetria e erros para confirmar ausência de PII,
  segredos, stack traces e IDs enumeráveis.
- [ ] Confirmar autorização multi-tenant em endpoints, exports, tarefas,
  workers e rotinas de retenção com testes negativos.
- [ ] Validar build/imagem e autenticação do mesmo commit que será implantado;
  executar smoke de intake desativado e ativo em staging isolado.

## Critério de liberação

Manter o formulário público desligado enquanto qualquer caixa acima estiver
aberta. A ativação exige revisão humana jurídica e técnica documentada, staging
aprovado, backup/restauração comprovados, migration revisada e plano de rollback.
Não habilitar por mera edição de variável de ambiente.

## Referências oficiais consultadas

- [Lei nº 13.709/2018 — texto consolidado no Planalto](https://planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm)
- [ANPD — Direitos dos titulares](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares)
- [ANPD — Guia de segurança para agentes de tratamento de pequeno porte](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte)

Referências servem como material de revisão, não como conclusão jurídica sobre
esta operação.
