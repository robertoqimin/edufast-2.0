# Escolas Teste 01 e Teste 02

Criadas e verificadas em 11/11/2026, em Docker Desktop 29.4.0 no Windows, imagem
local Python 3.12/Flask/Gunicorn e MySQL 8.4. Dados inteiramente fictícios.

| Escola | Endereço local | Administrador |
| --- | --- | --- |
| Escola Teste 01 | http://127.0.0.1:5081 | `admin@teste01.local` |
| Escola Teste 02 | http://127.0.0.1:5082 | `admin@teste02.local` |

**Senha inicial de todas as contas novas:** `Teste-escolas-2026!`.
As credenciais são públicas e exclusivas de demonstração local. Não usar na nuvem.

Cada escola possui 20 alunos, 5 professores, 3 matérias (Matemática, Português e
Ciências), um administrador e uma turma de demonstração em 2026. Todos os alunos
estão matriculados nessa turma e vinculados às três matérias (60 vínculos por
escola). Os professores estão vinculados à turma e distribuídos entre as matérias:
01/04 em Matemática, 02/05 em Português e 03 em Ciências.

Contas por escola:

- Teste 01: `aluno01@teste01.local` até `aluno20@teste01.local`;
  `professor01@teste01.local` até `professor05@teste01.local`.
- Teste 02: `aluno01@teste02.local` até `aluno20@teste02.local`;
  `professor01@teste02.local` até `professor05@teste02.local`.

Não foram criados boletins, notas, atividades, períodos letivos do módulo novo ou
aprovações de propostas. O cenário usa os vínculos existentes de turma/disciplina;
não comprova o planejamento acadêmico futuro nem concede permissão nova a professores.
Os identificadores obrigatórios dos professores são marcadores de teste, não CPFs reais.

## Iniciar, verificar e parar

**Correção de acesso em 11/11:** não usar as portas anteriores 5061/5062.
O Edge reproduziu `ERR_UNSAFE_PORT` na 5061. Os endereços atuais usam 5081/5082.
Para abrir fora da prévia do VS Code, executar na raiz:

```powershell
.\iniciar-duas-escolas.ps1
# Se as escolas já estiverem iniciadas:
.\iniciar-duas-escolas.ps1 -SomenteAbrir
```

O atalho abre as duas escolas no navegador padrão do Windows. `-SemNavegador`
permite iniciar/verificar saúde sem abrir janelas. O navegador interno do VS Code
usa um iframe e pode bloquear o acesso local ou a sessão. Não desativar políticas
do navegador, CSRF ou proteção de cookies para usar a prévia.

Na raiz do repositório, com Docker Desktop iniciado e Node 20+:

```powershell
node infra/demo.cjs start
node infra/demo.cjs verify
node infra/demo.cjs status
node infra/demo.cjs logs
node infra/demo.cjs stop
```

`start` constrói a imagem local, inicia os dois MySQL, prepara dados apenas em banco
novo ou revalida o cenário já identificado, inicia aplicações e confere saúde.
`verify` testa contagens, todos os logins/painéis HTTP e rejeição cruzada de
sessões/JWT. Se alterar uma senha inicial, a verificação desse login falhará;
o comando não redefine a senha. `stop` preserva os volumes; `start` mantém senhas,
estados e permissões existentes. O teste não modifica ambientes de teste anteriores.

Os subdomínios `.localhost` são destinados ao navegador da própria máquina,
sem compra de domínio ou configuração de DNS público. Os serviços são publicados
somente em `127.0.0.1`, portas 5081/5082, usando HTTP local e modo de desenvolvimento
com debug desativado. Cookies com nomes próprios separam as sessões mesmo quando
as duas escolas usam o IP 127.0.0.1 em portas distintas. Para
verificação automatizada, o script conecta ao loopback com o `Host` correspondente.

Não usar esta configuração na nuvem. O modelo HTTPS de produção permanece no
[guia CLOUD](../../infra/CLOUD.md), com segredos próprios e sem senhas públicas.
Esta demonstração não adiciona DNS ou certificados ao modelo de produção.

## Separação e preservação

Projeto Compose exclusivo: `edufast-duas-escolas-teste`.
Aplicações: `app-teste01`, `app-teste02`; MySQL: `db-teste01`, `db-teste02`.
Cada um possui rede de banco interna e volumes de banco/uploads exclusivos.
As redes de entrada locais de cada app permitem publicação no loopback; não há
rede de aplicação compartilhada entre as escolas nem porta MySQL publicada.

Configuração e segredos aleatórios ficam em `.ci-results/duas-escolas/`, ignorado
pelo Git. Não apagar essa pasta nem volumes para reiniciar. A descrição dos
serviços pode ser atualizada pelo iniciador, preservando `.env` e nomes de volumes.
No Windows, restringir ACLs da pasta quando necessário.

`two_school_test_data.py` exige opt-in, modo de desenvolvimento e combinação exata
de host/nome de banco desta demonstração. Cria esquema somente se o banco estiver
vazio. Banco com esquema diferente ou dados sem identificação da fixture é recusado.
Não executa migrations, DROP, reset de senha ou concessão adicional de permissões.
Uma segunda execução não repovoa nem substitui o conteúdo já identificado.

## Evidências e limites

Execução inicial em 11/11/2026:

- Dois bancos MySQL: 20 alunos, 5 professores, 3 matérias, 20 matrículas e 60
  vínculos aluno/matéria por escola.
- 52 logins aprovados (40 alunos, 10 professores e 2 administradores), com painéis
  HTTP retornando 200.
- Cookies e JWT de uma escola rejeitados na outra, nos dois sentidos.
- Busca administrativa retornou somente os 20 alunos da própria escola.
- Reinicialização da carga revalidou os dados sem duplicar registros.
- 4 testes Python aprovados em SQLite descartável: quantidades/contas locais,
  preservação de senha/estado, recusa de banco alheio e bloqueios de destino/opt-in.
- 12 testes Node aprovados para infraestrutura, operação e configuração local.

Na primeira execução, os painéis foram verificados apenas por HTTP. Não houve inspeção visual em navegador,
medição de carga, restauração de backup ou homologação acadêmica completa.
Naquela execução não houve alteração de layout, template, CSS ou regras de aprovação.

## Correção após falha de abertura e login

O teste anterior não exercitou as restrições reais do navegador. A regressão em
Edge headless reproduziu `ERR_UNSAFE_PORT` no endereço antigo com porta 5061.
As portas atuais são 5081/5082, sem flags para contornar esse bloqueio.
O usuário confirmou uso do navegador interno do VS Code. Essa prévia usa iframe;
o acesso local e os cookies podem ser bloqueados. A ferramenta de inspeção do
navegador pessoal não conseguiu verificar sua URL e foi encerrada. A validação
seguinte usou exclusivamente um perfil headless descartável.

Mudanças: atalho externo `iniciar-duas-escolas.ps1`, cookie `edufast_teste01` ou
`edufast_teste02`, conferência de sessão persistida em `/auth/session` antes do
redirecionamento e aviso no formulário quando estiver em iframe ou perder sessão.
O endpoint exige cookie e revalida estado, papel e versão de autenticação. JWT
isolado não comprova sessão do navegador. Nenhuma regra de perfil, aprovação,
CSRF, SameSite=Lax, HttpOnly ou HTTPS de produção foi removida. A troca de nome de
cookie requer novo login, sem redefinir contas, senhas ou dados.

Validação da correção em 11/11/2026:

- 19 testes de aplicação aprovados em SQLite descartável, incluindo sessão
  anônima, sessão válida, revogação e tentativa de usar somente JWT na conferência.
- Aprovações/segurança: 25 aprovados; 1 ignorado por exigir concorrência MySQL.
- 16 testes Node aprovados para infraestrutura, operação e proteção de envio.
- Navegador Edge headless: login pelo formulário para os três perfis nas duas
  escolas; sessões simultâneas no mesmo IP; professor/aluno sem acesso de admin;
  erro claro quando a conferência de sessão é simulada como bloqueada; aviso em
  iframe local de teste. A prévia real do VS Code não recebeu homologação de login.
- Capturas desktop 1440x1000 e mobile 390x844, sem overflow horizontal; referências
  originais preservadas e nova [comparação visual](../design/referencias/2026-11-11-login-escolas/comparacao.md).

Referências: [Simple Browser do VS Code](https://github.com/microsoft/vscode/blob/main/extensions/simple-browser/README.md)
e [configuração de cookies Flask](https://flask.palletsprojects.com/en/stable/config/).

### Retomada e conferência em 12/11/2026

O Docker Desktop estava desligado e foi iniciado. Uma primeira conferência ocorreu
antes de o MySQL ficar pronto e recebeu conexão recusada; nenhum dado foi alterado.
Após a inicialização, passaram novamente os 52 acessos HTTP e as verificações de
separação entre escolas, os 16 testes Node, o protocolo estático com os novos
manifestos e a regressão do formulário em Edge headless isolado. O atalho
`iniciar-duas-escolas.ps1 -SomenteAbrir -SemNavegador` confirmou os dois endereços.
Essa execução do atalho não abriu o navegador pessoal. Os dados continuaram com
20 alunos, 5 professores e 3 matérias por escola. Não foram executadas migrations.
