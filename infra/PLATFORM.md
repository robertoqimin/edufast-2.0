# Cadastro de escolas pelo administrador da plataforma

Atualização de 12/11/2026: o [painel do proprietário](../Documentos/planejamento/PAINEL_SUPREMO_2026-11-12.md)
oferece login web, cadastro de escolas, diretório de pessoas e financeiro. O método
por SSH abaixo continua como ferramenta operacional para preparar e ativar instalações.

Decisão de 12/11/2026: somente o proprietário da plataforma cadastra escolas.
O método implementado é um comando no servidor, autenticado pelo seu acesso SSH.
Este comando não oferece login web. Administradores e superadministradores das
escolas continuam com as permissões locais existentes.

## Preparar seu acesso

Usar uma conta pessoal no servidor com chave SSH, acesso administrativo restrito
por firewall e permissões para operar Docker. Essa conta tem controle do host;
não compartilhar com escolas. O cadastro não autentica operadores por senha
própria: sua proteção depende de SSH e permissões de arquivos do servidor.
Não expor Docker, socket ou este diretório por HTTP.

Requisitos: Node 20+, Docker Compose e imagem aprovada conforme [CLOUD.md](CLOUD.md).
Executar a partir do checkout do projeto. Criar o diretório pai `/srv/edufast`
com acesso exclusivo do operador. Usar armazenamento fora do repositório.

```bash
# Substituir DIGEST_APROVADO pelo SHA-256 de 64 caracteres da imagem aprovada.
node infra/platform.cjs init /srv/edufast/plataforma edufast-nuvem ghcr.io/samucau1/edufast-2.0@sha256:DIGEST_APROVADO
node infra/platform.cjs add /srv/edufast/plataforma teste01 teste01.seudominio.com.br
node infra/platform.cjs add /srv/edufast/plataforma teste02 teste02.seudominio.com.br
node infra/platform.cjs list /srv/edufast/plataforma
```

`init` exige pasta nova. `add` prepara uma revisão com aplicação, PostgreSQL, uploads,
redes, cookie e segredos separados por escola. O frontend é servido pela aplicação
de cada escola. O cadastro preserva as escolas anteriores e recusa IDs/domínios
duplicados. Não inicia containers, não cria tabelas ou contas e não configura DNS.
O endereço retornado só funciona depois da ativação abaixo.

Se já existe uma instalação de nuvem criada com `manage.cjs`, adotar a **última**
revisão, informando o mesmo projeto, em vez de cadastrar suas escolas novamente:

```bash
node infra/platform.cjs init /srv/edufast/plataforma edufast-nuvem ghcr.io/samucau1/edufast-2.0@sha256:DIGEST_APROVADO /srv/edufast/r2
```

Esse modo é para revisões de nuvem compatíveis. Não adotar os ambientes locais de
demonstração, que usam outros bancos e redes. Manter a revisão adotada e seus
certificados disponíveis. Não usar dois cadastros ativos sobre o mesmo projeto.

## Ativar uma escola

```bash
node infra/platform.cjs plan /srv/edufast/plataforma database teste01
node infra/platform.cjs run /srv/edufast/plataforma database teste01
```

Isso inicia só o PostgreSQL. **Revisar com o usuário o esquema/migrations antes de
executar qualquer SQL**, conforme [migrations](../Codigos/migrations/README.md).
Não há execução de migrations neste comando. Depois do banco preparado e revisado:

```bash
node infra/platform.cjs run /srv/edufast/plataforma start teste01
node infra/platform.cjs run /srv/edufast/plataforma create-admin teste01
```

`create-admin` solicita e-mail e senha com confirmação em terminal interativo;
senha mínima de 12 caracteres, armazenada pelo hash existente. Não informar senha
na linha de comando. Contas existentes não são alteradas. O administrador criado
pertence somente à escola escolhida. Para nome, sigla e identidade visual, usar
o fluxo escolar já existente com a permissão correspondente; o ID operacional
não configura automaticamente a identidade visual.

Criar o registro DNS de cada domínio apontando ao IP público do gateway e instalar
certificado válido cobrindo todos os domínios no diretório TLS da revisão inicial.
DNS e emissão/renovação de certificados permanecem operações externas. Depois:

```bash
node infra/platform.cjs run /srv/edufast/plataforma gateway
node infra/platform.cjs run /srv/edufast/plataforma status teste01
```

Repetir ativação e administrador para a escola 02. Conferir login em cada URL,
usando a conta daquela escola. O status consulta containers; `list` mostra somente
configurações cadastradas, sem afirmar disponibilidade. A recriação do gateway
pode causar breve interrupção compartilhada. Não há servidor em nuvem configurado
automaticamente por estes comandos.

## Recuperação e operação

`platform.json` aponta à última revisão preparada, não à última comprovadamente
ativa. Um lock exclusivo impede operações simultâneas deste comando. Só remover
`.operator-lock` após confirmar que nenhum operador/processo continua executando.
Não operar `manage.cjs` simultaneamente: ele não participa desse lock.

Falhas antes da promoção preservam o apontamento anterior; uma pasta de revisão
incompleta pode permanecer para diagnóstico. Não apagar volumes para repetir.
Revisões usam nomes únicos e não são sobrescritas. Guardar cadastro, revisões,
segredos e TLS em backup privado; nunca no Git. Em Windows, restringir também ACLs.

Atualizações, backups e recuperação continuam em [CLOUD.md](CLOUD.md). Ao preparar
uma revisão manual posterior, adotar essa revisão em um **novo** cadastro e aposentar
o anterior antes de continuar. Não voltar a usar um cadastro com inventário antigo.

Validação automatizada: `node --test infra/test_platform.cjs` cobre cadastro,
isolamento da configuração, preservação de segredos, adoção, duplicatas, lock e
direcionamento do administrador. Operações Docker nesses testes são simuladas;
não comprovam SSH, DNS, TLS, provisionamento ou funcionamento em nuvem.
