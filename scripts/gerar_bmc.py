"""Gera docs/BMC.md e docs/bmc/BMC.html (canvas) a partir do conteúdo abaixo.

Edite o conteúdo aqui e rode, na raiz do projeto:
    python scripts/gerar_bmc.py
    google-chrome --headless --no-pdf-header-footer --print-to-pdf=docs/BMC.pdf docs/bmc/BMC.html
"""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TITULO = "EduFast — Business Model Canvas"
LEMA = "Menos burocracia. Mais tempo para a educação."
RESUMO = ("Plataforma de gestão escolar que reúne direção, secretaria, professores e alunos "
          "no mesmo lugar, vendida por assinatura para cada instituição, com instalação e dados próprios.")

BLOCOS = {
    "parceiros": ("Parceiros-chave", "#475569", [
        "Provedor de nuvem: servidores, armazenamento e backup fora do servidor",
        "Registro de domínio e certificados HTTPS",
        "YouTube: vídeos embutidos nos materiais e nas aulas",
        "Escolas piloto e mantenedoras, que validam o produto e indicam outras escolas",
        "Consultoria jurídica (LGPD) e contábil/trabalhista para os módulos de folha e financeiro",
    ]),
    "atividades": ("Atividades-chave", "#7c3aed", [
        "Desenvolver e evoluir o produto com testes automatizados, acessibilidade e revisão visual",
        "Implantar cada instituição: instalação, migração de dados e configuração",
        "Operar a plataforma: hospedagem, backups, atualizações e segurança",
        "Treinar e dar suporte às equipes escolares",
        "Demonstrar e vender: escola de demonstração e piloto controlado",
    ]),
    "recursos": ("Recursos-chave", "#9333ea", [
        "Plataforma EduFast (aplicação web e API) e painel central do proprietário",
        "Infraestrutura em nuvem com uma instalação isolada por cliente",
        "Equipe de desenvolvimento, design/UX, implantação e suporte",
        "Design system próprio, base de testes e CI/CD",
        "Escola de demonstração com dados fictícios e telas reais",
    ]),
    "proposta": ("Proposta de valor", "#0e7490", [
        "Uma central só: matrículas, turmas, chamada, notas, materiais, cursos e comunicados",
        "Um caminho por tarefa e implantação guiada pelo checklist de primeiros passos",
        "A escola no controle: notas e materiais do professor passam pela secretaria; a avaliação inteira é aprovada em lote, com trilha de auditoria",
        "Estudo dentro da plataforma: PDF, slides, imagens e vídeo num leitor próprio, sem baixar arquivos",
        "Colégio e faculdade na mesma instituição, com secretarias separadas; o concluinte sobe levando o histórico",
        "Leve em computadores e celulares modestos, acessível (WCAG) e com a identidade visual da escola",
        "Privacidade: cada instituição com instalação, banco e arquivos próprios",
    ]),
    "relacionamento": ("Relacionamento com clientes", "#b45309", [
        "Implantação assistida e treinamento por perfil",
        "Autoatendimento: cada perfil resolve sua tarefa sem depender de TI própria",
        "Suporte por canal digital",
        "Acompanhamento próximo das escolas piloto, com evolução guiada pelo uso",
    ]),
    "canais": ("Canais", "#a16207", [
        "Demonstração ao vivo na escola fictícia, percorrendo cada perfil",
        "Venda direta à direção e às mantenedoras",
        "Piloto controlado com escola parceira",
        "Indicação entre escolas, eventos e redes sociais de educação",
        "Entrega pelo navegador, no endereço próprio da instituição",
    ]),
    "segmentos": ("Segmentos de clientes", "#15803d", [
        "Escolas particulares de educação básica, de pequeno e médio porte (quem decide: direção ou mantenedora)",
        "Instituições com colégio e faculdade na mesma mantenedora",
        "Cursos técnicos, livres e preparatórios (ex.: ENEM)",
        "Usuários: direção, secretaria, professores e alunos",
    ]),
    "custos": ("Estrutura de custos", "#be123c", [
        "Infraestrutura por instalação (servidor, banco, armazenamento e backup), que cresce com o número de clientes; o produto leve ajuda a contê-la",
        "Equipe: desenvolvimento, design, implantação e suporte",
        "Domínios, certificados e ferramentas de desenvolvimento e CI",
        "Vendas e marketing: demonstrações, visitas e eventos",
        "Segurança e conformidade com a LGPD",
    ]),
    "receitas": ("Fontes de receita", "#1d4ed8", [
        "Assinatura mensal por instituição, por faixa de número de alunos",
        "Taxa de implantação: instalação, migração de dados e treinamento",
        "Unidade adicional (ex.: faculdade) e módulos futuros: RH, ponto, folha de pagamento e financeiro escolar",
        "Serviços: suporte estendido, personalização e instalação local sob contrato",
        "O painel do proprietário acompanha faturamento, despesas e lucro por escola",
    ]),
}

HIPOTESES = [
    "Preço por faixa de alunos e disposição a pagar das escolas",
    "Tempo médio de implantação e de treinamento por instituição",
    "Redução de retrabalho da secretaria e do professor (meta ainda não medida com usuários)",
    "Custo de infraestrutura por instalação em uso real",
]

SITUACAO = [
    ("Acesso por perfil, secretaria, turmas, disciplinas, professor, aluno, documentos, comunicados", "Implementado"),
    ("Frequência com atestados, aprovação em lote, espaço da disciplina com leitor, cursos modulares", "Implementado"),
    ("Colégio e faculdade (unidades)", "Separação no back-end implementada; telas de troca de unidade em andamento"),
    ("Ensino superior por período e passagem de ano", "Planejado"),
    ("RH, ponto, folha de pagamento e financeiro", "Planejado (protótipos em docs/prototipo/)"),
]


def markdown():
    linhas = [f"# {TITULO}", "", f"**{LEMA}**", "", RESUMO, "",
              "Versão visual do canvas: [BMC.pdf](BMC.pdf). Fonte editável: "
              "[`scripts/gerar_bmc.py`](../scripts/gerar_bmc.py).", ""]
    ordem = ["segmentos", "proposta", "canais", "relacionamento", "receitas",
             "recursos", "atividades", "parceiros", "custos"]
    for i, chave in enumerate(ordem, 1):
        nome, _, itens = BLOCOS[chave]
        linhas += [f"## {i}. {nome}", ""] + [f"- {item}" for item in itens] + [""]
    linhas += ["## Hipóteses a validar no piloto", ""] + [f"- {h}" for h in HIPOTESES] + [""]
    linhas += ["## Situação do produto (novembro de 2026)", "", "| Módulo | Situação |", "| --- | --- |"]
    linhas += [f"| {m} | {s} |" for m, s in SITUACAO]
    linhas += ["", "Beta funcional, pronto para um piloto controlado; nenhuma instalação de produção "
               "homologada ainda.", ""]
    return "\n".join(linhas)


def bloco(chave, area):
    nome, cor, itens = BLOCOS[chave]
    lis = "".join(f"<li>{html.escape(i)}</li>" for i in itens)
    return f'<section style="grid-area:{area};border-top:5px solid {cor}"><h2 style="color:{cor}">{nome}</h2><ul>{lis}</ul></section>'


def pagina():
    e = html.escape
    situacao = "".join(f"<tr><td>{e(m)}</td><td>{e(s)}</td></tr>" for m, s in SITUACAO)
    hip = "".join(f"<li>{e(h)}</li>" for h in HIPOTESES)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{TITULO}</title>
<style>
@page {{ size: A3 landscape; margin: 9mm; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: Helvetica, Arial, sans-serif; color:#0f172a; font-size:10.5pt; line-height:1.35; }}
header {{ display:flex; align-items:baseline; justify-content:space-between; gap:20px; margin-bottom:6px; }}
h1 {{ font-size:20pt; margin:0; }} header p {{ margin:0; color:#475569; max-width:60%; text-align:right; }}
.canvas {{ display:grid; gap:6px; grid-template-columns: repeat(10, 1fr); grid-template-rows: 1fr 1fr 0.62fr; height:203mm;
  grid-template-areas:
   "par par ati ati pro pro rel rel seg seg"
   "par par rec rec pro pro can can seg seg"
   "cus cus cus cus cus rec2 rec2 rec2 rec2 rec2"; }}
section {{ border:1px solid #cbd5e1; border-radius:6px; padding:7px 10px; overflow:hidden; background:#fff; }}
h2 {{ font-size:11.5pt; margin:0 0 4px; text-transform:uppercase; letter-spacing:.03em; }}
ul {{ margin:0; padding-left:15px; }} li {{ margin:0 0 3px; }}
.lema {{ font-weight:bold; color:#0e7490; }}
.rodape {{ display:grid; grid-template-columns: 1fr 1.4fr; gap:10px; margin-top:6px; font-size:9pt; }}
.rodape h3 {{ font-size:9.5pt; margin:0 0 2px; }} table {{ border-collapse:collapse; width:100%; }} td {{ border:1px solid #e2e8f0; padding:2px 5px; vertical-align:top; }}
</style></head><body>
<header><h1>{TITULO} <span class="lema">· {LEMA}</span></h1><p>{e(RESUMO)}</p></header>
<div class="canvas">
{bloco("parceiros", "par")}{bloco("atividades", "ati")}{bloco("recursos", "rec")}{bloco("proposta", "pro")}
{bloco("relacionamento", "rel")}{bloco("canais", "can")}{bloco("segmentos", "seg")}{bloco("custos", "cus")}{bloco("receitas", "rec2")}
</div>
<div class="rodape"><div><h3>Hipóteses a validar no piloto</h3><ul>{hip}</ul></div>
<div><h3>Situação do produto (novembro de 2026)</h3><table>{situacao}</table></div></div>
</body></html>"""


def main():
    (ROOT / "docs" / "BMC.md").write_text(markdown(), encoding="utf-8")
    destino = ROOT / "docs" / "bmc"
    destino.mkdir(exist_ok=True)
    (destino / "BMC.html").write_text(pagina(), encoding="utf-8")
    print("docs/BMC.md e docs/bmc/BMC.html gerados")


if __name__ == "__main__":
    main()
