# AGENTS.md — Regras de trabalho do DevMark GrowthOS

Este arquivo orienta pessoas e agentes de programação em todo o repositório. Instruções mais específicas podem existir em subpastas, mas nunca podem enfraquecer as regras de segurança, multiempresa ou escopo aqui definidas.

## 1. Fronteira do produto

- Trabalhe somente no **DevMark GrowthOS**.
- Não altere o repositório institucional `bugijo/DevMark-ia` e não copie seu histórico, configuração ou segredos.
- Preserve o escopo da versão 1.0: operação, conteúdo, aprovação, notificações, relatório básico e registro manual.
- Não implemente publicação social real, Meta Ads, Google Ads, gasto automático ou WhatsApp oficial na versão 1.0.
- O sistema precisa funcionar integralmente com providers mock e sem API paga.
- Não crie apenas telas demonstrativas: toda tela entregue deve usar API, persistência e autorização reais.

### Estado atual

A fundação e a Fase 2 estão executáveis: identidade segura, matriz de papéis,
catálogos, presets, mídia privada, estratégia, calendário, conteúdo vinculado,
aprovações separadas, e-mail local, publicação manual, relatório e auditoria.
Não trate isso como release 1.0 concluída antes do gate final.

Permanecem pendentes, entre outros: preferências e resumos de notificação,
administração de providers/Hermes opcional, controles operacionais de LGPD,
revisão profissional automatizada, backup/restauração e hardening final. O
cadastro direto de revisor existe somente para compatibilidade em
desenvolvimento/teste e não substitui o convite de uso único.

## 2. Arquitetura

Use o monorepo com responsabilidades claras:

- `frontend/`: Next.js e TypeScript; apresentação, acessibilidade e chamadas à API;
- `backend/`: FastAPI; domínio, casos de uso, autorização e adaptadores;
- `worker/`: consumo da tabela de jobs e execução idempotente em segundo plano;
- `shared/`: somente contratos realmente compartilhados, sem acoplamento indevido;
- `infra/`: contêineres e configuração operacional;
- `tests/`: integração e ponta a ponta;
- `docs/`: requisitos, decisões, riscos e operação.

No backend, mantenha a direção de dependências:

```text
API/CLI -> casos de uso -> domínio
                 ^          ^
                 |          |
          adaptadores/infraestrutura
```

- O domínio não importa FastAPI, SQLAlchemy, clientes HTTP ou SDKs de providers.
- Casos de uso coordenam transações e políticas; rotas apenas validam, autenticam e traduzem entrada/saída.
- Repositórios, storage, e-mail, IA, imagens e Hermes entram por interfaces explícitas.
- Evite arquivos gigantes, regras duplicadas e acesso direto ao banco a partir de rotas.
- Mudanças estruturais relevantes exigem ADR em `docs/ADR/`.

## 3. Modelo de dados e multiempresa

O isolamento entre organizações é uma regra de segurança, não uma convenção de interface.

- Toda entidade pertencente a um tenant deve ter `organization_id` explícito ou um caminho de vínculo obrigatório e verificável.
- Toda consulta, alteração, job, arquivo, notificação e evento de auditoria deve carregar o contexto da organização.
- Nunca aceite `organization_id` do corpo da requisição como prova de acesso. Derive a organização da sessão/membership e valide o recurso no backend.
- Não use consultas sem escopo, inclusive em endpoints por ID, workers, relatórios, exports e rotinas administrativas.
- Use chaves estrangeiras, restrições e índices que reduzam a possibilidade de associação cruzada.
- Jobs devem persistir a organização e revalidar o acesso/contexto ao executar.
- URLs de arquivos devem ser assinadas, curtas e limitadas ao recurso autorizado.
- Testes negativos de isolamento são obrigatórios: um usuário da organização A nunca lê, altera, aprova ou enumera dados da B.
- `SUPER_ADMIN` não é atalho silencioso. Acesso global deve ser explícito, justificado e auditado.

Entidades usam UUID, timestamps UTC (`created_at`, `updated_at`) e soft delete somente quando retenção e recuperação justificarem. Migrações são aditivas e reversíveis quando possível; nunca edite uma migração já compartilhada.

## 4. Papéis e autorização

Papéis iniciais: `SUPER_ADMIN`, `AGENCY_ADMIN`, `STRATEGIST`, `CONTENT_EDITOR`, `DESIGNER`, `CLIENT_OWNER`, `CLIENT_REVIEWER` e `VIEWER`.

- A autorização deve ser declarada por capacidade/caso de uso e aplicada no backend.
- `CLIENT_OWNER` e `CLIENT_REVIEWER` só acessam a própria empresa; revisores podem aprovar e pedir alteração.
- `VIEWER` não altera dados.
- `DESIGNER` atua em mídia e visual; `CONTENT_EDITOR`, em conteúdo; `STRATEGIST`, em estratégia e planejamento.
- `AGENCY_ADMIN` administra a operação da organização, sem ultrapassar outras organizações.
- Convites, alterações de membership e permissões sempre geram audit log.
- O frontend pode ocultar ações proibidas, mas uma requisição direta também precisa ser negada.

## 5. Fluxos e estados

Use apenas os estados oficiais de conteúdo:

`DRAFT`, `INTERNAL_REVIEW`, `CLIENT_REVIEW`, `CHANGES_REQUESTED`, `APPROVED`, `SCHEDULED`, `PUBLISHED`, `FAILED`, `ARCHIVED`.

- Centralize a máquina de estados no domínio.
- Rejeite transições inválidas com erro claro e sem alteração parcial.
- Toda aprovação registra usuário, data, organização e versão exata.
- Pedido de alteração preserva histórico; a correção cria uma nova versão.
- Publicação na versão 1.0 é somente um registro manual e auditado.
- Ações repetidas por retry devem ser idempotentes.

## 6. Providers e jobs

- Providers implementam contratos; regras de negócio não importam SDKs externos.
- `mock` é o provider padrão e precisa ser determinístico em testes.
- Hermes é opcional: indisponibilidade não pode impedir o fluxo com mock.
- Nunca invente métricas, status de publicação ou resultado de campanha.
- Configure timeout, número máximo de tentativas, backoff e estado final para jobs.
- Não repita automaticamente uma ação externa não idempotente sem chave de idempotência.
- Registre duração, provider e resultado técnico sem salvar prompts, tokens ou dados pessoais desnecessários em logs.

## 7. Frontend e UX

- Interface em português do Brasil, preparada para internacionalização.
- Mobile first; o portal do cliente deve permitir aprovar em poucos toques.
- Use HTML semântico, navegação por teclado, foco visível, labels e contraste adequados.
- Mostre estados vazios úteis, progresso, erros em linguagem humana e próximo passo.
- A ação principal deve ser clara e ações destrutivas pedem confirmação.
- Não exponha termos internos ou detalhes técnicos ao cliente.
- Componentes não decidem autorização nem reproduzem regras de transição do domínio.
- Toda chamada deve tratar carregamento, falha, expiração de sessão e resposta vazia.

## 8. Segurança, privacidade e segredos

- Nunca grave chaves, tokens, senhas, cookies, dumps ou dados reais no repositório, fixtures, screenshots ou logs.
- `.env.example` contém somente nomes e valores locais não sensíveis; `.env` nunca é versionado.
- Use biblioteca mantida para senha e sessão; não implemente criptografia própria.
- Valide entrada e saída no backend, use queries parametrizadas e encode conteúdo exibido.
- Aplique CORS mínimo, cookies seguros, proteção CSRF quando aplicável e rate limiting em login/recuperação.
- Uploads exigem allowlist de MIME/extensão, limite de tamanho, nome gerado pelo servidor e verificação antes do acesso.
- Conteúdo veterinário ou de saúde não pode virar orientação automática nem usar informação clínica sensível; exige revisão profissional.
- Colete o mínimo de dados, documente retenção, exportação e exclusão, e preserve audit logs conforme a política legal.
- Se um segredo aparecer, pare, remova-o do alcance, informe o responsável e providencie rotação; apagar apenas o arquivo não torna o segredo seguro.

## 9. Padrões de código

- TypeScript em modo estrito e Python com type hints nas fronteiras e regras relevantes.
- Formatação e lint são automatizados; não desative regra para ocultar defeito.
- Nomes de domínio podem ser em inglês no código; textos visíveis ao usuário ficam em português claro.
- Erros da API seguem estrutura consistente, com código estável, mensagem segura e correlation ID.
- Logs são estruturados e não contêm segredos ou dados pessoais desnecessários.
- Datas são armazenadas em UTC e convertidas para o fuso do usuário na apresentação.
- Valores enumerados ficam centralizados; não espalhe strings mágicas.
- Nova dependência exige justificativa, manutenção ativa, licença compatível e verificação de vulnerabilidades.

## 10. Testes obrigatórios

Crie testes junto com a funcionalidade:

- unitários para domínio, permissões e transições;
- integração para repositórios, migrações, rotas, autenticação e jobs;
- contrato para providers mock e adaptadores;
- ponta a ponta para o fluxo agência → cliente → aprovação;
- acessibilidade e viewport móvel nas telas críticas;
- segurança negativa para isolamento entre organizações e papéis sem permissão.

Todo bug corrigido deve ganhar um teste que falhava antes. Não use API paga nem rede externa na suíte padrão. Relógio, UUID e provider devem poder ser controlados em testes.

Antes de concluir uma mudança, execute o conjunto proporcional ao risco e, antes de integrar:

```bash
make install
make lint
make test
make e2e
```

`make install`, `make lint` e `make test` usam o host e exigem Python 3.12 com `venv`, Node.js 22 e npm. Em Debian/Ubuntu, instale `python3.12-venv` quando necessário. `make setup` e `make e2e` usam somente Docker.

As imagens de aplicação são imagens de execução, não ambientes de desenvolvimento. Não instale nem execute pytest, Ruff, mypy, ESLint ou Vitest dentro dos contêineres de produção; use os alvos do Makefile e a CI.

A linha de base verificada fica registrada no `CHANGELOG.md` e no Pull Request da
fase. Preserve ou amplie essa evidência; não mantenha contagens antigas neste
arquivo normativo.

## 11. Migrações, seed e operação local

- Suba e aguarde a stack com `make setup`; esse fluxo usa Docker, aplica migrações e carrega o seed fictício quando habilitado.
- Use `make status`, `make logs` e `make down` para operação cotidiana.
- Use `make migrate` e `make seed` quando precisar executá-los explicitamente.
- Use `make reset` somente com intenção clara de apagar os volumes locais.
- Seeds são idempotentes, fictícios e limitados ao ambiente local/teste.
- Não execute seed ou reset destrutivo automaticamente em produção.
- Healthchecks devem distinguir processo ativo de dependências prontas.
- Alterações no schema acompanham migração, teste de migração e atualização do modelo documentado.

## 12. Documentação e comunicação

- Atualize o documento que define o comportamento alterado e o `CHANGELOG.md` quando a mudança for relevante ao usuário ou operador.
- Registre decisões duradouras como ADR, com contexto, decisão, alternativas e consequências.
- Critérios de aceite devem ser observáveis e testáveis.
- Ao encerrar uma etapa, explique em português simples: o que foi feito, o que funciona, o que falta, como testar, riscos e próximos passos.
- Não esconda limitações e não faça promessas comerciais sem evidência.

## 13. Commits e pull requests

- Faça commits pequenos, coesos e revisáveis.
- Use mensagens no imperativo com tipo e escopo, por exemplo: `feat(approvals): registra decisão do cliente`.
- Tipos preferidos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci` e `security`.
- Não misture formatação ampla, refatoração e funcionalidade no mesmo commit.
- Nunca reescreva ou descarte mudanças de outra pessoa sem autorização.
- Pull requests descrevem objetivo, comportamento, testes, migrações, riscos, segurança multiempresa, screenshots quando úteis e próximos passos.

## 14. Checklist de conclusão

Antes de marcar qualquer item como pronto, confirme:

- [ ] critérios de aceite atendidos;
- [ ] autorização e organização validadas no backend;
- [ ] audit log incluído para ação relevante;
- [ ] erros e estados vazios tratados;
- [ ] testes positivos e negativos adicionados e passando;
- [ ] lint e tipos passando;
- [ ] migração e rollback avaliados;
- [ ] nenhum segredo ou dado real incluído;
- [ ] documentação e changelog atualizados;
- [ ] provider mock continua funcional;
- [ ] nenhuma integração externa fora do escopo foi ativada.
