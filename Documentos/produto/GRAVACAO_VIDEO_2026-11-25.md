# Roteiro e ambiente para a gravação do vídeo

Preparado em 24/11/2026 e ensaiado de ponta a ponta no Edge, pela interface, com o código
atual (37 passos aprovados). Use somente dados fictícios na gravação.

## Antes de gravar

1. Abra o **Docker Desktop** e espere ficar pronto.
2. No PowerShell, na pasta do projeto:

   ```powershell
   .\iniciar-educafast.ps1 -Ambiente Gravacao -SemNavegador
   node infra/platform-demo.cjs start
   ```

   | O quê | Endereço | Acesso |
   | --- | --- | --- |
   | Painel Supremo (demonstração) | http://127.0.0.1:5093/login | `dono@plataforma.local` / `Plataforma-teste-2026!` |
   | Escola (vazia, sem contas) | http://localhost:5070 | criada no passo 2 do roteiro |

3. Teste rápido: abra os dois endereços no Edge. Os dois precisam mostrar a tela de login.

**Por que a porta 5070:** os navegadores bloqueiam a 5060. A escola do vídeo é separada do
ambiente manual (5050) e dos seus outros bancos; nada do que você criar mexe neles.

**Arquivos que valem a pena separar:**
- PDF, PNG ou JPEG de **até 5 MB** (apostilas, slides, imagens).
- **Slides:** exporte o PowerPoint para **PDF**. Arquivos `.pptx` não são aceitos. Também dá
  para usar um **link** dos slides (Google Slides, por exemplo).
- **Vídeos:** são **links do YouTube**. Não há envio de arquivo de vídeo.
- **Textos:** viram um "aviso" no Espaço da disciplina ou uma "aula de texto" no curso.

**Senhas:**
- professor e aluno: pelo menos 6 caracteres, com **um caractere especial** (ex.: `Prof-2026!`);
- admin e super admin: pelo menos **12** caracteres, com um especial (ex.: `Secretaria-2026!`).

## Roteiro

### 1. Supremo cadastra a escola

Entre no painel Supremo e preencha o cadastro de escola: nome, identificador (letras
minúsculas e hífen, ex.: `colegio-horizonte`), domínio e mensalidade.

**O que dizer no vídeo:** o painel responde "Escola cadastrada. **A ativação ainda precisa
ser concluída**". O Supremo registra a escola no diretório e no financeiro; a instalação e o
primeiro acesso da escola são ativados pelo operador. Esse é o próximo passo.

### 2. Ativar o super admin da escola (terminal)

```powershell
.\iniciar-educafast.ps1 -Ambiente Gravacao -Acao CriarAdmin -SuperAdmin
```

O comando pede o e-mail e a senha duas vezes; a senha não aparece na tela. Esse é o
comando real do operador. Na nuvem, ele roda no servidor da escola.

### 3. Super admin (http://localhost:5070)

- **Usuários e permissões → Novo usuário:** escolha o tipo e crie
  - o **Professor** (nome, e-mail, senha e CPF);
  - o **Administrador** (o campo nome também aparece; preencha);
  - os **Alunos** (nome, e-mail, senha e matrícula).
- **Regras e identidade da escola:**
  - **Criar calendário:** ano, nome, primeiro e último dia, dias da semana letivos e meta
    de dias. Depois use **Adicionar datas** (feriado, recesso, reposição).
  - **Regras do boletim → Criar versão das regras:** escolha o calendário, a divisão
    (bimestres, trimestres ou semestres), a média de referência, as casas decimais e as
    datas e pesos de cada período.
  - A regra só pode ser **aplicada a uma turma depois que a turma existir** (passo 4). Volte
    aqui depois e use **Aplicar regra e criar os períodos**.

### 4. Admin (entre com a conta de admin criada no passo 3)

1. **Disciplinas:**
   - **Cadastrar Disciplina** (ex.: Matemática);
   - em **Associar Professor**, ligue a professora à disciplina.
2. **Turmas:**
   - crie a turma (nome, código, ano letivo e turno);
   - associe a professora à turma;
   - associe cada aluno à turma. O aluno entra automaticamente nas disciplinas da turma.
3. (Opcional) Volte como **super admin** e aplique a regra do boletim à turma.

### 5. Professora

- **Espaço da disciplina →** escolha a disciplina e a turma **→ Preparar conteúdo:**
  - **Aviso:** texto para a turma;
  - **Link:** vídeo do YouTube ou slides online;
  - **Arquivo:** PDF, PNG ou JPEG.

  Em cada conteúdo, clique **Enviar para publicação**. Ele fica em rascunho, visível só para
  a professora, até a secretaria aprovar.
- **Meus cursos → Criar novo curso:**
  - escolha a disciplina, o título e a apresentação;
  - no editor, adicione um **módulo** e um **capítulo**, e depois **Nova aula de texto** e
    **Nova aula de vídeo** (cole o link do YouTube);
  - em cada aula, use **Enviar arquivo** (PDF ou imagem) e **Adicionar link**;
  - no fim, **Solicitar publicação**.

### 6. Admin aprova e libera — **não pule este passo**

Sem ele, o aluno não vê nada, e é esse o comportamento esperado: tudo o que o professor
publica passa pela secretaria.

1. **Solicitações e aprovações:** **Aprovar e aplicar** cada material e o curso.
2. **Meus cursos →** abra o curso **→** no bloco de turmas, escolha **1º ano A → Liberar**.
   A liberação do curso para a turma é feita pelo admin.

### 7. Aluno

- **Espaço da disciplina →** Matemática: aba **Avisos** e aba **Materiais de estudo**.
  Ao abrir um arquivo, ele é baixado; um link abre o vídeo ou os slides.
- **Meus cursos → Continuar estudando:**
  - a aula de texto e os anexos aparecem na tela;
  - na aula de vídeo, **Carregar vídeo do YouTube** carrega o player (o YouTube só é acionado
    depois desse clique, por privacidade);
  - **Marcar como concluída** registra o progresso.

## Se algo der errado na hora

| Situação | O que fazer |
| --- | --- |
| A escola não abre | `.\iniciar-educafast.ps1 -Ambiente Gravacao -SemNavegador` (os dados são mantidos) |
| O painel Supremo não abre | `node infra/platform-demo.cjs start`. Ele recomeça com as duas escolas fictícias, sem o seu cadastro |
| O aluno não vê o material ou o curso | Confira o passo 6: aprovar em **Solicitações e aprovações** e **Liberar** o curso para a turma |
| "Arquivo inválido" | Use PDF, PNG ou JPEG de até 5 MB |
| Senha recusada | Inclua um caractere especial; admin e super admin precisam de 12 caracteres |
| Quer recomeçar a escola do zero | Peça para eu zerar o ambiente de gravação; isso apaga só essa escola |

Detalhes técnicos e evidências do ensaio: [relatório](../testes/ENSAIO_GRAVACAO_2026-11-24.md).
