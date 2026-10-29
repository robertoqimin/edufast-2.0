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

```powershell
python .github/cicd/run_postman.py --newman CAMINHO/para/newman/bin/newman.js
```

O executor usa Newman instalado separadamente, cria servidor HTTP local e SQLite
temporários e verifica também os registros e arquivos finais. Não lê o `.env` como
destino e não executa migrations. A senha sintética fica apenas no ambiente temporário.

A coleção verifica contratos HTTP, repetição sequencial, conflito de conteúdo e
versões antigas. Os testes com duas requisições simultâneas estão em
`.github/cicd/tests/test_concurrency.py` e precisam de MySQL descartável.

Para regenerar os JSONs: `python .github/cicd/build_postman.py`.
