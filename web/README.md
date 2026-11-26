# EduFast — Aplicação web

## Como instalar, configurar e executar

A aplicação web é servida **pelo mesmo serviço da API**: as telas (HTML/Jinja, CSS e
JavaScript) ficam em [`api/app/templates/`](../api/app/templates) e
[`api/app/static/`](../api/app/static). Por isso, executar a API já disponibiliza a
aplicação web; não há um segundo servidor.

### Pré-requisitos

- Git;
- Docker 24+ com Docker Compose 2.24.4+ (Docker Desktop no Windows/macOS), **em execução**;
- Node.js 20+ (para o iniciador);
- portas 5095 e 5093 livres;
- navegador atualizado (Chrome, Edge, Firefox ou Safari).

### Dependências

Instaladas automaticamente nas imagens Docker (Python 3.12, Flask 3.1, SQLAlchemy 2.0,
psycopg 3, PostgreSQL 17). A interface usa apenas arquivos locais em
`api/app/static/` (fontes, CSS e JavaScript), sem CDN nem etapa de build. Lista
completa: [`api/README.md`](../api/README.md#dependências).

### Variáveis de ambiente

Nenhuma precisa ser definida à mão: o iniciador cria `.ci-results/demo-completa/.env`
com senhas e chaves aleatórias. A descrição de cada variável está em
[`api/README.md`](../api/README.md#variáveis-de-ambiente).

### Executar

Na **raiz do projeto** (Linux, macOS ou Windows):

```bash
node infra/demo-completa.cjs start
```

Quando a lista de contas aparecer, abra **http://localhost:5095** no navegador.
Contas de demonstração (públicas, só para este ambiente local), todas com a senha
**`Demo-EduFast-2026!`**:

| E-mail | Perfil | O que ver |
| --- | --- | --- |
| `diretoria@demo.edufast.test` | Super admin (direção) | visão geral, checklist de implantação, usuários e identidade da escola |
| `secretaria@demo.edufast.test` | Admin (secretaria) | turmas, alunos, professores e aprovação em lote |
| `ana.ribeiro@demo.edufast.test` | Professora | chamada, diário, notas e materiais |
| `bruno.lima@demo.edufast.test` | Aluno | disciplinas, materiais, cursos e boletim |

O painel da plataforma fica em **http://127.0.0.1:5093/login**
(`dono@plataforma.local` / `Plataforma-teste-2026!`).

Para parar: `node infra/demo-completa.cjs stop` (os dados são preservados).
Outros comandos e solução de problemas: [`api/README.md`](../api/README.md).

---

## Sobre a aplicação web

Interface responsiva (desktop e celular) organizada por perfil, com menu lateral,
barra superior e identidade visual personalizável pela direção. Cada tarefa tem uma
tela só, e as telas vazias indicam o próximo passo.

| Perfil | Principais telas |
| --- | --- |
| Super admin (direção) | visão geral, primeiros passos, usuários e permissões, identidade visual, calendários e políticas |
| Admin (secretaria) | alunos, professores, turmas, disciplinas, comunicados, solicitações e aprovações |
| Professor | minhas turmas, chamada, diário e avaliações, espaço da disciplina, biblioteca de cursos |
| Aluno | painel, disciplinas, leitor de materiais, cursos, boletim e privacidade |

O protocolo visual e as capturas de referência estão em
[`docs/PROTOCOLO_DESIGN.md`](../docs/PROTOCOLO_DESIGN.md) e
[`docs/design/`](../docs/design/README.md).
