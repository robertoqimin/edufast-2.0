# Ensaio do roteiro de gravação e correções

Data: 24/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«perf: mede jornadas e corrige gargalos de desempenho (B3)». Pedido do usuário: deixar o
ambiente pronto para gravar um vídeo com o fluxo completo da plataforma e testá-lo antes.
Guia para a gravação: [GRAVACAO_VIDEO_2026-11-25.md](../produto/GRAVACAO_VIDEO_2026-11-25.md).

## Ensaio

O roteiro foi automatizado no Edge, pela interface (formulários reais, com CSRF e sessão),
numa escola vazia criada como a da gravação. Rodadas sucessivas zeraram a escola entre
uma e outra. A rodada final passou nos **37 passos, sem nenhuma falha**:

1. **Supremo:** cadastra a escola.
2. **Operador:** cria o super admin pelo comando oficial `create-admin --super-admin`.
3. **Super admin:**
   - cria professora, admin e dois alunos;
   - cria o calendário com datas;
   - cria a regra do boletim (bimestres, com datas e pesos).
4. **Admin:**
   - cria a disciplina e liga a professora a ela;
   - cria a turma e coloca a professora e os alunos.

   Depois, o **super admin** aplica a regra do boletim à turma.
5. **Professora:**
   - publica 6 materiais: aviso, link de vídeo do YouTube, link de slides, PDF de apostila,
     PDF de slides e imagem PNG;
   - cria um curso com módulo, capítulo, aula de texto, aula de vídeo, PDF e link anexados à
     aula, e pede a publicação.
6. **Secretaria:** aprova as 7 solicitações e libera o curso para a turma.
7. **Aluno:**
   - vê o aviso e os 5 materiais;
   - baixa a apostila (o conteúdo baixado é o PDF original);
   - abre o link do vídeo;
   - abre o curso com a aula de texto e os anexos, e a aula de vídeo com o player.

Estado final conferido no banco: 2 matrículas aluno×disciplina, 6 materiais publicados e
7 solicitações aprovadas.

## Problemas encontrados e corrigidos

1. **Aluno não via materiais nem cursos.** Esse defeito já existia antes de hoje e
   bloquearia o fim do vídeo.
   - O Espaço da disciplina e os cursos exigem que o aluno esteja na turma **e** na disciplina
     (`alunos_disciplinas`), mas **nenhuma tela criava essa matrícula**.
   - **Correção** (`Codigos/app/services/matriculas.py`): o aluno colocado numa turma passa a
     ser matriculado nas disciplinas daquela turma; quando a turma ganha uma disciplina, os
     alunos dela também. Vale nas duas telas de turma (`/admin/turmas` e Gestão acadêmica).
   - **Desmatrícula:** ao sair da turma, o aluno perde só as disciplinas que não cursa em
     outra turma.
   - **Escopo:** nunca concede disciplina de outra turma, e as regras de acesso não mudaram.
   - **Dados antigos:** alunos ligados a turmas antes desta correção, em bancos já existentes,
     não ganham a matrícula automaticamente. Isso só importaria com dados reais, que hoje não
     existem.
2. **Porta bloqueada pelos navegadores.** A primeira porta escolhida para o ambiente de
   gravação (5060) é bloqueada por Edge e Chrome. O padrão passou a ser **5070**.

## Ambiente de gravação

`iniciar-educafast.ps1` ganhou `-Ambiente Gravacao`:
- projeto `edufast-gravacao`, banco `edufast_gravacao` e porta 5070;
- esquema base v8;
- **nenhuma conta pré-criada**, ao contrário do ambiente manual, que cria contas de teste;
- dados persistentes, e reiniciar não apaga nada.

O ambiente manual (5050) e os demais bancos não foram tocados. `scripts/compose.manual.yml`
passou a ler `DB_NAME` do `.env` de cada ambiente, com o mesmo padrão de antes.

Ao fim do ensaio, a escola de gravação foi **zerada** (escola vazia, sem super admin), e o
painel Supremo de demonstração foi reiniciado limpo, para a gravação começar do zero.

## Limitações registradas para o vídeo

- **Supremo:** o painel cadastra a escola no diretório e no financeiro, mas **não sobe a
  instalação nem cria o super admin**. Isso é um comando do operador (decisão de segurança de
  12/11/2026). O painel diz isso na tela.
- **Arquivos:** só PDF, PNG ou JPEG de até 5 MiB; `.pptx` deve ser exportado para PDF ou
  enviado como link. Vídeos são links do YouTube, sem envio de arquivo de vídeo.
- **Boletim:** a regra é aplicada a uma turma existente; no roteiro, a turma é criada depois
  da regra.
- **Aprovação e liberação:** materiais e cursos precisam da aprovação da secretaria, e o
  curso precisa ser liberado para a turma pelo admin.
- **Nome do admin:** a tela de usuários pede nome também para administrador, mas o servidor
  não guarda o nome para esse perfil. É inconsistência menor, registrada para correção futura.
- **Painel Supremo de demonstração:** usa banco em memória. Reiniciar o container volta às
  duas escolas fictícias.

## Testes

**Novo:** `test_matriculas_disciplinas.py`, com 4 casos:
- a tela antiga matricula nas disciplinas;
- o aluno já na turma recebe a disciplina nova;
- Gestão acadêmica: atribuir, matricular e desmatricular, preservando a disciplina de outra
  turma;
- o aluno matriculado pela interface vê as disciplinas.

Sem a correção, os 4 falham; com ela, passam.

**Resultados:**
- suíte completa local: **333 testes** aprovados, em SQLite de arquivo e em memória
  (43 pulados, os mesmos de antes);
- verificador de protocolo de design aprovado;
- regressão em containers (SQLite + PostgreSQL + HTTP): ver abaixo.

| Regressão em containers (`run_cursos_backend.py --suite regressao`) | Resultado |
| --- | --- |
| SQLite | 333 testes aprovados, 43 pulados |
| PostgreSQL + concorrência real | 333 aprovados, 2 pulados |
| HTTP real | 117 verificações aprovadas |
| Fonte inalterado durante a execução | Sim |

O ensaio também foi repetido numa **janela visível do Edge**, a pedido do usuário, com os
mesmos 37 passos aprovados.

Não foi rodada a bateria completa (`ci.py`, piloto, ensaio de atualização, Postman). Esta
entrega não altera imagem, infraestrutura de nuvem, migrations nem os fluxos cobertos por
esses executores. As mudanças são a matrícula nas disciplinas e o novo modo do iniciador
local.
