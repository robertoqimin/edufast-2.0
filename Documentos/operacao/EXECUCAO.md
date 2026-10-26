# Execução e manutenção local

[Início](../../README.md)

## Primeira instalação

Instale Git, Docker e Docker Compose. No Windows, inicie o Docker Desktop. Execute na raiz do projeto:

```powershell
Copy-Item 'Códigos/.env.example' 'Códigos/.env'
```

No Linux/macOS, use `cp Códigos/.env.example Códigos/.env`. Edite o arquivo antes de iniciar.

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Assinatura da sessão e dos tokens; use valor longo e aleatório |
| `DB_PASSWORD` | Senha do usuário da aplicação no MySQL |
| `MYSQL_ROOT_PASSWORD` | Senha administrativa do MySQL |
| `DB_NAME` / `DB_USER` | Banco e usuário; padrões no Compose: `app_web` / `app_user` |
| `DB_PORT` | Porta do MySQL dentro da conexão; mantenha 3306 no Compose padrão |
| `UPLOAD_FOLDER` | Diretório de uploads; o volume padrão persiste `/app/uploads` |
| `JWT_EXPIRATION_HOURS` | Padrão da configuração Python: 8; o Compose atual não repassa essa variável |
| `DB_URL` | Alternativa lida por `config.py` fora do Compose; não repassada pelo Compose atual |

O Compose repassa somente as variáveis listadas em `environment`. Alterar `DB_HOST` no `.env` não substitui `db`, definido no Compose. Se alterar a pasta de uploads, ajuste também o volume correspondente.

```powershell
.\iniciar-educafast.ps1 -SemNavegador
.\iniciar-educafast.ps1 -Acao Status
.\iniciar-educafast.ps1 -Acao Parar
```

O inicializador usa a pasta `Códigos` deste repositório. `Parar` preserva os volumes. A abertura do navegador não comprova que o Flask terminou de iniciar.

Alternativa direta, executada dentro de `Códigos/`:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

Acesse `http://localhost:5000` quando o app estiver pronto.

## Primeiro administrador

O seed atual executa `session.query(UsuarioModel).delete()` antes de inserir o administrador. **Não o execute em uma base com usuários que deseja preservar.** Somente em banco novo e descartável:

```bash
docker compose exec app python -m app.seed
```

Credenciais do seed de demonstração: `admin@admin.com` / `123`. Para criar um administrador sem apagar usuários, use `docker compose exec app flask --app 'app:create_app()' create-admin`. O comando pede email e senha e recusa sobrescrever contas existentes.

## Comandos úteis

Todos os comandos abaixo são executados em `Códigos/`:

```bash
docker compose ps
docker compose logs --tail 100 app
docker compose logs --tail 100 db
docker compose restart app
docker compose down
```

## Persistência e problemas comuns

- `mysql_data` mantém o banco e `uploads_data` mantém arquivos entre reinicializações. Faça backup dos dois antes de mudanças de esquema ou restauração.
- Variáveis de criação do usuário e banco MySQL são aplicadas no primeiro uso do volume. Trocar a senha no `.env` não modifica automaticamente um usuário já criado; atualize a credencial no banco com o procedimento administrativo adequado.
- Não remova volumes para corrigir conexão de um ambiente com dados importantes. `docker compose down -v` apaga os volumes e seus dados.
- Se as portas 5000 ou 3306 estiverem ocupadas, ajuste o lado esquerdo do mapeamento `ports` no Compose e acesse a nova porta da aplicação. Não altere a porta interna do MySQL apenas para mudar a porta publicada.
- Conflitos com `flask_app` ou `mysql_db` indicam outro container usando os mesmos nomes fixos. Revise a configuração antes de executar várias cópias simultâneas.
- Banco saudável não garante aplicação pronta: consulte os logs de `app`.

## Estado de validação

Os logs em `Documentos/testes/logs-historicos/` são históricos. O [CI/CD atual](../../.github/cicd/README.md) executa testes novos em ambiente descartável; os resultados ficam em `.ci-results` localmente e nos artefatos do Actions. Não execute utilitários de legado como parte da instalação.

O Compose de `Códigos` é de desenvolvimento. A [configuração de produção](../../.github/cicd/README.md) usa Gunicorn e Caddy com HTTPS e exige provisionamento, segredos, backups externos e homologação no servidor real.
