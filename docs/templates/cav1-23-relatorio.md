# Relatório de validação independente CAV1-23

> Preencha este documento sem remover falhas, tentativas ou pedidos de ajuda.
> A validação deve usar um clone novo e somente as instruções do README.

## Identificação

- **Nome do avaliador:**
- **Sistema operacional e versão:**
- **Hardware/arquitetura:**
- **Memória disponível para o Docker:**
- **Espaço livre inicial:**
- **Data e fuso horário:**
- **Commit testado (`git rev-parse HEAD`):**
- **Tempo total da validação:**

## Etapas concluídas

- [ ] Requisitos mínimos confirmados
- [ ] Clone novo e limpo confirmado
- [ ] `.env` criado a partir de `.env.example`
- [ ] `make setup`
- [ ] `make doctor`
- [ ] `make status` com seis serviços saudáveis
- [ ] Frontend acessível
- [ ] Backend/OpenAPI acessível
- [ ] Mailpit acessível
- [ ] Login como agência
- [ ] Login como cliente revisor
- [ ] Roteiro manual do README
- [ ] `make e2e`
- [ ] `make install`, `make lint` e `make test` (opcionais; indicar se não executados)
- [ ] Evidências salvas antes da limpeza
- [ ] `make down` ou `make reset`

## Comandos e tempos

| Comando/etapa | Início | Fim | Resultado | Observação |
|---|---|---|---|---|
| Clone | | | | |
| `make setup` | | | | |
| `make doctor` | | | | |
| `make status` | | | | |
| Teste manual | | | | |
| `make e2e` | | | | |
| Testes opcionais | | | | |

## Erros encontrados

Para cada erro, informe comando, saída completa ou arquivo de log, etapa,
tentativa de repetição e impacto. Não corrija código durante a validação.

1. **Erro:**
   - Comando/etapa:
   - Saída ou evidência:
   - Repetiu na segunda tentativa?:
   - Impacto:

## Necessidade de ajuda externa

- **Foi necessária ajuda externa?** Sim / Não
- **Quem ajudou e por qual canal?**
- **Qual informação não estava clara ou não existia no README?**
- **A validação teria sido concluída sem essa ajuda?** Sim / Não

## Evidências

Liste caminhos ou links para logs, screenshots e vídeos. Remova ou masque
qualquer segredo antes de anexar ao PR.

- Log do `scripts/cav1-23-check.sh`:
- Saída do `git status --short --branch`:
- Saída do `git rev-parse HEAD`:
- Saída do `make doctor`:
- Saída do `make status`:
- Resultado do `make e2e`:
- Screenshots do frontend e Mailpit:
- Outras evidências:

## Resultado final

- **Resultado:** PASS / FAIL
- **Justificativa objetiva:**
- **Há instrução implícita ou ausente no README?**
- **Há bloqueio para declarar CAV1-23 concluído?**
- **Recomendação ao responsável pelo PR:**

### Regra para PASS

Marque `PASS` somente quando a instalação partir de clone novo, os seis serviços
ficarem saudáveis, os acessos e logins funcionarem, o roteiro manual e o E2E
passarem, e nenhuma ajuda externa tiver sido necessária para suprir instrução
ausente. O preenchimento deste relatório, por si só, não muda a matriz oficial.
