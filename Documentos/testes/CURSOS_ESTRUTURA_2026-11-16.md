# Estrutura de cursos — primeiro lote de leveza

Data: 16/11/2026. Base: `7e996a167c5f40657eab12d9bde36e8af223e030`
mais as alterações locais em `Códigos/app/services/cursos.py` e
`.github/cicd/tests/test_course_outline.py`. Não representa um commit publicado.
Entrega MS00 do [plano de ensino médio e superior](../planejamento/ENSINO_MEDIO_SUPERIOR_2026-11-16.md).

## Alteração

`estrutura()` consultava capítulos e depois executava consultas de temas por
capítulo e aulas por tema. Pelo fluxo anterior, o número de SELECTs era
`1 + quantidade de capítulos + quantidade de temas` (análise do código, não
benchmark de duração). A nova leitura agrupa capítulos, temas e aulas em até três
consultas filtradas pelo curso. Curso sem capítulos retorna após uma consulta.

O formato retornado permanece compatível com os consumidores atuais. Ordenação,
capítulos/temas vazios e duplicação são preservados. Autoria e acesso à oferta
continuam sendo verificados pelos chamadores; o serviço não concede permissões.

## Verificação executada

Windows/PowerShell, Python 3.14.3 no ambiente virtual local existente, SQLite
em memória. A suíte de estrutura cria engine privada com chaves estrangeiras
habilitadas; a regressão de restauração usa `DB_URL=sqlite:///:memory:` e opt-in
descartável. Nenhum teste conecta a banco escolar persistente.

```powershell
$env:PYTHONPATH = "$PWD/Códigos;$PWD/.github/cicd/tests"
$env:DB_URL = 'sqlite:///:memory:'
$env:APP_ENV = 'development'
$env:SECRET_KEY = 'course-outline-synthetic-key-for-isolated-tests-only'
$env:EDUFAST_TEST_DISPOSABLE = '1'
& .ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe -m unittest test_course_outline test_restauracao -v
& .ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe Códigos/tests/verificar_protocolo_design.py
```

O caminho do Python é local e ignorado pelo Git; em outro checkout, usar um
ambiente virtual com as dependências da aplicação e dos testes instaladas.

| Verificação | Resultado |
| --- | --- |
| Estrutura modular: ordem, vazios e isolamento entre cursos | Aprovada |
| Crescimento de 1 capítulo/1 tema/2 aulas para 21 capítulos/61 temas/122 aulas | Quantidade de consultas não cresce e permanece até três; aulas conferidas |
| Curso vazio/inexistente | Lista vazia e até uma consulta |
| Duplicação | Conteúdo preservado, capítulos independentes e origem registrada |
| Total combinado com restauração | 18 executados, 17 aprovados, 1 exclusivo de MySQL ignorado; 6,296 s |
| Protocolo estático de design | Aprovado |

## Limitações

Docker Engine indisponível no início da verificação. MySQL/runtime Linux não
foram executados. A contagem de consultas usa banco real SQLite com listener SQL,
sem simular resultados. Não foram medidos latência, RAM/CPU, carga concorrente ou
capacidade por escola. A mudança reduz viagens ao banco, mas ainda materializa o
conteúdo do curso; crescimento de memória precisa de medição própria.

Sem alteração de template/CSS e sem inspeção visual nova. Há avisos de
`datetime.utcnow` e `ResourceWarning` na regressão existente; nenhuma asserção falhou.
Não foi investigada a origem do recurso não fechado neste lote.

Confirmação direta docente, espaço da disciplina, materiais e abas são entregas
seguintes. O comportamento de frequência continua sendo o anterior até MS01.
Nenhuma migration, implantação ou alteração em conta/permissão foi executada.
