# Permissões e aprovações

O servidor consulta papel, estado e versão da autenticação no banco em cada
requisição. Cadastro público permanece pendente, sem privilégios nem login,
até aprovação administrativa. Valores enviados pelo navegador não concedem acesso.

| Perfil | Acesso |
| --- | --- |
| Admin da secretaria | Operações administrativas diretas, CPF, aprovação de cadastros e alterações, designação de revisor de materiais |
| Super admin | Mesmo acesso administrativo e concessão de papéis administrativos a outras contas |
| Professor ativo | Consulta de alunos vinculados por matrícula, nome ou turma; propostas de turma, disciplina, edição acadêmica de aluno, nota, atividade/material e documento |
| Professor revisor de materiais | Acesso de professor e aprovação de atividade/material de outro professor em disciplina atribuída ao revisor |
| Aluno | Seus documentos e atividades das turmas em que está matriculado |
| Cadastro pendente | Sem acesso institucional |

Revisor não aprova o próprio envio, cadastro, nota, edição de aluno ou documento
administrativo. Também não recebe CPF nem poderes da secretaria. O painel fica
em `/solicitacoes`, com links nos painéis existentes.

## Fluxo

1. Professor envia proposta com chave de idempotência. O servidor valida campos,
   vínculos, versões e escopo; a entidade acadêmica ainda não é alterada.
2. Arquivo anexado fica privado e pendente. Autor e revisor autorizado podem
   consultá-lo pela rota da solicitação; a rota normal não o publica.
3. Admin ou revisor autorizado decide. O banco bloqueia a linha da proposta;
   revalida vínculos e versões e grava decisão e efeito na mesma transação.
4. Segunda decisão recebe conflito, sem repetir o efeito. Rejeição mantém os
   dados originais. Arquivos rejeitados permanecem privados para auditoria.

`GET/POST /solicitacoes/alteracoes` lista/envia propostas. POST JSON usa
`Idempotency-Key` e `{ "tipo": "...", "payload": {...} }`.
`POST /solicitacoes/alteracoes/<id>/decidir` recebe `decisao` igual a
`aprovar` ou `rejeitar` e justificativa opcional. O conteúdo aprovado é o
armazenado no banco; o decisor não substitui o payload.

`POST /admin/usuarios/<id>/permissoes` concede `revisor_materiais` booleano.
Somente super admin pode alterar `papel` de outra conta ativa. Não ativa cadastro
pendente. Alterações de permissão e logout revogam sessões/JWT anteriores.
Provisionamento inicial usa `flask create-admin --super-admin` para conta nova.

## Proteções comuns

**Login (desde 23/11/2026):** 5 falhas seguidas bloqueiam a conta por 15 minutos (até a
senha correta é recusada, com 429 e `Retry-After`); um IP é bloqueado após 30 falhas em
qualquer conta. E-mail inexistente e senha errada têm a mesma resposta (401, "E-mail ou
senha inválidos") e o mesmo custo, então o login não revela quais contas existem. A tabela
`limites_login` guarda apenas HMAC do e-mail e do IP. Limites ajustáveis por
`LOGIN_MAX_TENTATIVAS`, `LOGIN_MAX_TENTATIVAS_IP` e `LOGIN_BLOQUEIO_MINUTOS`.

**Senhas:** todos os perfis, pelo menos 12 caracteres com um caractere especial; no máximo 128
(decisão do usuário em 24/11/2026; antes, 6 caracteres para aluno e professor). A regra vale no
servidor e nos formulários (`minlength`). Contas existentes não são alteradas: a regra vale
para novas senhas.

**Cabeçalhos:** toda resposta da escola e do painel central leva CSP com nonce (scripts só
do próprio servidor), proteção contra enquadramento, `nosniff`, `Referrer-Policy` e
`Permissions-Policy`; páginas de usuário logado não são armazenadas em cache
(`Vary: Cookie`, `Cache-Control: private, no-store`). Relatório:
`Documentos/testes/SEGURANCA_CORRECOES_2026-11-23.md`.

CPF e data de nascimento não integram a busca de professores. Busca por CPF fica
restrita a admin/super admin. Download aplica a mesma autorização de objeto a
cookie e JWT, inclusive foto de perfil. Respostas de arquivo são privadas,
anexadas e sem cache. Formulários incluem proteção CSRF e bloqueio de reenvio;
o banco continua sendo a proteção contra concorrência.

SECRET_KEY própria de pelo menos 32 caracteres é obrigatória. Debug só é
permitido em desenvolvimento; a entrada local usa loopback por padrão e as
portas de desenvolvimento são publicadas no loopback. Produção mantém proxy/TLS.
Se a chave padrão foi usada em ambiente acessível, substituí-la e invalidar
sessões emitidas anteriormente antes de liberar acesso.

## Implantação pendente de revisão

Não executar automaticamente `migrations/002_aprovacoes_e_permissoes.sql`.
Ela adiciona estado, capacidade de revisão, versão de autenticação e tabela de
propostas. Coloca professores legados em quarentena, pois o legado não registra
se vieram de cadastro público ou administrativo. Revisar a lista de professores
confiáveis antes da execução, com backup e validação em cópia do banco.
Nenhum dado duplicado é removido. A aplicação não executa DDL na inicialização.

## Refatoração e testes

`ci.py` e `admin_controller.py` preservam fachadas e nomes públicos. Extrações
individuais foram verificadas com testes de caracterização antes das mudanças
de segurança. Comportamentos alterados intencionalmente têm testes próprios:
envio docente pendente, admissão aprovada e acesso restrito a arquivos/CPF.

Suítes: `test_ci_characterization.py`, `tests/test_admin_characterization.py`,
`tests/test_approvals_security.py`, `tests/test_concurrency.py`, testes existentes
de API e deploy, testes Node de envio, CI com SQLite/PostgreSQL e Postman/Newman.
Postman usa somente dados sintéticos; nenhum teste aplica migration em banco existente.

Fora desta correção: falha de limpeza do CI pode impedir gravação do resumo,
comportamento preservado pelos testes de caracterização. Especificações futuras
em `next` não foram relaxadas para fazer a implementação atual passar.

Referências: [autorização OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
e [upload de arquivos OWASP](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
