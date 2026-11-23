from datetime import date

def format_created_at(value):
    if not value:
        return "Sem data"

    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")

    return str(value)

def status_class(status):
    status_normalized = (status or "").strip().lower()
    if status_normalized == "ativo":
        return "status-active"
    if status_normalized == "pendente":
        return "status-pending"
    if status_normalized == "inativo":
        return "status-inactive"

    return "status-neutral"

def format_relative_date(value, *, clock=date):
    if not value or not hasattr(value, "date"):
        return "Agora"

    days = (clock.today() - value.date()).days
    if days <= 0:
        return "Hoje"
    if days == 1:
        return "Ha 1 dia"

    return f"Ha {days} dias"

def present_get_admin_data(total_alunos, total_professores, matriculas_pendentes, matriculas_hoje, aluno_rows, professor_rows):
    alunos = [{'id': aluno.id, 'matricula': aluno.matricula, 'nome': aluno.nome, 'email': email, 'curso': aluno.curso_serie or 'Nao informado', 'status': aluno.status_matricula or 'Nao informado', 'status_class': status_class(aluno.status_matricula), 'created_at': aluno.created_at, 'created_at_label': format_created_at(aluno.created_at)} for aluno, email in aluno_rows]
    professores = [{'id': professor.id, 'nome': professor.nome, 'email': email, 'cpf': professor.cpf, 'disciplina': professor.disciplina_principal or 'Nao informado', 'created_at': professor.created_at, 'created_at_label': format_created_at(professor.created_at)} for professor, email in professor_rows]
    registros_recentes = [{'aluno_id': aluno['id'], 'nome': aluno['nome'], 'tipo': 'Matricula Escolar', 'detalhe': aluno['curso'], 'created_at': aluno['created_at'], 'created_at_label': aluno['created_at_label']} for aluno in alunos[:8]] + [{'aluno_id': None, 'nome': professor['nome'], 'tipo': 'Cadastro de Professor', 'detalhe': professor['disciplina'], 'created_at': professor['created_at'], 'created_at_label': professor['created_at_label']} for professor in professores[:8]]
    registros_recentes.sort(key=lambda item: item['created_at'].isoformat() if hasattr(item['created_at'], 'isoformat') else str(item['created_at'] or ''), reverse=True)
    return {'total_alunos': total_alunos, 'total_professores': total_professores, 'matriculas_pendentes': matriculas_pendentes, 'matriculas_hoje': matriculas_hoje, 'alunos': alunos, 'professores': professores, 'registros_recentes': registros_recentes[:8]}

def present_get_comunicados(comunicados):
    return [{'id': comunicado.id, 'titulo': comunicado.titulo, 'destinatario': comunicado.destinatario, 'mensagem': comunicado.mensagem, 'mensagem_resumo': comunicado.mensagem[:92] + '...' if len(comunicado.mensagem) > 95 else comunicado.mensagem, 'created_at_label': format_relative_date(comunicado.created_at)} for comunicado in comunicados]

def present_get_disciplinas(disciplinas):
    return [{'id': disciplina.id, 'nome': disciplina.nome, 'codigo': disciplina.codigo, 'carga_horaria': disciplina.carga_horaria} for disciplina in disciplinas]

def present_get_disciplinas_page_data(disciplinas, professores, professor_vinculos):
    return {'disciplinas': [{'id': disciplina.id, 'nome': disciplina.nome, 'codigo': disciplina.codigo, 'carga_horaria': disciplina.carga_horaria} for disciplina in disciplinas], 'professores': [{'id': professor.id, 'nome': professor.nome, 'disciplina': professor.disciplina_principal or 'Nao informado'} for professor in professores], 'professor_vinculos': [{'professor': professor.nome, 'disciplina': disciplina.nome, 'codigo': disciplina.codigo, 'data': format_created_at(vinculo.created_at)} for vinculo, professor, disciplina in professor_vinculos]}

def present_get_turmas_page_data(turmas, alunos, professores, disciplinas_por_professor, aluno_vinculos, professor_vinculos, disciplina_vinculos):
    return {'turmas': [{'id': turma.id, 'nome': turma.nome, 'codigo': turma.codigo, 'ano_letivo': turma.ano_letivo, 'turno': turma.turno or 'Nao informado'} for turma in turmas], 'alunos': [{'id': aluno.id, 'nome': aluno.nome, 'matricula': aluno.matricula} for aluno in alunos], 'professores': [{'id': professor.id, 'nome': professor.nome, 'disciplinas': ', '.join(disciplinas_por_professor.get(professor.id) or []) or 'Sem disciplina associada'} for professor in professores], 'aluno_vinculos': [{'aluno': aluno.nome, 'matricula': aluno.matricula, 'turma': turma.nome, 'codigo': turma.codigo, 'data': format_created_at(vinculo.created_at)} for vinculo, aluno, turma in aluno_vinculos], 'professor_vinculos': [{'professor': professor.nome, 'disciplina': ', '.join(disciplinas_por_professor.get(professor.id) or []) or 'Sem disciplina associada', 'turma': turma.nome, 'codigo': turma.codigo, 'data': format_created_at(vinculo.created_at)} for vinculo, professor, turma in professor_vinculos], 'disciplina_vinculos': [{'turma': turma.nome, 'codigo': turma.codigo, 'disciplina': disciplina.nome, 'disciplina_codigo': disciplina.codigo, 'data': format_created_at(vinculo.created_at)} for vinculo, turma, disciplina in disciplina_vinculos]}

def present_get_aluno_detail(aluno, email, documentos, solicitacoes):
    return {'aluno': {'versao': aluno.versao, 'id': aluno.id, 'nome': aluno.nome, 'email': email, 'cpf': aluno.cpf or 'Nao informado', 'cpf_value': aluno.cpf or '', 'matricula': aluno.matricula, 'curso': aluno.curso_serie or 'Nao informado', 'curso_value': aluno.curso_serie or '', 'foto_perfil': aluno.foto_perfil, 'status': aluno.status_matricula or 'Nao informado', 'status_value': aluno.status_matricula or '', 'data_nascimento': aluno.data_nascimento.strftime('%d/%m/%Y') if aluno.data_nascimento else 'Nao informado', 'data_nascimento_value': aluno.data_nascimento.isoformat() if aluno.data_nascimento else '', 'created_at_label': format_created_at(aluno.created_at)}, 'documentos': [{'titulo': documento.titulo, 'arquivo': documento.caminho_arquivo, 'data_envio': format_created_at(documento.data_envio)} for documento in documentos], 'solicitacoes_documentos': [{'id': solicitacao.id, 'titulo': solicitacao.titulo, 'mensagem': solicitacao.mensagem or 'Sem instrucoes adicionais.', 'status': solicitacao.status, 'status_label': 'Enviado' if solicitacao.status == 'enviado' else 'Pendente', 'data': format_created_at(solicitacao.created_at)} for solicitacao in solicitacoes]}

def present_get_professor_detail(professor, email, disciplinas, documentos, notas, arquivos_professor, solicitacoes):
    return {'professor': {'versao': professor.versao, 'id': professor.id, 'nome': professor.nome, 'email': email, 'cpf': professor.cpf or 'Nao informado', 'cpf_value': professor.cpf or '', 'telefone': professor.telefone or 'Nao informado', 'telefone_value': professor.telefone or '', 'disciplina': professor.disciplina_principal or 'Nao informado', 'disciplina_value': professor.disciplina_principal or '', 'formacao': professor.formacao_academica or 'Nao informado', 'formacao_value': professor.formacao_academica or '', 'regime': professor.regime_trabalho or 'Nao informado', 'regime_value': professor.regime_trabalho or '', 'foto_perfil': professor.foto_perfil, 'data_admissao': professor.data_admissao.strftime('%d/%m/%Y') if professor.data_admissao else 'Nao informado', 'data_admissao_value': professor.data_admissao.isoformat() if professor.data_admissao else '', 'created_at_label': format_created_at(professor.created_at)}, 'disciplinas': [{'nome': disciplina.nome, 'codigo': disciplina.codigo, 'carga_horaria': disciplina.carga_horaria, 'data': format_created_at(vinculo.created_at)} for vinculo, disciplina in disciplinas], 'documentos': [{'titulo': documento.titulo, 'arquivo': documento.caminho_arquivo, 'aluno': aluno.nome, 'disciplina': disciplina.nome, 'data_envio': format_created_at(documento.data_envio)} for documento, aluno, disciplina in documentos], 'arquivos_professor': [{'titulo': documento.titulo, 'arquivo': documento.caminho_arquivo, 'disciplina': disciplina.nome, 'data_envio': format_created_at(documento.data_envio)} for documento, disciplina in arquivos_professor], 'solicitacoes_documentos': [{'id': solicitacao.id, 'titulo': solicitacao.titulo, 'mensagem': solicitacao.mensagem or 'Sem instrucoes adicionais.', 'status': solicitacao.status, 'status_label': 'Enviado' if solicitacao.status == 'enviado' else 'Pendente', 'data': format_created_at(solicitacao.created_at)} for solicitacao in solicitacoes], 'notas': [{'aluno': aluno.nome, 'disciplina': f'{disciplina.nome} · {avaliacao.titulo} ({periodo.nome})', 'nota': nota.valor, 'observacao': nota.observacao or 'Sem observacao.', 'data': format_created_at(nota.atualizada_em)} for nota, aluno, disciplina, avaliacao, periodo in notas]}
