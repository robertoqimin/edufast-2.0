# Desempenho e experiência: ambientes de teste

[Início da revisão](README.md) · [Metas propostas](../../planejamento/DESEMPENHO.md)

## Executor HTTP preparado

O executor [benchmark.py](../../../.github/cicd/next/benchmark.py) chama Gunicorn por HTTP real dentro do container e usa o PostgreSQL descartável. Não substitui respostas por mocks nem usa o cliente Flask para calcular tempos.

```bash
# Ensaio curto do executor; não aprova desempenho:
python .github/cicd/next_stage.py --suite performance --smoke

# 30 s de aquecimento e ao menos 10 min em cada patamar:
python .github/cicd/next_stage.py --suite performance --duration 600
```

Massa proposta: 5 escolas e 1.000 alunos por escola. Carga: 1, 10 e 25 sessões; 70% consultas, 20% buscas/paginação e 10% cadastros. Há pausas entre ações e o relatório informa requisições por segundo. Cada resposta é verificada quanto ao escopo da escola.

Relatórios incluem quantidade de amostras, mediana, p95, erros, duração e limites do ambiente. O ensaio completo exige ao menos 100 amostras bem-sucedidas de cada tipo por patamar, sem erros, p95 até 500 ms para leitura/busca e 1 s para gravação. São metas propostas para revisão, ainda não resultados obtidos.

Limites configurados: container de testes 1 CPU/768 MiB e PostgreSQL 1 CPU/1 GiB. Gerador de carga e Gunicorn compartilham o primeiro container; isso deve ser considerado ao interpretar resultados. O pico de memória registrado nesse container inclui os dois processos. O proxy não participa deste ensaio, e o hardware físico do host não é equivalente a um computador antigo apenas por limitar CPU/RAM.

O modo smoke verifica apenas a capacidade de completar requisições. Seu relatório tem `qualified: false`. Os recursos futuros ainda ausentes também impedem esse modo de passar hoje; isso não é um benchmark de desempenho ruim da versão atual.

## Roteiro para navegador e equipamento real

Estes casos são de aceitação manual nesta preparação. Não há automação de navegador implementada, nem resultado de LCP/interação declarado.

| ID | Cenário | Critério de aceite proposto |
| --- | --- | --- |
| UX-001 | Conta com duas escolas abre a plataforma | Seleção contém somente vínculos disponíveis |
| UX-002 | Trocar escola com filtros e formulário em andamento | Contexto visível; dados, filtros e rascunhos incompatíveis não vazam |
| UX-003 | Cadastro de aluno com campo inválido | Erro próximo do campo; preenchimento preservado |
| UX-004 | Criar matrícula e consultar a turma | Registro aparece uma única vez e com estado correto |
| UX-005 | Tentar salvar após revogação de acesso | Operação bloqueada com mensagem clara; sem sucesso antecipado |
| UX-006 | Lista sem dados, erro de conexão e carregamento | Estados distintos e possibilidade de recuperação |
| UX-007 | Navegar por teclado | Foco visível e todas as ações principais acessíveis |
| UX-008 | Abrir turma e documentos em celular | Conteúdo e ações acessíveis sem perda de contexto |
| UX-009 | Comparar cache frio/quente em equipamento modesto | Registrar recursos transferidos e LCP; meta provisória de até 3 s no percentil 75 |
| UX-010 | Buscar aluno, abrir turma e preencher matrícula | Medir interação até próxima pintura; meta provisória de até 200 ms no percentil 75 |
| UX-011 | Abrir páginas com rede limitada | Sem dependência de carregamento de toda a base; feedback visível |
| UX-012 | Medir HTML/CSS/JS e perfil de CPU | Meta inicial de até 300 KiB comprimidos nas telas comuns; registrar terceiros |

Usar os perfis de cliente/rede do plano de desempenho, registrar aparelho, navegador, commit e amostras. As metas de navegador não são comprovadas pelos testes de API/unitários ou pelo ensaio HTTP.

## Antes de promover para bloqueio de CI

Medir a linha de base e sua variabilidade. Verificações determinísticas, como tamanho dos recursos e número de consultas, poderão virar bloqueios após implementação do build de assets e definição dos contratos dessas medições. Não há limite de consultas inventado apenas para fazer o teste passar.

Para homologar capacidade e consumo totais, executar carga com gerador separado, proxy, monitoramento de todos os serviços e limites do servidor contratado. O ensaio preparado aqui é uma etapa reproduzível de desenvolvimento, não um SLA comercial.
