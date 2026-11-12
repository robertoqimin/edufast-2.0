# Frequência, faltas e atestados — 12/11/2026

Estado: código preparado e testado em ambientes descartáveis. A migration
[`004_frequencia.sql`](../../Códigos/migrations/004_frequencia.sql) **não foi
executada nas escolas Teste 01/02 nem em produção**. Base: commit `7c39bc0` mais
os arquivos deste módulo. Alterações anteriores nos contratos da próxima versão
foram preservadas e não integram esta entrega.

## Regras confirmadas pelo usuário

- Professor faz a chamada da própria turma e matéria, com aprovação administrativa.
- Admin consulta presenças/faltas, confere chamadas e emite relatório.
- Atestado aceito mantém a falta como **justificada**, sem abono ou conversão em presença.

## Uso

Menu compartilhado: **Frequência e atestados**, rota `/frequencia`.

Professor seleciona a oferta turma/matéria autorizada, data e número de aula no dia
(1 a 20). Marca explicitamente cada aluno como presente ou falta, sem marcação
automática por padrão. Envio completo gera chamada pendente. A administração vê
a turma/matéria, abre a chamada e aprova/rejeita com motivo e versão do registro.
Proposta não entra no relatório até aprovação.

Reenviar data/aula já aprovada exige motivo de correção e produz nova revisão.
A chamada anterior permanece vigente até aprovação da nova, quando fica como
substituída. Rejeição da correção preserva o resultado anterior. Histórico,
motivo docente e motivo da decisão são mantidos separadamente. Não há edição
direta ou exclusão de chamada confirmada pelo professor.

Admin filtra o relatório por datas e turma/matéria; pela API também pode filtrar
aluno. Professor consulta apenas oferta autorizada; aluno consulta somente seus
registros. Relatório HTML detalha aula, turma, matéria, aluno e situação. CSV é
restrito ao admin, registra período, protege células contra fórmulas e audita a
exportação. Nenhum anexo ou motivo de atestado entra no relatório.

Somente chamadas aprovadas e vigentes compõem o denominador. O percentual é
`presenças / (presenças + faltas não justificadas + faltas justificadas) * 100`.
O total de faltas soma justificadas e não justificadas. Ausência de chamada não
implica falta nem presença. Não foi adicionada regra de reprovação automática.

Aluno envia seu atestado; admin pode enviar para aluno da própria instalação.
São aceitos PDF/PNG/JPEG de até 5 MiB, com verificação inicial de assinatura do
arquivo. Isso não equivale a antivírus ou validação médica. O servidor gera o nome
e cifra o conteúdo com a chave da instalação. Downloads exigem autorização,
registram auditoria e são entregues como anexo, sem cache e com `nosniff`.
Professor e outros alunos não acessam o documento. Não há campo para diagnóstico.

Admin aceita ou rejeita o atestado com motivo, sem detalhes médicos. Apenas um
atestado aceito e que cubra a data justifica faltas; marcações originais continuam
como falta. Justificativa também aparece quando a chamada é aprovada depois do
aceite. Intervalo de consulta/atestado limitado a 367 dias. Aluno vê a decisão
do próprio documento. Não há revogação automática de decisão de atestado.

## Permissões e integridade

Autenticação usa os mecanismos atuais (cookie/JWT, estado e versão da conta).
POSTs de navegador exigem CSRF mesmo sem header Origin. Todos os envios e decisões
usam idempotência persistida e transação. Decisões exigem versão e estado pendente;
aprovar chamada revalida conta docente, vínculo e turma não arquivada.

Ofertas com atribuições explícitas usam `AtribuicaoDocenteModel` ativo. Enquanto
uma oferta não tiver atribuições reconciliadas, preserva-se a regra legada de
professor/turma e professor/disciplina. Essa compatibilidade não resolve a futura
modelagem de papéis institucionais; deve ser substituída pela reconciliação de
atribuições, sem inventar vínculos históricos. O isolamento de escolas permanece
na conexão e nos containers por cliente; não existe troca de banco por parâmetro.

O elenco da chamada inicial usa matrículas atuais da turma; revisões preservam
o elenco da chamada aprovada. Não há cronologia de matrículas neste módulo.
Datas retroativas precisam de conferência administrativa conforme os registros
da escola. As datas seguem o relógio do servidor; configurar o fuso operacional
da instalação antes do uso real. Aulas/turnos/calendários e fechamento de frequência
por período não foram automatizados nesta versão.

## Esquema e ativação

Quatro tabelas novas: `frequencia_chamadas`, `frequencia_presencas`,
`frequencia_atestados`, `frequencia_auditoria`. O SQL inclui chaves estrangeiras,
unicidade por aula/revisão e por aluno/chamada, além de constraints de estados.
Importação dos modelos é explícita: iniciar uma instalação existente não cria nem
migra tabelas. Sem o esquema, o módulo informa indisponibilidade e preserva login
e telas anteriores. O iniciador das duas escolas reconhece o módulo já instalado
sem recriar tabelas, senhas ou dados.

Seguir [o procedimento de revisão](../../Códigos/migrations/README.md), revisar o
SQL e fazer backup de banco/uploads/chave antes de pedir a execução em cada escola.
Os testes usam bancos novos e descartáveis, não migrations nas escolas existentes.

## Validação executada

Imagem local `edufast-frequencia:test`, Python 3.12, MySQL 8.4 e SQLite.

- Frequência em MySQL: **14 testes aprovados**, incluindo duas propostas e duas
  decisões concorrentes, privacidade de documentos, rollback de arquivo/banco,
  repetição idempotente, correção e justificativa sem remoção da falta.
- Aplicação, aprovações e frequência em SQLite: **59 testes**, 56 aprovados e
  3 ignorados por exigirem concorrência MySQL; nenhuma falha.
- Infraestrutura e proteção de submissão: **16 testes Node aprovados**.
- Edge headless, contexto isolado: professor marca 20 alunos, envia chamada;
  admin aprova; aluno 02 envia documento fictício; admin aceita; relatório exibe
  1 falta justificada, 1 falta total e 0,00% de presença para esse aluno.
- Capturas novas em desktop 1440x1000 e mobile 390x844; referências anteriores
  preservadas. Comparação no manifesto e relatório visual de 12/11.
- Verificador estático ampliado para os templates `frequencia_*`.

Nos primeiros ensaios houve ajuste do contrato JSON para multipart e do caminho
de importação do servidor visual/gerador SQL; os testes finais acima foram
executados depois dessas correções. A regressão legada emitiu ResourceWarning de
arquivos não fechados em testes de download, sem falha de asserção. Não atribuir
essa advertência ao módulo novo sem investigação específica.

Não houve teste de carga, dispositivo físico, antivírus, retenção automatizada,
integração com boletim/reprovação, produção remota ou migração de dados históricos.
O ambiente visual local 5091 é descartável e não deve receber dados reais.
