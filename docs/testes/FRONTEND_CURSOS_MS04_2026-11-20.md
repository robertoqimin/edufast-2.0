# MS04 — frontend e demonstração de Matemática para o ENEM

Data: 20/11/2026. Implementação local sobre `aedf8ad4b81ee654857e82b40678086d12aebe72`, ainda sem commit desta etapa. Complementa o relatório histórico [backend/API](API_CURSOS_MS04_2026-11-20.md).

## Entrega

Biblioteca, organização de módulos/capítulos/aulas, edição de texto/vídeo,
materiais privados, pedido de publicação, revisão administrativa, ofertas,
navegação, conclusão e retomada. HTML/Jinja usa o layout e os tokens existentes.
As gravações usam os endpoints da API com `interface=web`: mesmas permissões,
CSRF, chave de envio, versão e transação, retornando 303 para destinos internos.
JSON mantém o contrato anterior, inclusive quando enviado com esse parâmetro.

`/cursos`, `/cursos/<id>` e `/aprender/<oferta>` usam o novo frontend quando o
esquema MS04 está disponível. Instalações sem as tabelas opcionais conservam
a biblioteca anterior; abrir diretamente o novo módulo retorna 503 sem DDL.
O espaço da disciplina oferece o link **Cursos** quando o esquema está pronto.

`/aprendizagem` é a biblioteca; `/aprendizagem/cursos/<id>` organiza o curso;
`/aprendizagem/cursos/<id>/aulas/<id>` edita/confere uma aula;
`/aprendizagem/ofertas/<id>` apresenta a jornada do aluno.

## Demonstração para teste manual

Acesso: **http://127.0.0.1:5092**. Depois do login, abra **Meus cursos** como
aluno ou **Biblioteca de cursos** como professor. Também pode abrir `/cursos`.

| Papel | E-mail fictício | Senha da demonstração |
| --- | --- | --- |
| Aluno | aluno02@teste01.local | Teste-escolas-2026! |
| Professor de Matemática | professor01@teste01.local | Teste-escolas-2026! |
| Administração | admin@teste01.local | Teste-escolas-2026! |

Use janelas/perfis separados para testar papéis simultaneamente.

A matéria **Matemática** está vinculada à turma **Preparatório ENEM — 2026**.
O curso publicado **Matemática para o ENEM** contém quatro módulos, oito
capítulos e doze aulas de texto, com objetivos, explicações, exemplos,
exercícios autorais e gabaritos comentados. Há um gráfico PNG autoral para
download na aula **Leitura de gráficos e pontos**. Não são questões oficiais.

O professor encontra também **Matemática para o ENEM — laboratório do professor**,
uma cópia em rascunho das doze aulas, para testar alterações sem modificar o
curso publicado. A cópia não está liberada ao aluno. O ambiente manual foi
verificado por login e leituras: aluno com 0% de progresso e nenhuma retomada;
curso publicado e laboratório em rascunho. Os testes automatizados alteraram
outro ambiente, na porta 5093.

### Roteiro sugerido

1. Aluno: continuar estudando, abrir outra aula, sair e retornar. Deve reabrir
   a última aula visitada, mesmo que não concluída.
2. Aluno: marcar uma aula como concluída, conferir o progresso e baixar o gráfico.
3. Professor: abrir o laboratório, editar uma aula, renomear/ordenar grupos,
   adicionar capítulo e aula de texto, enviar arquivo ou link.
4. Professor: solicitar publicação; administração: conferir em **Solicitações e
   aprovações**, aprovar e liberar para a turma na tela do curso.
5. Aluno: conferir a nova edição. O progresso no curso original deve continuar
   preservado. A nova edição começa com progresso independente.

### Ciclo de vida do ambiente

`node infra/enem-demo.cjs start` inicia o projeto Docker `edufast-enem-demo`,
reutilizando a imagem local de testes `edufast-platform:test` apenas como runtime
e montando o código atual para leitura. `status` consulta; `stop` interrompe.
O script limita a porta ao loopback. O banco SQLite e os arquivos são novos e
temporários em `/tmp` (tmpfs): **parar/reiniciar o container descarta os testes
manuais e recria a massa**. Enquanto o container permanece ativo, alterações
e progresso permanecem disponíveis. Não usar para dados reais.

Nenhuma migration foi executada nos bancos persistentes. O servidor da demo
recusa outros destinos e bancos já preenchidos. A habilitação nas escolas
existentes continua dependendo da revisão das propostas SQL, conforme AGENTS.md.
Configuração e chaves da demo ficam ignoradas em `.ci-results/enem-demo/`.

## Validação

- Seis testes de integração HTML: rotas novas e antigas, escape de conteúdo,
  autorização, criação/edição, replay, erro de versão, CSRF, JSON preservado,
  publicação, ofertas, revisão e fallback sem esquema opcional.
- Playwright/Edge em 1440×1000 e 390×844: login dos três papéis, biblioteca,
  navegação/retomada, conclusão, download, rascunho, módulo/capítulo/aula,
  link, publicação/aprovação/oferta e bloqueio do aluno no editor.
- Teclado: foco avança do título da aula para formato. Sem JavaScript após
  autenticação: abrir/navegar mantém gravação da retomada e opção de conclusão.
- Player não cria iframe antes do clique. Teste substitui a resposta do host
  externo: confirma criação sob demanda e URL, **não reprodução real do YouTube**.
  As doze aulas da demo manual não exigem vídeo nem usam IDs fictícios.
- Duas execuções finais de navegador aprovadas, 20 capturas por paleta e zero
  erros JavaScript. Assertivas verificam ausência de overflow e uso do token de
  texto nos avisos. Corrigido contraste dos avisos na paleta clara.
- Protocolo estático e catálogo estrutural aprovados; `git diff --check` limpo.
- Postman: 57 requisições e 65 assertivas aprovadas, incluindo verificação de
  registros e arquivos físicos persistidos na fixture descartável.
- Regressão completa SQLite: 228 testes, 203 aprovados e 25 pulados.
- Regressão completa MySQL: 228 testes, 226 aprovados e dois casos específicos
  de SQLite pulados; inclui concorrência real e os seis testes HTML.
- HTTP real: 117 verificações aprovadas (30 frequência, 33 estudos e 54 cursos),
  com JWT, multipart, permissões e downloads.

Evidências visuais finais: `.ci-results/cursos-visual/2026-11-20T16-01-56-699Z`
(claro/verde) e `2026-11-20T16-02-37-799Z` (escuro/ciano). As capturas e a
comparação estão na [galeria datada](../design/referencias/2026-11-20-cursos-enem/COMPARACAO.md).
Execuções anteriores com falhas de seletores ou contraste não são usadas como
aprovação; a falha inicial da regressão Docker ocorreu com o motor desligado.

Limites: não foi medido desempenho/capacidade sob carga, nem homologada a
instalação persistente ou produção. Login mantém a dependência JavaScript já
existente. Não há editor de texto rico, importação de questões oficiais ou
correção automática dos exercícios; o material usa texto simples escapado.

## Evidência final da regressão

Comando: `python .github/cicd/run_cursos_backend.py --suite regressao`.
Python 3.12 na imagem local `edufast-platform:test`, SQLite em memória e MySQL
8.4 em tmpfs/rede interna; HTTP em fixture distinta, também descartável.
Resultado `.ci-results/cursos-backend/edufast-ms04-7658e579ed/summary.json`:
`passed=true`, `cleaned=true`, `source_unchanged=true`. Logs `sqlite.log`,
`mysql.log`, `http.log`, `http.json` e `cleanup.log` na mesma pasta ignorada.
Fingerprint de fontes/testes Python e scripts HTTP do runner:
`6fdcbbe82c350dd3d243c29dcf07f65c862e6917f41410e5e11edee419130163`.

O manifesto visual registra também o hash de caminhos e bytes de `.py`, `.html`,
`.css` e `.js` em `api/app`:
`d5c3215d9bce5f852406bc858290942292656ff77955252bac379377da3d241a`.
Nenhuma mudança de runtime foi feita após essas validações. O catálogo ainda
mantém cenários parciais para medição de desempenho e aceite manual pelo usuário;
seu estado não substitui os resultados executados.
