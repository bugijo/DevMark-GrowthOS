# Fluxos e experiência do usuário

## 1. Direção de experiência

O GrowthOS atende pessoas que não precisam conhecer detalhes técnicos. A interface deve dizer o que aconteceu, o que precisa de atenção e qual é o próximo passo. O portal do cliente prioriza celular e aprovação em poucos toques; o painel da agência prioriza contexto e segurança operacional.

Regras comuns:

- uma ação principal visível por tela;
- linguagem em português do Brasil e termos técnicos traduzidos;
- estados de carregamento, vazio, sucesso e falha em todo fluxo;
- confirmação para ação destrutiva e possibilidade de desfazer quando segura;
- feedback imediato; jobs longos mostram progresso consultável;
- contagem de pendências no menu e atalho **Revisar aprovações**;
- histórico e versão anterior acessíveis sem poluir a ação principal;
- acessibilidade por teclado, foco visível, rótulos, contraste e mensagens anunciáveis;
- autorização real no backend; esconder um botão não é controle de acesso.

## 2. Entradas e navegação

### Agência

Login, Dashboard, Clientes, Novo cliente, Perfil da marca, Brand Kit, Presets visuais, Serviços, Públicos, Estratégias, Calendário, Conteúdos, Editor, Mídia, Aprovações, Comentários, Notificações, Relatórios, Provedores de IA, Configurações e Logs.

No primeiro ciclo, a navegação pode mostrar apenas módulos já conectados. Itens futuros não devem parecer funcionais.

### Cliente

Login, Início, Pendências, Aprovações, Calendário, Conteúdos aprovados, Resultados, Notificações, Marca, Preferências e Usuários.

A tela inicial destaca:

- quantidade aguardando decisão;
- botão **Revisar aprovações**;
- próximo conteúdo e calendário da semana;
- notificações e mensagens da equipe;
- resultados disponíveis, com estado vazio honesto quando não há dados.

## 3. Login e seleção de contexto

```mermaid
sequenceDiagram
    actor U as Usuário
    participant F as Frontend
    participant A as API
    participant D as Banco

    U->>F: informa e-mail e senha
    F->>A: envia credenciais e proteção CSRF
    A->>D: busca usuário e valida hash
    alt credenciais válidas e membership ativa
        A->>D: cria/rotaciona sessão e audita
        A-->>F: cookie HttpOnly + contexto permitido
        F-->>U: abre dashboard ou empresa única
    else inválidas/inativas
        A->>D: registra falha segura quando aplicável
        A-->>F: mensagem genérica
        F-->>U: permite tentar ou recuperar acesso
    end
```

Se houver várias organizações/empresas permitidas, a seleção exibe apenas opções retornadas pelo backend. A troca de contexto renova o contexto autorizado; IDs recebidos da interface nunca são aceitos sem revalidação.

## 4. Onboarding de cliente

```mermaid
flowchart TD
    A[Criar empresa] --> B[Dados e contatos]
    B --> C[Brand Kit]
    C --> D[Serviços, públicos e objetivos]
    D --> E[Logos e referências]
    E --> F[Preset visual]
    F --> G[Tom, termos e restrições]
    G --> H[Responsáveis por aprovação]
    H --> I[Preferências de notificação]
    I --> J[Revisar resumo]
    J --> K[Ativar cliente e gerar diagnóstico]
```

O sistema salva rascunho entre etapas. Um checklist mostra itens concluídos e o efeito dos campos. Para a primeira fatia vertical, Brand Kit básico é suficiente; campos ainda ausentes aparecem como pendência, não são inventados pelo provider.

Conteúdo veterinário/saúde ativa a regra de revisão profissional e explica, em linguagem simples, por que essa confirmação é necessária.

## 5. Fluxo vertical de conteúdo e aprovação

```mermaid
sequenceDiagram
    actor E as Equipe da agência
    participant G as GrowthOS
    participant P as Provider mock
    actor C as Cliente revisor
    participant L as Audit log

    E->>G: cria conteúdo com empresa e objetivo
    G->>P: solicita rascunho com Brand Kit autorizado
    P-->>G: conteúdo mock determinístico
    G->>L: registra criação e provider
    E->>G: envia versão para revisão interna
    G->>L: DRAFT → INTERNAL_REVIEW
    E->>G: libera versão para cliente
    G->>C: cria notificação interna/e-mail configurado
    G->>L: INTERNAL_REVIEW → CLIENT_REVIEW
    C->>G: aprova ou pede alteração
    G->>L: registra usuário, versão, decisão e data
    alt aprovado
        G->>E: notifica aprovação
        G->>L: CLIENT_REVIEW → APPROVED
    else alteração pedida
        G->>E: notifica com justificativa
        E->>G: cria nova versão sem apagar anterior
        G->>L: registra nova versão e nova rodada
    end
```

### Cartão/tela de aprovação

Deve mostrar, antes dos botões:

- preview visual e legenda;
- rede, formato e data sugerida;
- objetivo, público e CTA;
- observações e sinalização de conteúdo sensível;
- versão atual e acesso ao histórico;
- comentários visíveis ao cliente.

Ações:

- **Aprovar:** confirmação curta e decisão sobre a versão exibida;
- **Pedir alteração:** abre campo obrigatório e exemplos do tipo de feedback útil;
- **Reprovar:** exige motivo e informa que o item sairá das pendências;
- **Salvar para depois:** não muda o estado e apenas mantém a pendência.

Se outra pessoa decidir enquanto a tela está aberta, a API retorna conflito e a tela recarrega a decisão atual; não registra uma segunda decisão contraditória.

## 6. Máquina de estados do conteúdo

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> INTERNAL_REVIEW: enviar para equipe
    DRAFT --> FAILED: falha de geração/processamento
    INTERNAL_REVIEW --> CLIENT_REVIEW: liberar internamente
    INTERNAL_REVIEW --> CHANGES_REQUESTED: ajustes internos
    CLIENT_REVIEW --> APPROVED: cliente aprova
    CLIENT_REVIEW --> CHANGES_REQUESTED: cliente pede alteração
    CHANGES_REQUESTED --> DRAFT: iniciar nova versão
    APPROVED --> SCHEDULED: registrar agendamento
    SCHEDULED --> APPROVED: retirar do calendário
    SCHEDULED --> PUBLISHED: registrar publicação manual
    SCHEDULED --> FAILED: falha operacional
    FAILED --> DRAFT: corrigir/gerar novamente
    FAILED --> SCHEDULED: repetir operação elegível
    DRAFT --> ARCHIVED
    INTERNAL_REVIEW --> ARCHIVED
    CLIENT_REVIEW --> ARCHIVED: reprovar
    APPROVED --> ARCHIVED
    PUBLISHED --> ARCHIVED
    ARCHIVED --> [*]
```

| Origem | Ação | Destino | Quem pode | Efeito adicional |
| --- | --- | --- | --- | --- |
| `DRAFT` | Enviar para revisão | `INTERNAL_REVIEW` | Editor/estrategista autorizado | Congela a versão submetida |
| `INTERNAL_REVIEW` | Liberar | `CLIENT_REVIEW` | Revisor interno autorizado | Cria aprovação e notifica cliente |
| `INTERNAL_REVIEW` | Pedir ajuste | `CHANGES_REQUESTED` | Revisor interno | Motivo obrigatório e notificação |
| `CLIENT_REVIEW` | Aprovar | `APPROVED` | Owner/reviewer cliente | Registra decisão da versão e notifica agência |
| `CLIENT_REVIEW` | Pedir ajuste | `CHANGES_REQUESTED` | Owner/reviewer cliente | Motivo obrigatório; versão preservada |
| `CLIENT_REVIEW` | Reprovar | `ARCHIVED` | Owner/reviewer cliente | Decisão `REJECTED`, motivo e auditoria |
| `CLIENT_REVIEW` | Salvar para depois | sem mudança | Owner/reviewer cliente | Mantém pendência; pode registrar preferência |
| `CHANGES_REQUESTED` | Iniciar ajuste | `DRAFT` | Editor autorizado | Cria nova versão a partir da anterior |
| `APPROVED` | Agendar manualmente | `SCHEDULED` | Equipe autorizada | Registra data; não publica externamente |
| `SCHEDULED` | Marcar como publicado | `PUBLISHED` | Equipe autorizada | Registra ator/data/referência manual |
| elegível | Arquivar | `ARCHIVED` | Papel autorizado | Confirmação e audit log |

Para conteúdo veterinário/saúde, a transição final para `APPROVED` só ocorre quando a revisão profissional exigida estiver registrada. Reabrir um aprovado para edição cria nova versão e nova rodada; a aprovação anterior permanece histórica.

## 7. Pedido de alteração e versão nova

1. Revisor informa uma justificativa objetiva.
2. O conteúdo passa a `CHANGES_REQUESTED`; a versão decidida fica imutável.
3. Editor escolhe **Criar nova versão** e vê o feedback ao lado.
4. O sistema copia os campos editáveis para a nova versão e muda o item para `DRAFT`.
5. A nova versão percorre revisão interna novamente.
6. Cliente recebe nova pendência com indicação “versão 2” e pode comparar com a anterior.

Não há edição silenciosa de uma versão em `CLIENT_REVIEW` ou já decidida.

## 8. Notificações

| Evento | Destinatário | Canal mínimo | Urgência padrão |
| --- | --- | --- | --- |
| Conteúdo liberado ao cliente | Revisores da empresa | Interno; e-mail conforme preferência | Normal ou imediata se marcado urgente |
| Alteração solicitada | Responsável interno | Interno + e-mail configurado | Imediata |
| Conteúdo aprovado/reprovado | Responsável interno | Interno | Normal |
| Nova versão disponível | Cliente que decidiu/está atribuído | Interno; e-mail conforme preferência | Normal |
| Job falhou definitivamente | Administrador/equipe responsável | Interno | Importante |
| Convite criado | Pessoa convidada | E-mail | Imediata |

O registro interno é a fonte de verdade e não depende do sucesso do e-mail. Preferências aceitas: imediato, resumo diário, semanal e somente importante. Contagem de pendências usa aprovações pendentes, não apenas notificações não lidas.

## 9. Calendário e publicação manual

- `APPROVED` pode receber uma data e virar `SCHEDULED`.
- O calendário diferencia sugerido, aprovado e publicado por texto/ícone, não só por cor.
- Arrastar ou editar uma data exige permissão e registra a mudança.
- Na 1.0, **Marcar como publicado** solicita data e referência opcional; não chama rede social.
- Falha ou ausência de uma publicação real não é escondida como sucesso.

## 10. Estados vazios e falhas

| Situação | Mensagem/ação esperada |
| --- | --- |
| Sem cliente | Explicar que o primeiro passo é cadastrar uma empresa; botão **Novo cliente** |
| Brand Kit incompleto | Listar campos úteis que faltam; permitir continuar com aviso quando seguro |
| Sem pendências | Confirmar que está tudo revisado e mostrar próximo conteúdo |
| Sem resultado | Informar que métricas ainda não foram registradas; não mostrar números fictícios |
| Provider indisponível | Preservar dados, mostrar tentativa e oferecer mock/novo envio se autorizado |
| Sessão expirada | Salvar rascunho local seguro quando possível e pedir novo login |
| Acesso negado | Não revelar dados do recurso; orientar troca de contexto/contato com administrador |
| Conflito de versão | Informar que houve atualização e recarregar sem sobrescrever |

## 11. Critérios de UX do fluxo vertical

- Cliente chega da notificação à versão correta.
- Em viewport móvel, preview, resumo e decisão são legíveis sem zoom horizontal.
- A ação principal é alcançável por teclado e leitor de tela.
- Pedido de alteração não pode ser enviado sem motivo.
- Depois da decisão, a tela mostra estado, versão, pessoa e horário.
- Voltar/recarregar não duplica decisão ou notificação.
- Usuário de outra empresa recebe negação segura mesmo conhecendo a URL.
- Operação demorada não bloqueia a página e tem estado consultável.

## 12. Limites da versão 1.0

Não haverá botão que publique automaticamente, altere campanha paga ou envie WhatsApp real. Integrações futuras podem aparecer em um Centro de Integrações como indisponíveis/desconectadas apenas quando isso ajudar a configuração; nunca devem simular sucesso.

