# Contrato proposto para revisão

[Início da revisão](README.md) · [Plano de produto](../../planejamento/PROXIMA_VERSAO.md)

**Revisão técnica de 05/11/2026:** consulte [divergências e decisões pendentes](REVISAO_2026-11-05.md). O catálogo anterior precisa ser conciliado com as aprovações docentes e com o esquema atual antes da implementação; esta revisão não aprova migrations.

## Decisões ainda revisáveis

A [matriz de permissões e transições](PERMISSOES_E_TRANSICOES.md) detalha atores,
precondições, recusas e lacunas. Escritas docentes de notas e atividades criam
propostas pendentes; `API-051` e `API-055` exigem ausência de efeito acadêmico
imediato. A aprovação deve preservar as garantias da versão atual.

Os testes tornam explícitas as seguintes propostas. Elas ainda podem ser alteradas após sua leitura, antes de iniciar a implementação:

- Somente o administrador da plataforma cria novas instituições nesta primeira etapa.
- Gestor e secretaria administram cadastros, turmas, matrículas e documentos locais; coordenação administra disciplinas, ofertas e atribuições docentes.
- Professor atua na oferta explicitamente atribuída; aluno lê seus próprios dados e envia seus documentos.
- Matrícula de identificação do aluno é única por escola; código de turma é único por escola/período.
- Transferência encerra o vínculo original como `transferida` e cria uma nova matrícula `ativa`, preservando histórico. Não transfere dados entre escolas.
- Notas usam escala inicial 0–10 nos casos de API; a função unitária recebe os limites explicitamente. Regras específicas do segmento da escola piloto ainda precisam ser definidas.
- Exportação de alunos é CSV nesta etapa; novos formatos exigem casos próprios.
- Extensões iniciais de documentos: PDF, PNG e JPG/JPEG, com limite de arquivo de 16 MiB. Cabeçalho/MIME informado pelo cliente não é suficiente para aceitar um arquivo inválido.
- Escola suspensa bloqueia novas gravações. Leitura e política de recuperação de acesso deverão ser detalhadas antes da implementação do estado operacional.

O limite total da requisição precisa considerar o overhead do multipart para permitir o tamanho de arquivo contratado. Esse ajuste será parte da implementação; os testes de arquivo acima do limite continuam exigindo resposta 413.

## Formato HTTP

Prefixo proposto: `/api/v1`. Rotas institucionais contêm `/escolas/{escola_id}`. O servidor consulta a participação atual e valida o proprietário do recurso, sem confiar no escopo do corpo ou apenas no JWT.

```json
{"data": {"id": 1, "escola_id": 1, "nome": "Exemplo fictício"}}
```

Listas têm ordenação inicial por ID crescente e paginação no servidor:

```json
{"data": [{"id": 1, "escola_id": 1}], "meta": {"page": 1, "per_page": 25, "total": 1}}
```

Erros da API usam JSON:

```json
{"error": {"code": "not_found", "message": "Recurso não encontrado"}}
```

Os testes verificam o código de erro estável, sem impor a redação exata da mensagem. Downloads e exportações retornam seus bytes e os cabeçalhos adequados, não esse envelope JSON.

| HTTP | Significado proposto |
| --- | --- |
| 200 | Consulta/alteração concluída |
| 201 | Novo recurso criado |
| 400 | Entrada incompatível no endpoint legado, preservando seu contrato quando indicado |
| 401 | Falta de autenticação válida |
| 403 | Falta de permissão em contexto conhecido ou participação revogada |
| 404 | Recurso inexistente ou pertencente a contexto que não pode ser revelado |
| 409 | Duplicidade ou transição incompatível com o estado atual |
| 410 | Convite expirado |
| 413 | Conteúdo acima do limite |
| 422 | Validação de campos/regras de entrada |

## Autenticação e rotas antigas

`POST /api/v1/auth/login` recebe email e senha e retorna `data.access_token`. Os testes usam o token real em `Authorization: Bearer ...`. `POST /api/v1/contexto` seleciona a escola autorizada e também estabelece o contexto usado pelas páginas legadas na mesma sessão.

O contrato preserva JWT HS256 nesta etapa. Email inexistente e senha incorreta retornam o mesmo erro `invalid_credentials`, sem emitir token. Um Bearer inválido/expirado não pode ser aceito por existir uma sessão web anterior. O teste de expiração reaproveita o token real, altera somente `exp` e o assina novamente com a chave fictícia do ambiente, para distinguir expiração de assinatura inválida.

A API de teste não ignora autorização e não cria um endpoint público de reset de banco. A massa é inserida diretamente pelo executor isolado.

As entradas antigas de alunos, busca e arquivos são testadas explicitamente: seu nome ou formato de URL não pode permitir contornar o isolamento. Contas com dois vínculos mantêm papéis diferentes em cada escola.

## Massa fictícia

Senha única de fixture: `Senha-ci-123456`, restrita ao ambiente descartável.

| Ator | Escola Alfa (1) | Escola Beta (2) |
| --- | --- | --- |
| `plataforma` | Sem acesso acadêmico automático | Sem acesso acadêmico automático |
| `gestor_a` | Gestor | Sem vínculo |
| `secretaria_a` | Secretaria | Sem vínculo |
| `coordenacao_a` | Coordenação | Sem vínculo |
| `professor_a` | Professor, atribuído apenas à oferta 1 | Sem vínculo |
| `aluno_a` | Dono do aluno 1 | Sem vínculo |
| `dupla` | Gestor; cadastro de aluno 3 | Aluno; cadastro de aluno 4 |
| `gestor_b` | Sem vínculo | Gestor |
| `aluno_b` | Sem vínculo | Dono do aluno 2 |
| `sem_vinculo` | Nenhuma participação | Nenhuma participação |
| `convidado` | Convite pendente, sem participação | Sem vínculo |

Todos os emails seguem `<ator>@example.test`. As escolas têm suas próprias turmas, disciplinas, documentos e comunicados. Há uma turma local adicional sem matrícula, para exercitar novas matrículas e transferências.

Cada teste restaura a fixture. Convite válido tem token sintético conhecido e validade até 2099; o expirado terminou em 2000. Os unitários testam o instante exato de expiração com relógio recebido como argumento. Tokens são armazenados na fixture somente como hash SHA-256; a aplicação futura poderá introduzir um adaptador se adotar outro armazenamento, sem mudar o comportamento esperado.

## Interfaces unitárias propostas

Módulo futuro: `app.services.academic_policy`. Exceção: `PolicyError(code, status)`. As funções e suas entradas constam em [UNITARIOS.md](UNITARIOS.md). Nenhum desses serviços foi criado para fazer os testes passarem.

As funções validam regra de aplicação, não substituem transações, autorização nos endpoints ou restrições do banco. Os testes de API e integração cobram essas outras camadas.

## Contrato físico dos dados

A fixture de integração propõe tabelas e colunas explícitas em [fixtures.py](../../../.github/cicd/next/fixtures.py), sem criar modelos de aplicação. Isso permite verificar persistência e integridade de verdade.

Se a revisão escolher nomes ou uma estrutura diferente, adaptar a fixture e as consultas dos testes para o mesmo comportamento de negócio. Não criar tabelas paralelas, endpoints fictícios ou serviços de teste que devolvam respostas pré-fabricadas apenas para satisfazer o catálogo.
