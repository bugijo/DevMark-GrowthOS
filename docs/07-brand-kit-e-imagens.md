# Brand Kit e imagens

## Objetivo

O Brand Kit é a fonte de verdade da identidade de cada cliente. Ele orienta pessoas, templates e providers de IA para que o conteúdo mantenha consistência de marca e não dependa apenas da qualidade de um prompt.

Na primeira entrega vertical, o sistema precisa cadastrar um Brand Kit básico e usá-lo na criação de conteúdo mock. Até o fechamento da versão 1.0, deve também suportar presets visuais, upload seguro, modo template e a estrutura dos modos híbrido e por IA.

## Limites de isolamento

- Todo Brand Kit, preset e arquivo possui `organization_id` e `business_id` quando aplicável.
- A organização é obtida da sessão e da associação autorizada do usuário, nunca aceita apenas de um campo enviado pelo frontend.
- Usuários do cliente acessam somente a própria empresa. Acesso da agência exige associação explícita e papel compatível.
- Referências, prompts, exemplos e aprendizados de uma organização não podem ser usados para outra sem autorização explícita e registrada.
- URLs de arquivos não são públicas por padrão; o acesso deve usar autorização no backend ou URL assinada com validade curta.

## Estrutura do Brand Kit

### Campos mínimos do primeiro fluxo vertical

- nome da marca;
- nome público;
- descrição;
- segmento;
- público principal;
- cores principais;
- tom de voz;
- palavras preferidas e proibidas;
- slogan, quando houver;
- diferenciais;
- serviços ou produtos;
- contatos e links;
- chamadas para ação preferidas;
- observações internas.

Nome da marca, segmento, público, tom de voz e ao menos uma cor principal são obrigatórios para considerar o cadastro básico completo. Campos ausentes devem aparecer como pendência clara, não ser inventados pelo provider.

### Evolução prevista para a versão 1.0

- logo principal e alternativas;
- cores secundárias e fontes;
- endereço, hashtags e termos obrigatórios;
- regras jurídicas e restrições de imagem;
- exemplos aprovados e rejeitados;
- referências visuais e concorrentes;
- catálogo de serviços e produtos estruturado.

Alterações relevantes criam histórico com autor, data, valores alterados e motivo opcional. Exclusão deve ser lógica quando o registro já estiver ligado a conteúdo ou aprovação.

## Presets visuais

Uma empresa pode manter vários presets, como `Institucional`, `Educativo`, `Promoção`, `Urgente`, `Datas comemorativas`, `Depoimento`, `Bastidores`, `Reels` e `Stories`.

Cada preset pode definir:

- objetivo, formato e proporção;
- paleta e fontes permitidas;
- posição e tamanho do logo;
- margens seguras;
- estilo de fundo, fotografia e iluminação;
- nível de realismo e composição;
- limite e regras de texto;
- prompt-base e prompt negativo;
- referências, elementos permitidos e proibidos;
- assinatura visual e CTA padrão.

O preset deve ser versionado ou copiado para a versão de conteúdo. Assim, uma alteração futura no preset não modifica silenciosamente uma peça que já foi enviada para aprovação.

## Modos de criação visual

| Modo | Comportamento | Situação na versão 1.0 |
|---|---|---|
| `TEMPLATE` | Usa layout determinístico da marca. | Obrigatório e funcional. |
| `AI_IMAGE` | Um `ImageProvider` produz a imagem-base. | Contrato e provider mock obrigatórios; provider pago é opcional. |
| `HYBRID` | IA produz a base e o renderizador aplica logo e texto. | Modo recomendado; deve funcionar com base mock ou enviada. |
| `MANUAL` | Usuário envia a imagem e o sistema aplica/adapta a identidade. | Upload e registro obrigatórios. |

O sistema deve funcionar sem chave paga. Em desenvolvimento, testes e demonstração, o provider mock devolve um ativo previsível ou uma referência local identificada como mock, sem simular resultados ou métricas reais.

## Pipeline visual preferencial

1. O conteúdo define objetivo, canal, formato, proporção e preset.
2. O serviço valida Brand Kit, permissões e restrições.
3. O `ImageProvider` ou upload fornece fundo, foto, ilustração ou elemento visual.
4. Um renderizador determinístico aplica textos, logo, preço e CTA.
5. O sistema valida dimensão, área segura, contraste, extensão e tamanho.
6. A saída vira um `media_asset` ligado a uma versão de conteúdo.
7. A peça passa por revisão interna e depois por aprovação do cliente.

Textos importantes não devem ser gerados dentro da imagem pela IA. O renderizador determinístico reduz erros de ortografia e mantém posição, tipografia e contraste verificáveis.

## Arquivos e validações

- Permitir somente tipos e tamanhos configurados; validar conteúdo real do arquivo, não apenas extensão.
- Normalizar nomes, remover metadados desnecessários e impedir execução de conteúdo enviado.
- Rejeitar SVG não sanitizado e formatos não suportados.
- Calcular hash para integridade e eventual deduplicação dentro da mesma organização.
- Guardar dimensões, tipo MIME, tamanho, autor, origem e vínculo com a organização.
- Nunca incluir dados pessoais, credenciais ou informações clínicas nos nomes de arquivos, prompts ou metadados.
- Aplicar varredura antimalware quando o armazenamento de produção for habilitado.

## Conteúdo veterinário e uso responsável

- Não inserir informação clínica sensível em material de marketing.
- Não produzir diagnóstico, prescrição ou orientação veterinária automática.
- Conteúdo de saúde, urgência, tratamento ou prevenção precisa ser marcado como sensível e revisado por profissional responsável antes da aprovação final.
- O provider não pode inventar preços, resultados, credenciais profissionais, depoimentos ou promessas terapêuticas.
- Imagens enganosas, chocantes ou incompatíveis com as restrições da marca devem ser bloqueadas ou sinalizadas para revisão.

## Papéis

- `AGENCY_ADMIN`: administra Brand Kits, presets e políticas.
- `STRATEGIST`: consulta e propõe ajustes de posicionamento e tom.
- `CONTENT_EDITOR`: usa a identidade nos conteúdos e edita campos textuais autorizados.
- `DESIGNER`: administra presets e ativos visuais.
- `CLIENT_OWNER`: revisa dados da própria marca e autoriza mudanças permitidas.
- `CLIENT_REVIEWER`: consulta a marca e revisa peças; não muda regras estruturais por padrão.
- `VIEWER`: somente leitura.
- `SUPER_ADMIN`: acesso excepcional de plataforma, limitado e auditado.

Toda alteração de permissão, Brand Kit, preset ou ativo relevante entra no audit log.

## Critérios de aceite

1. **BK-01:** um usuário interno autorizado consegue criar e editar o Brand Kit básico de uma empresa.
2. **BK-02:** campos obrigatórios ausentes geram mensagens claras e impedem marcar o kit como completo.
3. **BK-03:** um usuário de outra organização recebe negação no backend, mesmo manipulando URL ou payload.
4. **BK-04:** cada alteração relevante registra organização, autor, data e campos alterados no audit log.
5. **BK-05:** o conteúdo mock recebe contexto apenas do Brand Kit da empresa selecionada.
6. **BK-06:** um preset visual pode ser criado, consultado e associado a uma versão de conteúdo.
7. **BK-07:** o provider mock produz resultado determinístico sem chave ou API paga.
8. **BK-08:** uploads inválidos por tipo ou tamanho são rejeitados sem serem disponibilizados ao usuário.
9. **BK-09:** a versão enviada à aprovação preserva a configuração visual usada naquele momento.
10. **BK-10:** o portal funciona em tela móvel e explica o próximo passo quando o Brand Kit está vazio ou incompleto.
11. **BK-11:** conteúdos veterinários sensíveis exibem a exigência de revisão profissional.
12. **BK-12:** nenhuma peça é publicada automaticamente a partir deste fluxo.

## Fora do escopo desta etapa

- geração automática de vídeo;
- biblioteca comercial completa de templates;
- treinamento de modelos com dados dos clientes;
- publicação direta em redes sociais;
- compra de mídia ou alteração de orçamento;
- remoção automática de fundo e edição gráfica avançada;
- garantia de qualidade de providers externos não configurados.

