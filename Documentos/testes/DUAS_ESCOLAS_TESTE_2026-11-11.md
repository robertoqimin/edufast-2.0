# Escolas Teste 01 e Teste 02

Criadas e verificadas em 11/11/2026, em Docker Desktop 29.4.0 no Windows, imagem
local Python 3.12/Flask/Gunicorn e MySQL 8.4. Dados inteiramente fictícios.

| Escola | Endereço local | Administrador |
| --- | --- | --- |
| Escola Teste 01 | http://teste01.localhost:5061 | `admin@teste01.local` |
| Escola Teste 02 | http://teste02.localhost:5062 | `admin@teste02.local` |

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
somente em `127.0.0.1`, portas 5061/5062, usando HTTP local e modo de desenvolvimento
com debug desativado. Os hosts distintos separam os cookies no navegador. Para
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

Os painéis foram verificados por HTTP. Não houve inspeção visual em navegador,
medição de carga, restauração de backup ou homologação acadêmica completa.
Nenhum layout, template, CSS, autenticação ou regra de aprovação foi alterado.
