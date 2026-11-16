# Documentação do EduFast

[Apresentação do projeto](../README.md)

| Documento | Conteúdo |
| --- | --- |
| [Confirmação direta de chamada — 16/11](testes/CHAMADA_DIRETA_2026-11-16.md) | MS01: confirmação docente, correção com histórico, testes atuais e limites de MySQL |
| [Primeira versão — ensino médio e superior](planejamento/ENSINO_MEDIO_SUPERIOR_2026-11-16.md) | Turmas, confirmação docente de presença, materiais, abas, cursos modulares e entregas com testes |
| [Preparação para entrega — 16/11/2026](planejamento/PREPARACAO_ENTREGA_2026-11-16.md) | Mapa funcional, diretrizes propostas, prioridades, agenda da semana e critérios de liberação |
| [Protocolo de design](PROTOCOLO_DESIGN.md) | Layout, tokens, acessibilidade e portões de entrega |
| [Galeria visual preservada](design/README.md) | Prints desktop/celular e manifesto das referências |
| [Organização do Git](design/ORGANIZACAO_GIT.md) | Escopo dos commits, arquivos locais e revisão |
| [Entrega da restauração](testes/ENTREGA_RESTAURACAO.md) | Resultados executados e pendências conhecidas |
| [Arquitetura](arquitetura/ARQUITETURA.md) | Camadas, dados, requisições e evolução |
| [Estudo para várias escolas](arquitetura/ESTUDO_MULTIESCOLAS.md) | Estratégias de isolamento, organização dos dados, disponibilidade e evolução |
| [Instâncias por cliente — plano de aplicação](planejamento/INSTANCIAS_POR_CLIENTE_2026-11-11.md) | Mapeamento de banco, backend e frontend próprios, ações e critérios de aceite |
| [Duas escolas de teste](testes/DUAS_ESCOLAS_TESTE_2026-11-11.md) | Teste 01 e Teste 02, com 20 alunos, 5 professores e 3 matérias cada; acessos locais e evidências |
| [Frequência e atestados](testes/FREQUENCIA_2026-11-12.md) | Chamadas docentes com aprovação, faltas justificadas, relatório e migration para revisão |
| [Testes de API de frequência](testes/API_FREQUENCIA_2026-11-12.md) | Runner reproduzível em SQLite/MySQL e HTTP real, contratos e resultados |
| [Ambientes locais, nuvem e híbridos](../infra/README.md) | Geração de ambientes por escola, limites de tráfego e modelo de recuperação |
| [Revisão antes do commit](testes/REVISAO_PRE_COMMIT_2026-11-04.md) | Testes atuais, preservação visual e ambiente para avaliação manual |
| [Telas e UX/UI](produto/TELAS_E_UX.md) | Telas existentes, protótipos e critérios de experiência |
| [Execução](operacao/EXECUCAO.md) | Ambiente, configuração, comandos e persistência |
| [CI/CD e produção](../.github/cicd/README.md) | Testes, imagem, deploy e recuperação |
| [Roadmap](planejamento/ROADMAP.md) | Etapas, dependências e critérios de entrega |
| [Próxima versão](planejamento/PROXIMA_VERSAO.md) | Acadêmico e secretaria para várias escolas; isolamento, migração e backlog |
| [Desempenho](planejamento/DESEMPENHO.md) | Experiência em hardware modesto, orçamento de recursos e testes de carga |
| [Testes para revisão](testes/proxima-versao/README.md) | API, unitários e integração preparados antes da implementação |
| [Concorrência e repetição](testes/CONCORRENCIA.md) | Correções, comparação com a base, regressão e coleção Postman |
| [Planejamento anterior](planejamento/PLANEJAMENTO_EDUCAFAST.md) | Proposta histórica de cursos e gestão acadêmica |
| [Histórico de testes](testes/README.md) | Origem e limites dos logs preservados |
| [Arquivo CI2](arquivo/README.md) | Pacote histórico e suas dependências |

## Referências originais

O [painel do proprietário](planejamento/PAINEL_SUPREMO_2026-11-12.md) reúne escolas,
pessoas e financeiro; consulte também o [relatório de validação](testes/PAINEL_SUPREMO_2026-11-12.md).

Os documentos abaixo foram preservados como fontes históricas. Podem usar a identidade anterior “Secretaria Escolar DF” e não substituem a descrição atual do código.

- [Arquitetura original em PDF](Documentação%20de%20Arquitetura%20do%20Sistema.docx%20%2814%29.pdf)
- [Arquitetura em DOCX](documentacao-arquitetura-secretaria-df.docx)
- [Casos de uso em Markdown](Especificação%20de%20Casos%20de%20Uso.md)
- [Casos de uso em PDF](Especificação%20de%20Casos%20de%20Uso.pdf)
- [UX/UI em DOCX](Documentacao_UX_UI_SecretariaDF.docx)
- [Relatório de API em DOCX](relatorio-api-secretaria-df.docx)
- [Plano de negócios original](plano%20de%20negócios)

Mantenha documentação técnica em `arquitetura`, decisões de experiência em `produto`, instruções de execução em `operacao` e propostas futuras em `planejamento`. Resultados de novos testes devem informar commit, ambiente, comando e data, sem sobrescrever evidências históricas.
