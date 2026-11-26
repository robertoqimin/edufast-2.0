# Revisão antes do commit — 04/11/2026

Pedido: executar funcionalidades, API, regressão e Postman; preservar design;
disponibilizar o programa para avaliação manual antes de commit/push.

Base: `fb840c6ce1de4ea073339e8bcc8b1e865e466eeb` com alterações locais de
ambientes independentes. Nenhum commit ou push autorizado antes do "ok" do usuário.
Remoto conferido: `origin`, `https://github.com/Samucau1/edufast-2.0.git`.

## Resultados desta rodada

| Verificação | Resultado |
| --- | --- |
| Comparação com HEAD: API anterior | 18 testes aprovados |
| Contratos adicionais de API em SQLite | 28 testes: 15 aprovados, 13 dependentes de MySQL ignorados |
| Regressão da API existente após os contratos adicionais | 18 testes aprovados |
| CI completo com Python 3.12 em containers | Aprovado: 99 testes MySQL; SQLite com 84 aprovados e 15 específicos de MySQL ignorados |
| HTTPS, CA, HSTS, login, backup/restauração e persistência dos uploads | Aprovados no ambiente descartável desta rodada |
| Bloqueios e cenários de deploy | 11 testes aprovados dentro da imagem Linux |
| Postman/Newman em servidor HTTP descartável | 57 requisições e 65 asserções aprovadas; registros e arquivos físicos conferidos |
| Node: ambientes e proteção de envio | 8 testes aprovados |
| Caracterização do executor de CI | 7 testes aprovados |
| Infraestrutura de contratos futuros | 5 testes aprovados; funcionalidades futuras não executadas |
| Iniciador manual com Docker simulado | Asserções de configuração, preservação, esquema explícito e falhas aprovadas |
| Compose de duas escolas | Configuração aprovada |
| Nginx 1.30.6 em container com certificado sintético | `nginx -t` aprovado |
| Gunicorn na imagem Linux construída | `--check-config -c /app/gunicorn.conf.py` aprovado |
| Sintaxe de `infra/verify.sh` | `bash -n` aprovado |
| Protocolo estático de design | Aprovado |
| Navegador: login, quatro perfis, modais, aprovação, personalização e acesso negado | Aprovado em 1440×1000 e 390×844; 23 capturas, zero erros JavaScript e zero rolagem horizontal da página |
| Sonda de `/healthz` em localhost:5050 | 100 respostas HTTP 200, concorrência 4; não representa carga acadêmica |
| Templates e estáticos | Nenhuma alteração no diff contra HEAD |
| Manifesto histórico r2 | 23 hashes preservados |

## Preservação visual

O teste de navegador usou SQLite em memória e contas fictícias em servidor separado
na porta 5052. A personalização clara é exercitada e restaurada nesse ambiente;
não foi alterada a configuração visual do banco manual que o usuário vai avaliar.
O script de navegador versionado foi copiado para `.ci-results/` apenas para apontar
a saída para uma pasta nova desta rodada. Nenhum template, CSS, JavaScript do produto
ou captura histórica foi editado.

Capturas atuais: `.ci-results/visual-pre-revisao/`, com `resumo.json`,
`manifesto-atual.json` e comparação SHA-256 em `comparacao-r2.json`.
De 23 capturas, 10 são idênticas em bytes à referência r2; as demais não são idênticas.
Dados dinâmicos e instantes da captura impedem usar hash diferente como diagnóstico
isolado de regressão. Inspeção direta incluiu login, usuários e painel administrativo
em desktop/móvel, além da comparação da tela de usuários com a referência r2.
Não se declara equivalência pixel a pixel de todos os pares nem aprovação do usuário.

## Ambiente disponível para revisão do usuário

- URL: `http://localhost:5050` — iniciador restaurado, código atual, MySQL isolado.
- Projeto: `edufast-manual-restaurado`; banco, senhas e permissões existentes preservados.
- Contas fictícias: `superadmin@teste.local`, `admin@teste.local`,
  `professor@teste.local`, `aluno@teste.local`.
- Senha inicial pública de demonstração: `Teste-local-2026!`, somente se não alterada.
- Navegador aberto na URL; ambiente permanece disponível após os testes.
- Nenhuma migration executada em banco existente; o iniciador validou o esquema.

Sugestão de avaliação: entrar nos quatro perfis, conferir menus e painéis, abrir
usuários/aprovações com superadmin e conferir turmas, disciplinas, documentos e
comunicados com admin. Reduzir a janela para conferir navegação móvel. Mudanças
docentes devem seguir o fluxo de aprovação existente.

## Evidências locais e limites

Logs em `.ci-results/ci-pre-revisao.log`, `.ci-results/regressao-pre-revisao.log`,
`.ci-results/postman-pre-revisao.log`, `.ci-results/visual-pre-revisao.log` e
`.ci-results/manual-pre-revisao.log`; arquivos locais ignorados pelo Git.
Postman: `.ci-results/mutations/postman.json`; comparador:
`.ci-results/mutations/summary-sqlite.json`.

A sonda de saúde não testa throughput de login, notas ou arquivos. Esta rodada não
homologa capacidade de produção, failover híbrido ou sincronização entre bancos.
O CI utiliza bancos/volumes descartáveis e a revisão manual usa ambiente separado.

## Fechamento do CI completo

Execução concluída com código 0. Resumo efetivo conferido em
`.ci-results/summary.json`: `passed: true`, projeto `edufast-ci-f4e1ef6fb5`.
Imagem construída e testada: `edufast-ci-f4e1ef6fb5:tested`, Python 3.12.
MySQL: 99 testes aprovados em 382,049 s. SQLite: 99 descobertos, 84 aprovados e
15 ignorados em 29,131 s. Os testes de deploy somaram mais 11 aprovações.

O smoke HTTPS validou a release, confiança da CA, rejeição de CA não confiável,
cookie seguro, HSTS e login. O banco descartável foi exportado/restaurado e os
uploads persistiram após recriação da aplicação. O executor removeu somente os
containers, redes e volumes do projeto de CI; o ambiente manual permaneceu saudável.

Esta é aprovação técnica local da rodada descrita, não publicação da imagem nem
aprovação visual do usuário. Alguns testes emitiram `ResourceWarning` de arquivos
de resposta não fechados; não impediram a execução. Não houve correção de design.

## Publicação

O usuário respondeu "ok" em 04/11/2026 após disponibilização do programa e dos
resultados, autorizando commit e push. Essa aprovação encerra a espera registrada
acima; não representa implantação em produção.
Não incluir `.env`, bancos, uploads, chaves, logs nem `.ci-results` no commit.
