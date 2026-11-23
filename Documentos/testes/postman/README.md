# Postman — concorrência e repetição

Importar `EduFast.postman_collection.json` e `EduFast.postman_environment.json`.
Usar **somente banco sintético**, com aluno/professor, turma, disciplina e vínculos
da fixture de testes. Preencher URL, credenciais e IDs; nenhuma senha real é distribuída.
Desabilitar redirecionamentos automáticos para conferir os HTTP 302.

O fluxo altera cadastros e notas, cria comunicados, solicitações, atividades e arquivos.
Selecionar este repositório como diretório de trabalho e permitir leitura do arquivo
`Documentos/testes/postman/arquivo.txt`. Os IDs de solicitação precisam estar pendentes
e a nota precisa estar ausente ao iniciar. Para repetir a coleção inteira, recriar
somente o banco descartável; não limpar um banco existente.

Executar tudo de forma isolada, sem preparar banco manualmente:

O CI principal já executa este fluxo antes da publicação da imagem. Para instalar
o executor versionado localmente, executar `npm ci` em `.github/cicd/http` (Node 22+).
Na raiz, usar o caminho `.github/cicd/http/node_modules/newman/bin/newman.js` no
comando abaixo. As dependências Python de `Codigos/requirements.txt` devem estar
instaladas no interpretador utilizado.

```powershell
python .github/cicd/run_postman.py --newman CAMINHO/para/newman/bin/newman.js
```

O executor usa Newman instalado separadamente, cria servidor HTTP local e SQLite
temporários e verifica também os registros e arquivos finais. Não lê o `.env` como
destino e não executa migrations. A senha sintética fica apenas no ambiente temporário.

A coleção verifica contratos HTTP, repetição sequencial, conflito de conteúdo e
versões antigas. Os testes com duas requisições simultâneas estão em
`.github/cicd/tests/test_concurrency.py` e precisam de PostgreSQL descartável.

Para regenerar os JSONs: `python .github/cicd/build_postman.py`.

Os envios docentes agora criam propostas: a coleção entra como admin para
autorizar notas, atividade e resposta documental antes de conferir seus efeitos.
Repetir a mesma chave após aprovação não cria outro documento; outra chave para
a solicitação documental já concluída recebe conflito. O executor confere quatro
propostas aprovadas e a nota final, além das contagens anteriores.

A coleção também verifica o superperfil restaurado: admin comum recebe 403,
o superperfil lê o formulário protegido por CSRF, cria um administrador sem duplicar
na repetição e salva identidade institucional com rejeição de versão desatualizada.
O executor provisiona esse superperfil somente na sua fixture descartável.
