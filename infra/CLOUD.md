# Containers por cliente na nuvem

Uma VM Linux com Docker Compose 2.24.4+, Node 20+ e gateway Nginx HTTPS atende
vários clientes. Cada cliente possui aplicação Flask/Gunicorn (frontend Jinja/React
e backend), PostgreSQL, redes privadas, volumes e segredos próprios. Contas e permissões
continuam locais. Clientes acessam pelo navegador, sem acesso ao Docker/SSH.
Host e gateway são compartilhados: sua falha pode afetar todos os clientes.

## Preparar a instalação

Reservar IP estável, configurar DNS, firewall (443 pública, administração restrita),
armazenamento persistente, backup fora da VM e monitoramento de recursos/TLS.
Não publicar PostgreSQL ou o socket/API Docker. Não instalar outro proxy na mesma 443.

Copiar `infra/cloud.example.json` para um manifesto **privado**. Informar domínios
reais e digest da imagem aprovada pelo CI. O formato/repositório são validados,
mas a aprovação do CI deve ser conferida pelo procedimento de
`.github/cicd/README.md`. O campo `project` determina nomes de volumes e redes:
escolher um nome único por instalação e nunca trocá-lo numa atualização.

Exemplo no servidor (diretório privado `/srv/edufast` previamente criado):

```bash
node infra/manage.cjs prepare /srv/edufast/clientes.json /srv/edufast/r1
node infra/manage.cjs plan /srv/edufast/r1 database cliente-a
node infra/manage.cjs run /srv/edufast/r1 validate
```

`prepare` apenas escreve uma configuração nova. A pasta não pode existir.
São gerados `inventory.json`, `compose.json`, `nginx.conf`, `.env` e `tls/`.
Não versionar esses arquivos operacionais. Usar pasta privada fora do checkout ou
`.ci-results/` durante testes. Os segredos não são impressos. No Linux, pastas
usam 0700 e arquivos 0600; no Windows, restringir também as ACLs.

## Banco revisado, administrador e acesso

```bash
node infra/manage.cjs run /srv/edufast/r1 database cliente-a
```

Isso inicia somente o PostgreSQL de A. **Não cria tabelas da aplicação.** Revisar o
provisionamento de banco novo ou as migrations aplicáveis em
`Codigos/migrations/README.md` antes de executar SQL. O aplicativo em produção
recusa esquema pendente. Não há comando de migration neste gerenciador: depois da
revisão, usar `aplicar_migracoes.py` no serviço do cliente (plano por padrão; aplica
somente com `--aplicar --confirmar <banco>`), conforme o guia de migrations.

Após esquema revisado e preparado, iniciar A:

```bash
node infra/manage.cjs run /srv/edufast/r1 start cliente-a
docker compose -p edufast-nuvem --env-file /srv/edufast/r1/.env -f /srv/edufast/r1/compose.json exec app-cliente-a flask --app 'app:create_app()' create-admin
```

O exemplo assume `project=edufast-nuvem`. Criar administrador com credenciais
próprias; o comando é interativo. Repetir banco, revisão e administrador para B.
Nenhuma conta pública de demonstração é criada pelo gerenciador.

Instalar `tls/fullchain.pem` e `tls/privkey.pem`, com certificado válido para
**todos** os domínios. Só então:

```bash
node infra/manage.cjs run /srv/edufast/r1 gateway
```

O gateway passa por `nginx -t` antes da recriação. O teste não comprova confiança,
validade temporal ou cobertura de nomes do certificado: verificar externamente.
DNS dos clientes aponta ao IP do gateway, que encaminha pelo domínio. O gateway
não inicia apps/bancos implicitamente. Renovação de certificado é externa; depois
da substituição dos arquivos, repetir `gateway`. Pode haver breve interrupção
compartilhada nessa recriação; não há promessa de atualização sem indisponibilidade.

## Adicionar cliente ou atualizar release

Alterar o manifesto privado e preparar outra pasta, sempre passando a configuração
mais recente como terceiro argumento:

```bash
node infra/manage.cjs prepare /srv/edufast/clientes.json /srv/edufast/r2 /srv/edufast/r1
node infra/manage.cjs run /srv/edufast/r2 validate
```

Segredos, volumes, projeto e caminho dos certificados existentes são preservados.
Remoção de cliente, mudança de ID/domínio ou perda de segredo abortam a geração.
Novos clientes recebem segredos novos. Não omitir o argumento anterior ao atualizar:
isso produziria outros segredos. Não usar uma revisão antiga para planejar mudanças
novas, nem preparar alterações concorrentes; o operador controla a revisão vigente.

Para atualizar A, definir `image` **no objeto de A em `schools`**, por digest
aprovado. A imagem default no topo vale para novos clientes; os existentes mantêm
a imagem anterior se não houver override explícito. Conservar o inventário gerado
como referência das imagens efetivas. Fazer backup e revisar compatibilidade de
esquema antes da atualização:

```bash
node infra/manage.cjs backup /srv/edufast/r1 cliente-a /srv/edufast/backups/a-2026-11-11
node infra/manage.cjs plan /srv/edufast/r2 update cliente-a
node infra/manage.cjs run /srv/edufast/r2 update cliente-a
node infra/manage.cjs run /srv/edufast/r2 status cliente-a
```

`update` faz pull e recria apenas a aplicação de A, sem iniciar dependências ou
atualizar banco/B. Se falhar, interrompe sem reverter esquema ou apagar volumes.
Para retornar imagem, preparar outra revisão com digest anterior, somente se
compatível com o esquema. Não reaplicar configuração antiga da frota inteira.

Cliente novo: provisionar seu banco revisado, iniciar app e criar administrador;
ampliar o certificado antes de executar `gateway` na nova revisão. A atualização
do gateway é necessária para incluir a nova rede/domínio.

Outras operações: `stop cliente-a` para somente a aplicação; `logs cliente-a` para
últimas 100 linhas; `status cliente-a` para app/banco. Banco continua ativo em
`stop`. `plan` imprime executável e argumentos em JSON, sem executar nem imprimir
segredos. `run` valida Compose silenciosamente antes da ação.

## Backup e restauração

`backup` exige pasta de saída nova. Verifica se A está rodando, para sua aplicação,
gera dump PostgreSQL (`pg_dump --clean --if-exists`) e arquivo de uploads, guarda **somente** os quatro segredos de A
e os metadados de release/domínio/projeto. Retoma o container existente caso o tenha
parado, inclusive em falha de captura. Não atualiza imagem ao retomar. Suspender
escritores externos/tarefas e não executar atualizações simultaneamente; o script
só controla a aplicação desse Compose. Uma aplicação já parada permanece parada.

O marcador `COMPLETE` só aparece após capturas e retomada sem falha. Sua existência
não comprova restauração. O pacote contém dados e segredos **sem criptografia**:
criptografar, transferir para destino privado fora da VM e aplicar retenção acordada.
Não enviar para Git nem anexar aos artefatos públicos do CI. Confirmar espaço em
disco antes da captura. Em Linux os arquivos ficam privados; em Windows revisar ACLs.

Restauração é deliberadamente explícita: após revisão, criar destino isolado com
rede/volumes novos, restaurar o dump e uploads, configurar a chave de criptografia
preservada e a release compatível. Conferir contas, aprovações, vínculos, arquivos e
dados cifrados; medir RPO/RTO. Só promover após impedir gravações no destino anterior.
Não restaurar sobre B ou sobre cliente ativo. O gerenciador não executa restore,
DROP, migrations, exclusão de cliente, `down -v` ou failover automático.

## Verificação

```bash
node --test infra/test_environments.cjs infra/test_manage.cjs
bash infra/verify.sh
```

O CI também executa `node infra/smoke_cloud.cjs` após criar sua imagem descartável.
Esse piloto usa dois PostgreSQL novos, certificado de teste validado, HTTPS, login,
rejeição cruzada de JWT/cookie, conexão PostgreSQL bloqueada entre clientes, backup e
persistência de upload após recriar A sem recriar B. O override de imagem local e
a exclusão de volumes existem apenas no projeto temporário com UUID desse teste.
Não são comandos de produção. Não substituem restauração ensaiada, teste de carga,
inspeção visual ou validação do TLS real. Nenhuma interface foi alterada nesta entrega.

Referências: [Compose em produção](https://docs.docker.com/compose/how-tos/production/),
[execução sem dependências](https://docs.docker.com/reference/cli/docker/compose/run/)
e [retomada de containers existentes](https://docs.docker.com/reference/cli/docker/compose/start/).
