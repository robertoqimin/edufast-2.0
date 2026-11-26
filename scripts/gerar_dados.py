"""Gera docs/dados/ (diagrama ER editável) e docs/DADOS.html a partir dos modelos SQLAlchemy.

Uso, na raiz do projeto (requer Graphviz `dot`):
    SECRET_KEY=x DB_URL=sqlite:// PYTHONPATH=api python scripts/gerar_dados.py
Depois converta o HTML em PDF, por exemplo:
    google-chrome --headless --no-pdf-header-footer --print-to-pdf=docs/DADOS.pdf docs/DADOS.html
"""
import html
import subprocess
from datetime import date
from pathlib import Path

from app import models  # noqa: F401  (registra as tabelas)
from app.database import Base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "dados"

GRUPOS = [
    ("Identidade e acesso", "#0e7490", {
        "usuarios": "Conta de acesso: e-mail, senha (hash), perfil e versão de autenticação para revogar tokens.",
        "alunos": "Dados cadastrais e acadêmicos do aluno, ligados a uma conta de usuário.",
        "professores": "Dados cadastrais e funcionais do professor, ligados a uma conta de usuário.",
        "limites_login": "Tentativas de login por chave e janela de tempo, para bloquear força bruta.",
        "idempotencias": "Respostas de operações já processadas (por ator e chave), evitando gravação duplicada.",
        "configuracoes": "Cores de fundo e de destaque da interface.",
        "educafast_migracoes": "Versões de esquema já aplicadas ao banco.",
    }),
    ("Organização escolar", "#7c3aed", {
        "turmas": "Turma com nome, código, ano letivo e turno.",
        "disciplinas": "Disciplina com nome, código e carga horária.",
        "turma_estados": "Indica se a turma está arquivada.",
        "turmas_disciplinas": "Oferta de uma disciplina em uma turma.",
        "alunos_turmas": "Matrícula do aluno em uma turma.",
        "alunos_disciplinas": "Vínculo do aluno a uma disciplina.",
        "professores_turmas": "Professor associado a uma turma.",
        "professores_disciplinas": "Professor habilitado em uma disciplina.",
        "atribuicoes_docentes": "Professor responsável por uma oferta turma × disciplina.",
    }),
    ("Vida acadêmica", "#b45309", {
        "academico_periodos": "Períodos letivos de cada turma, com média de referência e fechamento.",
        "academico_avaliacoes": "Avaliações de uma oferta turma × disciplina em um período, com peso e publicação.",
        "academico_notas": "Nota do aluno em uma avaliação, com versão e ligação à nota do modelo anterior.",
        "academico_auditoria": "Trilha de alterações acadêmicas (quem, quando, o quê).",
        "atividades": "Atividades lançadas pelo professor para a turma/disciplina.",
        "notas": "Notas do modelo anterior, mantidas para conciliação.",
    }),
    ("Unidades (colégio e faculdade)", "#0f766e", {
        "unidades": "Unidades da instituição (ex.: colégio e faculdade), com nível e rótulos próprios.",
        "usuario_unidades": "Unidades a que cada usuário tem acesso; separa as secretarias.",
        "transferencias_unidade": "Histórico de alunos transferidos entre unidades (ex.: concluinte que sobe para a faculdade).",
    }),
    ("Frequência", "#a16207", {
        "frequencia_chamadas": "Chamada de uma aula (turma × disciplina, dia e aula), com revisão e aprovação.",
        "frequencia_presencas": "Situação de cada aluno em uma chamada (presente, falta, justificada).",
        "frequencia_atestados": "Atestados enviados para justificar faltas, com decisão da secretaria.",
        "frequencia_auditoria": "Trilha das ações de frequência.",
    }),
    ("Espaço da disciplina (materiais de estudo)", "#9333ea", {
        "estudo_secoes": "Abas/seções que organizam os materiais de uma oferta turma × disciplina.",
        "estudo_conteudos": "Materiais de estudo (texto, link, PDF, imagem ou vídeo), com estado e versão.",
        "estudo_conteudo_secao": "Ligação entre materiais e seções.",
        "estudo_auditoria": "Trilha das ações sobre os materiais.",
        "estudo_secao_auditoria": "Trilha das ações sobre as seções.",
    }),
    ("Calendário e políticas da escola", "#15803d", {
        "escola_identidade": "Identidade visual da escola (nome, siglas, cores e logotipo), versionada.",
        "escola_calendarios": "Calendários escolares por ano letivo.",
        "escola_eventos": "Eventos e datas de um calendário.",
        "escola_politicas": "Políticas configuráveis (avaliação, frequência) de um calendário.",
        "escola_regras_periodos": "Aplicação de uma política a um período.",
        "escola_regras_turmas": "Aplicação de uma política a uma turma.",
    }),
    ("Cursos", "#be185d", {
        "cursos": "Curso da biblioteca, com disciplina, professor autor, origem (cópia) e estado.",
        "curso_capitulos": "Capítulos de um curso.",
        "curso_temas": "Temas de um capítulo.",
        "curso_aulas": "Aulas de um tema, com vídeo e posição.",
        "curso_ofertas": "Disponibilização de um curso para uma oferta turma × disciplina.",
        "curso_progressos": "Aulas concluídas por aluno em cada oferta.",
        "curso_auditoria": "Trilha de alterações nos cursos.",
        "curso_versoes": "Versões publicadas de cada curso.",
        "curso_aula_conteudos": "Conteúdo textual de uma aula.",
        "curso_aula_recursos": "Arquivos e links de apoio de uma aula (PDF, vídeo, imagem).",
        "curso_retomadas": "Ponto em que o aluno parou em cada oferta, para retomar o curso.",
    }),
    ("Documentos, comunicação e aprovações", "#1d4ed8", {
        "documentos": "Arquivos enviados por alunos e professores, com título e caminho.",
        "solicitacoes_documentos": "Pedidos de documento feitos pela secretaria.",
        "comunicados": "Comunicados publicados para a escola.",
        "solicitacoes_alteracoes": "Propostas de alteração que exigem aprovação de um revisor.",
    }),
    ("Privacidade", "#475569", {
        "pedidos_privacidade": "Pedidos do titular sobre seus dados pessoais (texto cifrado).",
        "auditoria_privacidade": "Trilha de tratamento dos pedidos de privacidade.",
    }),
]


def tipo(col):
    try:
        return str(col.type).lower()
    except Exception:
        return col.type.__class__.__name__.lower()


def main():
    tabelas = {t.name: t for t in Base.metadata.sorted_tables}
    agrupadas = {n for _, _, d in GRUPOS for n in d}
    faltando = sorted(set(tabelas) - agrupadas)
    if faltando:
        GRUPOS.append(("Outras", "#334155", {n: "" for n in faltando}))
    OUT.mkdir(parents=True, exist_ok=True)

    # Diagrama ER (DOT é o arquivo editável; SVG é gerado a partir dele)
    dot = ['digraph EduFast {', ' graph [rankdir=LR, fontname="Helvetica", splines=true, nodesep=0.25, ranksep=0.9, pad=0.3];',
           ' node [shape=plain, fontname="Helvetica", fontsize=10];', ' edge [color="#64748b", arrowhead=crow, arrowtail=tee, dir=both];']
    for i, (grupo, cor, descr) in enumerate(GRUPOS):
        dot.append(f' subgraph cluster_{i} {{ label="{grupo}"; fontsize=13; color="{cor}"; fontcolor="{cor}"; style=rounded;')
        for nome in descr:
            t = tabelas[nome]
            linhas = [f'<tr><td bgcolor="{cor}" colspan="2"><font color="white"><b>{nome}</b></font></td></tr>']
            for c in t.columns:
                if c.primary_key or c.foreign_keys:
                    marca = "PK" if c.primary_key else "FK"
                    if c.primary_key and c.foreign_keys:
                        marca = "PK FK"
                    linhas.append(f'<tr><td align="left">{c.name}</td><td align="left"><font color="#64748b">{marca}</font></td></tr>')
            outras = sum(1 for c in t.columns if not (c.primary_key or c.foreign_keys))
            if outras:
                linhas.append(f'<tr><td align="left" colspan="2"><font color="#94a3b8">+ {outras} colunas</font></td></tr>')
            dot.append(f'  "{nome}" [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="3">{"".join(linhas)}</table>>];')
        dot.append(' }')
    for t in tabelas.values():
        for fk in t.foreign_keys:
            dot.append(f' "{fk.column.table.name}" -> "{t.name}";')
    dot.append('}')
    (OUT / "modelo-dados.dot").write_text("\n".join(dot) + "\n", encoding="utf-8")
    subprocess.run(["dot", "-Tsvg", str(OUT / "modelo-dados.dot"), "-o", str(OUT / "modelo-dados.svg")], check=True)
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", str(OUT / "modelo-dados.dot"), "-o", str(OUT / "modelo-dados.png")], check=True)

    # Dicionário de dados
    e = html.escape
    corpo = []
    for grupo, cor, descr in GRUPOS:
        corpo.append(f'<h2 style="color:{cor}">{e(grupo)}</h2>')
        for nome, texto in descr.items():
            t = tabelas[nome]
            corpo.append(f'<h3>{e(nome)}</h3><p>{e(texto)}</p><table><thead><tr><th>Coluna</th><th>Tipo</th><th>Chave</th><th>Nulo</th><th>Referência</th></tr></thead><tbody>')
            for c in t.columns:
                chave = " ".join(k for k, ok in (("PK", c.primary_key), ("FK", bool(c.foreign_keys)), ("UQ", bool(c.unique))) if ok)
                ref = ", ".join(f"{fk.column.table.name}.{fk.column.name}" for fk in c.foreign_keys)
                corpo.append(f'<tr><td><code>{e(c.name)}</code></td><td>{e(tipo(c))}</td><td>{chave}</td><td>{"sim" if c.nullable else "não"}</td><td>{e(ref)}</td></tr>')
            corpo.append('</tbody></table>')
            uniq = [", ".join(col.name for col in u.columns) for u in t.constraints if u.__class__.__name__ == "UniqueConstraint" and len(u.columns) > 1]
            if uniq:
                corpo.append('<p class="nota">Únicos compostos: ' + "; ".join(f"({e(u)})" for u in uniq) + '</p>')

    n_fk = sum(len(t.foreign_keys) for t in tabelas.values())
    svg = (OUT / "modelo-dados.svg").read_text(encoding="utf-8")
    svg = svg[svg.index("<svg"):]
    import re
    svg = re.sub(r'<svg width="([\d.]+)pt" height="([\d.]+)pt"', r'<svg', svg, count=1)
    pagina = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>EduFast — Modelo de dados</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
@page diagrama {{ size: A3 portrait; margin: 8mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color:#0f172a; font-size:10.5pt; line-height:1.45; }}
h1 {{ font-size:22pt; margin:0 0 4px; }} h2 {{ font-size:14pt; margin:22px 0 6px; border-bottom:2px solid currentColor; padding-bottom:3px; break-after:avoid; }}
h3 {{ font-size:11pt; margin:14px 0 2px; break-after:avoid; }} p {{ margin:2px 0 6px; }}
table {{ border-collapse:collapse; width:100%; font-size:9pt; break-inside:auto; }} th,td {{ border:1px solid #cbd5e1; padding:3px 6px; text-align:left; vertical-align:top; }}
th {{ background:#f1f5f9; }} tr {{ break-inside:avoid; }} code {{ font-family: Menlo, Consolas, monospace; font-size:8.5pt; }}
.sub {{ color:#475569; }} .nota {{ color:#475569; font-size:9pt; }}
.diagrama {{ page: diagrama; break-before:page; break-after:page; }} .diagrama svg {{ display:block; margin:0 auto; width:auto; height:auto; max-width:100%; max-height:385mm; }} .diagrama h2 {{ margin-top:0; }}
</style></head><body>
<h1>EduFast — Modelo de dados</h1>
<p class="sub">Banco relacional PostgreSQL 17, mapeado com SQLAlchemy 2.0. Gerado a partir dos modelos em <code>api/app/models/</code> em {date.today().strftime('%d/%m/%Y')}.</p>
<h2 style="color:#0f172a">Visão geral</h2>
<p>O modelo tem <b>{len(tabelas)} tabelas</b> e <b>{n_fk} chaves estrangeiras</b>, organizadas em {len(GRUPOS)} grupos. A conta de acesso fica em <code>usuarios</code>; alunos e professores estendem essa conta com seus dados. Turmas e disciplinas são ligadas por tabelas de vínculo, e a oferta <code>turmas_disciplinas</code> é o ponto de partida de avaliações, atribuições docentes e cursos. Alterações sensíveis passam por <code>solicitacoes_alteracoes</code> (aprovação) e deixam trilha nas tabelas de auditoria.</p>
<table><thead><tr><th>Grupo</th><th>Tabelas</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(g)}</td><td>{", ".join(f"<code>{n}</code>" for n in d)}</td></tr>' for g, _, d in GRUPOS)}
</tbody></table>
<p class="nota">Legenda: PK = chave primária; FK = chave estrangeira; UQ = valor único. No diagrama, cada caixa mostra apenas as colunas de chave; o dicionário a seguir lista todas as colunas. Arquivos editáveis: <code>docs/dados/modelo-dados.dot</code> (Graphviz) e <code>docs/dados/modelo-dados.svg</code>.</p>
<section class="diagrama"><h2 style="color:#0f172a">Diagrama entidade-relacionamento</h2>{svg}</section>
<h2 style="color:#0f172a;border:0">Dicionário de dados</h2>
{''.join(corpo)}
</body></html>"""
    (ROOT / "docs" / "DADOS.html").write_text(pagina, encoding="utf-8")
    print(f"{len(tabelas)} tabelas, {n_fk} FKs -> docs/DADOS.html e docs/dados/")


if __name__ == "__main__":
    main()
