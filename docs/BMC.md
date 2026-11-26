# EduFast — Business Model Canvas

**Menos burocracia. Mais tempo para a educação.**

Plataforma de gestão escolar que reúne direção, secretaria, professores e alunos no mesmo lugar, vendida por assinatura para cada instituição, com instalação e dados próprios.

Versão visual do canvas: [BMC.pdf](BMC.pdf). Fonte editável: [`scripts/gerar_bmc.py`](../scripts/gerar_bmc.py).

## 1. Segmentos de clientes

- Escolas particulares de educação básica, de pequeno e médio porte (quem decide: direção ou mantenedora)
- Instituições com colégio e faculdade na mesma mantenedora
- Cursos técnicos, livres e preparatórios (ex.: ENEM)
- Usuários: direção, secretaria, professores e alunos

## 2. Proposta de valor

- Uma central só: matrículas, turmas, chamada, notas, materiais, cursos e comunicados
- Um caminho por tarefa e implantação guiada pelo checklist de primeiros passos
- A escola no controle: notas e materiais do professor passam pela secretaria; a avaliação inteira é aprovada em lote, com trilha de auditoria
- Estudo dentro da plataforma: PDF, slides, imagens e vídeo num leitor próprio, sem baixar arquivos
- Colégio e faculdade na mesma instituição, com secretarias separadas; o concluinte sobe levando o histórico
- Leve em computadores e celulares modestos, acessível (WCAG) e com a identidade visual da escola
- Privacidade: cada instituição com instalação, banco e arquivos próprios

## 3. Canais

- Demonstração ao vivo na escola fictícia, percorrendo cada perfil
- Venda direta à direção e às mantenedoras
- Piloto controlado com escola parceira
- Indicação entre escolas, eventos e redes sociais de educação
- Entrega pelo navegador, no endereço próprio da instituição

## 4. Relacionamento com clientes

- Implantação assistida e treinamento por perfil
- Autoatendimento: cada perfil resolve sua tarefa sem depender de TI própria
- Suporte por canal digital
- Acompanhamento próximo das escolas piloto, com evolução guiada pelo uso

## 5. Fontes de receita

- Assinatura mensal por instituição, por faixa de número de alunos
- Taxa de implantação: instalação, migração de dados e treinamento
- Unidade adicional (ex.: faculdade) e módulos futuros: RH, ponto, folha de pagamento e financeiro escolar
- Serviços: suporte estendido, personalização e instalação local sob contrato
- O painel do proprietário acompanha faturamento, despesas e lucro por escola

## 6. Recursos-chave

- Plataforma EduFast (aplicação web e API) e painel central do proprietário
- Infraestrutura em nuvem com uma instalação isolada por cliente
- Equipe de desenvolvimento, design/UX, implantação e suporte
- Design system próprio, base de testes e CI/CD
- Escola de demonstração com dados fictícios e telas reais

## 7. Atividades-chave

- Desenvolver e evoluir o produto com testes automatizados, acessibilidade e revisão visual
- Implantar cada instituição: instalação, migração de dados e configuração
- Operar a plataforma: hospedagem, backups, atualizações e segurança
- Treinar e dar suporte às equipes escolares
- Demonstrar e vender: escola de demonstração e piloto controlado

## 8. Parceiros-chave

- Provedor de nuvem: servidores, armazenamento e backup fora do servidor
- Registro de domínio e certificados HTTPS
- YouTube: vídeos embutidos nos materiais e nas aulas
- Escolas piloto e mantenedoras, que validam o produto e indicam outras escolas
- Consultoria jurídica (LGPD) e contábil/trabalhista para os módulos de folha e financeiro

## 9. Estrutura de custos

- Infraestrutura por instalação (servidor, banco, armazenamento e backup), que cresce com o número de clientes; o produto leve ajuda a contê-la
- Equipe: desenvolvimento, design, implantação e suporte
- Domínios, certificados e ferramentas de desenvolvimento e CI
- Vendas e marketing: demonstrações, visitas e eventos
- Segurança e conformidade com a LGPD

## Hipóteses a validar no piloto

- Preço por faixa de alunos e disposição a pagar das escolas
- Tempo médio de implantação e de treinamento por instituição
- Redução de retrabalho da secretaria e do professor (meta ainda não medida com usuários)
- Custo de infraestrutura por instalação em uso real

## Situação do produto (novembro de 2026)

| Módulo | Situação |
| --- | --- |
| Acesso por perfil, secretaria, turmas, disciplinas, professor, aluno, documentos, comunicados | Implementado |
| Frequência com atestados, aprovação em lote, espaço da disciplina com leitor, cursos modulares | Implementado |
| Colégio e faculdade (unidades) | Separação no back-end implementada; telas de troca de unidade em andamento |
| Ensino superior por período e passagem de ano | Planejado |
| RH, ponto, folha de pagamento e financeiro | Planejado (protótipos em docs/prototipo/) |

Beta funcional, pronto para um piloto controlado; nenhuma instalação de produção homologada ainda.
