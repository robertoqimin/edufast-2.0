# Regressão, Postman e revisão de segurança

Data: 22/11/2026. Branch `feature/melhoria-dezembro`, commit
«feat: adiciona aplicador revisado de migrations e ensaio de atualizacao (A4)».
Pedido do usuário: commit do que já foi feito, teste de regressão, Postman e conferência da
segurança atual da aplicação. **Esta etapa não alterou código:** registra resultados e achados.

## Commit

Todo o trabalho já estava no GitHub: o branch local era igual ao remoto. A única pendência
local é `.vscode/settings.json`, configuração pessoal do editor, que não foi versionada.

## Regressão

`python .github/cicd/run_cursos_backend.py --suite regressao`, com a imagem de teste reconstruída.

| Banco | Resultado |
| --- | --- |
| SQLite | 291 aprovados, 43 ignorados (casos exclusivos de PostgreSQL) |
| PostgreSQL, com concorrência real | **291 aprovados, 2 ignorados** (concorrência do painel central, coberta pelo runner próprio) |
| HTTP real (JWT, multipart, download) | 117 verificações aprovadas |

Fonte inalterada durante a execução; limpeza dos containers ok.

## Postman

`run_postman.py` nos dois bancos: **57 requisições, 65 asserções, 0 falhas** em SQLite e em
PostgreSQL, com registros persistidos e arquivos físicos conferidos.

## Revisão de segurança — método

1. **Dependências:** `pip-audit` consultou bases públicas de vulnerabilidades, enviando apenas
   nomes e versões dos pacotes.
2. **Análise estática:** `bandit` em `Codigos/` (fora o legado MySQL).
3. **Revisão manual:** autenticação, sessão, JWT, CSRF, senhas, uploads e downloads, SQL
   dinâmico, cabeçalhos HTTP, templates.
4. **Sondagem real** contra o ambiente manual local (loopback, dados fictícios), sem gravar
   dados: só leituras, logins e envios que param na validação ou na proteção CSRF.

Evidências locais: `.ci-results/regressao-seguranca-2026-11-22/` (pip-audit e bandit em JSON).

## Achados

Ordem por gravidade. "Confirmado" significa reproduzido na sondagem real.

### Alta

| # | Achado | Evidência | Recomendação |
| --- | --- | --- | --- |
| S1 | **Login da aplicação escolar sem limite de tentativas.** A tabela `limites_login` existe (proposta 003), mas nenhum código a usa. O limite do Nginx por IP (20/s) não impede adivinhação de senha | Confirmado: 30 senhas erradas seguidas, todas 401; a correta entrou em seguida | Bloqueio progressivo por conta e por IP usando `limites_login`, como o painel Supremo já faz (5 falhas, 15 min) |
| S2 | **`cryptography` 45.0.7 com 9 vulnerabilidades conhecidas**, entre elas o OpenSSL embutido nas wheels (GHSA-537c-gmf6-5ccf) e leitura além do buffer em `Hash.update()` com buffers não contíguos. `requirements.txt` limita a `<46` | pip-audit | Atualizar para a 50.x (ou ao menos 48.0.1), conferindo Fernet e os arquivos cifrados com a regressão |

### Média

| # | Achado | Evidência | Recomendação |
| --- | --- | --- | --- |
| S3 | **Sem proteção contra enquadramento (clickjacking) e sem Content-Security-Policy**, nem na aplicação, nem no Caddy, nem no Nginx da frota | Confirmado nos cabeçalhos da página; Caddyfile e gerador do Nginx | `frame-ancestors 'none'` / `X-Frame-Options: DENY` e uma CSP compatível com os scripts locais (os templates novos já evitam scripts inline) |
| S4 | **Cadastro público aceita qualquer senha não vazia** (até 1 caractere). Só a criação de admin exige 12 | `cadastrar_usuario` sem verificação de tamanho | Mínimo de 12 caracteres em todos os cadastros e na troca de senha |
| S5 | **Flask 3.1.0** com 2 vulnerabilidades: `Vary: Cookie` ausente em alguns acessos à sessão (cache intermediário pode guardar páginas de usuário logado) e chave alternativa usada para assinar | pip-audit | Atualizar para Flask 3.1.3 |
| S6 | **Login revela se a conta existe:** 404 "Usuário não encontrado" para e-mail desconhecido e 401 para senha errada | Confirmado | Mesma resposta (401, mensagem genérica) nos dois casos |
| S7 | **Gateway Nginx da frota só envia HSTS**; o Caddy da instalação única também envia `nosniff` e `Referrer-Policy` | `infra/generate.cjs` | Igualar os cabeçalhos no Nginx (junto com S3) |

### Baixa

| # | Achado | Observação |
| --- | --- | --- |
| S8 | Token CSRF só é exigido quando o navegador envia `Origin`. Confirmado: sem `Origin` e sem token, um POST de admin chegou à validação (200) | Mitigado por `SameSite=Lax` (o cookie não acompanha POST de outro site) e pela recusa de `Origin` estranha ou `Sec-Fetch-Site: cross-site` (403 confirmados). Recomendação: exigir o token em todo POST com sessão |
| S9 | Upload de documentos aceita qualquer tipo de arquivo e grava sem criptografia (os módulos novos cifram) | O download é forçado como anexo com `nosniff`, então não vira XSS no sistema; o risco é distribuir arquivo malicioso. Recomendação: lista de tipos permitidos e verificação do conteúdo |
| S10 | Logout por GET | Permite deslogar alguém por um link; impacto pequeno |
| S11 | Mesma `SECRET_KEY` assina sessões e JWT; o JWT carrega o e-mail | Separar as chaves e reduzir o conteúdo do token |
| S12 | python-dotenv 1.0.1 (`set_key`/`unset_key` seguem links simbólicos) | O projeto não usa essas funções; atualizar para 1.2.x junto com as demais |
| S13 | Cabeçalho `Server` revela a versão do Werkzeug no ambiente manual | Servidor de desenvolvimento, só local; a produção usa Gunicorn atrás do proxy |

### Itens do bandit que não são vulnerabilidade

- 7 "possível SQL injection": os valores vêm do catálogo do banco ou dos modelos, ou são literais
  validados por expressão regular (`literal_registro`, `sql_checksum_base`). Nenhum vem do usuário.
- 1 "escuta em todas as interfaces" (demo ENEM): é dentro do container, e a porta é publicada
  só no loopback.
- 3 "senha no código": credenciais públicas e documentadas das demonstrações locais.

## O que está bem

- **Segredos:** `SECRET_KEY` fraca ou de exemplo é recusada; debug proibido fora de
  desenvolvimento; `TRUSTED_HOSTS` obrigatório em produção; um único proxy confiável.
- **JWT:** assinatura conferida antes de ler o conteúdo, em tempo constante; algoritmo fixo;
  expiração; revogação consultada no banco a cada requisição (`auth_version`).
- **Sessão:** cookie `HttpOnly` e `SameSite=Lax`, `Secure` em produção; logout e mudança de
  permissão revogam sessões.
- **Controle de acesso:** confirmado na sondagem que rota de admin sem login e com conta de aluno
  é recusada (403); download conferindo o dono do arquivo; tentativa de sair da pasta
  (`../../etc/passwd`) recusada (404).
- **CSRF:** origem estranha e `Sec-Fetch-Site: cross-site` recusadas (403 confirmados); token
  exigido quando há `Origin`.
- **Banco:** papel da aplicação sem superusuário; acesso só pela rede interna; SQL dinâmico
  restrito a nomes de catálogo e literais validados; registro de versões e recusa de esquema
  incompatível.
- **Senhas:** hash do Werkzeug; `create-admin` exige 12 caracteres; painel Supremo com bloqueio
  após 5 falhas.
- **Arquivos:** nomes sanitizados com prefixo aleatório; limite de 16 MB; respostas privadas,
  sem cache e com `nosniff`; módulos novos cifram em repouso.

## Próximo passo sugerido

Corrigir S1–S7 numa etapa própria, com testes para cada item (incluindo a sondagem acima
automatizada) e a bateria completa, antes da revisão das migrations (A5). Nenhum código foi
alterado nesta etapa.
