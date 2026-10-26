# EduFast 2.0 — CI/CD e preparação de produção

Repositório privado: https://github.com/Samucau1/edufast-2.0. A aplicação continua sendo EducaFast. Esta entrega prepara automação e imagem; **não existe servidor de produção configurado nem implantação real executada**.

## CI disponível agora

Em pushes na `main`, pull requests e execução manual, `.github/workflows/ci.yml`:

1. Instala os executores em Python 3.12 e constrói o ambiente Docker de testes.
2. Executa o protocolo de design, regressão e Postman em SQLite descartável e depois em MySQL 8.4 descartável, em sequência.
3. Compara contagens, identificação dos cenários e verificações JUnit com o baseline anterior à migração. Falha diante de regressões, perdas de cobertura ou aumento de testes ignorados.
4. Constrói a imagem de produção e verifica HTTPS, certificado, HSTS e transporte TLS do MySQL usando certificados temporários e recursos isolados.
5. Preserva evidências em artefatos, inclusive em falhas. Na `main`, somente após aprovação do CI, publica a imagem privada em `ghcr.io/samucau1/edufast-2.0`, com tag `sha-<commit>` e referência por digest.

Actions foram fixadas em commits oficiais, em vez de referências mutáveis. Os jobs usam permissões explícitas; pull requests não publicam imagens. O CI não usa `.env`, credenciais ou dados do ambiente manual/produção. Os novos resultados ficam em `resultados/ci/` no runner e não sobrescrevem as evidências históricas do repositório.

O workflow não exige secrets fornecidos pelo usuário para executar testes ou publicar no GHCR: usa o `GITHUB_TOKEN` emitido para o job. O registro/imagem precisa continuar privado; confira a visibilidade do pacote no GitHub após a primeira publicação.

## CD preparado para quando houver servidor

`.github/workflows/deploy.yml` só é acionado manualmente na `main`. Sem host, credenciais e confirmação de provisionamento, ele termina antes de contatar servidor algum. Não há implantação automática em push.

Quando a hospedagem for definida, provisione um servidor Linux com Docker Compose, acesso SSH e domínio HTTPS válido. O modelo atual de implantação é VPS/servidor com Docker; uma plataforma gerenciada pode exigir um adaptador diferente.

Crie o ambiente `production` no GitHub, configure proteção/aprovação quando disponível no plano e cadastre:

| Variável | Finalidade |
| --- | --- |
| `DEPLOY_HOST` | Nome/IP do servidor SSH |
| `DEPLOY_USER` | Usuário de implantação |
| `DEPLOY_PORT` | Porta SSH; padrão 22 |
| `DEPLOY_DIR` | Caminho absoluto, por exemplo `/srv/educafast` |
| `PUBLIC_URL` | URL-base HTTPS, por exemplo `https://escola.exemplo.com` |

| Secret | Finalidade |
| --- | --- |
| `DEPLOY_SSH_KEY` | Chave privada do usuário de implantação |
| `DEPLOY_KNOWN_HOSTS` | Identidade SSH previamente conferida por canal confiável |

O servidor deve estar autenticado no GHCR com credencial de leitura do pacote privado. As credenciais de produção ficam **no servidor**, em `.env.production`, nunca no Git. O CD não encaminha o token de Actions como credencial persistente do servidor.

## Primeira instalação assistida

1. Colocar o código/compose da versão revisada em `DEPLOY_DIR`, preservando a pasta `Códigos`.
2. Criar `.env.production` na raiz com `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, `LGPD_CONTATO`, `TRUSTED_HOSTS`, `DB_PASSWORD`, `MYSQL_ROOT_PASSWORD` e as demais opções do compose. Gerar chaves próprias, não usar valores sintéticos. Preservar a chave de criptografia em backup seguro separado.
3. Instalar em `Códigos/certs` os certificados/chaves esperados pelo compose: CA e certificado do MySQL com identidade `db`; certificado HTTPS completo e chave para o domínio público. Conferir permissões e renovação.
4. Exportar `EDUCAFAST_IMAGE=ghcr.io/samucau1/edufast-2.0@sha256:<digest-validado>` e validar a configuração sem imprimir seus segredos:

   ```bash
   docker compose -p educafast-production --env-file .env.production -f Códigos/docker-compose.production.yml config --quiet
   docker compose -p educafast-production --env-file .env.production -f Códigos/docker-compose.production.yml pull app
   docker compose -p educafast-production --env-file .env.production -f Códigos/docker-compose.production.yml up -d --no-build
   ```

5. Conferir migração em cópia antes de dados reais, acesso HTTPS, conexão TLS do banco, criação do superadmin e plano de restauração. Fazer a primeira instalação de forma assistida, não pelo workflow de atualizações.

## Atualizações futuras pelo CD

Selecione o digest produzido pelo CI e confirme o plano de backup. O script remoto:

- Confere diretório, repositório da imagem, configuração, instalação existente e trava de concorrência.
- Baixa a imagem por digest, interrompe a aplicação e gera cópias de banco e uploads no servidor, com permissões restritas. As chaves e configurações precisam de backup seguro próprio.
- Sobe a imagem sem build local e confere a URL HTTPS. Não executa `down -v` nem recria volumes.

Há indisponibilidade durante o backup/atualização. Em falha antes de iniciar a versão nova, tenta retomar a imagem anterior. Após iniciar migrações, não faz downgrade/restauração automaticamente: DDL do MySQL pode ter sido aplicado parcialmente. Nesse caso, analisar logs e restaurar versão/banco/uploads compatíveis com procedimento revisado. Backups locais precisam de política de retenção e cópia externa; o modelo não substitui esse plano.

O CD foi preparado e validado sintaticamente, mas **não foi homologado em um servidor remoto**, pois ele ainda não existe. Configurar domínio, certificados, secrets, armazenamento, proteção de branch e recuperação é a etapa seguinte antes de produção real.

## Rodar o mesmo CI localmente

Em Linux com Docker, Python e dependências dos executores:

```bash
python3 -m pip install -r Códigos/requirements.txt
bash scripts/ci.sh
```

No Windows, os executores individuais continuam funcionando pelo Python e Docker Compose, como no guia de testes. Não rodar as suítes no projeto Docker `educafast-manual`: ele é reservado aos testes interativos do usuário.

Referências oficiais usadas na configuração: [publicação de imagens no GitHub](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images), [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) e [artefatos](https://github.com/actions/upload-artifact).
