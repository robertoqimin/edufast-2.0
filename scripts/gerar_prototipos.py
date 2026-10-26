"""Gera as pranchas SVG de apresentação. Apenas biblioteca padrão; sem dados reais."""
from html import escape
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / 'Protótipo' / 'edufast'
INK = '#162f35'
MUTED = '#526b72'


def rect(x, y, w, h, fill, radius=12, stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def text(x, y, value, size=14, fill=INK, weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}">{escape(str(value))}</text>'


def pill(x, y, value, fill='#e2f3ed', color='#18624d', width=110):
    return rect(x, y, width, 28, fill, 14) + text(x+12, y+19, value, 12, color, 600)


def card(x, label, value, note):
    return ''.join([
        rect(x, 196, 212, 112, '#ffffff', 14, '#dce6e5'),
        text(x+18, 225, label, 13, MUTED),
        text(x+18, 262, value, 29, INK, 700),
        text(x+18, 287, note, 12, MUTED),
    ])


SCREENS = {
    'painel': {
        'title': 'Sua escola, em um só lugar.', 'section': 'Visão geral',
        'subtitle': 'Uma visão clara do dia para organizar o que vem a seguir.',
        'action': 'Ver agenda', 'tag': 'PROPOSTA VISUAL',
        'cards': [('Alunos', '480', 'Exemplo de visão consolidada'), ('Turmas', '18', 'Organização acadêmica'),
                  ('Professores', '32', 'Equipe pedagógica'), ('Pendências', '07', 'Itens para acompanhar')],
        'table': 'Prioridades da secretaria', 'cols': ['TAREFA', 'ÁREA', 'SITUAÇÃO'],
        'rows': [('Conferir documentos de matrícula', 'Secretaria', 'A revisar'),
                 ('Organizar vínculos da turma 8º A', 'Acadêmico', 'Em andamento'),
                 ('Publicar comunicado da reunião', 'Comunicação', 'Rascunho'),
                 ('Revisar ajustes de jornada', 'Pessoas · futuro', 'Planejado')],
        'aside': 'Um dia mais organizado',
        'steps': [('01', 'Encontre o que precisa', 'Buscas e atalhos por contexto.'),
                  ('02', 'Resolva as pendências', 'Ações com prioridade visível.'),
                  ('03', 'Acompanhe o resultado', 'Status claros em cada etapa.')],
    },
    'turmas': {
        'title': 'Turmas bem organizadas.', 'section': 'Turmas',
        'subtitle': 'Alunos, disciplinas e professores com contexto em cada vínculo.',
        'action': '+ Nova turma', 'tag': 'PROPOSTA VISUAL',
        'cards': [('Turmas', '18', 'No período de exemplo'), ('Alunos vinculados', '480', 'Dados de demonstração'),
                  ('Professores', '32', 'Equipe de exemplo'), ('Turnos', '02', 'Manhã e tarde')],
        'table': 'Turmas da escola', 'cols': ['TURMA', 'ALUNOS / TURNO', 'SITUAÇÃO'],
        'rows': [('6º ano A', '28 · Manhã', 'Ativa'), ('7º ano A', '26 · Manhã', 'Ativa'),
                 ('8º ano A', '30 · Tarde', 'Ativa'), ('9º ano B', '27 · Tarde', 'Ativa')],
        'aside': 'Detalhe da turma',
        'steps': [('01', 'Alunos e matrículas', 'Consulte a composição da turma.'),
                  ('02', 'Disciplinas e docentes', 'Revise as atribuições de ensino.'),
                  ('03', 'Atividades e documentos', 'Acesse a rotina acadêmica.')],
    },
    'ponto': {
        'title': 'Jornadas com mais clareza.', 'section': 'Folha de ponto',
        'subtitle': 'Consulte marcações e revise exceções antes do fechamento.',
        'action': 'Revisar ajustes', 'tag': 'MÓDULO PLANEJADO',
        'cards': [('Colaboradores', '42', 'Exemplo de equipe'), ('Jornadas regulares', '36', 'Sem pendências no exemplo'),
                  ('Ajustes solicitados', '04', 'Aguardam análise'), ('Justificativas', '02', 'Aguardam documentação')],
        'table': 'Espelho de ponto · demonstração', 'cols': ['COLABORADOR', 'JORNADA', 'SITUAÇÃO'],
        'rows': [('Ana · Secretaria', '08:00 – 17:00', 'Regular'),
                 ('Bruno · Professor', '07:00 – 13:00', 'A revisar'),
                 ('Carla · Coordenação', '08:00 – 17:00', 'Regular'),
                 ('Diego · Apoio', '09:00 – 18:00', 'Justificativa')],
        'aside': 'Revisão com contexto',
        'steps': [('01', 'Consultar marcações', 'Exiba os registros da jornada.'),
                  ('02', 'Analisar a justificativa', 'Registre o motivo do ajuste.'),
                  ('03', 'Aprovar e preservar', 'Mantenha o histórico da decisão.')],
    },
    'pagamentos': {
        'title': 'Pagamentos sob controle.', 'section': 'Pagamentos',
        'subtitle': 'Obrigações da escola com revisão e acompanhamento por competência.',
        'action': 'Ver competência', 'tag': 'MÓDULO PLANEJADO',
        'cards': [('Folha prevista', 'R$ 84 mil', 'Exemplo · colaboradores'), ('Contas a pagar', 'R$ 12 mil', 'Exemplo · fornecedores'),
                  ('Recebimentos', 'R$ 96 mil', 'Exemplo · financeiro escolar'), ('Em revisão', '03', 'Sem pagamento automático')],
        'table': 'Obrigações · dados fictícios', 'cols': ['DESCRIÇÃO', 'VALOR PREVISTO', 'SITUAÇÃO'],
        'rows': [('Folha · equipe pedagógica', 'R$ 62.000,00', 'A revisar'),
                 ('Folha · equipe administrativa', 'R$ 22.000,00', 'Rascunho'),
                 ('Serviços e fornecedores', 'R$ 12.000,00', 'A revisar'),
                 ('Demonstrativos da competência', 'Consulta', 'Planejado')],
        'aside': 'Do cálculo à confirmação',
        'steps': [('01', 'Preparar e conferir', 'Revise eventos e valores.'),
                  ('02', 'Aprovar o fechamento', 'Separe revisão e autorização.'),
                  ('03', 'Confirmar a transação', 'Concilie com o pagamento real.')],
    },
}


def render(key, data):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760" role="img" aria-labelledby="title desc">',
             f'<title id="title">EduFast — {escape(data["section"])} — protótipo</title>',
             '<desc id="desc">Prancha conceitual estática com dados fictícios. Não representa uma tela funcional.</desc>',
             '<g font-family="Segoe UI, Arial, sans-serif">',
             rect(0, 0, 1200, 760, '#f3f7f6', 0), rect(0, 0, 228, 760, '#102e32', 0),
             rect(24, 28, 36, 36, '#6fe1b8', 10), text(34, 53, 'E', 24, '#102e32', 800),
             text(72, 53, 'EduFast', 25, '#ffffff', 700), text(26, 92, 'GESTÃO ESCOLAR', 11, '#b1c9ca', 600),
             text(26, 137, 'ESPAÇO DE TRABALHO', 10, '#a5c3c4', 600)]
    nav = ['Visão geral', 'Turmas', 'Alunos e professores', 'Disciplinas', 'Documentos', 'Folha de ponto', 'Pagamentos']
    for i, item in enumerate(nav):
        y = 159+i*49
        selected = item == data['section']
        if selected:
            parts.append(rect(16, y, 196, 39, '#25564f', 9))
        parts += [rect(30, y+12, 13, 13, '#6fe1b8' if selected else '#6d9698', 4),
                  text(55, y+26, item, 13, '#ffffff' if selected else '#bed2d3', 600 if selected else 400)]
    parts += [text(26, 677, 'Escola Horizonte', 14, '#ffffff', 600),
              text(26, 699, 'Instituição fictícia', 12, '#bed2d3'),
              rect(228, 0, 972, 70, '#ffffff', 0), text(264, 42, 'Escola Horizonte  /  '+data['section'], 13, MUTED),
              pill(947, 21, data['tag'], '#edf4f1', '#28574b', 225),
              text(264, 119, data['title'], 30, INK, 700),
              text(264, 149, data['subtitle'], 14, MUTED),
              text(264, 177, 'APRESENTAÇÃO DO PRODUTO · DADOS FICTÍCIOS', 10, MUTED, 600)]
    for i, values in enumerate(data['cards']):
        parts.append(card(264+i*230, *values))
    parts += [rect(264, 330, 580, 337, '#ffffff', 14, '#dce6e5'),
              text(284, 361, data['table'], 16, INK, 600),
              rect(284, 379, 374, 34, '#f3f7f6', 7), text(296, 401, 'Buscar por nome ou identificação…', 12, MUTED),
              pill(672, 382, 'Filtrar', width=150),
              rect(284, 429, 540, 31, '#f3f7f6', 4)]
    for x, value in zip([296, 551, 702], data['cols']):
        parts.append(text(x, 450, value, 10, MUTED, 600))
    for i, (name, value, status) in enumerate(data['rows']):
        y = 484+i*49
        parts += [text(296, y, name, 12, INK, 500), text(551, y, value, 12, MUTED)]
        ok = status in ('Ativa', 'Regular')
        parts.append(pill(693, y-20, status, '#e2f3ed' if ok else '#fff1d9', '#18624d' if ok else '#7b5510', 124))
        parts.append(f'<path d="M284 {y+15} H824" stroke="#edf1f0"/>')
    parts += [rect(862, 330, 304, 337, '#ffffff', 14, '#dce6e5'), text(882, 361, data['aside'], 16, INK, 600)]
    for i, (number, title, note) in enumerate(data['steps']):
        y = 401+i*72
        parts += [pill(882, y-17, number, width=37), text(931, y, title, 13, INK, 600),
                  text(882, y+26, note, 12, MUTED)]
    parts += [rect(882, 613, 264, 35, '#18624d', 8), text(900, 636, data['action'], 13, '#ffffff', 600),
              text(264, 706, 'Protótipo conceitual · As ações ilustradas não executam operações.', 12, MUTED),
              text(264, 729, 'Direção de UX/UI: menos etapas, contexto visível e feedback claro.', 12, MUTED),
              text(1041, 729, 'EDUFAST 2.0', 11, '#18624d', 700), '</g></svg>']
    return '\n'.join(parts)


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for key, data in SCREENS.items():
        (OUTPUT / f'{key}.svg').write_text(render(key, data), encoding='utf-8')
    print(f'{len(SCREENS)} protótipos gerados em {OUTPUT}')
