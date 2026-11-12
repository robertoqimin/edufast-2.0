# Entrega da restauração — 30/10/2026

Referência funcional e visual: `Samucau1/Projeto-Educa-Fast`, commit `cb27d3c`.
Base anterior deste trabalho: `51cde1b`. A restauração está organizada para revisão.
A referência visual r2 concluiu os cenários descritos abaixo; isso não representa
implantação em produção nem comprovação de ausência de toda vulnerabilidade.

## Evidências disponíveis

| Verificação executada | Resultado registrado |
| --- | --- |
| CI completo SQLite | 96 testes, 15 cenários exclusivos de MySQL ignorados |
| CI completo MySQL | 96 testes aprovados |
| Suíte focada de restauração MySQL | 14 testes aprovados, incluindo conteúdo com acentos e aprovação versionada |
| Testes anteriores da API, após ajuste dos erros HTML | 18 aprovados |
| Postman/Newman | 57 requisições e 65 asserções aprovadas |
| Comparação com a base anterior | API anterior, novos testes e regressão aprovados em SQLite |
| Caracterização do CI | 7 aprovados |
| Proteção de envio na interface | 4 testes Node aprovados |
| Infraestrutura de especificações futuras | 5 aprovados; funcionalidades futuras não foram executadas |
| Workflows | actionlint 1.7.7 aprovado |
| Protocolo estático de design | Aprovado; não substitui inspeção visual |

O CI completo também verificou HTTPS/CA/HSTS, login, backup/restauração MySQL,
persistência de uploads e proteções do deploy. Não aplicou migrations em banco existente.

As execuções acima ocorreram durante a integração. Houve ajustes posteriores de
apresentação, incluindo erros HTML e seleção de revisores. Os contratos antigos
de API e os testes focados foram repetidos, mas isso não equivale a declarar que
toda checagem foi repetida contra cada alteração posterior.

## Referência visual e fechamento da pendência

A [galeria versionada](../design/README.md) preserva a primeira referência de 21
imagens e a revisão r2 com 23 imagens, todas com dados fictícios. Os manifestos
registram os hashes; um resumo antigo não foi usado como aprovação final.

A rodada ampliada inicialmente parou na captura de acesso negado. Após a revisão
automática voltar a permitir o diagnóstico, a seleção de HTML/JSON foi corrigida
usando os tipos suportados na negociação de `Accept`. A resposta permaneceu 403;
nenhuma autorização foi relaxada. Os 18 contratos da API foram repetidos e passaram.
A rodada completa do navegador passou, incluindo captura desktop/móvel do acesso
negado, modais, quatro perfis e paleta personalizada, sem erros JavaScript.

## Banco e ambiente

A prévia restaurada usa o projeto Docker `edufast-manual-restaurado` e a porta
5050, com volume novo. O projeto/volume anterior foi preservado. Somente dados
sintéticos foram provisionados no ambiente novo; o esquema anterior não foi atualizado.

`Códigos/migrations/003_restauracao_educafast.sql` é proposta para revisão humana:
24 tabelas novas, sem apagar registros ou deduzir vínculos históricos.
Credenciais de infraestrutura e DATA_ENCRYPTION_KEY permanecem fora do Git.
