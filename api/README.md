# EduFast — API e serviços de backend

## Como instalar, configurar e executar

### Pré-requisitos

| Ferramenta | Versão | Observação |
| --- | --- | --- |
| Git | qualquer recente | para clonar o projeto |
| Docker Engine (Linux) ou Docker Desktop (Windows/macOS) | 24 ou superior | precisa estar **em execução** |
| Docker Compose | 2.24.4 ou superior | já incluído no Docker Desktop (`docker compose version`) |
| Node.js | 20 ou superior | executa o iniciador da demonstração (`node --version`) |
| Portas livres | 5095 e 5093 | escola e painel da plataforma |

### Dependências

Não é preciso instalar nada além dos pré-requisitos: as dependências são baixadas e
instaladas automaticamente dentro das imagens Docker na primeira execução.

| Dependência | Versão | Arquivo |
| --- | --- | --- |
| Python (imagem `python:3.12-slim`) | 3.12 | `api/Dockerfile` |
| Flask | 3.1.3 | `api/requirements.txt` |
| SQLAlchemy | 2.0.44 | `api/requirements.txt` |
| psycopg (driver PostgreSQL) | 3.2.10 | `api/requirements.txt` |
| python-dotenv | 1.2.4 | `api/requirements.txt` |
| cryptography | ≥ 48.0.1, < 51 | `api/requirements.txt` |
| PostgreSQL (imagem `postgres:17-alpine`) | 17 | `api/docker-compose.yml` |

### Variáveis de ambiente

O iniciador **cria o arquivo de configuração sozinho**, com senhas e chaves aleatórias,
em `.ci-results/demo-completa/.env` (fora do Git). Não é preciso copiar nem editar nada
para executar. A tabela é referência para quem quiser configurar manualmente a partir
de `api/.env.example`.

| Variável | Obrigatória | Uso |
| --- | --- | --- |
| `SECRET_KEY` | sim | assina a sessão e os tokens JWT; valor longo e aleatório |
| `DB_PASSWORD` | sim | senha do usuário da aplicação no PostgreSQL |
| `POSTGRES_ADMIN_PASSWORD` | sim | senha do superusuário `postgres` (só administração) |
| `DATA_ENCRYPTION_KEY` | sim | chave Fernet que cifra arquivos, vídeos e textos sensíveis; guarde junto do backup |
| `DB_NAME` | não | nome do banco (padrão `app_web`) |
| `DB_USER` | não | usuário da aplicação no banco (padrão `app_user`) |
| `DB_PORT` | não | porta do PostgreSQL na rede do Compose (padrão `5432`) |
| `UPLOAD_FOLDER` | não | pasta de arquivos enviados (padrão `uploads`) |
| `JWT_EXPIRATION_HOURS` | não | validade do token em horas (padrão `8`) |

### Executar

Todos os comandos são executados **na raiz do projeto** (a pasta que contém `api/`,
`web/` e `docs/`). Funciona igual em Linux, macOS e Windows:

```bash
node infra/demo-completa.cjs start
```

A primeira execução leva alguns minutos (download das imagens). O iniciador:

1. gera a configuração com senhas e chaves aleatórias;
2. constrói a imagem da aplicação e sobe o PostgreSQL;
3. cria a escola de demonstração **Colégio Horizonte**, com dados fictícios (só na primeira vez);
4. sobe a aplicação e aguarda `GET /healthz` responder;
5. sobe o painel da plataforma e mostra na tela os endereços e as contas.

| Endereço | O que é |
| --- | --- |
| **http://localhost:5095** | aplicação da escola (web + API) |
| **http://127.0.0.1:5093/login** | painel da plataforma (dono do produto) |

Contas de demonstração (públicas, válidas só neste ambiente local):

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Super admin (direção) | `diretoria@demo.edufast.test` | `Demo-EduFast-2026!` |
| Admin (secretaria) | `secretaria@demo.edufast.test` | `Demo-EduFast-2026!` |
| Professora | `ana.ribeiro@demo.edufast.test` | `Demo-EduFast-2026!` |
| Aluno | `bruno.lima@demo.edufast.test` | `Demo-EduFast-2026!` |
| Dono da plataforma (painel 5093) | `dono@plataforma.local` | `Plataforma-teste-2026!` |

Há outros professores e alunos; o iniciador lista todos ao terminar.

**Outros comandos**

| Comando | Efeito |
| --- | --- |
| `node infra/demo-completa.cjs status` | mostra os contêineres |
| `node infra/demo-completa.cjs stop` | para tudo, preservando os dados |
| `node infra/demo-completa.cjs reset` | apaga a escola de demonstração e recria do zero |
| `node infra/demo-completa.cjs start --sem-supremo` | sobe só a escola, sem o painel da plataforma |

Para ver os logs da aplicação:

```bash
docker compose -p edufast-demo-completa logs -f app
```

**Alternativa no Windows (escola de teste vazia, porta 5050):** `.\iniciar-educafast.ps1`
no PowerShell cria um ambiente com as contas `superadmin@teste.local`,
`admin@teste.local`, `professor@teste.local` e `aluno@teste.local` (senha
`Teste-local-2026!`). Parar: `.\iniciar-educafast.ps1 -Acao Parar`.

### Testes

Com Python 3.12 instalado, na raiz do projeto:

```bash
python -m venv .venv
.venv/bin/pip install -r api/requirements.txt
PYTHONPATH=api .venv/bin/python -m unittest discover -s .github/cicd/tests/unit -v
.venv/bin/python api/tests/verificar_protocolo_design.py
```

No Windows, use `.venv\Scripts\python` no lugar de `.venv/bin/python` e defina
`$env:PYTHONPATH='api'` antes do `unittest`.

### Problemas comuns

| Sintoma | Solução |
| --- | --- |
| `Docker indisponível` | abra o Docker Desktop ou inicie o serviço (`sudo systemctl start docker`) |
| `port is already allocated` | libere as portas 5095/5093 ou pare o outro serviço |
| `permission denied` ao chamar o Docker no Linux | adicione seu usuário ao grupo `docker` ou execute com `sudo` |
| escola não responde em `/healthz` | veja os logs com o comando acima |
| dados inconsistentes depois de testes | `node infra/demo-completa.cjs reset` |

Instalação própria com Compose direto, banco existente e migrations:
[guia de execução](../docs/operacao/EXECUCAO.md) e
[procedimento de migração](migrations/README.md).

---

## Sobre a API

A API é um monólito **Flask** em camadas que atende tanto as telas web
(ver [`web/`](../web/README.md)) quanto as chamadas JSON. A persistência usa
SQLAlchemy sobre PostgreSQL 17.

```text
api/
├── app.py                # ponto de entrada (create_app)
├── config.py             # configuração por variáveis de ambiente
├── app/
│   ├── routes/           # rotas HTTP e verificação de perfil (guards.py)
│   ├── controllers/      # regras de cada operação
│   ├── services/         # serviços de aplicação (identidade, aprovações, cursos…)
│   ├── models/           # entidades SQLAlchemy
│   ├── templates/        # telas da aplicação web (HTML/Jinja)
│   └── static/           # CSS, JavaScript e fontes locais
├── control_plane/        # painel da plataforma (dono do produto), banco separado
├── migrations/           # scripts SQL, aplicados só após revisão
├── demo_completa.py      # dados fictícios da escola de demonstração
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Autenticação

`POST /login` recebe JSON `{"email": "...", "senha": "...", "csrf_token": "..."}` e
devolve os dados do usuário e um token JWT (HS256), além de abrir a sessão do
navegador. `GET /auth/session` confirma a sessão; `GET /logout` encerra e revoga os
tokens anteriores. Cada rota verifica o perfil (super admin, admin, professor ou
aluno) e a unidade antes de executar.

### Principais grupos de rotas

| Prefixo | Perfil | Conteúdo |
| --- | --- | --- |
| `/login`, `/logout`, `/auth/session`, `/unidade` | todos | acesso, sessão e troca de unidade |
| `/super/usuarios`, `/super/escola`, `/super/layout` | super admin | usuários, permissões, identidade visual, calendários e políticas |
| `/admin/...`, `/cadastro/...` | admin | alunos, professores, turmas, disciplinas, comunicados e privacidade |
| `/turmas`, `/disciplinas`, `/academico/...` | admin / professor | turmas, períodos, avaliações e boletim |
| `/professor/...` | professor | painel, atividades, notas e documentos |
| `/aluno/...`, `/boletim` | aluno | painel, disciplinas, notas e envio de documentos |
| `/frequencia/...` | professor / admin | chamadas, atestados, aprovação e relatório |
| `/solicitacoes/...` | admin / professor | propostas de alteração e aprovação em lote |
| `/estudos/...` | professor / aluno | materiais por disciplina (PDF, imagem, vídeo) e leitor |
| `/videos/envios/...` | professor | envio de vídeos em partes, cifrados |
| `/aprendizagem/...`, `/api/cursos/...`, `/api/aprender/...` | admin / professor / aluno | cursos modulares, publicação e progresso (JSON) |
| `/arquivos/...` | conforme permissão | envio e download de arquivos |
| `/minha-privacidade`, `/admin/privacidade` | todos / admin | pedidos sobre dados pessoais |
| `/healthz` | público | verificação de funcionamento |

A coleção Postman com os fluxos por perfil está em
[`docs/testes/postman/`](../docs/testes/postman/README.md).
