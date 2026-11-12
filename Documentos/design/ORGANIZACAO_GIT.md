# Organização da entrega de restauração

## O que deve ser versionado

- Código, dependências locais de interface e respectivas licenças.
- Testes, verificador do protocolo e workflows.
- Documentação, galeria visual e manifesto das capturas.
- Migration proposta, claramente identificada como pendente de revisão.

## O que permanece local

`.env`, `.ci-results/`, caches, arquivos enviados, bancos, backups, chaves e logs.
O `.gitignore` já protege esses caminhos. Não publicar credenciais de infraestrutura
nem copiar o resumo antigo de um teste como aprovação da entrega atual.

## Commits e revisão

Manter a restauração numa branch própria e publicar para revisão. A unidade de
commit do código precisa incluir os modelos, rotas, serviços, templates e testes
dos quais depende: não criar uma revisão intermediária que importe arquivos ausentes.
Separar em seguida a documentação e as referências visuais, quando possível.

Antes do push, conferir os arquivos staged, `git diff --cached --check`, testes
executados, pendências registradas e ausência de segredos. Não fazer force push,
não apagar branches existentes e não alterar a `main` automaticamente.

A publicação em branch de revisão não aplica a migration
`003_restauracao_educafast.sql`. A execução em banco existente continua dependendo
da revisão explícita do usuário.
