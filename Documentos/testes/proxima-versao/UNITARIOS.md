# Testes unitários — regras propostas

Gerado de `.github/cicd/next/catalog.py`. As funções futuras de `app.services.academic_policy` devem ser puras: sem criar aplicação, abrir banco, enviar email ou acessar rede.

Falhas de negócio usam `PolicyError`, com atributos `code` e `status`. Os testes não incluem implementação alternativa dessas regras.

| ID | Área | Cenário | Função |
| --- | --- | --- | --- |
| UNIT-001 | Permissões | Secretaria consulta recurso local | `authorize` |
| UNIT-002 | Permissões | Mesmo papel não permite recurso externo | `authorize` |
| UNIT-003 | Permissões | Vínculo revogado bloqueia acesso | `authorize` |
| UNIT-004 | Permissões | Aluno só consulta seu próprio cadastro | `authorize` |
| UNIT-005 | Permissões | Aluno não cria turma | `authorize` |
| UNIT-006 | Permissões | Sem participação não há acesso institucional | `authorize` |
| UNIT-007 | Períodos | Intervalo letivo válido | `validate_period` |
| UNIT-008 | Períodos | Datas invertidas são inválidas | `validate_period` |
| UNIT-009 | Períodos | Data inexistente é inválida | `validate_period` |
| UNIT-010 | Períodos | Período de um dia é aceito | `validate_period` |
| UNIT-011 | Matrículas | Transição ativa → transferida | `validate_enrollment_transition` |
| UNIT-012 | Matrículas | Transição ativa → cancelada | `validate_enrollment_transition` |
| UNIT-013 | Matrículas | Transição transferida → ativa | `validate_enrollment_transition` |
| UNIT-014 | Matrículas | Transição cancelada → ativa | `validate_enrollment_transition` |
| UNIT-015 | Matrículas | Período fechado bloqueia alteração | `validate_enrollment_transition` |
| UNIT-016 | Integridade | Relações locais são válidas | `validate_scope` |
| UNIT-017 | Integridade | Uma relação externa invalida a operação inteira | `validate_scope` |
| UNIT-018 | Docência | Oferta exata permite docência | `teacher_can_access` |
| UNIT-019 | Docência | Outra oferta não é inferida por cruzamento | `teacher_can_access` |
| UNIT-020 | Docência | Outra escola não permite docência | `teacher_can_access` |
| UNIT-021 | Docência | Outro professor não recebe acesso | `teacher_can_access` |
| UNIT-022 | Docência | Atribuição inativa é rejeitada | `teacher_can_access` |
| UNIT-023 | Notas | Nota 0 | `validate_grade` |
| UNIT-024 | Notas | Nota 10 | `validate_grade` |
| UNIT-025 | Notas | Nota 8.5 | `validate_grade` |
| UNIT-026 | Notas | Nota -1 | `validate_grade` |
| UNIT-027 | Notas | Nota 11 | `validate_grade` |
| UNIT-028 | Notas | Nota NaN | `validate_grade` |
| UNIT-029 | Convites | Convite válido para o destinatário | `validate_invitation` |
| UNIT-030 | Convites | Expiração é inclusiva no instante limite | `validate_invitation` |
| UNIT-031 | Convites | Convite utilizado não pode ser reusado | `validate_invitation` |
| UNIT-032 | Convites | Email diferente não pode aceitar | `validate_invitation` |
| UNIT-033 | Paginação | Página padrão limita a 25 registros | `pagination` |
| UNIT-034 | Paginação | Pedido excessivo limita a 100 registros | `pagination` |
| UNIT-035 | Paginação | Página zero é inválida | `pagination` |
| UNIT-036 | Paginação | Texto arbitrário não vira página válida | `pagination` |
| UNIT-037 | Arquivos | PDF dentro do limite é permitido | `validate_upload_metadata` |
| UNIT-038 | Arquivos | Extensão executável é rejeitada | `validate_upload_metadata` |
| UNIT-039 | Arquivos | Arquivo vazio é rejeitado | `validate_upload_metadata` |
| UNIT-040 | Arquivos | Tamanho acima de 16 MiB é rejeitado | `validate_upload_metadata` |
| UNIT-041 | Cache | Cache separa escolas | `private_cache_key` |
| UNIT-042 | Cache | Cache separa usuários | `private_cache_key` |
| UNIT-043 | Cache | Cache invalida mudança de permissão | `private_cache_key` |
| UNIT-044 | Cache | Cache separa filtros de período | `private_cache_key` |
| UNIT-045 | Comunicação | Aluno recebe comunicado para alunos | `can_read_notice` |
| UNIT-046 | Comunicação | Aluno não recebe comunicado restrito à equipe | `can_read_notice` |
| UNIT-047 | Comunicação | Professor recebe comunicado para equipe | `can_read_notice` |

## UNIT-001 — Secretaria consulta recurso local

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": {
      "usuario_id": 3,
      "escola_id": 1,
      "papel": "secretaria",
      "status": "ativa"
    },
    "resource": {
      "escola_id": 1,
      "tipo": "aluno"
    },
    "action": "read"
  },
  "result": true
}
```

## UNIT-002 — Mesmo papel não permite recurso externo

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": {
      "usuario_id": 3,
      "escola_id": 1,
      "papel": "secretaria",
      "status": "ativa"
    },
    "resource": {
      "escola_id": 2,
      "tipo": "aluno"
    },
    "action": "read"
  },
  "error": "not_found",
  "status": 404
}
```

## UNIT-003 — Vínculo revogado bloqueia acesso

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": {
      "usuario_id": 3,
      "escola_id": 1,
      "papel": "secretaria",
      "status": "revogada"
    },
    "resource": {
      "escola_id": 1,
      "tipo": "aluno"
    },
    "action": "read"
  },
  "error": "membership_inactive",
  "status": 403
}
```

## UNIT-004 — Aluno só consulta seu próprio cadastro

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": {
      "usuario_id": 6,
      "escola_id": 1,
      "papel": "aluno",
      "status": "ativa"
    },
    "resource": {
      "escola_id": 1,
      "tipo": "aluno",
      "usuario_id": 7
    },
    "action": "read"
  },
  "error": "not_found",
  "status": 404
}
```

## UNIT-005 — Aluno não cria turma

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": {
      "usuario_id": 3,
      "escola_id": 1,
      "papel": "aluno",
      "status": "ativa"
    },
    "resource": {
      "escola_id": 1,
      "tipo": "turma"
    },
    "action": "create"
  },
  "error": "forbidden",
  "status": 403
}
```

## UNIT-006 — Sem participação não há acesso institucional

**Função proposta:** `authorize`.

```json
{
  "arguments": {
    "member": null,
    "resource": {
      "escola_id": 1,
      "tipo": "aluno"
    },
    "action": "read"
  },
  "error": "not_found",
  "status": 404
}
```

## UNIT-007 — Intervalo letivo válido

**Função proposta:** `validate_period`.

```json
{
  "arguments": {
    "inicio": "2027-02-01",
    "fim": "2027-12-15"
  },
  "result": true
}
```

## UNIT-008 — Datas invertidas são inválidas

**Função proposta:** `validate_period`.

```json
{
  "arguments": {
    "inicio": "2027-12-15",
    "fim": "2027-02-01"
  },
  "error": "invalid_period",
  "status": 422
}
```

## UNIT-009 — Data inexistente é inválida

**Função proposta:** `validate_period`.

```json
{
  "arguments": {
    "inicio": "2027-02-30",
    "fim": "2027-12-15"
  },
  "error": "invalid_period",
  "status": 422
}
```

## UNIT-010 — Período de um dia é aceito

**Função proposta:** `validate_period`.

```json
{
  "arguments": {
    "inicio": "2027-02-01",
    "fim": "2027-02-01"
  },
  "result": true
}
```

## UNIT-011 — Transição ativa → transferida

**Função proposta:** `validate_enrollment_transition`.

```json
{
  "arguments": {
    "current": "ativa",
    "target": "transferida",
    "period_status": "aberto"
  },
  "result": true
}
```

## UNIT-012 — Transição ativa → cancelada

**Função proposta:** `validate_enrollment_transition`.

```json
{
  "arguments": {
    "current": "ativa",
    "target": "cancelada",
    "period_status": "aberto"
  },
  "result": true
}
```

## UNIT-013 — Transição transferida → ativa

**Função proposta:** `validate_enrollment_transition`.

```json
{
  "arguments": {
    "current": "transferida",
    "target": "ativa",
    "period_status": "aberto"
  },
  "error": "invalid_enrollment_transition",
  "status": 409
}
```

## UNIT-014 — Transição cancelada → ativa

**Função proposta:** `validate_enrollment_transition`.

```json
{
  "arguments": {
    "current": "cancelada",
    "target": "ativa",
    "period_status": "aberto"
  },
  "error": "invalid_enrollment_transition",
  "status": 409
}
```

## UNIT-015 — Período fechado bloqueia alteração

**Função proposta:** `validate_enrollment_transition`.

```json
{
  "arguments": {
    "current": "ativa",
    "target": "transferida",
    "period_status": "fechado"
  },
  "error": "period_closed",
  "status": 409
}
```

## UNIT-016 — Relações locais são válidas

**Função proposta:** `validate_scope`.

```json
{
  "arguments": {
    "escola_id": 1,
    "resources": [
      {
        "escola_id": 1
      },
      {
        "escola_id": 1
      }
    ]
  },
  "result": true
}
```

## UNIT-017 — Uma relação externa invalida a operação inteira

**Função proposta:** `validate_scope`.

```json
{
  "arguments": {
    "escola_id": 1,
    "resources": [
      {
        "escola_id": 1
      },
      {
        "escola_id": 2
      }
    ]
  },
  "error": "not_found",
  "status": 404
}
```

## UNIT-018 — Oferta exata permite docência

**Função proposta:** `teacher_can_access`.

```json
{
  "arguments": {
    "assignments": [
      {
        "escola_id": 1,
        "professor_id": 1,
        "oferta_id": 1,
        "ativo": true
      }
    ],
    "escola_id": 1,
    "professor_id": 1,
    "oferta_id": 1
  },
  "result": true
}
```

## UNIT-019 — Outra oferta não é inferida por cruzamento

**Função proposta:** `teacher_can_access`.

```json
{
  "arguments": {
    "assignments": [
      {
        "escola_id": 1,
        "professor_id": 1,
        "oferta_id": 1,
        "ativo": true
      }
    ],
    "escola_id": 1,
    "professor_id": 1,
    "oferta_id": 3
  },
  "result": false
}
```

## UNIT-020 — Outra escola não permite docência

**Função proposta:** `teacher_can_access`.

```json
{
  "arguments": {
    "assignments": [
      {
        "escola_id": 1,
        "professor_id": 1,
        "oferta_id": 1,
        "ativo": true
      }
    ],
    "escola_id": 2,
    "professor_id": 1,
    "oferta_id": 1
  },
  "result": false
}
```

## UNIT-021 — Outro professor não recebe acesso

**Função proposta:** `teacher_can_access`.

```json
{
  "arguments": {
    "assignments": [
      {
        "escola_id": 1,
        "professor_id": 1,
        "oferta_id": 1,
        "ativo": true
      }
    ],
    "escola_id": 1,
    "professor_id": 2,
    "oferta_id": 1
  },
  "result": false
}
```

## UNIT-022 — Atribuição inativa é rejeitada

**Função proposta:** `teacher_can_access`.

```json
{
  "arguments": {
    "assignments": [
      {
        "escola_id": 1,
        "professor_id": 1,
        "oferta_id": 1,
        "ativo": false
      }
    ],
    "escola_id": 1,
    "professor_id": 1,
    "oferta_id": 1
  },
  "result": false
}
```

## UNIT-023 — Nota 0

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": 0,
    "minimum": 0,
    "maximum": 10
  },
  "result": true
}
```

## UNIT-024 — Nota 10

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": 10,
    "minimum": 0,
    "maximum": 10
  },
  "result": true
}
```

## UNIT-025 — Nota 8.5

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": 8.5,
    "minimum": 0,
    "maximum": 10
  },
  "result": true
}
```

## UNIT-026 — Nota -1

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": -1,
    "minimum": 0,
    "maximum": 10
  },
  "error": "invalid_grade",
  "status": 422
}
```

## UNIT-027 — Nota 11

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": 11,
    "minimum": 0,
    "maximum": 10
  },
  "error": "invalid_grade",
  "status": 422
}
```

## UNIT-028 — Nota NaN

**Função proposta:** `validate_grade`.

```json
{
  "arguments": {
    "value": "NaN",
    "minimum": 0,
    "maximum": 10
  },
  "error": "invalid_grade",
  "status": 422
}
```

## UNIT-029 — Convite válido para o destinatário

**Função proposta:** `validate_invitation`.

```json
{
  "arguments": {
    "invitation": {
      "email": "nova@example.test",
      "status": "pendente",
      "expires_at": "2026-11-01T12:00:00Z"
    },
    "email": "nova@example.test",
    "now": "2026-11-01T11:59:59Z"
  },
  "result": true
}
```

## UNIT-030 — Expiração é inclusiva no instante limite

**Função proposta:** `validate_invitation`.

```json
{
  "arguments": {
    "invitation": {
      "email": "nova@example.test",
      "status": "pendente",
      "expires_at": "2026-11-01T12:00:00Z"
    },
    "email": "nova@example.test",
    "now": "2026-11-01T12:00:00Z"
  },
  "error": "invitation_expired",
  "status": 410
}
```

## UNIT-031 — Convite utilizado não pode ser reusado

**Função proposta:** `validate_invitation`.

```json
{
  "arguments": {
    "invitation": {
      "email": "nova@example.test",
      "status": "aceito",
      "expires_at": "2026-11-01T12:00:00Z"
    },
    "email": "nova@example.test",
    "now": "2026-11-01T11:00:00Z"
  },
  "error": "invitation_used",
  "status": 409
}
```

## UNIT-032 — Email diferente não pode aceitar

**Função proposta:** `validate_invitation`.

```json
{
  "arguments": {
    "invitation": {
      "email": "nova@example.test",
      "status": "pendente",
      "expires_at": "2026-11-01T12:00:00Z"
    },
    "email": "outra@example.test",
    "now": "2026-11-01T11:00:00Z"
  },
  "error": "invitation_recipient_mismatch",
  "status": 403
}
```

## UNIT-033 — Página padrão limita a 25 registros

**Função proposta:** `pagination`.

```json
{
  "arguments": {
    "page": null,
    "per_page": null
  },
  "result": {
    "page": 1,
    "per_page": 25
  }
}
```

## UNIT-034 — Pedido excessivo limita a 100 registros

**Função proposta:** `pagination`.

```json
{
  "arguments": {
    "page": 1,
    "per_page": 10000
  },
  "result": {
    "page": 1,
    "per_page": 100
  }
}
```

## UNIT-035 — Página zero é inválida

**Função proposta:** `pagination`.

```json
{
  "arguments": {
    "page": 0,
    "per_page": 25
  },
  "error": "invalid_pagination",
  "status": 422
}
```

## UNIT-036 — Texto arbitrário não vira página válida

**Função proposta:** `pagination`.

```json
{
  "arguments": {
    "page": "abc",
    "per_page": 25
  },
  "error": "invalid_pagination",
  "status": 422
}
```

## UNIT-037 — PDF dentro do limite é permitido

**Função proposta:** `validate_upload_metadata`.

```json
{
  "arguments": {
    "filename": "documento.pdf",
    "size": 1024
  },
  "result": true
}
```

## UNIT-038 — Extensão executável é rejeitada

**Função proposta:** `validate_upload_metadata`.

```json
{
  "arguments": {
    "filename": "arquivo.exe",
    "size": 1024
  },
  "error": "invalid_file",
  "status": 422
}
```

## UNIT-039 — Arquivo vazio é rejeitado

**Função proposta:** `validate_upload_metadata`.

```json
{
  "arguments": {
    "filename": "documento.pdf",
    "size": 0
  },
  "error": "invalid_file",
  "status": 422
}
```

## UNIT-040 — Tamanho acima de 16 MiB é rejeitado

**Função proposta:** `validate_upload_metadata`.

```json
{
  "arguments": {
    "filename": "documento.pdf",
    "size": 16777217
  },
  "error": "payload_too_large",
  "status": 413
}
```

## UNIT-041 — Cache separa escolas

**Função proposta:** `private_cache_key`.

```json
{
  "arguments": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  },
  "different_from": {
    "escola_id": 2,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  }
}
```

## UNIT-042 — Cache separa usuários

**Função proposta:** `private_cache_key`.

```json
{
  "arguments": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  },
  "different_from": {
    "escola_id": 1,
    "usuario_id": 8,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  }
}
```

## UNIT-043 — Cache invalida mudança de permissão

**Função proposta:** `private_cache_key`.

```json
{
  "arguments": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  },
  "different_from": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 2,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  }
}
```

## UNIT-044 — Cache separa filtros de período

**Função proposta:** `private_cache_key`.

```json
{
  "arguments": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 1
    }
  },
  "different_from": {
    "escola_id": 1,
    "usuario_id": 7,
    "permissions_version": 1,
    "resource": "painel",
    "params": {
      "periodo_id": 2
    }
  }
}
```

## UNIT-045 — Aluno recebe comunicado para alunos

**Função proposta:** `can_read_notice`.

```json
{
  "arguments": {
    "role": "aluno",
    "audience": "alunos"
  },
  "result": true
}
```

## UNIT-046 — Aluno não recebe comunicado restrito à equipe

**Função proposta:** `can_read_notice`.

```json
{
  "arguments": {
    "role": "aluno",
    "audience": "equipe"
  },
  "result": false
}
```

## UNIT-047 — Professor recebe comunicado para equipe

**Função proposta:** `can_read_notice`.

```json
{
  "arguments": {
    "role": "professor",
    "audience": "equipe"
  },
  "result": true
}
```
