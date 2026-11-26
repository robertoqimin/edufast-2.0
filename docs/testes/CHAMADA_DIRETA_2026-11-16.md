# Chamada confirmada pelo professor — MS01

Data: 16/11/2026. Base: `7e996a167c5f40657eab12d9bde36e8af223e030`
mais alterações locais. Não houve commit, publicação ou migration neste lote.
Direção autorizada pelo usuário: **professor confirma diretamente a chamada**.

## Comportamento implementado

- Professor autorizado marca explicitamente todos os alunos e confirma. A chamada
  entra imediatamente no relatório; não exige uma decisão administrativa posterior.
- A interface apresenta o estado **confirmada**. A API/banco preservam `aprovada`
  como valor técnico compatível com o esquema existente. `decidido_por` identifica
  o professor; a auditoria distingue `confirmar_chamada` e `corrigir_chamada`.
- Conferir chamada → **Corrigir chamada** abre as marcações da revisão vigente.
  A data, o número de aula e o elenco original são preservados. Motivo obrigatório
  entre 5 e 500 caracteres. A nova revisão substitui a anterior na mesma transação,
  mantendo marcações, autor e histórico originais.
- Correção exige `anterior_id` e `versao` da chamada vigente. Uma tela antiga,
  referência incorreta ou tentativa de lançar novamente a aula recebe conflito.
  A versão é incrementada na revisão substituída; a nova inicia em 1.
- Repetir a mesma chave/conteúdo devolve a resposta gravada, sem duplicar registros.
  Uma chave reutilizada com conteúdo diferente continua recusada.
- Chamadas antigas **pendentes** continuam pendentes e bloqueiam um novo registro
  da mesma aula até decisão administrativa. Não foram convertidas automaticamente.
- Atestados continuam restritos ao aluno e à administração; aceite justifica a
  falta sem transformá-la em presença. Aprovações de notas/materiais não mudaram.
- Contas inativas, professor sem vínculo, aluno, turma arquivada, data futura,
  elenco incompleto e situações inválidas continuam sendo recusados.

## Contrato HTTP

`POST /frequencia/chamadas`, com autenticação e `Idempotency-Key`, continua retornando
201; agora responde `estado: aprovada`, `versao` e mensagem de confirmação direta.
Formulários usam CSRF e chave de envio como antes.

Para corrigir, enviar turma/disciplina, dia/aula, elenco completo e:

```json
{"anterior_id": 123, "versao": 1, "motivo": "Correção conferida pelo professor"}
```

Sem versão em uma correção válida: 428; versão antiga, referência substituída,
duplicação ou pendência legada: 409. O endpoint administrativo de decisão permanece
para chamadas legadas pendentes e análise de atestados. Uma chamada já confirmada
não aceita nova decisão administrativa por esse endpoint.

## Validação executada

Windows/PowerShell, Python 3.14.3 no ambiente virtual existente, SQLite em memória,
Node e Edge headless. Todos os dados fictícios. Os servidores temporários usaram
somente `127.0.0.1:5091`, em duas execuções independentes, e foram encerrados.
Uploads ficaram em diretório temporário do processo. Nenhum banco escolar foi acessado.

| Verificação | Resultado |
| --- | --- |
| `test_frequencia test_restauracao test_approvals_security test_course_outline` | 76 testes: 71 aprovados, 5 exclusivos de MySQL ignorados; 48,732 s |
| Frequência dentro dessa rodada | 32 testes: 29 aprovados e 3 exclusivos de MySQL ignorados |
| HTTP real, `.github/cicd/frequencia_http.cjs` | 30 verificações aprovadas: login, confirmação, correção, conflitos, multipart, download e CSV |
| `node api/tests/verificar_frequencia.cjs` | Fluxo completo aprovado; 14 capturas, nenhum erro JavaScript e sem overflow horizontal na página |
| Teclado, rodada complementar no mesmo ambiente | Tab entre seletores de alunos e validação nativa de campos obrigatórios aprovados |
| Protocolo estático de design, sintaxe dos dois scripts Node e `git diff --check` | Aprovados |

A suíte verifica confirmação sem admin, auditoria, correção imediata, duplicidade,
replay de correção, motivo/versão/referência, elenco histórico após desmatrícula,
acesso ao formulário, preservação de pendências antigas e rollback da correção
quando o fechamento da transação falha. O runner MySQL contém cenários de chamadas
e correções simultâneas, além da decisão concorrente sobre pendência legada.

### Reprodução local

Usar Python com as dependências da aplicação/testes instaladas. Nesta execução:
`.ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe`.

```powershell
$env:PYTHONPATH = "$PWD/api;$PWD/.github/cicd/tests"
$env:DB_URL = 'sqlite:///:memory:'
$env:APP_ENV = 'development'
$env:SECRET_KEY = 'attendance-synthetic-key-for-isolated-tests-only'
$env:EDUFAST_TEST_DISPOSABLE = '1'
& .ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe -m unittest test_frequencia test_restauracao test_approvals_security test_course_outline -v
& .ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe api/tests/verificar_protocolo_design.py
```

Para o servidor visual local, manter `DB_URL=sqlite:///:memory:`, definir
`EDUFAST_FREQUENCIA_VISUAL=1`, gerar `DATA_ENCRYPTION_KEY` sintética com Fernet e
executar `python .github/cicd/tests/frequencia_visual_fixture.py --local`.
Em outro terminal, definir `PLAYWRIGHT_MODULE` para o Playwright instalado e rodar
`node api/tests/verificar_frequencia.cjs`. Usar servidor novo para repetir
o navegador ou o teste HTTP, pois ambos criam sua própria chamada do dia.
O modo local recusa conexão persistente e não aceita destino externo.

Quando Docker estiver disponível, `node .github/cicd/run_frequencia_api.cjs`
executa SQLite, MySQL descartável e HTTP real sem conectar bancos escolares.

## Inspeção visual e limites

[Capturas e hashes](../design/referencias/2026-11-16-chamada-direta/manifesto.json)
e [comparação](../design/referencias/2026-11-16-chamada-direta/comparacao.md).
Inspecionados formulário desktop, correção/conferência mobile e conjunto das 14
capturas em folha de contato. Identidade padrão, 1440×1000 e 390×844; componentes,
fontes, menu e tokens preservados. Não houve nova personalização de paleta.

Docker Engine indisponível; MySQL, concorrência real e runtime Linux **não foram
validados nesta rodada**. MS01 está implementado e validado em SQLite/HTTP/navegador,
com aceite MySQL pendente antes da liberação comercial. Não houve teste de carga
ou promessa de capacidade. Há avisos de depreciação e recursos não fechados nas
suítes existentes; nenhuma asserção falhou. Não foi investigada sua origem neste lote.

Esta mudança não altera o esquema. Instalação que ainda não tem as tabelas de
frequência continua exigindo revisão de `004_frequencia.sql`; não executar migrations
nas escolas Teste 01/02 ou em outro banco persistente sem revisão do usuário.
