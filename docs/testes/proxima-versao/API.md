# Testes de API — contrato proposto

Gerado de `.github/cicd/next/catalog.py`. Revisar antes de implementar. Cada caso começa com a mesma massa fictícia restaurada.

Os testes chamam a aplicação real pelo cliente HTTP do Flask e verificam respostas e, quando indicado, o estado do banco. Não são respostas simuladas.

| ID | Área | Cenário | Esperado |
| --- | --- | --- | --- |
| API-001 | Escolas | Sem autenticação não lista escolas | 401 |
| API-002 | Escolas | Gestor lista apenas a própria escola | 200 |
| API-003 | Escolas | Conta com dois vínculos lista as duas escolas | 200 |
| API-004 | Escolas | Conta sem vínculo não ganha escola automaticamente | 200 |
| API-005 | Escolas | Administrador da plataforma cria instituição | 201 |
| API-006 | Escolas | Gestor local não cria outra instituição | 403 |
| API-007 | Escolas | Seleciona escola autorizada | 200 |
| API-008 | Escolas | Selecionar escola alheia não concede acesso | 404 |
| API-009 | Escolas | Conta dupla mantém papel de aluno na escola B | 403 |
| API-010 | Escolas | Revogação invalida o token já emitido | 403 |
| API-011 | Escolas | Escola suspensa bloqueia escrita acadêmica | 403 |
| API-012 | Escolas | Admin da plataforma não lê conteúdo acadêmico sem vínculo | 404 |
| API-013 | Convites | Gestor convida membro local sem enviar email real no teste | 201 |
| API-014 | Convites | Professor não concede papel de gestor | 403 |
| API-015 | Convites | Aceitar convite cria apenas o vínculo indicado | 200 |
| API-016 | Convites | Convite expirado não cria vínculo | 410 |
| API-017 | Convites | Convite não pode ser utilizado por outro email | 403 |
| API-018 | Convites | Segundo aceite não duplica participação | 409 |
| API-019 | Períodos | Secretaria cria período válido | 201 |
| API-020 | Períodos | Fim anterior ao início é rejeitado | 422 |
| API-021 | Períodos | Período alheio não aparece por ID direto | 404 |
| API-022 | Períodos | Fechamento preserva período e registros | 200 |
| API-023 | Pessoas | Busca de alunos não revela nome da outra escola | 200 |
| API-024 | Pessoas | Detalhe de aluno externo retorna 404 | 404 |
| API-025 | Pessoas | Edição de aluno externo não altera o banco | 404 |
| API-026 | Pessoas | Aluno consulta seu cadastro | 200 |
| API-027 | Pessoas | Aluno não consulta outro aluno da mesma escola | 404 |
| API-028 | Pessoas | Professor externo não aparece em busca | 200 |
| API-029 | Pessoas | Secretaria cria aluno na escola ativa | 201 |
| API-030 | Pessoas | Campo escola_id no corpo não redireciona gravação | 422 |
| API-031 | Pessoas | Matrícula pode repetir em escolas diferentes | 201 |
| API-032 | Pessoas | Matrícula duplicada na mesma escola é rejeitada | 409 |
| API-033 | Turmas | Lista apenas turmas da escola | 200 |
| API-034 | Turmas | Cria turma vinculada ao período local | 201 |
| API-035 | Turmas | Período de outra escola não pode receber turma | 404 |
| API-036 | Turmas | Código duplicado no mesmo período é rejeitado | 409 |
| API-037 | Turmas | Arquivamento mantém matrículas históricas | 200 |
| API-038 | Disciplinas | Cria disciplina local | 201 |
| API-039 | Disciplinas | Oferta cruza apenas dados da mesma escola | 404 |
| API-040 | Disciplinas | Oferta válida é criada | 201 |
| API-041 | Matrículas | Matricula aluno local em turma local | 201 |
| API-042 | Matrículas | Repetir matrícula não duplica registro | 409 |
| API-043 | Matrículas | Aluno externo não pode ser matriculado | 404 |
| API-044 | Matrículas | Turma arquivada não recebe matrícula | 409 |
| API-045 | Matrículas | Período fechado bloqueia matrícula | 409 |
| API-046 | Matrículas | Transferência encerra vínculo antigo e mantém histórico | 201 |
| API-047 | Matrículas | Transferência para outra escola não altera origem | 404 |
| API-048 | Docência | Coordenação atribui professor à oferta exata | 201 |
| API-049 | Docência | Professor externo não recebe atribuição local | 404 |
| API-050 | Docência | Professor não se autoatribui | 403 |
| API-051 | Notas | Professor propõe nota na própria oferta sem gravação acadêmica imediata | 201 |
| API-052 | Notas | Mesmo professor em pares separados não autoriza outra oferta | 403 |
| API-053 | Notas | Revogação docente bloqueia token existente | 403 |
| API-054 | Notas | Nota fora da escala não é gravada | 422 |
| API-055 | Atividades | Professor propõe atividade na oferta atribuída sem publicação imediata | 201 |
| API-056 | Atividades | Aluno não cria atividade | 403 |
| API-057 | Documentos | Secretaria solicita documento de aluno local | 201 |
| API-058 | Documentos | Aluno envia arquivo da própria solicitação | 201 |
| API-059 | Documentos | Documento de outra escola não é baixado | 404 |
| API-060 | Documentos | Aluno não envia documento de colega | 404 |
| API-061 | Documentos | Executável disfarçado não é aceito | 422 |
| API-062 | Documentos | Arquivo acima de 16 MiB é recusado | 413 |
| API-063 | Documentos | Download autorizado entrega bytes e anexo | 200 |
| API-064 | Documentos | Foto de perfil externa também exige escopo | 404 |
| API-065 | Comunicação | Comunicado é criado na escola local | 201 |
| API-066 | Comunicação | Aluno não lê comunicado restrito à equipe | 404 |
| API-067 | Comunicação | Listagem não revela comunicado da escola B | 200 |
| API-068 | Painel | Indicadores contam apenas a escola local | 200 |
| API-069 | Painel | Paginação é executada no servidor | 200 |
| API-070 | Painel | Página inválida recebe erro de validação | 422 |
| API-071 | Exportação | Exportação não inclui dados externos | 200 |
| API-072 | Auditoria | Ação administrativa registra ator e escola | 200 |
| API-073 | Compatibilidade | Rota antiga de detalhe não ignora isolamento | 404 |
| API-074 | Compatibilidade | Busca antiga também aplica contexto da escola | 200 |
| API-075 | Compatibilidade | Arquivo antigo não fica público pelo nome | 401 |
| API-076 | Compatibilidade | Cadastro público não aceita papel privilegiado | 400 |
| API-077 | Cache | Alternar escola não reaproveita painel privado anterior | 403 |
| API-078 | Matrículas | Duas requisições concorrentes criam apenas uma matrícula | [201, 409] |
| API-079 | Convites | Dois aceites concorrentes não duplicam participação | [200, 409] |
| API-080 | Compatibilidade | Foto antiga não fica pública pelo nome | 401 |
| API-081 | Compatibilidade | Download antigo autenticado não ignora escola | 404 |
| API-082 | Compatibilidade | Foto antiga autenticada não ignora escola | 404 |
| API-083 | Pessoas | Secretaria cadastra professor apenas na escola local | 201 |
| API-084 | Compatibilidade | Cadastro público de aluno não cria vínculo na escola informada | 403 |
| API-085 | Escolas | Redução de papel bloqueia token emitido antes da mudança | 403 |
| API-086 | Autenticação | Email inexistente não recebe token | 401 |
| API-087 | Autenticação | Senha incorreta não recebe token | 401 |
| API-088 | Autenticação | Login incompleto retorna validação | 422 |
| API-089 | Autenticação | Token adulterado é rejeitado mesmo com sessão anterior | 401 |
| API-090 | Autenticação | Token válido na assinatura mas expirado é rejeitado | 401 |

## API-001 — Sem autenticação não lista escolas

**Perfil:** `não autenticado`. **Requisição:** `GET /api/v1/escolas`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "unauthenticated"
}
```

## API-002 — Gestor lista apenas a própria escola

**Perfil:** `gestor_a`. **Requisição:** `GET /api/v1/escolas`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1
  ]
}
```

## API-003 — Conta com dois vínculos lista as duas escolas

**Perfil:** `dupla`. **Requisição:** `GET /api/v1/escolas`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1,
    2
  ]
}
```

## API-004 — Conta sem vínculo não ganha escola automaticamente

**Perfil:** `sem_vinculo`. **Requisição:** `GET /api/v1/escolas`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": []
}
```

## API-005 — Administrador da plataforma cria instituição

**Perfil:** `plataforma`. **Requisição:** `POST /api/v1/escolas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Escola Gama",
    "codigo": "GAMA"
  },
  "equals": {
    "data.nome": "Escola Gama"
  },
  "db": [
    {
      "table": "escolas",
      "where": {
        "codigo": "GAMA"
      },
      "count": 1
    }
  ]
}
```

## API-006 — Gestor local não cria outra instituição

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/escolas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Escola Gama",
    "codigo": "GAMA"
  },
  "error": "forbidden",
  "db": [
    {
      "table": "escolas",
      "where": {
        "codigo": "GAMA"
      },
      "count": 0
    }
  ]
}
```

## API-007 — Seleciona escola autorizada

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/contexto`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "escola_id": 1
  },
  "equals": {
    "data.escola_id": 1
  }
}
```

## API-008 — Selecionar escola alheia não concede acesso

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/contexto`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "escola_id": 2
  },
  "error": "not_found"
}
```

## API-009 — Conta dupla mantém papel de aluno na escola B

**Perfil:** `dupla`. **Requisição:** `POST /api/v1/escolas/2/turmas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Sem permissão",
    "codigo": "NEGADA",
    "periodo_id": 2,
    "turno": "manha"
  },
  "error": "forbidden"
}
```

## API-010 — Revogação invalida o token já emitido

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "mutate": {
    "table": "participacoes_escolas",
    "where": {
      "usuario_id": 3,
      "escola_id": 1
    },
    "values": {
      "status": "revogada"
    }
  },
  "error": "membership_inactive"
}
```

## API-011 — Escola suspensa bloqueia escrita acadêmica

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/escolas/1/turmas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Bloqueada",
    "codigo": "SUSP",
    "periodo_id": 1,
    "turno": "manha"
  },
  "mutate": {
    "table": "escolas",
    "where": {
      "id": 1
    },
    "values": {
      "status": "suspensa"
    }
  },
  "error": "school_inactive"
}
```

## API-012 — Admin da plataforma não lê conteúdo acadêmico sem vínculo

**Perfil:** `plataforma`. **Requisição:** `GET /api/v1/escolas/1/alunos`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-013 — Gestor convida membro local sem enviar email real no teste

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/escolas/1/convites`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "nova@example.test",
    "papel": "secretaria"
  },
  "equals": {
    "data.escola_id": 1,
    "data.papel": "secretaria"
  },
  "db": [
    {
      "table": "convites_escolas",
      "where": {
        "email": "nova@example.test",
        "escola_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-014 — Professor não concede papel de gestor

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/convites`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "nova@example.test",
    "papel": "gestor"
  },
  "error": "forbidden"
}
```

## API-015 — Aceitar convite cria apenas o vínculo indicado

**Perfil:** `convidado`. **Requisição:** `POST /api/v1/convites/aceitar`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "token": "convite-ci-valido"
  },
  "db": [
    {
      "table": "participacoes_escolas",
      "where": {
        "usuario_id": 11,
        "escola_id": 1,
        "papel": "secretaria"
      },
      "count": 1
    },
    {
      "table": "participacoes_escolas",
      "where": {
        "usuario_id": 11,
        "escola_id": 2
      },
      "count": 0
    }
  ]
}
```

## API-016 — Convite expirado não cria vínculo

**Perfil:** `convidado`. **Requisição:** `POST /api/v1/convites/aceitar`.

**Resposta esperada:** `410`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "token": "convite-ci-expirado"
  },
  "error": "invitation_expired",
  "db": [
    {
      "table": "participacoes_escolas",
      "where": {
        "usuario_id": 11
      },
      "count": 0
    }
  ]
}
```

## API-017 — Convite não pode ser utilizado por outro email

**Perfil:** `sem_vinculo`. **Requisição:** `POST /api/v1/convites/aceitar`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "token": "convite-ci-valido"
  },
  "error": "invitation_recipient_mismatch"
}
```

## API-018 — Segundo aceite não duplica participação

**Perfil:** `convidado`. **Requisição:** `POST /api/v1/convites/aceitar`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "before": [
    {
      "method": "POST",
      "path": "/api/v1/convites/aceitar",
      "json": {
        "token": "convite-ci-valido"
      },
      "status": 200
    }
  ],
  "json": {
    "token": "convite-ci-valido"
  },
  "error": "invitation_used",
  "db": [
    {
      "table": "participacoes_escolas",
      "where": {
        "usuario_id": 11,
        "escola_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-019 — Secretaria cria período válido

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/periodos`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "2027",
    "inicio": "2027-02-01",
    "fim": "2027-12-15"
  },
  "equals": {
    "data.escola_id": 1
  }
}
```

## API-020 — Fim anterior ao início é rejeitado

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/periodos`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Inválido",
    "inicio": "2027-12-01",
    "fim": "2027-02-01"
  },
  "error": "invalid_period"
}
```

## API-021 — Período alheio não aparece por ID direto

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/periodos/2`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-022 — Fechamento preserva período e registros

**Perfil:** `gestor_a`. **Requisição:** `POST /api/v1/escolas/1/periodos/1/fechar`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "equals": {
    "data.status": "fechado"
  },
  "db": [
    {
      "table": "periodos_letivos",
      "where": {
        "id": 1,
        "status": "fechado"
      },
      "count": 1
    },
    {
      "table": "matriculas",
      "where": {
        "id": 1
      },
      "count": 1
    }
  ]
}
```

## API-023 — Busca de alunos não revela nome da outra escola

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos?q=Aluno`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1,
    3
  ],
  "absent": [
    "Aluno Beta",
    "aluno.b@example.test"
  ]
}
```

## API-024 — Detalhe de aluno externo retorna 404

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/2`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-025 — Edição de aluno externo não altera o banco

**Perfil:** `secretaria_a`. **Requisição:** `PATCH /api/v1/escolas/1/alunos/2`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Alterado"
  },
  "error": "not_found",
  "db": [
    {
      "table": "alunos",
      "where": {
        "id": 2,
        "nome": "Aluno Beta"
      },
      "count": 1
    }
  ]
}
```

## API-026 — Aluno consulta seu cadastro

**Perfil:** `aluno_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/1`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "equals": {
    "data.nome": "Aluno Alfa"
  }
}
```

## API-027 — Aluno não consulta outro aluno da mesma escola

**Perfil:** `aluno_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/3`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-028 — Professor externo não aparece em busca

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/professores`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1
  ],
  "absent": [
    "Professor Beta"
  ]
}
```

## API-029 — Secretaria cria aluno na escola ativa

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/alunos`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Nova Aluna",
    "email": "nova.aluna@example.test",
    "matricula": "ALFA-NEW"
  },
  "equals": {
    "data.escola_id": 1
  },
  "db": [
    {
      "table": "alunos",
      "where": {
        "matricula": "ALFA-NEW",
        "escola_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-030 — Campo escola_id no corpo não redireciona gravação

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/alunos`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Teste",
    "email": "teste@example.test",
    "matricula": "INJETADA",
    "escola_id": 2
  },
  "error": "scope_mismatch",
  "db": [
    {
      "table": "alunos",
      "where": {
        "matricula": "INJETADA"
      },
      "count": 0
    }
  ]
}
```

## API-031 — Matrícula pode repetir em escolas diferentes

**Perfil:** `gestor_b`. **Requisição:** `POST /api/v1/escolas/2/alunos`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Aluna Beta Dois",
    "email": "beta.dois@example.test",
    "matricula": "A001"
  },
  "equals": {
    "data.escola_id": 2
  }
}
```

## API-032 — Matrícula duplicada na mesma escola é rejeitada

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/alunos`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Duplicada",
    "email": "duplicada@example.test",
    "matricula": "A001"
  },
  "error": "duplicate_student_number"
}
```

## API-033 — Lista apenas turmas da escola

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/turmas`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1,
    3
  ]
}
```

## API-034 — Cria turma vinculada ao período local

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "7º A",
    "codigo": "7A",
    "periodo_id": 1,
    "turno": "manha"
  },
  "equals": {
    "data.escola_id": 1,
    "data.periodo_id": 1
  }
}
```

## API-035 — Período de outra escola não pode receber turma

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Inválida",
    "codigo": "CROSS",
    "periodo_id": 2
  },
  "error": "not_found",
  "db": [
    {
      "table": "turmas",
      "where": {
        "codigo": "CROSS"
      },
      "count": 0
    }
  ]
}
```

## API-036 — Código duplicado no mesmo período é rejeitado

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Duplicada",
    "codigo": "6A",
    "periodo_id": 1
  },
  "error": "duplicate_class_code"
}
```

## API-037 — Arquivamento mantém matrículas históricas

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas/1/arquivar`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "equals": {
    "data.status": "arquivada"
  },
  "db": [
    {
      "table": "matriculas",
      "where": {
        "turma_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-038 — Cria disciplina local

**Perfil:** `coordenacao_a`. **Requisição:** `POST /api/v1/escolas/1/disciplinas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "História",
    "codigo": "HIS",
    "carga_horaria": 80
  },
  "equals": {
    "data.escola_id": 1
  }
}
```

## API-039 — Oferta cruza apenas dados da mesma escola

**Perfil:** `coordenacao_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "turma_id": 1,
    "disciplina_id": 2,
    "periodo_id": 1
  },
  "error": "not_found"
}
```

## API-040 — Oferta válida é criada

**Perfil:** `coordenacao_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "turma_id": 3,
    "disciplina_id": 3,
    "periodo_id": 1
  },
  "equals": {
    "data.turma_id": 3,
    "data.escola_id": 1
  }
}
```

## API-041 — Matricula aluno local em turma local

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 3,
    "turma_id": 3,
    "periodo_id": 1
  },
  "equals": {
    "data.status": "ativa"
  },
  "db": [
    {
      "table": "matriculas",
      "where": {
        "aluno_id": 3,
        "turma_id": 3,
        "status": "ativa"
      },
      "count": 1
    }
  ]
}
```

## API-042 — Repetir matrícula não duplica registro

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 1,
    "turma_id": 1,
    "periodo_id": 1
  },
  "error": "duplicate_enrollment",
  "db": [
    {
      "table": "matriculas",
      "where": {
        "aluno_id": 1,
        "turma_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-043 — Aluno externo não pode ser matriculado

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 2,
    "turma_id": 1,
    "periodo_id": 1
  },
  "error": "not_found"
}
```

## API-044 — Turma arquivada não recebe matrícula

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 3,
    "turma_id": 3,
    "periodo_id": 1
  },
  "mutate": {
    "table": "turmas",
    "where": {
      "id": 3
    },
    "values": {
      "status": "arquivada"
    }
  },
  "error": "class_archived"
}
```

## API-045 — Período fechado bloqueia matrícula

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `409`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 3,
    "turma_id": 3,
    "periodo_id": 1
  },
  "mutate": {
    "table": "periodos_letivos",
    "where": {
      "id": 1
    },
    "values": {
      "status": "fechado"
    }
  },
  "error": "period_closed"
}
```

## API-046 — Transferência encerra vínculo antigo e mantém histórico

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas/1/transferir`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "turma_destino_id": 3,
    "motivo": "Mudança de turno"
  },
  "db": [
    {
      "table": "matriculas",
      "where": {
        "id": 1,
        "status": "transferida"
      },
      "count": 1
    },
    {
      "table": "matriculas",
      "where": {
        "aluno_id": 1,
        "turma_id": 3,
        "status": "ativa"
      },
      "count": 1
    }
  ]
}
```

## API-047 — Transferência para outra escola não altera origem

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas/1/transferir`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "turma_destino_id": 2,
    "motivo": "Inválida"
  },
  "error": "not_found",
  "db": [
    {
      "table": "matriculas",
      "where": {
        "id": 1,
        "status": "ativa"
      },
      "count": 1
    }
  ]
}
```

## API-048 — Coordenação atribui professor à oferta exata

**Perfil:** `coordenacao_a`. **Requisição:** `POST /api/v1/escolas/1/atribuicoes`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "professor_id": 1,
    "oferta_id": 3
  },
  "equals": {
    "data.professor_id": 1,
    "data.oferta_id": 3
  }
}
```

## API-049 — Professor externo não recebe atribuição local

**Perfil:** `coordenacao_a`. **Requisição:** `POST /api/v1/escolas/1/atribuicoes`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "professor_id": 2,
    "oferta_id": 1
  },
  "error": "not_found"
}
```

## API-050 — Professor não se autoatribui

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/atribuicoes`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "professor_id": 1,
    "oferta_id": 3
  },
  "error": "forbidden"
}
```

## API-051 — Professor propõe nota na própria oferta sem gravação acadêmica imediata

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/1/notas`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 1,
    "nota": 8.5
  },
  "equals": {
    "data.escola_id": 1,
    "data.estado": "pendente",
    "data.tipo": "salvar_nota",
    "data.payload.oferta_id": 1,
    "data.payload.aluno_id": 1,
    "data.payload.nota": 8.5
  },
  "db": [
    {
      "table": "notas",
      "where": {
        "escola_id": 1
      },
      "count": 0
    },
    {
      "table": "solicitacoes_alteracoes",
      "where": {
        "escola_id": 1,
        "solicitante_id": 5,
        "tipo": "salvar_nota",
        "estado": "pendente",
        "decidido_por": null
      },
      "count": 1
    }
  ]
}
```

## API-052 — Mesmo professor em pares separados não autoriza outra oferta

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/3/notas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 3,
    "nota": 8.5
  },
  "error": "assignment_required"
}
```

## API-053 — Revogação docente bloqueia token existente

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/1/notas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 1,
    "nota": 8.5
  },
  "mutate": {
    "table": "atribuicoes_docentes",
    "where": {
      "id": 1
    },
    "values": {
      "ativo": false
    }
  },
  "error": "assignment_required"
}
```

## API-054 — Nota fora da escala não é gravada

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/1/notas`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 1,
    "nota": 11
  },
  "error": "invalid_grade"
}
```

## API-055 — Professor propõe atividade na oferta atribuída sem publicação imediata

**Perfil:** `professor_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/1/atividades`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "titulo": "Exercício",
    "descricao": "Dados fictícios",
    "data_entrega": "2099-11-15"
  },
  "equals": {
    "data.escola_id": 1,
    "data.estado": "pendente",
    "data.tipo": "lancar_atividade",
    "data.payload.oferta_id": 1,
    "data.payload.titulo": "Exercício"
  },
  "db": [
    {
      "table": "atividades",
      "where": {
        "escola_id": 1
      },
      "count": 0
    },
    {
      "table": "solicitacoes_alteracoes",
      "where": {
        "escola_id": 1,
        "solicitante_id": 5,
        "tipo": "lancar_atividade",
        "estado": "pendente",
        "decidido_por": null
      },
      "count": 1
    }
  ]
}
```

## API-056 — Aluno não cria atividade

**Perfil:** `aluno_a`. **Requisição:** `POST /api/v1/escolas/1/ofertas/1/atividades`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "titulo": "Indevida"
  },
  "error": "forbidden"
}
```

## API-057 — Secretaria solicita documento de aluno local

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/solicitacoes-documentos`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "aluno_id": 1,
    "titulo": "Comprovante"
  },
  "equals": {
    "data.status": "pendente",
    "data.escola_id": 1
  }
}
```

## API-058 — Aluno envia arquivo da própria solicitação

**Perfil:** `aluno_a`. **Requisição:** `POST /api/v1/escolas/1/solicitacoes-documentos/1/arquivo`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "upload": {
    "filename": "comprovante.pdf",
    "content_type": "application/pdf",
    "content": "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 20 40 Td (COMPROVANTE-CI) Tj ET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000241 00000 n \n0000000335 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n405\n%%EOF\n"
  },
  "followup": {
    "method": "GET",
    "path": "/api/v1/escolas/1/documentos/{data.id}/arquivo",
    "status": 200,
    "body_contains": "COMPROVANTE-CI"
  },
  "db": [
    {
      "table": "solicitacoes_documentos",
      "where": {
        "id": 1,
        "status": "enviado"
      },
      "count": 1
    }
  ]
}
```

## API-059 — Documento de outra escola não é baixado

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/documentos/2/arquivo`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found",
  "absent": [
    "DOCUMENTO-BETA"
  ]
}
```

## API-060 — Aluno não envia documento de colega

**Perfil:** `aluno_a`. **Requisição:** `POST /api/v1/escolas/1/solicitacoes-documentos/3/arquivo`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "upload": {
    "filename": "comprovante.pdf",
    "content_type": "application/pdf",
    "content": "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 20 40 Td (COMPROVANTE-CI) Tj ET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000241 00000 n \n0000000335 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n405\n%%EOF\n"
  },
  "error": "not_found"
}
```

## API-061 — Executável disfarçado não é aceito

**Perfil:** `aluno_a`. **Requisição:** `POST /api/v1/escolas/1/solicitacoes-documentos/1/arquivo`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "upload": {
    "filename": "documento.pdf",
    "content_type": "application/pdf",
    "content": "MZ-not-a-pdf"
  },
  "error": "invalid_file"
}
```

## API-062 — Arquivo acima de 16 MiB é recusado

**Perfil:** `aluno_a`. **Requisição:** `POST /api/v1/escolas/1/solicitacoes-documentos/1/arquivo`.

**Resposta esperada:** `413`. **Bancos:** sqlite, postgresql.

```json
{
  "upload": {
    "filename": "grande.pdf",
    "content_type": "application/pdf",
    "size": 16777217
  },
  "error": "payload_too_large"
}
```

## API-063 — Download autorizado entrega bytes e anexo

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/documentos/1/arquivo`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "body_contains": "DOCUMENTO-ALFA",
  "headers_contains": {
    "Content-Disposition": "attachment"
  }
}
```

## API-064 — Foto de perfil externa também exige escopo

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/2/foto`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-065 — Comunicado é criado na escola local

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/comunicados`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "titulo": "Reunião",
    "mensagem": "Comunicado de teste",
    "destinatario": "alunos"
  },
  "equals": {
    "data.escola_id": 1
  }
}
```

## API-066 — Aluno não lê comunicado restrito à equipe

**Perfil:** `aluno_a`. **Requisição:** `GET /api/v1/escolas/1/comunicados/3`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "not_found"
}
```

## API-067 — Listagem não revela comunicado da escola B

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/comunicados`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1,
    3
  ],
  "absent": [
    "Comunicado Beta"
  ]
}
```

## API-068 — Indicadores contam apenas a escola local

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/painel`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "equals": {
    "data.alunos": 2,
    "data.turmas": 2,
    "data.professores": 1,
    "data.escola_id": 1
  }
}
```

## API-069 — Paginação é executada no servidor

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos?page=1&per_page=1`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "ids": [
    1
  ],
  "equals": {
    "meta.total": 2,
    "meta.page": 1,
    "meta.per_page": 1
  }
}
```

## API-070 — Página inválida recebe erro de validação

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos?page=0`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "error": "invalid_pagination"
}
```

## API-071 — Exportação não inclui dados externos

**Perfil:** `secretaria_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/exportacao`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "body_contains": "Aluno Alfa",
  "absent": [
    "Aluno Beta"
  ],
  "headers_contains": {
    "Content-Disposition": "attachment",
    "Content-Type": "text/csv"
  }
}
```

## API-072 — Ação administrativa registra ator e escola

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas/1/arquivar`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "db": [
    {
      "table": "eventos_auditoria",
      "where": {
        "escola_id": 1,
        "ator_id": 3,
        "acao": "turma.arquivada",
        "recurso_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-073 — Rota antiga de detalhe não ignora isolamento

**Perfil:** `secretaria_a`. **Requisição:** `GET /admin/alunos/2`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "Aluno Beta"
  ]
}
```

## API-074 — Busca antiga também aplica contexto da escola

**Perfil:** `professor_a`. **Requisição:** `GET /alunos/busca?termo=Aluno`.

**Resposta esperada:** `200`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "Aluno Beta"
  ]
}
```

## API-075 — Arquivo antigo não fica público pelo nome

**Perfil:** `não autenticado`. **Requisição:** `GET /arquivos/download/documento-beta.pdf`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "DOCUMENTO-BETA"
  ]
}
```

## API-076 — Cadastro público não aceita papel privilegiado

**Perfil:** `não autenticado`. **Requisição:** `POST /cadastro`.

**Resposta esperada:** `400`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "invasor@example.test",
    "senha": "Senha-ci-123456",
    "nome": "Teste",
    "tipo": "gestor",
    "escola_id": 2
  },
  "db": [
    {
      "table": "participacoes_escolas",
      "where": {
        "escola_id": 2
      },
      "count": 3
    }
  ]
}
```

## API-077 — Alternar escola não reaproveita painel privado anterior

**Perfil:** `dupla`. **Requisição:** `GET /api/v1/escolas/2/painel`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "before": [
    {
      "method": "GET",
      "path": "/api/v1/escolas/1/painel",
      "status": 200
    }
  ],
  "error": "forbidden"
}
```

## API-078 — Duas requisições concorrentes criam apenas uma matrícula

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/matriculas`.

**Resposta esperada:** `[201, 409]`. **Bancos:** postgresql.

```json
{
  "json": {
    "aluno_id": 3,
    "turma_id": 3,
    "periodo_id": 1
  },
  "concurrent": 2,
  "conflict_error": "duplicate_enrollment",
  "db": [
    {
      "table": "matriculas",
      "where": {
        "aluno_id": 3,
        "turma_id": 3
      },
      "count": 1
    }
  ]
}
```

## API-079 — Dois aceites concorrentes não duplicam participação

**Perfil:** `convidado`. **Requisição:** `POST /api/v1/convites/aceitar`.

**Resposta esperada:** `[200, 409]`. **Bancos:** postgresql.

```json
{
  "json": {
    "token": "convite-ci-valido"
  },
  "concurrent": 2,
  "conflict_error": "invitation_used",
  "db": [
    {
      "table": "participacoes_escolas",
      "where": {
        "usuario_id": 11,
        "escola_id": 1
      },
      "count": 1
    }
  ]
}
```

## API-080 — Foto antiga não fica pública pelo nome

**Perfil:** `não autenticado`. **Requisição:** `GET /arquivos/perfil/perfil_beta.png`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "FOTO-BETA"
  ]
}
```

## API-081 — Download antigo autenticado não ignora escola

**Perfil:** `secretaria_a`. **Requisição:** `GET /arquivos/download/documento-beta.pdf`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "DOCUMENTO-BETA"
  ]
}
```

## API-082 — Foto antiga autenticada não ignora escola

**Perfil:** `secretaria_a`. **Requisição:** `GET /arquivos/perfil/perfil_beta.png`.

**Resposta esperada:** `404`. **Bancos:** sqlite, postgresql.

```json
{
  "absent": [
    "FOTO-BETA"
  ]
}
```

## API-083 — Secretaria cadastra professor apenas na escola local

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/professores`.

**Resposta esperada:** `201`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Docente Novo",
    "email": "docente.novo@example.test",
    "cpf": "12345000350"
  },
  "equals": {
    "data.escola_id": 1
  },
  "db": [
    {
      "table": "professores",
      "where": {
        "escola_id": 1,
        "cpf": "12345000350"
      },
      "count": 1
    },
    {
      "table": "professores",
      "where": {
        "escola_id": 2,
        "cpf": "12345000350"
      },
      "count": 0
    }
  ]
}
```

## API-084 — Cadastro público de aluno não cria vínculo na escola informada

**Perfil:** `não autenticado`. **Requisição:** `POST /cadastro`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "publico@example.test",
    "senha": "Senha-ci-123456",
    "nome": "Teste",
    "tipo": "aluno",
    "escola_id": 2,
    "matricula": "PUBLICA"
  },
  "db": [
    {
      "table": "alunos",
      "where": {
        "matricula": "PUBLICA"
      },
      "count": 0
    },
    {
      "table": "participacoes_escolas",
      "where": {
        "escola_id": 2
      },
      "count": 3
    }
  ]
}
```

## API-085 — Redução de papel bloqueia token emitido antes da mudança

**Perfil:** `secretaria_a`. **Requisição:** `POST /api/v1/escolas/1/turmas`.

**Resposta esperada:** `403`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "nome": "Negada",
    "codigo": "NEGADA",
    "periodo_id": 1
  },
  "error": "forbidden",
  "mutate": {
    "table": "participacoes_escolas",
    "where": {
      "usuario_id": 3,
      "escola_id": 1
    },
    "values": {
      "papel": "aluno"
    }
  }
}
```

## API-086 — Email inexistente não recebe token

**Perfil:** `não autenticado`. **Requisição:** `POST /api/v1/auth/login`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "inexistente@example.test",
    "senha": "Senha-ci-123456"
  },
  "error": "invalid_credentials",
  "absent": [
    "access_token"
  ]
}
```

## API-087 — Senha incorreta não recebe token

**Perfil:** `não autenticado`. **Requisição:** `POST /api/v1/auth/login`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "gestor_a@example.test",
    "senha": "senha-incorreta"
  },
  "error": "invalid_credentials",
  "absent": [
    "access_token"
  ]
}
```

## API-088 — Login incompleto retorna validação

**Perfil:** `não autenticado`. **Requisição:** `POST /api/v1/auth/login`.

**Resposta esperada:** `422`. **Bancos:** sqlite, postgresql.

```json
{
  "json": {
    "email": "gestor_a@example.test"
  },
  "error": "invalid_payload",
  "absent": [
    "access_token"
  ]
}
```

## API-089 — Token adulterado é rejeitado mesmo com sessão anterior

**Perfil:** `aluno_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/1`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "auth_override": "tampered",
  "error": "unauthenticated"
}
```

## API-090 — Token válido na assinatura mas expirado é rejeitado

**Perfil:** `aluno_a`. **Requisição:** `GET /api/v1/escolas/1/alunos/1`.

**Resposta esperada:** `401`. **Bancos:** sqlite, postgresql.

```json
{
  "auth_override": "expired",
  "error": "unauthenticated"
}
```
