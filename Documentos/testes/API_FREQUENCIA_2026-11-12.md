# Testes de API de frequência — 12/11/2026

Migração das escolas permanece adiada por solicitação do usuário. Os testes abaixo
criam seus próprios ambientes descartáveis; não conectam às escolas Teste 01/02.

## Executar

Na raiz, com Docker, Compose e Node 20+:

```powershell
node .github/cicd/run_frequencia_api.cjs
```

O comando constrói imagem de teste, executa a suíte em SQLite e MySQL e inicia um
servidor HTTP temporário com massa fictícia. O runner não aceita URL, conexão de
banco ou manifesto externos. Cada execução usa projeto/containers/volumes com ID
aleatório, sem portas MySQL publicadas; o servidor HTTP usa porta aleatória no
loopback. Os recursos de runtime são removidos ao concluir, inclusive em falha.
Imagens construídas ficam no cache local do Docker.

Para reutilizar a imagem local de homologação:

```powershell
node .github/cicd/run_frequencia_api.cjs --image edufast-frequencia:test
```

O CI pode passar a imagem `edufast-ci-<10 hex>:tested` que acabou de construir.
O workflow `cloud-instances.yml` executa o mesmo runner. Os resultados e logs
ficam em `.ci-results/frequencia-api/<id>/`, ignorado pelo Git. Segredos temporários
ficam fora dessa pasta de relatórios; não são impressos nem incluídos no resumo.
Não confundir `--image` com aprovação para publicar a imagem em produção.

## Camadas e resultado desta execução

| Camada | Execução | Resultado |
| --- | --- | --- |
| API Flask + SQLite | `test_frequencia.py` | 25 descobertos: 23 aprovados, 2 ignorados por exigirem MySQL |
| API Flask + MySQL 8.4 | Mesma suíte e banco novo real | 25 aprovados, inclusive concorrência; nenhum ignorado |
| HTTP por socket + SQLite | `frequencia_http.cjs` | 27 verificações aprovadas: JSON, multipart, download e CSV |
| Contratos futuros pendentes | `next_stage.py --check` | 5 verificações de consistência aprovadas; não executa/homologa os 90 contratos futuros |

Execução local: imagem `edufast-frequencia:test`, projeto
`edufast-freq-api-b391acdd1a`. SQLite em 11,186 s e MySQL em 84,276 s.
O resumo registrou sucesso e limpeza dos recursos. A camada MySQL usa o cliente
de testes do Flask com persistência real; a camada HTTP externa usa SQLite em
container. Não afirmar que as 27 verificações de socket foram executadas em MySQL.

## Contrato exercitado

Login é real por `POST /login`. Chamadas e decisões de API usam Bearer e
`Idempotency-Key`. Formulários de navegador continuam exigindo CSRF. Headers de
idempotência são opacos e não devem ser reutilizados para conteúdo diferente.

| Método e caminho | Cenário principal | Esperado |
| --- | --- | --- |
| `POST /frequencia/chamadas` | Professor vinculado envia elenco completo, presente/falta | 201, pendente |
| Mesmo caminho | Elenco incompleto, aluno externo, situação inválida, data futura ou aula fora de 1–20 | 400, sem chamada |
| Mesmo caminho | Professor de outra oferta ou aluno tenta lançar | 403 |
| Mesmo caminho | Falta chave de idempotência | 428 |
| Mesmo caminho | Reenvio com mesma chave/conteúdo | Mesmo ID e resposta, sem duplicação |
| Mesmo caminho | Outra chamada pendente na mesma aula ou chave com outro conteúdo | 409 |
| `GET /frequencia/chamadas/{id}?formato=json` | Conferência da chamada dentro do escopo | Estado, versão e marcações |
| `POST /frequencia/chamada/{id}/decidir` | Admin decide com versão atual e motivo | 200 |
| Mesmo caminho | Professor decide, versão antiga, registro já decidido, turma arquivada ou vínculo revogado | Recusa 403/409 conforme caso |
| `POST /frequencia/atestados?formato=json` | Multipart: aluno próprio, início/fim e arquivo fictício | 201, pendente |
| Mesmo caminho | Arquivo ausente, assinatura inválida ou mais de 5 MiB | 400, sem arquivo persistido |
| `POST /frequencia/atestado/{id}/decidir` | Admin aceita/rejeita com versão e motivo | 200; aceite não transforma falta em presença |
| `GET /frequencia/atestados/{id}/arquivo` | Titular ou admin | 200, attachment, no-store e conteúdo cifrado em disco |
| Mesmo caminho | Professor ou outro aluno | 404 |
| `GET /frequencia/relatorio?formato=json` | Datas e escopo autorizados | Totais e detalhamento só de chamadas aprovadas |
| Mesmo caminho | Aluno | Somente seus registros |
| `GET /frequencia/relatorio?formato=csv` | Admin | CSV com período e proteção contra células de fórmula |
| Mesmo caminho | Professor | 403 |
| `GET /frequencia?formato=json` | Sem autenticação / Bearer inválido | 403 / 401 |
| Mesmo caminho | Esquema do módulo ausente | 503, sem criar tabelas nem interromper login |

## Garantias adicionais verificadas

- Atribuição explícita ativa prevalece sobre os pares legados; conta docente
  pendente/inativa não grava usando token anterior.
- Correção só substitui chamada vigente depois de aprovada; rejeitar correção
  preserva o relatório anterior.
- Repetir decisão idempotente não reaplica efeitos; outra decisão conflita.
- Atestado rejeitado preserva falta não justificada; atestado aceito antes da
  aprovação da chamada também é considerado depois.
- A falta justificada permanece no total de faltas e não aumenta presença.
- Duas aulas com uma presença resultam em 50,00%; detalhes identificam turma e matéria.
- Falha no fechamento do envio de atestado reverte banco e remove o arquivo criado.
- Duas propostas simultâneas geram uma pendência; duas decisões simultâneas geram
  uma aprovação. Esses dois casos rodam apenas em MySQL, sem simular locks.

Não foram executadas migrations nas escolas, teste de carga, validação médica ou
antivírus. A execução de contratos futuros permanece separada: documentos de
`proxima-versao/` são propostas para revisão, não capacidade funcional entregue.
