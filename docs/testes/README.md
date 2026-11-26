# Evidências de testes

[Mapa das suítes e comandos atuais](../../.github/cicd/tests/README.md): unitários, integração, API, concorrência e fluxos por perfil.

[Diagnóstico de 05/11/2026](DIAGNOSTICO_2026-11-05.md): regressão da versão atual, limites de execução, fluxos HTTP e limitações de cobertura.

[Revisar os testes da próxima versão antes da implementação](proxima-versao/README.md): contratos de API, regras unitárias, migrações, desempenho e execução isolada.

O [CI/CD ativo](../../.github/cicd/README.md) contém os testes atuais. Consulte o [relatório de validação](../../.github/cicd/VALIDACAO.md) e os artefatos de cada execução no GitHub Actions.

Os arquivos `ci2-*.txt`, antes na raiz, estão em [logs-historicos](logs-historicos/). Foram preservados no formato original, incluindo logs UTF-16 e um arquivo de build vazio.

São registros anteriores. Não foram reexecutados nesta organização e não comprovam que todos os cenários passam no código de `api/`.

Relatórios e baselines adicionais estão no [pacote arquivado](../arquivo/ci2/Documentos/testes/). Esse pacote faz referência a uma base mais ampla, com arquivos que não existem na aplicação atual.

Novas evidências devem identificar commit, sistema, banco, dependências, comandos, data e resultado real. Não apresentar totais de outra versão como cobertura atual.
