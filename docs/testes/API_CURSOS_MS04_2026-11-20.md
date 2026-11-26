# Backend e API de cursos MS04

Data: 20/11/2026. Base `aedf8ad` mais alterações locais deste lote.
Continuação do [esqueleto MS04](../planejamento/ESQUELETO_MS04_2026-11-20.md).

O backend organiza curso → módulos → capítulos → aulas, permite autoria de
rascunhos pela API, revisão administrativa da publicação, ofertas por disciplina,
retomada da última aula e conclusão independente. Suporta texto e YouTube com
apoios privados. O frontend permanece para a etapa seguinte.

## Ativação e compatibilidade

A API usa o prefixo **`/api`**, com blueprint separado dos formulários legados.
Os caminhos anteriores continuam com suas regras atuais, incluindo propostas
docentes de cursos e aprovações acadêmicas. Um rascunho criado pela nova API
persiste diretamente; isso não publica o curso nem libera uma turma.

Primeira edição/duplicação pela API adota o curso na gestão versionada. A partir
disso, operações de gravação pelo editor legado são recusadas com 409, incluindo
tentativas via propostas antigas, para não contornar versão/snapshot. Propostas
de cursos que continuam no fluxo legado permanecem válidas sob suas regras
anteriores. Não houve alteração de templates, CSS, fontes, menu ou JavaScript
do produto neste lote.

Aulas antigas sem metadados novos são vídeo. Cursos com aulas em texto retornam
409 nas telas HTML antigas que dependeriam de iframe; a leitura completa está
na API. Isso evita apresentar um player inválido antes do frontend correspondente.
O mapeamento visual continua previsto: `CapituloModel` é módulo e `TemaModel`
é capítulo. Os tipos de payload legados `capitulo`, `tema` e `aula` são preservados.

Sem as quatro tabelas opcionais ou sem `video_id` aceitar NULL, a API retorna
503. O startup não cria/altera tabelas. O esquema é preparado pela
[proposta SQL 007](../../api/migrations/007_cursos_backend_ms04.sql),
**pendente de revisão e não executada em banco persistente**.

## Autenticação e respostas

Usar `Authorization: Bearer <token>` obtido pelo login existente ou sessão
autenticada. POST com sessão exige `X-CSRF-Token` ou campo `csrf_token`; não
basta conhecer o ID. Todos os envios de gravação exigem `Idempotency-Key`, ou
`idempotency_key` em formulário. JSON desconhecido é recusado, sem aceitar
campos arbitrários de autoria, oferta, estado ou permissão.

As respostas da API recebem `Cache-Control: no-store` e
`X-Content-Type-Options: nosniff`. JSON retorna erros com `erro`; downloads são
anexos privados. Identificadores/versões rejeitam booleanos, negativos, texto
inválido e valores além de inteiro suportado. Chave de envio reutilizada com
corpo diferente retorna 409.

| Situação | HTTP |
| --- | --- |
| Criação de curso, recurso ou cópia | 201 |
| Pedido de publicação aguardando revisão | 202 |
| Consulta/gravação concluída | 200 |
| Abertura via formulário seguida de navegação | 303 |
| Dados/campos/tipo inválidos | 400 |
| JWT inválido ou conta revogada | 401 |
| Perfil, autoria ou CSRF não autorizado | 403 |
| Oferta/aula/recurso fora do acesso | 404 |
| Versão antiga, revisão obsoleta ou edição publicada | 409 |
| Versão ou chave de envio ausente | 428 |
| Esquema MS04 ainda não habilitado | 503 |

Idempotência não concede acesso: novas requisições continuam sujeitas à identidade
atual e às restrições da oferta. Gravações de conteúdo usam a versão do agregado
curso; abertura usa a versão de retomada daquele aluno/oferta. As versões não
são intercambiáveis e não representam a edição pedagógica.

## Biblioteca e autoria

| Método e caminho | Perfis e comportamento |
| --- | --- |
| `GET /api/cursos?pagina=1` | Autor vê seus cursos com vínculo atual; administração vê cursos; aluno vê ofertas autorizadas. 25 itens por página |
| `POST /api/cursos` | Professor cria rascunho próprio; administração informa responsável autorizado |
| `GET /api/cursos/<curso_id>` | Autor/admin consultam curso, versão, índice leve, revisão e ofertas |
| `GET /api/cursos/<curso_id>/aulas/<aula_id>` | Autor/admin consultam conteúdo e metadados de apoios da aula |
| `POST /api/cursos/<curso_id>/estrutura` | Autor/admin alteram somente rascunho, com versão atual |
| `POST /api/cursos/<curso_id>/duplicar` | Cópia independente em rascunho, sem copiar conclusões ou cursor |

Criação docente:

```json
{"disciplina_id": 1, "titulo": "Funções", "descricao": "Estudo orientado"}
```

Retorno: `curso_id`, `versao: 1`, `estado: "rascunho"`. Para administração,
acrescentar `professor_id`. O responsável deve ser professor ativo vinculado à
disciplina. Professor não pode escolher outro autor. O ID do ator vem da
autenticação, nunca do corpo enviado.

Exemplos de estrutura; sempre usar a versão retornada pela última gravação:

```json
{"acao":"adicionar","tipo":"capitulo","titulo":"Módulo 1","versao":1}
```

```json
{"acao":"adicionar","tipo":"tema","pai_id":10,"titulo":"Capítulo 1","versao":2}
```

```json
{"acao":"adicionar","tipo":"aula","pai_id":20,"titulo":"Aula em texto","tipo_aula":"texto","corpo":"Conteúdo da aula","versao":3}
```

```json
{"acao":"adicionar","tipo":"aula","pai_id":20,"titulo":"Videoaula","tipo_aula":"video","video":"abcdefghijk","descricao":"Orientação de estudo","versao":4}
```

`tipo=capitulo` representa módulo e `tipo=tema` representa capítulo. `pai_id`
sempre pertence ao mesmo curso. Para `editar`, informar `id`, tipo e título;
em aula, informar também seu formato completo. `subir`, `descer` e `remover`
usam tipo/id/versão. `acao=curso` altera título/descrição do rascunho.

Títulos: até 150 caracteres; descrição/corpo: até 10.000 cada. Texto exige corpo
não vazio e não usa ID fictício de vídeo. Vídeo usa a validação YouTube existente.
JSON trata texto como dado; a futura interface deve manter escape ao renderizar.

Uma gravação incrementa a versão, inclusive reordenação. A transação bloqueia
o curso e grava conteúdo/auditoria juntos. Aula com recursos ou histórico não é
apagada fisicamente pelo editor; preparar outra edição preserva as referências.

## Publicação e ofertas

| Método e caminho | Regra |
| --- | --- |
| `POST /api/cursos/<curso_id>/solicitar-publicacao` | Autor envia `versao`; pedido inclui snapshot da árvore, corpos e recursos |
| `POST /solicitacoes/alteracoes/<id>/decidir` | Administração aprova/rejeita pelo contrato existente |
| `POST /api/cursos/<curso_id>/estado` | Administração publica rascunho completo ou arquiva; exige versão |
| `POST /api/cursos/<curso_id>/ofertas` | Administração cria/ativa/revoga oferta exata, sem ampliar matrícula |

Pedido de publicação: `{"versao":5}`. A aprovação valida outra vez autor ativo,
vínculo, estado, versão e assinatura do conteúdo. Edição posterior invalida a
revisão; mesmo alteração externa sem incremento de versão é detectada pelo hash.
Revisor docente de outros materiais não recebe permissão de publicar cursos.
Uma rejeição permite corrigir e enviar novo pedido; o pedido anterior é preservado.

Publicação exige módulos/capítulos preenchidos e aulas válidas. Conteúdo publicado
é imutável; arquivar suspende acesso sem apagar progresso. Exemplo administrativo:
`{"estado":"publicado","versao":5}` ou `{"estado":"arquivado","versao":7}`.

Oferta:

```json
{"turma_disciplina_id":1,"ativa":true,"versao":6}
```

O curso deve estar publicado e a turma ativa; disciplina do curso e do par devem
coincidir. `ativa:false` revoga uma oferta existente. O retorno informa `id`,
`ativa` e versão atualizada. Oferta e publicação são operações separadas.
Alterar oferta pela API também exige e atualiza a versão do curso.

## Aprendizagem e retomada

| Método e caminho | Comportamento |
| --- | --- |
| `GET /api/estudos/disciplinas/<par_id>/cursos?pagina=1` | Lista paginada de ofertas publicadas/ativas daquela disciplina autorizada |
| `GET /api/aprender/<oferta_id>` | Abre última aula registrada; sem cursor, primeira não concluída, ou primeira se todas concluídas |
| `GET /api/aprender/<oferta_id>?aula=<aula_id>` | Consulta a aula escolhida sem registrar conclusão/abertura |
| `GET /api/aprender/<oferta_id>/retomada` | Consulta apenas cursor atual, sem carregar corpos de todas as aulas |
| `POST /api/aprender/<oferta_id>/aulas/<aula_id>/abrir` | Registra última aula acessada, sem concluir |
| `POST /api/aprender/<oferta_id>/aulas/<aula_id>/concluir` | Conclusão explícita e monotônica; corpo JSON vazio |

Aluno precisa de turma e disciplina vinculadas, matrícula ativa, curso publicado,
oferta ativa e turma não arquivada. A regra também é conferida no download e no
fluxo HTML legado. Aula deve pertencer ao curso da oferta, mesmo quando o ID
existe em outra árvore. Turma, disciplina e curso não são inferidos pelo cliente.

Primeira abertura: `{"versao":0}`. Retorno: `oferta_id`, `aula_id`, `versao:1`
e `destino`. Para próxima abertura, enviar a versão retornada. Duas abas ou
dispositivos com a mesma versão concorrem; a versão antiga recebe 409. A chave
idempotente permite repetir o envio exato sem mover novamente o cursor.

Abertura por formulário pode enviar `csrf_token`, `idempotency_key` e `versao`;
a resposta 303 aponta para a consulta JSON da aula. O backend sem JavaScript está
testado; o formulário/navegação visual completo será feito no frontend.

A leitura inclui `curso`, `modulos`, `aula` selecionada, `anterior_id`,
`proxima_id`, `retomada`, IDs `concluidas`, `total` e `progresso`. O índice não
inclui corpo textual de todas as aulas; só a aula selecionada traz corpo/recursos.
Primeira/última aula têm anterior/próxima nulos quando cabível. Curso legado vazio
retorna aula nula e progresso zero; não há divisão por zero.

Concluir não atualiza o cursor nem conclui a próxima aula. Um único registro é
persistido por aluno/oferta/aula, inclusive sob concorrência. A mesma aula em
outra oferta possui conclusões e retomada independentes. Conclusão não equivale
a presença, nota, certificado ou comprovação de segundos assistidos.

## Materiais de apoio e arquivos

| Método e caminho | Regra |
| --- | --- |
| `POST /api/cursos/<curso_id>/aulas/<aula_id>/recursos` | Autor/admin acrescenta link HTTPS ou arquivo ao rascunho, com versão |
| `POST /api/cursos/<curso_id>/aulas/<aula_id>/recursos/<id>/arquivar` | Autor/admin arquiva recurso do rascunho, com versão |
| `GET /api/cursos/<curso_id>/aulas/<aula_id>/recursos/<id>/arquivo` | Autor/admin confere arquivo, inclusive durante revisão |
| `GET /api/aprender/<oferta_id>/aulas/<aula_id>/recursos/<id>/arquivo` | Aluno baixa apenas recurso ativo da aula/oferta autorizada |

Link: `{"tipo":"link","titulo":"Leitura","link":"https://example.test/apoio","versao":5}`.
O servidor valida HTTPS, não busca o endereço e não aceita credenciais na URL.
Arquivo: multipart com `tipo=arquivo`, `titulo`, `versao` e um campo `arquivo`.
Limites: 20 recursos ativos por aula; PDF/PNG/JPEG de até 5 MiB por arquivo.
Validação de assinatura/tamanho não é antivírus ou validação pedagógica.

Arquivos ficam cifrados em `uploads/materiais_curso`, com nomes aleatórios e a
chave existente `DATA_ENCRYPTION_KEY`. Respostas não expõem caminho/nome interno.
Recursos não usam endpoints de documentos pessoais, atestados ou o vínculo de
um material MS02. Download é anexo, auditado, com `no-store` e `nosniff`.

Duplicar uma edição cria novos IDs de aula/recurso e compartilha somente o objeto
binário cifrado imutável. Cada referência tem autorização própria. Arquivar a
edição anterior não retira o arquivo da cópia publicada, nem transfere progresso.
Não há exclusão física automática; falhas antes do commit removem apenas o objeto
novo daquela tentativa, sem apagar arquivos já referenciados por outras edições.

## Esquema e implantação futura

Para preservar a leitura do esquema antigo, versão e corpos ficam em tabelas de
extensão: `curso_versoes`, `curso_aula_conteudos`, `curso_retomadas` e
`curso_aula_recursos`. A única alteração de coluna proposta é permitir NULL em
`curso_aulas.video_id`. Cursos sem registro de versão leem versão 1; a primeira
gravação/duplicação pela API adota a gestão versionada.

As FKs e constraints garantem referências, unicidades, tipo e metadados mínimos.
A relação entre tipo da extensão e vídeo na aula, e a pertença da aula ao curso
da oferta, também são validadas pela API e na publicação; FKs individuais não
substituem essas verificações entre tabelas.

Antes de ativar: revisão do usuário do SQL 007, preflight de tabelas/tipos/dados,
backup recuperável de banco/uploads/chave e ensaio no destino isolado. DDL MySQL
pode ficar parcial e não deve ser repetido às cegas. Não executar DROP ou limpeza
de arquivos ao voltar código. O player antigo não suporta aulas em texto;
rollback de aplicação após novos formatos exige avaliar essa incompatibilidade.

## Reprodução dos testes

Suíte focada: `.github/cicd/tests/test_cursos_ms04.py`. Usa apenas fixtures com
`EDUFAST_TEST_DISPOSABLE=1`; não executar descoberta contra o banco da aplicação.
Para repetir em SQLite em memória, usar chave sintética, `APP_ENV=development`,
`PYTHON_DOTENV_DISABLED=1` e `PYTHONPATH` com `api`/`.github/cicd/tests`.

```powershell
python -m unittest test_cursos_ms04 -v
python .github/cicd/run_cursos_backend.py --suite ms04
python .github/cicd/run_cursos_backend.py --suite regressao
```

O runner Docker usa imagens locais de teste, monta o checkout atual somente para
leitura e cria projeto/rede/MySQL próprios, sem porta pública do banco. Os dados
MySQL ficam em tmpfs; o HTTP usa SQLite/arquivos em `/tmp` do container e porta
aleatória somente no loopback. Ao terminar remove apenas seu projeto. Não aceita
URL de banco externo. A imagem fornece runtime/dependências; o código testado é
o checkout montado. O resumo registra hash de fonte inicial/final e só aprova se
o código permaneceu igual, além de registrar a limpeza.

O HTTP encadeado de `cursos_http.cjs` também integra o piloto existente via
`frequencia_http.cjs`. Testa JWT, rascunho, hierarquia, vídeo/texto, upload,
aprovação, revisão obsoleta, oferta, cursor, conclusão, cópia e revogação.
### Resultados da execução final

Execução `edufast-ms04-b360c8b097`, ambiente Docker Linux, Python **3.12.16**, MySQL
**8.4**, código atual montado somente para leitura. A imagem local de runtime
`edufast-platform:test` tem ID
`sha256:2459b46f5df64370c68edd03b38357f40d40912c8cd91294f4aae7aedd356af3`.

| Verificação final | Resultado |
| --- | --- |
| Regressão completa SQLite | 222 testes: **197 aprovados, 25 exclusivos de MySQL ignorados**, nenhuma falha; 81,708 s |
| Regressão completa MySQL | 222 testes: **220 aprovados, dois cenários centrais ignorados**, nenhuma falha; 189,219 s |
| Novos testes MS04 dentro da regressão MySQL | **32 aprovados**, incluindo concorrência de edição, retomada e conclusão |
| HTTP real no container Linux | **117 verificações aprovadas**: 30 frequência, 33 estudos/abas e 54 cursos |
| Postman/Newman existente, fixture nova Windows/SQLite | **57 requisições e 65 asserções aprovadas**, com registros/arquivos conferidos |
| Catálogo estrutural | Quatro serviços, 28 caminhos/métodos existentes, 16 cenários descritos; sem aceite automático de frontend |
| Protocolo estático, sintaxe Node e revisão de whitespace | Aprovados |
| Fonte preservada durante testes e limpeza | `source_unchanged:true`, `cleaned:true`; containers da execução removidos |

Os dois casos centrais ignorados na descoberta MySQL usam engine SQLite própria
e exigem o executor central para concorrência. Não são testes ignorados do MS04.
As 32 verificações MS04 usam o MySQL descartável da execução e passaram sem skip.

O resumo registra hash dos fontes Python/CJS antes/depois
`b619a52679dced6f3df8195465a570035f4530ecd7db51b6f4e009406bef25c8` e
`passed:true`. Não foi usada a rodada focada inicial como aprovação final após
os testes adicionais. Nenhuma alteração de código funcional foi feita depois
da rodada final; apenas documentação/catálogo.

Logs locais ignorados pelo Git:

- `.ci-results/cursos-backend/edufast-ms04-b360c8b097/summary.json`;
- `sqlite.log`, `mysql.log`, `http.log`, `http.json` e `cleanup.log` na mesma pasta;
- `.ci-results/ms04-backend-2026-11-20/postman.log`;
- `.ci-results/mutations/summary.json` e `postman.json` da coleção existente.

A validação usa metadata para criar esquemas novos, não aplica a proposta SQL
007 a um banco legado. Não homologa a instalação persistente, a imagem final
de produção, capacidade/carga ou a interface futura. Há avisos de depreciação e
recursos não fechados nas suítes existentes; as asserções finais passaram.

## Próximo lote

Atualização posterior em 20/11: o [frontend e a demo ENEM](FRONTEND_CURSOS_MS04_2026-11-20.md)
foram implementados. O texto abaixo descreve o próximo lote no momento do aceite
do backend, preservado como histórico; resultados atuais estão no novo relatório.

Integrar o frontend aos contratos acima, seguindo o protocolo visual: editor e
estados de revisão, player sob demanda, seleção por módulos/capítulos, navegação
sem JavaScript, retomada e apoios privados. Fazer nova inspeção desktop/mobile e
medir assets/consultas/latência/memória. A suíte backend não constitui aceite da
interface ou medição de capacidade comercial.
