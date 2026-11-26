# Correções de segurança S1–S7

Data: 23/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«docs: registra regressao, Postman e revisao de seguranca».
Corrige os achados de [Regressão, Postman e segurança](REGRESSAO_SEGURANCA_2026-11-22.md),
com as decisões do usuário em 23/11/2026.

## O que foi feito

| # | Achado | Decisão / correção |
| --- | --- | --- |
| S1 | Login sem limite de tentativas | **5 falhas seguidas bloqueiam a conta por 15 minutos**, inclusive a senha correta (429 com `Retry-After`). Limite por IP mais alto (30), porque uma escola inteira costuma sair pelo mesmo IP: serve contra quem testa muitas contas. Usa a tabela `limites_login` já existente (proposta 003), sem migration nova. Guarda só HMAC-SHA256 (com a `SECRET_KEY`) do e-mail e do IP. Contagem atômica e limpeza das linhas vencidas pelo índice da tabela |
| S2 | `cryptography` 45.0.7 com 9 vulnerabilidades | Atualizada para `>=48.0.1,<51` (instalada: 50.0.2). **Compatibilidade verificada:** texto cifrado com Fernet na 45.0.7 foi decifrado na 50.0.2 |
| S3 | Sem proteção contra clickjacking e sem CSP | Módulo `api/seguranca_http.py`, ligado na escola e no painel central: CSP com **nonce por requisição** (scripts só do próprio servidor ou com o nonce da página), `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `object-src 'none'`, `form-action 'self'`, `base-uri 'self'`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`. Os dois scripts embutidos (cadastro de aluno e professor) receberam o nonce |
| S4 | Cadastro público aceitava qualquer senha | **Aluno e professor: no mínimo 6 caracteres e um caractere especial** (decisão do usuário). Contas administrativas mantêm 12 caracteres e passam a exigir especial. Máximo de 128 (evita senha enorme consumindo CPU no hash). Regra única em `app/services/senha_service.py` |
| S5 | Flask 3.1.0: `Vary: Cookie` ausente em alguns casos e chave alternativa de assinatura errada | Atualizado para **Flask 3.1.3**. Além disso, toda resposta que usa a sessão leva `Vary: Cookie`, e páginas de usuário logado levam `Cache-Control: private, no-store` (rotas que já proibiam cache são respeitadas). Nenhum cache intermediário guarda página de usuário, mesmo com proxy ou CDN no futuro |
| S6 | Login revelava se a conta existe | Resposta **única** para e-mail inexistente e senha errada: 401 "E-mail ou senha inválidos". O e-mail inexistente também passa pela verificação de senha (num hash fictício) e também conta tentativas, então nem o tempo nem o bloqueio diferenciam. O estado da conta (pendente ou inativa) só é revelado com a senha correta |
| S7 | Gateway Nginx da frota com menos cabeçalhos | O Nginx gerado passa a enviar `X-Frame-Options`, `nosniff` e `Referrer-Policy` também nas respostas **que ele mesmo gera** (429 do limite de tráfego, 502), sem duplicar os da aplicação (`proxy_hide_header`), e `server_tokens off`. O Caddy da instalação única ganhou `X-Frame-Options` |

Também atualizado: python-dotenv 1.2.4 (S12). O pip-audit depois das atualizações:
**nenhuma vulnerabilidade conhecida**.

### Por que estilos embutidos continuam permitidos na CSP

Os templates usam `<style>` para os tokens de tema da escola e atributos `style=` em telas
legadas. Bloqueá-los exigiria refazer templates, o que o protocolo de design manda fazer com
inspeção visual própria. Estilo injetado tem risco baixo; o vetor de XSS é script, e **scripts
estão restritos**.

### Configuração

`LOGIN_MAX_TENTATIVAS` (5), `LOGIN_MAX_TENTATIVAS_IP` (30) e `LOGIN_BLOQUEIO_MINUTOS` (15),
com limites validados. Os valores padrão valem sem configuração.

## Revisão de código

1. **Login com sucesso quebrado:** depois do `commit`, o SQLAlchemy expira os atributos do
   usuário, e a resposta era montada depois de fechar a sessão. Corrigido montando a resposta
   antes do `commit`.
2. **Cache sobrescrito:** o módulo trocava `no-store` de rotas existentes por
   `private, no-store`, quebrando dois contratos testados. Agora só acrescenta quando a rota
   ainda não proíbe cache.
3. **Tabela do limitador sem limpeza:** e-mails inexistentes geravam linhas indefinidamente.
   Agora linhas vencidas são apagadas a cada falha registrada, pelo índice de `janela`.
4. **Acoplamento:** o módulo de cabeçalhos ficou em `api/seguranca_http.py`, fora do pacote
   da escola, porque o painel central não deve carregar o banco nem os modelos da escola.

**Limitação conhecida:** tentativas que chegam exatamente ao mesmo tempo passam pela checagem
antes de serem contadas e podem exceder o limite por um instante, no máximo pelo número de
conexões simultâneas (4 por escola). O bloqueio vale em seguida.

## Validação

**Testes novos** (`test_seguranca_login_cabecalhos.py`, 13 casos, SQLite e PostgreSQL):
bloqueio após 5 falhas mesmo com senha correta e `Retry-After`; fim do bloqueio após a
janela; senha correta zera a contagem; limite por IP; chaves sem e-mail nem IP; limpeza das
linhas vencidas; resposta idêntica para conta inexistente e senha errada (inclusive no
bloqueio); regra de senha no cadastro (curta, sem especial, só espaço, longa demais, válida);
contas administrativas; cabeçalhos em toda página; nonce do script igual ao da CSP e
diferente a cada requisição; cache proibido para usuário logado e permitido para arquivos
estáticos; painel central com os mesmos cabeçalhos. Mais o teste do Nginx gerado em
`infra/test_environments.cjs`.

**Navegador real (Edge, Playwright):** login como admin, professor e aluno e visita a todas
as páginas alcançáveis por links internos (GET): **66 páginas, 0 violações de CSP**. Um único
erro de console (404 de um recurso durante a navegação em `admin_painel.html`) não se repetiu
ao abrir a página diretamente e não é violação de CSP.

**Sondagem real** (ambiente manual, mesma da revisão anterior):

| Verificação | Antes | Depois |
| --- | --- | --- |
| E-mail inexistente / senha errada | 404 / 401 | 401 / 401, mesma mensagem |
| Falhas seguidas na mesma conta | 30 aceitas, senha correta entrava | 5ª falha bloqueia; senha correta recebe 429, `Retry-After: 900`; outra conta segue entrando |
| Cabeçalhos da página | nenhum de proteção | CSP com nonce, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Vary: Cookie` |
| Bibliotecas | Flask 3.1.0, cryptography 45.0.7 | Flask 3.1.3, cryptography 50.0.2 |

**Bateria completa** (`.ci-results/seguranca-s1-s7-2026-11-23/`), com as imagens
reconstruídas com as bibliotecas novas:

| Etapa | Resultado |
| --- | --- |
| Regressão | SQLite 304 ✓ (43 ign.), **PostgreSQL 304 ✓ (2 ign., os mesmos de sempre)**, HTTP 117 ✓. Os 13 testes novos passaram também em PostgreSQL |
| `ci.py` (imagem de produção) | Deploy 11 ✓, SQLite 304 ✓, PostgreSQL 304 ✓, HTTPS/login e backup/restauração ✓ |
| Piloto de duas escolas | ✓ (aplicações de produção com os novos cabeçalhos e o limitador) |
| API de frequência | SQLite, PostgreSQL e HTTP 117 ✓ |
| Painel central | 18/18 ✓ |
| Postman | SQLite e PostgreSQL: 57 requisições, 65 asserções, 0 falhas |
| Ensaio de atualização | ✓ na segunda execução, ver abaixo |

O ensaio falhou na primeira execução por **expectativa desatualizada**: ele esperava 404 para a
conta legada com maiúsculas no e-mail, e a correção S6 passou a responder 401, a mesma resposta
de qualquer credencial inválida. A expectativa foi atualizada, e o ensaio passou em seguida
(dados preservados, aplicação funcionando e volta atrás idêntica).

**Protocolo de design:** verificador estático aprovado. A única mudança em templates é o
atributo `nonce` em dois `<script>`, sem efeito visual; por isso não houve novas capturas em
`docs/design/referencias/`. A navegação real acima confirma que as páginas funcionam
com a CSP.

## Pendências

Itens de gravidade baixa da revisão anterior continuam abertos: token CSRF quando falta
`Origin` (S8), tipos de arquivo e cifra dos documentos (S9), logout por GET (S10), chaves
separadas para sessão e JWT (S11).
