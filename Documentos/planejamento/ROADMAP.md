# Roadmap do EduFast

[Início](../../README.md) · [Arquitetura](../arquitetura/ARQUITETURA.md)

Esta é uma sequência proposta, sem datas ou compromisso de entrega. Gestão completa é a visão do produto; a tabela de funcionalidades do README identifica a implementação presente.

| Etapa | Entrega | Critério de conclusão |
| --- | --- | --- |
| 1. Base reproduzível | Instalação, testes e inventário do código ativo | Nova instalação validada e cenários de login, cadastros, turmas, notas e arquivos reproduzíveis |
| 2. Experiência | Componentes compartilhados e identidade EduFast | Fluxos avaliados com usuários, teclado e celular; estados de falha e vazio definidos |
| 3. Acadêmico | Atribuição docente explícita e histórico por período | Migração ensaiada e permissões verificadas por recurso |
| 4. Pessoas | Colaboradores, contratos e jornadas | Dados consistentes e acesso restrito por função |
| 5. Ponto | Marcações, justificativas e aprovação | Ajustes rastreáveis, fechamento revisável e histórico preservado |
| 6. Folha | Eventos, cálculo, revisão e demonstrativos | Regras validadas por responsáveis especializados e fechamento versionado |
| 7. Financeiro | Mensalidades, contas, recebimentos e conciliação | Transações sem duplicidade, estados claros e rastreabilidade |
| 8. Gestão integrada | Relatórios e suporte a unidades | Escopo institucional explícito e indicadores reconciliados com os registros |

Cursos e conteúdo digital podem ser desenvolvidos em uma frente própria após a base acadêmica, seguindo o [planejamento anterior](PLANEJAMENTO_EDUCAFAST.md). Esse documento antigo preserva o contexto original, inclusive referências a outros repositórios e caminhos; não descreve integralmente o estado atual.

## Dependências de negócio

- Definir tipos de escola, calendário, períodos e regras de matrícula antes de expandir o histórico acadêmico.
- Separar frequência de alunos da jornada de colaboradores: são processos diferentes.
- Definir regras de jornada e revisão de ponto com os responsáveis da escola antes de automatizar a folha.
- Separar cálculo de folha, autorização e execução de pagamento. A interface não deve tratar uma proposta de pagamento como transação confirmada.
- Definir retenção de dados, papéis de acesso, backup e recuperação antes de uso real.
- Revisar requisitos legais e integrações aplicáveis na fase de implementação de RH, ponto e folha; esta documentação não especifica conformidade ou cálculos legais.

## Aceite por módulo

Cada módulo precisa de modelo de dados, migração, permissões, tratamento de erros, interface acessível, testes de regras e fluxo completo de ponta a ponta. Os protótipos aprovam uma direção de experiência; não substituem esses critérios.
