# Execução e manutenção local

[Início](../../README.md)

## Primeira instalação

### Teste manual no Windows

Com o Docker Desktop aberto, execute na raiz:

```powershell
.\iniciar-educafast.ps1
```

Não é necessário copiar ou editar `Codigos/.env` para esse modo. O iniciador gera
segredos aleatórios em `.ci-results/manual-postgres/.env` e usa exclusivamente o
projeto Docker `edufast-manual-postgres`, em **http://localhost:5050**, com banco
e uploads próprios. O ambiente anterior não é alterado. Na primeira configuração,
cria o esquema somente se o banco estiver vazio. Em banco existente, confere o
esquema e recusa alterações automáticas. Não executa migrations.

| Login local | Perfil |
| --- | --- |
| `superadmin@teste.local` | Super admin |
| `admin@teste.local` | Admin |
| `professor@teste.local` | Professor |
| `aluno@teste.local` | Aluno |

Senha inicial de todos: **`Teste-local-2026!`**. São credenciais públicas, somente
para teste local em loopback. Professor e aluno têm vínculo com a turma
`TESTE-2026` e a disciplina `MAT-TESTE`. O professor começa sem poder de revisor;
o administrador pode conceder a permissão no painel de solicitações.

O iniciador não redefine senhas, estado ou permissões de contas existentes.
Não apague o arquivo de configuração para tentar redefinir senhas do PostgreSQL:
as senhas precisam corresponder às do volume já criado.

```powershell
.\iniciar-educafast.ps1 -SemNavegador
.\iniciar-educafast.ps1 -Porta 5051
.\iniciar-educafast.ps1 -Acao Status
.\iniciar-educafast.ps1 -Acao Logs
.\iniciar-educafast.ps1 -Acao Parar
```

Se a configuração foi criada mas a preparação inicial foi interrompida com o banco
ainda vazio, retome com `-PrepararBancoNovo`. Esse parâmetro recusa banco com tabelas.
`Parar` preserva volumes. O navegador só abre depois de `/healthz` responder.
Se quiser outra conta administrativa, use `-Acao CriarAdmin` (ou adicione
`-SuperAdmin`); o comando pede credenciais próprias e não substitui usuários.

Desde 22/11/2026 o iniciador usa PostgreSQL. Os ambientes manuais anteriores em
MySQL (`.ci-results/manual` e `.ci-results/manual-restaurado`, projetos
`edufast-manual` e `edufast-manual-restaurado`) foram preservados com seus volumes,
sem alteração; `-Ambiente Atual` apenas informa isso. Para remover esses volumes
antigos, faça manualmente e só depois de confirmar que não precisa dos dados. A chave
`DATA_ENCRYPTION_KEY`, gerada para o ambiente manual, protege os textos de
solicitações de privacidade. Guarde-a junto do backup; não a substitua se houver
dados cifrados que precisam ser lidos.

### Instalação própria com Compose direto

Instale Git, Docker e Docker Compose. No Windows, inicie o Docker Desktop. Execute na raiz do projeto:

```powershell
Copy-Item 'Codigos/.env.example' 'Codigos/.env'
```

No Linux/macOS, use `cp Codigos/.env.example Codigos/.env`. Edite o arquivo antes de iniciar.

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Assinatura da sessão e dos tokens; use valor longo e aleatório |
| `DB_PASSWORD` | Senha do usuário da aplicação no PostgreSQL (papel sem superusuário, dono do banco) |
| `POSTGRES_ADMIN_PASSWORD` | Senha do superusuário `postgres`, somente administração |
| `DB_NAME` / `DB_USER` | Banco e usuário; padrões no Compose: `app_web` / `app_user` |
| `DB_PORT` | Porta do PostgreSQL dentro da conexão; mantenha 5432 no Compose padrão |
| `UPLOAD_FOLDER` | Diretório de uploads; o volume padrão persiste `/app/uploads` |
| `JWT_EXPIRATION_HOURS` | Padrão da configuração Python: 8; o Compose atual não repassa essa variável |
| `DB_URL` | Alternativa lida por `config.py` fora do Compose; não repassada pelo Compose atual |

O Compose repassa somente as variáveis listadas em `environment`. Alterar `DB_HOST` no `.env` não substitui `db`, definido no Compose. Se alterar a pasta de uploads, ajuste também o volume correspondente.

Execute dentro de `Codigos/`:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

Acesse `http://localhost:5000` quando o app estiver pronto.

## Primeiro administrador

Para uma instalação própria, revise primeiro o [procedimento do banco](../../Codigos/migrations/README.md).
Depois, provisione o administrador pelo comando não destrutivo:

```bash
docker compose exec app flask --app 'app:create_app()' create-admin
```

O comando pede email e senha e recusa sobrescrever contas existentes. Adicione
`--super-admin` para uma conta nova desse perfil. O seed destrutivo antigo foi
desativado. As contas fixas de teste são exclusivas do iniciador manual.

## Comandos úteis

Todos os comandos abaixo são executados em `Codigos/`:

```bash
docker compose ps
docker compose logs --tail 100 app
docker compose logs --tail 100 db
docker compose restart app
docker compose down
```

## Persistência e problemas comuns

- `postgres_data` mantém o banco e `uploads_data` mantém arquivos entre reinicializações. Faça backup dos dois antes de mudanças de esquema ou restauração.
- Variáveis de criação do usuário e banco PostgreSQL são aplicadas no primeiro uso do volume. Trocar a senha no `.env` não modifica automaticamente um usuário já criado; atualize a credencial no banco com o procedimento administrativo adequado.
- Não remova volumes para corrigir conexão de um ambiente com dados importantes. `docker compose down -v` apaga os volumes e seus dados.
- Se as portas 5000 ou 5432 estiverem ocupadas, ajuste o lado esquerdo do mapeamento `ports` no Compose e acesse a nova porta da aplicação. Não altere a porta interna do PostgreSQL apenas para mudar a porta publicada.
- Conflitos com `flask_app` ou `postgres_db` indicam outro container usando os mesmos nomes fixos. Revise a configuração antes de executar várias cópias simultâneas.
- Banco saudável não garante aplicação pronta: consulte os logs de `app`.

## Estado de validação

Os logs em `Documentos/testes/logs-historicos/` são históricos. O [CI/CD atual](../../.github/cicd/README.md) executa testes novos em ambiente descartável; os resultados ficam em `.ci-results` localmente e nos artefatos do Actions. Não execute utilitários de legado como parte da instalação.

O Compose de `Codigos` é de desenvolvimento. A [configuração de produção](../../.github/cicd/README.md) usa Gunicorn e Caddy com HTTPS e exige provisionamento, segredos, backups externos e homologação no servidor real.
