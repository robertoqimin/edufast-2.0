# Painel do proprietário da plataforma

Pedido: um login exclusivo para acompanhar todas as escolas, pessoas cadastradas,
faturamento recebido, despesas e lucro por escola. Somente o proprietário cadastra
escolas. O acesso escolar continua independente.

## Hierarquia de responsabilidade e alcance

Decisão confirmada pelo proprietário em 12/11/2026: o **Supremo** é o dono da
plataforma e está acima dos perfis escolares. No painel implementado, essa conta
é identificada como proprietário (`platform_owner`). Ela não é o `super_admin`
de uma escola.

| Nível | Perfil | Alcance |
| --- | --- | --- |
| 1 | Supremo / proprietário da plataforma | Todas as escolas, diretório de pessoas e resultados financeiros |
| 2 | Superadmin da escola (`super_admin`) | Configurações, identidade e administração da própria escola |
| 3 | Admin da escola (`admin`) | Administração e aprovações autorizadas na própria escola |
| 4 | Professor (`professor`) | Turmas, matérias e ações docentes autorizadas |
| 5 | Aluno (`aluno`) | Conteúdos e registros pessoais autorizados |

A ordem representa responsabilidade e alcance; não altera automaticamente as
permissões existentes nem concede acesso a documentos restritos de outros perfis.
Somente o Supremo cadastra escolas no painel central. Nenhum perfil escolar pode
criar, promover, rebaixar ou alterar a conta Suprema: essa conta pertence ao banco
central e é provisionada exclusivamente pelo operador autorizado.

O painel atual permite consultar pessoas de todas as escolas. Alterar permissões,
bloquear usuários globalmente, redefinir senhas escolares ou entrar como outro
usuário **não está implementado**. Esses controles exigem implementação própria,
com autorização e auditoria, antes de serem oferecidos ao Supremo. Esta definição
não executa mudanças de perfis, tabelas ou dados existentes.

## O que foi implementado

- Aplicação Flask `control_plane:create_app()` separada da aplicação escolar,
  com banco central próprio, chave de sessão própria e cookie exclusivo.
- Uma única conta de proprietário criada pelo operador, sem cadastro público.
  Cinco falhas bloqueiam novas tentativas durante 15 minutos. Recuperação por
  SSH revoga sessões anteriores. A sessão expira em quatro horas.
- Cadastro de escolas com nome, identificador, domínio, situação comercial e
  mensalidade contratada. Alterações concorrentes geram conflito.
- Diretório de pessoas por escola: nome, e-mail, perfil e situação, com busca,
  paginação e data da última sincronização. Uma pessoa com contas em escolas
  diferentes aparece uma vez por conta/escola. Administradores sem perfil de
  nome cadastrado aparecem identificados pelo e-mail.
- Recebimentos e despesas manuais em reais, armazenados em centavos inteiros.
  Relatório mensal por escola e consolidado. **Lucro registrado = recebimentos
  menos despesas registradas pela data do pagamento**. Pode ser negativo.
- Mensalidade contratada não gera recebimento automático. Custos compartilhados,
  impostos e taxas só entram se forem lançados e atribuídos às escolas. Não é
  uma apuração contábil completa nem uma integração bancária.
- Cancelamento financeiro com motivo e histórico preservado, sem apagar o
  lançamento original. Repetições do mesmo envio não duplicam receita/despesa.
- Auditoria de acessos, consultas de pessoas, cadastros, integrações e movimentos.

Não há entrada automática na conta de um aluno/professor nem alteração global de
senhas escolares. Nenhuma senha, CPF, nota, documento ou atestado é sincronizado.

## Experimentar localmente

Na raiz do repositório, com Node 20+ e Docker Desktop:

```powershell
node infra/platform-demo.cjs start
```

Abrir **http://127.0.0.1:5093/login** em navegador externo:

- E-mail fictício: `dono@plataforma.local`
- Senha pública somente de demonstração: `Plataforma-teste-2026!`

São duas escolas fictícias com 26 contas cada: 20 alunos, cinco professores e um
administrador. Os valores financeiros são fictícios: recebido R$ 1.200,00,
despesas R$ 300,00 e lucro R$ 900,00. Os domínios `.example.test` não são acessos
escolares reais. O ambiente não consulta os bancos persistentes das portas 5081/5082.

```powershell
node infra/platform-demo.cjs status
node infra/platform-demo.cjs stop
```

Parar descarta o banco sintético. Repetir `start` com o container em execução
preserva a demonstração atual; para carregar código novo, parar e iniciar outra vez.
Estas credenciais nunca devem ser usadas em produção.

## Ativação permanente em nuvem

O exemplo [cloud.platform.example.json](../../infra/cloud.platform.example.json)
adiciona `platform.host` ao manifesto. Substituir domínios e digest fictícios pela
imagem aprovada no CI. Usar o mesmo `project` e incluir todas as escolas existentes.
O gerador cria `app-plataforma-central`, `db-plataforma-central`, redes privadas,
volumes e segredos próprios, além da entrada HTTPS no gateway compartilhado.
O banco central é `edufast_platform`; não tem conexão aos bancos escolares.

Preparar nova revisão conforme [CLOUD.md](../../infra/CLOUD.md), passando sempre a
revisão anterior nas instalações existentes. Não iniciar a frota inteira com
`compose up`: os serviços são ativados explicitamente por cliente.

```bash
node infra/manage.cjs prepare /srv/edufast/clientes.json /srv/edufast/r3 /srv/edufast/r2
node infra/manage.cjs run /srv/edufast/r3 database plataforma-central
```

**Revisão obrigatória antes de aplicar SQL:**
[001_central.sql](../../Codigos/control_plane/migrations/001_central.sql) é uma
proposta de seis tabelas para o banco **central vazio**. Não aplicar em bancos
escolares. Não há migrations automáticas na inicialização. O painel recusa esquema
pendente. Nenhuma migration foi aplicada em banco persistente nesta entrega.

Depois de revisado e provisionado o banco central, iniciar somente seu aplicativo:

```bash
node infra/manage.cjs run /srv/edufast/r3 start plataforma-central
docker compose -p edufast-nuvem --env-file /srv/edufast/r3/.env -f /srv/edufast/r3/compose.json exec app-plataforma-central flask --app 'control_plane:create_app()' create-owner
```

O comando pede e-mail e senha com confirmação; senha entre 12 e 256 caracteres.
O hash fica no banco, sem senha na linha de comando. Para recuperação, executar
no mesmo serviço `reset-owner-password`, também interativo. Proteger SSH e backups
do banco central; estes contêm nomes, e-mails, contratos e registros financeiros.

Criar DNS e ampliar o certificado para incluir o domínio do painel. Então executar
`node infra/manage.cjs run /srv/edufast/r3 gateway`. O acesso real será
`https://<dominio-do-painel>/login`. O gateway só deve encaminhar um salto de proxy
confiável; não publicar portas de aplicativos/bancos ou socket Docker.

## Trazer pessoas das escolas

O operador gera uma chave exclusiva por escola com `integration-key <id> --output
<arquivo-privado-novo>`, no CLI do serviço central. O banco guarda somente SHA-256
da chave. `--rotate` revoga a chave anterior daquela escola. Transferir o arquivo
ao host por canal privado, restringir acesso e nunca versionar/anexar ao CI.
Por exemplo, executar no serviço central com `--output /app/uploads/teste01.key`
e copiar com `docker compose ... cp app-plataforma-central:/app/uploads/teste01.key
/srv/edufast/keys/teste01.key`. No Linux, restringir o arquivo no host a 0600;
em Windows, restringir ACLs. Não imprimir a chave no terminal.

Depois, no host do operador:

```bash
node infra/publish-platform.cjs /srv/edufast/r3 teste01 https://painel.seudominio.com.br /srv/edufast/keys/teste01.key
```

Esse comando consulta somente o container da escola escolhida com a CLI
`platform-directory` e envia o diretório por HTTPS. A escola continua em redes
internas, sem exigir egress público, portas MySQL ou acesso ao banco central.
Redirecionamentos não recebem a chave. O operador pode agendar o comando por escola
no servidor; não foi instalado agendamento automático. A interface mostra o último
envio, não promete dados em tempo real. As escolas precisam da versão da imagem
com `platform-directory` antes de serem sincronizadas.

Cada envio substitui atomicamente apenas a lista da própria escola. Repetições,
datas antigas/futuras e conteúdo inválido são recusados. O limite é de 10 mil contas
por escola por envio; ultrapassar esse limite aborta sem truncar a lista anterior.
Relógios precisam estar sincronizados; snapshots têm validade de 30 minutos.

## Cadastrar e preparar novas instalações

Cadastre as escolas no painel. Para instalações já existentes, cadastrar os mesmos
IDs e domínios antes de exportar; isso não copia nem recria os bancos escolares.
No serviço central, `export-schools --project <projeto> --image <digest-aprovado>
--platform-host <dominio-central> --output <arquivo-privado-novo>` gera manifesto
compatível com `manage.cjs prepare`. Copiar o manifesto ao host e preparar outra
revisão passando a revisão anterior. A exportação inclui também escolas suspensas
para preservar volumes e segredos; suspensão comercial não interrompe containers.

Provisionamento, DNS, TLS e primeiro administrador escolar continuam explícitos,
conforme [PLATFORM.md](../../infra/PLATFORM.md). O painel não recebe socket Docker
nem executa migrations por uma requisição web. Para atualizar a imagem do próprio
painel, definir `platform.image` explicitamente; alterar o default preserva a imagem
central e as imagens das escolas existentes.

## Verificação

[Relatório da entrega](../testes/PAINEL_SUPREMO_2026-11-12.md). A proposta SQL pode
ser regenerada offline com `PYTHONPATH=Codigos python -m control_plane.schema`;
esse comando somente imprime SQL, não conecta nem aplica alterações.
