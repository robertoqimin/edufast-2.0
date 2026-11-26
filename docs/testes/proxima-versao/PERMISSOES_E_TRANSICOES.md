# Etapa 2 — permissões e transições

Base examinada: `1a93537`, em 05/11/2026. Documento proposto para revisão de negócio.
Preservar autenticação, aprovações e restrições atuais é requisito confirmado;
a distribuição entre os novos papéis institucionais abaixo é proposta, não aprovação
automática de novos privilégios. Não implementa rotas, modelos ou migrations.

## Regras comuns

Cada operação institucional deve verificar identidade atual, participação ativa,
escola do recurso, papel local e condição específica. Escola na URL, cookie ou
JWT não substitui a verificação. Papel de outra escola não concede autoridade.
Negar por padrão; consultar, contar, exportar e baixar também exigem autorização.

Um Bearer inválido não pode aproveitar uma sessão válida como alternativa.
Escrita autenticada por cookie exige CSRF e origem válida. A política de coexistência
entre cookie e Bearer precisa ser explicitada antes de converter as rotas legadas.

## Matriz por recurso e ação

Todos os papéis abaixo são locais, exceto administração da plataforma. Gestor,
secretaria e coordenação ainda não correspondem automaticamente ao `tipo` global
existente. A conversão exige inventário de contas e revisão de permissões.

| Recurso / ação | Ator proposto | Condição / efeito | Recusa esperada | Rastreabilidade |
| --- | --- | --- | --- | --- |
| Criar instituição | Administração da plataforma | Cadastro operacional; não concede leitura acadêmica | 403 para gestor local | API-005/006/012 |
| Listar/selecionar escolas | Conta autenticada | Apenas participações autorizadas; seleção não cria vínculo | 401 sem autenticação; 404 para contexto externo | API-001 a 009 |
| Convidar equipe | Gestor | Escola ativa; destinatário e papel local; não enviar email externo no teste | 403 para professor; 404 contexto externo | API-013 a 018 |
| Conceder/revogar papéis | Gestor, dentro da alçada a definir | Sem promover conta a administrador da plataforma; alteração invalida autorização subsequente | Negar concessão fora da alçada | REV-02/03; falta contrato completo |
| Períodos | Gestor/secretaria, conforme operação | Criar intervalo válido; fechamento não apaga histórico | 422 intervalo inválido; 404 externo | API-019 a 022 |
| Cadastros de alunos/docentes | Gestor/secretaria | Consultar/alterar apenas registros locais; unicidade institucional | 404 recurso externo; 409 duplicidade | API-023 a 032 |
| Cadastro próprio | Aluno | Leitura do próprio registro na escola | 404 registro de outro aluno | API-026/027 |
| Turmas e matrículas | Gestor/secretaria | Escola e período compatíveis; preservar transferências | 404 vínculo externo; 409 estado/duplicidade | API-033 a 047 |
| Disciplinas/ofertas/docência | Coordenação | Oferta exata; professor local; sem autoatribuição | 403 autoatribuição; 404 vínculo externo | API-038 a 040, 048 a 050 |
| Propor nota | Professor | Atribuição ativa à oferta e aluno elegível; criar proposta pendente | 403 sem atribuição; 422 nota inválida | API-051 a 054 |
| Propor atividade | Professor | Oferta atribuída; proposta pendente sem publicação | 403 aluno; 404 oferta externa | API-055/056 |
| Decidir proposta | Revisor autorizado ao tipo de proposta | Autor diferente do decisor; revalidar vínculos, versões e escola; um único efeito | 403 autoaprovação; 404 externa; 409 conflito | Regressão atual; ampliar catálogo futuro |
| Solicitar documentos | Gestor/secretaria | Titular local; solicitação rastreável | 404 titular externo | API-057 |
| Enviar documento próprio | Aluno | Solicitação própria pendente; tamanho/conteúdo válidos | 404 solicitação alheia; 413 excesso | API-058 a 064 |
| Resposta documental docente | Professor | Preservar aprovação antes do efeito definitivo | Negar envio/decisão fora da alçada | Regressão atual; falta contrato futuro específico |
| Download/foto/exportação | Titular ou papel autorizado ao recurso | Mesmas regras de propriedade para URL direta e listagem | 404 recurso externo | API-059, 068 a 071, 075, 080 a 082 |
| Comunicados | Papel autorizado ao público local | Destinatários limitam leitura; contexto institucional obrigatório | Negar criação por aluno; não revelar público alheio | API-065 a 067 |
| Auditoria | Gestor com alçada local | Consultar eventos próprios da escola; conteúdo minimizado | 404 contexto externo | API-072; completar teste de leitura |

As células marcadas como incompletas são lacunas de aceite; o catálogo não deve ser
considerado completo só porque sua verificação estrutural passa.

## Transições verificáveis

| Objeto | Origem → destino | Precondições | Invariantes |
| --- | --- | --- | --- |
| Proposta docente | Ausente → pendente | Autor autorizado à oferta e operação; dados válidos | Não criar nota/atividade final; registrar escola, autor e conteúdo |
| Proposta | Pendente → aprovada | Revisor autorizado e diferente do autor; escola e participação ativas; vínculo e versão válidos | Decisão e efeito atômicos; uma execução; auditoria |
| Proposta | Pendente → rejeitada | Decisor autorizado; justificativa conforme regra atual | Sem efeito acadêmico; preservar autoria e decisão |
| Proposta decidida | Aprovada/rejeitada → nova decisão | Proibido reabrir implicitamente | Repetição idempotente ou conflito conforme contrato explícito; nunca segundo efeito |
| Participação | Ativa → revogada | Autoridade competente na mesma escola | Próxima operação perde acesso, inclusive token/sessão anterior e aprovação pendente |
| Convite | Pendente → aceito | Email, validade e utilização única | Criar só participação indicada; concorrência não duplica |
| Convite | Pendente → expirado | Relógio igual ou posterior ao limite de validade definido | Não criar participação |
| Matrícula | Ativa → transferida + nova ativa | Turma de destino local elegível; período permitido | Preservar origem e histórico; transação atômica |
| Período | Aberto → fechado | Alçada adequada; regra institucional | Bloquear novas operações proibidas; manter consulta histórica |
| Turma | Ativa → arquivada | Permissão local | Preservar matrículas; negar novas matrículas |
| Escola | Ativa → suspensa | Autoridade operacional a definir | Catálogo atual exige bloqueio de escrita; leitura/recuperação ainda pendentes |

Contas com vários papéis não contornam impedimentos: quem é autor de uma proposta
não pode aprová-la apenas por também possuir papel de revisor. A capacidade atual
de revisar materiais não autoriza aprovar notas. A distribuição dessa capacidade
entre gestor, secretaria e coordenação deve ser fechada antes da implementação.

## Ajustes concretos neste incremento

`API-051` e `API-055` passam a exigir criação de proposta pendente e ausência de
efeito nas tabelas finais. `201` identifica a criação da proposta, não a publicação
da nota/atividade. A fixture passa a exigir `solicitacoes_alteracoes` com escola,
autor, tipo, conteúdo, estado e decisor; não cria a tabela nem simula a API.
O envelope de resposta identifica a proposta em `data`, com o conteúdo em
`data.payload`; os casos verificam a oferta e os valores propostos além do estado.
Os 90 cenários são preservados, com documentos regenerados do catálogo.

O fechamento completo exige novos cenários para decisão, autoaprovação, revisor de
materiais, revogação antes de decidir, conflitos e aprovação concorrente. A regressão
atual continua sendo requisito e não deve ser substituída pelos contratos futuros.

## Decisões necessárias e próximos artefatos

| Decisão | Proposta inicial | Consequência antes de implementar |
| --- | --- | --- |
| Segmento piloto | Não presumir ensino básico ou curso livre | Definir calendário, avaliação e matrícula; evitar escala universal 0–10 |
| Alçada por papel | Separar gestão operacional, secretaria e coordenação | Fechar quem aprova notas/documentos e concede cada papel |
| Escola suspensa | Bloquear escrita, como já contratado | Especificar leitura, downloads e recuperação sem conceder acesso acadêmico global |
| Superperfil atual | Preservar restrições de concessão e revogação | Mapear capacidades para administração da plataforma sem ampliá-las |
| Períodos | Distinguir período letivo institucional de período de avaliação da turma | Mapear modelo atual para futuro sem perder avaliações, notas e reconciliações |

Após revisão, ampliar testes de decisões e compatibilidade; inventariar todas as
entradas institucionais e preparar decisão arquitetural e plano de conversão.
Snapshots históricos continuam preservados. Novo cenário sintético do esquema
atual deve verificar aprovações, calendários e histórico acadêmico. Nenhuma
migration será executada sem revisão do usuário.
