# Enquadramento das siglas T01/T02 — 12/11/2026

Pedido: corrigir a logo T02 que saiu do enquadramento, seguindo a T01.
Base: commit `92d3a33`, com o ajuste da marca compartilhada desta entrega.

Antes: em `../2026-11-11-login-escolas/admin-teste02-mobile.png`, a sigla T02
quebrava em duas linhas. A regra de quebra de palavras do nome da escola era
herdada pelo símbolo. A largura de T02 expunha a falha mais facilmente que T01.

Depois: a marca não encolhe nem quebra a sigla; três caracteres usam fonte de
18px, mantendo o quadrado e os tokens existentes. Login e menu usam a mesma
classe. A seta e a composição original são preservadas. A versão do CSS foi
atualizada para que um recarregamento carregue a correção.

Validação: `Códigos/tests/verificar_login_escolas.cjs` passou em Edge headless
isolado, incluindo login dos três perfis nas duas escolas, sessões simultâneas e
avisos de sessão bloqueada. Em cada captura desktop 1440x1000 e mobile 390x844,
o teste espera a fonte local e verifica que a sigla ocupa uma única linha e que
sua caixa de texto fica dentro da marca. Também verifica ausência de overflow
horizontal. Foram inspecionados visualmente o menu T02 mobile e o login T01
desktop. Capturas anteriores permanecem intactas; o manifesto registra as novas.

Não houve alteração de banco, contas, permissões, tema ou navegação. Não foi
realizado teste em dispositivo físico nem com todas as siglas possíveis.
