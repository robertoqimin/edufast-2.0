# Validação das aprovações e permissões — 2026-10-29

Base de comparação: `af50046ec27e42b15cae5e2278dfcfb6e8471e83`.
Ambientes de teste novos e descartáveis. Nenhuma migration foi aplicada a banco existente.

| Verificação | Resultado |
| --- | --- |
| Suite atual SQLite | 78 testes, 14 cenários de concorrência exclusivos de MySQL ignorados |
| Suite atual MySQL | 78 testes aprovados, nenhum ignorado |
| Caracterização da entrada do CI | 7 aprovados |
| Caracterização de admin_controller | 6 aprovados, incluídos na suite atual |
| Contratos de segurança e aprovação | 26, incluídos na suite atual |
| Proteções do deploy | 11 aprovados |
| Imagem de produção, HTTPS/CA/HSTS e login | Aprovados no CI completo |
| Backup/restauração MySQL e persistência de uploads após reinicialização | Aprovados no CI completo |
| Envio na interface (Node) | 4 aprovados |
| Infraestrutura das especificações futuras | 5 aprovados; funcionalidades futuras não executadas |
| Workflows (actionlint 1.7.7) | Aprovados |
| Postman/Newman | 49 requisições e 56 asserções aprovadas; registros e arquivos conferidos |
| Comparação API anterior → novos testes → regressão anterior | Aprovada no SQLite; 18 testes antigos preservados |

## Comandos

Com Docker ativo e dependências do projeto disponíveis:

```text
python .github/cicd/ci.py
python .github/cicd/test_ci_characterization.py
node --test .github/cicd/test_submission.cjs
python .github/cicd/next_stage.py --check
python .github/cicd/review_mutations.py --base-ref af50046
python .github/cicd/run_postman.py --newman CAMINHO/newman/bin/newman.js
```

Os testes reproduzem e bloqueiam autoativação de professor, concessão de papel
pelo cliente, exposição de CPF a docente e download de outro usuário por JWT.
Verificam também os controles legítimos: admissão aprovada, cadastro administrativo
direto, revisão limitada de material, acesso do proprietário e edição com versão.
Uma decisão concorrente retorna sucesso e a outra conflito, com só um efeito.

A revisão independente encontrou e motivou testes adicionais para tipo de
proposta malformado (400) e repetição idempotente após aprovação documental.
Formulários administrativos via AJAX têm teste com Origin e token CSRF válidos.

Os registros detalhados locais ficam em `.ci-results/`, ignorado pelo Git.
Há avisos ResourceWarning de recursos dos testes, sem falhas de asserção.
Não foi realizada homologação manual visual de todas as telas nem teste em banco
real. Não há alegação de ausência de toda vulnerabilidade possível.

A implantação depende da revisão humana de `002_aprovacoes_e_permissoes.sql`,
especialmente da quarentena dos professores legados. Consultar
`Documentos/seguranca-aprovacoes.md` e `Códigos/migrations/README.md`.
