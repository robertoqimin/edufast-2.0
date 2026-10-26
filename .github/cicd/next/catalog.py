"""Contratos propostos para revisão. Não implementa regras ou respostas da aplicação."""
API = []
UNIT = []
from sample_files import pdf


def api(code, area, title, actor, method, path, status, **checks):
    API.append(dict(id=code, area=area, title=title, actor=actor, method=method,
                    path=path, status=status, **checks))


def unit(code, area, title, function, arguments, **expected):
    UNIT.append(dict(id=code, area=area, title=title, function=function,
                     arguments=arguments, **expected))


S = '/api/v1/escolas/1'
B = '/api/v1/escolas/2'

api('API-001', 'Escolas', 'Sem autenticação não lista escolas', None, 'GET', '/api/v1/escolas', 401, error='unauthenticated')
api('API-002', 'Escolas', 'Gestor lista apenas a própria escola', 'gestor_a', 'GET', '/api/v1/escolas', 200, ids=[1])
api('API-003', 'Escolas', 'Conta com dois vínculos lista as duas escolas', 'dupla', 'GET', '/api/v1/escolas', 200, ids=[1, 2])
api('API-004', 'Escolas', 'Conta sem vínculo não ganha escola automaticamente', 'sem_vinculo', 'GET', '/api/v1/escolas', 200, ids=[])
api('API-005', 'Escolas', 'Administrador da plataforma cria instituição', 'plataforma', 'POST', '/api/v1/escolas', 201,
    json={'nome': 'Escola Gama', 'codigo': 'GAMA'}, equals={'data.nome': 'Escola Gama'}, db=[{'table': 'escolas', 'where': {'codigo': 'GAMA'}, 'count': 1}])
api('API-006', 'Escolas', 'Gestor local não cria outra instituição', 'gestor_a', 'POST', '/api/v1/escolas', 403,
    json={'nome': 'Escola Gama', 'codigo': 'GAMA'}, error='forbidden', db=[{'table': 'escolas', 'where': {'codigo': 'GAMA'}, 'count': 0}])
api('API-007', 'Escolas', 'Seleciona escola autorizada', 'gestor_a', 'POST', '/api/v1/contexto', 200, json={'escola_id': 1}, equals={'data.escola_id': 1})
api('API-008', 'Escolas', 'Selecionar escola alheia não concede acesso', 'gestor_a', 'POST', '/api/v1/contexto', 404, json={'escola_id': 2}, error='not_found')
api('API-009', 'Escolas', 'Conta dupla mantém papel de aluno na escola B', 'dupla', 'POST', B+'/turmas', 403,
    json={'nome': 'Sem permissão', 'codigo': 'NEGADA', 'periodo_id': 2, 'turno': 'manha'}, error='forbidden')
api('API-010', 'Escolas', 'Revogação invalida o token já emitido', 'secretaria_a', 'GET', S+'/alunos', 403,
    mutate={'table': 'participacoes_escolas', 'where': {'usuario_id': 3, 'escola_id': 1}, 'values': {'status': 'revogada'}}, error='membership_inactive')
api('API-011', 'Escolas', 'Escola suspensa bloqueia escrita acadêmica', 'gestor_a', 'POST', S+'/turmas', 403,
    json={'nome': 'Bloqueada', 'codigo': 'SUSP', 'periodo_id': 1, 'turno': 'manha'},
    mutate={'table': 'escolas', 'where': {'id': 1}, 'values': {'status': 'suspensa'}}, error='school_inactive')
api('API-012', 'Escolas', 'Admin da plataforma não lê conteúdo acadêmico sem vínculo', 'plataforma', 'GET', S+'/alunos', 404, error='not_found')

api('API-013', 'Convites', 'Gestor convida membro local sem enviar email real no teste', 'gestor_a', 'POST', S+'/convites', 201,
    json={'email': 'nova@example.test', 'papel': 'secretaria'}, equals={'data.escola_id': 1, 'data.papel': 'secretaria'}, db=[{'table': 'convites_escolas', 'where': {'email': 'nova@example.test', 'escola_id': 1}, 'count': 1}])
api('API-014', 'Convites', 'Professor não concede papel de gestor', 'professor_a', 'POST', S+'/convites', 403,
    json={'email': 'nova@example.test', 'papel': 'gestor'}, error='forbidden')
api('API-015', 'Convites', 'Aceitar convite cria apenas o vínculo indicado', 'convidado', 'POST', '/api/v1/convites/aceitar', 200,
    json={'token': 'convite-ci-valido'}, db=[{'table': 'participacoes_escolas', 'where': {'usuario_id': 11, 'escola_id': 1, 'papel': 'secretaria'}, 'count': 1}, {'table': 'participacoes_escolas', 'where': {'usuario_id': 11, 'escola_id': 2}, 'count': 0}])
api('API-016', 'Convites', 'Convite expirado não cria vínculo', 'convidado', 'POST', '/api/v1/convites/aceitar', 410,
    json={'token': 'convite-ci-expirado'}, error='invitation_expired', db=[{'table': 'participacoes_escolas', 'where': {'usuario_id': 11}, 'count': 0}])
api('API-017', 'Convites', 'Convite não pode ser utilizado por outro email', 'sem_vinculo', 'POST', '/api/v1/convites/aceitar', 403,
    json={'token': 'convite-ci-valido'}, error='invitation_recipient_mismatch')
api('API-018', 'Convites', 'Segundo aceite não duplica participação', 'convidado', 'POST', '/api/v1/convites/aceitar', 409,
    before=[{'method': 'POST', 'path': '/api/v1/convites/aceitar', 'json': {'token': 'convite-ci-valido'}, 'status': 200}],
    json={'token': 'convite-ci-valido'}, error='invitation_used', db=[{'table': 'participacoes_escolas', 'where': {'usuario_id': 11, 'escola_id': 1}, 'count': 1}])

api('API-019', 'Períodos', 'Secretaria cria período válido', 'secretaria_a', 'POST', S+'/periodos', 201,
    json={'nome': '2027', 'inicio': '2027-02-01', 'fim': '2027-12-15'}, equals={'data.escola_id': 1})
api('API-020', 'Períodos', 'Fim anterior ao início é rejeitado', 'secretaria_a', 'POST', S+'/periodos', 422,
    json={'nome': 'Inválido', 'inicio': '2027-12-01', 'fim': '2027-02-01'}, error='invalid_period')
api('API-021', 'Períodos', 'Período alheio não aparece por ID direto', 'secretaria_a', 'GET', S+'/periodos/2', 404, error='not_found')
api('API-022', 'Períodos', 'Fechamento preserva período e registros', 'gestor_a', 'POST', S+'/periodos/1/fechar', 200,
    equals={'data.status': 'fechado'}, db=[{'table': 'periodos_letivos', 'where': {'id': 1, 'status': 'fechado'}, 'count': 1}, {'table': 'matriculas', 'where': {'id': 1}, 'count': 1}])

api('API-023', 'Pessoas', 'Busca de alunos não revela nome da outra escola', 'secretaria_a', 'GET', S+'/alunos?q=Aluno', 200, ids=[1, 3], absent=['Aluno Beta', 'aluno.b@example.test'])
api('API-024', 'Pessoas', 'Detalhe de aluno externo retorna 404', 'secretaria_a', 'GET', S+'/alunos/2', 404, error='not_found')
api('API-025', 'Pessoas', 'Edição de aluno externo não altera o banco', 'secretaria_a', 'PATCH', S+'/alunos/2', 404,
    json={'nome': 'Alterado'}, error='not_found', db=[{'table': 'alunos', 'where': {'id': 2, 'nome': 'Aluno Beta'}, 'count': 1}])
api('API-026', 'Pessoas', 'Aluno consulta seu cadastro', 'aluno_a', 'GET', S+'/alunos/1', 200, equals={'data.nome': 'Aluno Alfa'})
api('API-027', 'Pessoas', 'Aluno não consulta outro aluno da mesma escola', 'aluno_a', 'GET', S+'/alunos/3', 404, error='not_found')
api('API-028', 'Pessoas', 'Professor externo não aparece em busca', 'secretaria_a', 'GET', S+'/professores', 200, ids=[1], absent=['Professor Beta'])
api('API-029', 'Pessoas', 'Secretaria cria aluno na escola ativa', 'secretaria_a', 'POST', S+'/alunos', 201,
    json={'nome': 'Nova Aluna', 'email': 'nova.aluna@example.test', 'matricula': 'ALFA-NEW'},
    equals={'data.escola_id': 1}, db=[{'table': 'alunos', 'where': {'matricula': 'ALFA-NEW', 'escola_id': 1}, 'count': 1}])
api('API-030', 'Pessoas', 'Campo escola_id no corpo não redireciona gravação', 'secretaria_a', 'POST', S+'/alunos', 422,
    json={'nome': 'Teste', 'email': 'teste@example.test', 'matricula': 'INJETADA', 'escola_id': 2}, error='scope_mismatch', db=[{'table': 'alunos', 'where': {'matricula': 'INJETADA'}, 'count': 0}])
api('API-031', 'Pessoas', 'Matrícula pode repetir em escolas diferentes', 'gestor_b', 'POST', B+'/alunos', 201,
    json={'nome': 'Aluna Beta Dois', 'email': 'beta.dois@example.test', 'matricula': 'A001'}, equals={'data.escola_id': 2})
api('API-032', 'Pessoas', 'Matrícula duplicada na mesma escola é rejeitada', 'secretaria_a', 'POST', S+'/alunos', 409,
    json={'nome': 'Duplicada', 'email': 'duplicada@example.test', 'matricula': 'A001'}, error='duplicate_student_number')

api('API-033', 'Turmas', 'Lista apenas turmas da escola', 'secretaria_a', 'GET', S+'/turmas', 200, ids=[1, 3])
api('API-034', 'Turmas', 'Cria turma vinculada ao período local', 'secretaria_a', 'POST', S+'/turmas', 201,
    json={'nome': '7º A', 'codigo': '7A', 'periodo_id': 1, 'turno': 'manha'}, equals={'data.escola_id': 1, 'data.periodo_id': 1})
api('API-035', 'Turmas', 'Período de outra escola não pode receber turma', 'secretaria_a', 'POST', S+'/turmas', 404,
    json={'nome': 'Inválida', 'codigo': 'CROSS', 'periodo_id': 2}, error='not_found', db=[{'table': 'turmas', 'where': {'codigo': 'CROSS'}, 'count': 0}])
api('API-036', 'Turmas', 'Código duplicado no mesmo período é rejeitado', 'secretaria_a', 'POST', S+'/turmas', 409,
    json={'nome': 'Duplicada', 'codigo': '6A', 'periodo_id': 1}, error='duplicate_class_code')
api('API-037', 'Turmas', 'Arquivamento mantém matrículas históricas', 'secretaria_a', 'POST', S+'/turmas/1/arquivar', 200,
    equals={'data.status': 'arquivada'}, db=[{'table': 'matriculas', 'where': {'turma_id': 1}, 'count': 1}])
api('API-038', 'Disciplinas', 'Cria disciplina local', 'coordenacao_a', 'POST', S+'/disciplinas', 201,
    json={'nome': 'História', 'codigo': 'HIS', 'carga_horaria': 80}, equals={'data.escola_id': 1})
api('API-039', 'Disciplinas', 'Oferta cruza apenas dados da mesma escola', 'coordenacao_a', 'POST', S+'/ofertas', 404,
    json={'turma_id': 1, 'disciplina_id': 2, 'periodo_id': 1}, error='not_found')
api('API-040', 'Disciplinas', 'Oferta válida é criada', 'coordenacao_a', 'POST', S+'/ofertas', 201,
    json={'turma_id': 3, 'disciplina_id': 3, 'periodo_id': 1}, equals={'data.turma_id': 3, 'data.escola_id': 1})

api('API-041', 'Matrículas', 'Matricula aluno local em turma local', 'secretaria_a', 'POST', S+'/matriculas', 201,
    json={'aluno_id': 3, 'turma_id': 3, 'periodo_id': 1}, equals={'data.status': 'ativa'}, db=[{'table': 'matriculas', 'where': {'aluno_id': 3, 'turma_id': 3, 'status': 'ativa'}, 'count': 1}])
api('API-042', 'Matrículas', 'Repetir matrícula não duplica registro', 'secretaria_a', 'POST', S+'/matriculas', 409,
    json={'aluno_id': 1, 'turma_id': 1, 'periodo_id': 1}, error='duplicate_enrollment', db=[{'table': 'matriculas', 'where': {'aluno_id': 1, 'turma_id': 1}, 'count': 1}])
api('API-043', 'Matrículas', 'Aluno externo não pode ser matriculado', 'secretaria_a', 'POST', S+'/matriculas', 404,
    json={'aluno_id': 2, 'turma_id': 1, 'periodo_id': 1}, error='not_found')
api('API-044', 'Matrículas', 'Turma arquivada não recebe matrícula', 'secretaria_a', 'POST', S+'/matriculas', 409,
    json={'aluno_id': 3, 'turma_id': 3, 'periodo_id': 1}, mutate={'table': 'turmas', 'where': {'id': 3}, 'values': {'status': 'arquivada'}}, error='class_archived')
api('API-045', 'Matrículas', 'Período fechado bloqueia matrícula', 'secretaria_a', 'POST', S+'/matriculas', 409,
    json={'aluno_id': 3, 'turma_id': 3, 'periodo_id': 1}, mutate={'table': 'periodos_letivos', 'where': {'id': 1}, 'values': {'status': 'fechado'}}, error='period_closed')
api('API-046', 'Matrículas', 'Transferência encerra vínculo antigo e mantém histórico', 'secretaria_a', 'POST', S+'/matriculas/1/transferir', 201,
    json={'turma_destino_id': 3, 'motivo': 'Mudança de turno'},
    db=[{'table': 'matriculas', 'where': {'id': 1, 'status': 'transferida'}, 'count': 1}, {'table': 'matriculas', 'where': {'aluno_id': 1, 'turma_id': 3, 'status': 'ativa'}, 'count': 1}])
api('API-047', 'Matrículas', 'Transferência para outra escola não altera origem', 'secretaria_a', 'POST', S+'/matriculas/1/transferir', 404,
    json={'turma_destino_id': 2, 'motivo': 'Inválida'}, error='not_found', db=[{'table': 'matriculas', 'where': {'id': 1, 'status': 'ativa'}, 'count': 1}])

api('API-048', 'Docência', 'Coordenação atribui professor à oferta exata', 'coordenacao_a', 'POST', S+'/atribuicoes', 201,
    json={'professor_id': 1, 'oferta_id': 3}, equals={'data.professor_id': 1, 'data.oferta_id': 3})
api('API-049', 'Docência', 'Professor externo não recebe atribuição local', 'coordenacao_a', 'POST', S+'/atribuicoes', 404,
    json={'professor_id': 2, 'oferta_id': 1}, error='not_found')
api('API-050', 'Docência', 'Professor não se autoatribui', 'professor_a', 'POST', S+'/atribuicoes', 403,
    json={'professor_id': 1, 'oferta_id': 3}, error='forbidden')
api('API-051', 'Notas', 'Professor lança nota apenas na própria oferta', 'professor_a', 'POST', S+'/ofertas/1/notas', 201,
    json={'aluno_id': 1, 'nota': 8.5}, equals={'data.oferta_id': 1, 'data.nota': 8.5})
api('API-052', 'Notas', 'Mesmo professor em pares separados não autoriza outra oferta', 'professor_a', 'POST', S+'/ofertas/3/notas', 403,
    json={'aluno_id': 3, 'nota': 8.5}, error='assignment_required')
api('API-053', 'Notas', 'Revogação docente bloqueia token existente', 'professor_a', 'POST', S+'/ofertas/1/notas', 403,
    json={'aluno_id': 1, 'nota': 8.5}, mutate={'table': 'atribuicoes_docentes', 'where': {'id': 1}, 'values': {'ativo': False}}, error='assignment_required')
api('API-054', 'Notas', 'Nota fora da escala não é gravada', 'professor_a', 'POST', S+'/ofertas/1/notas', 422,
    json={'aluno_id': 1, 'nota': 11}, error='invalid_grade')
api('API-055', 'Atividades', 'Professor cria atividade na oferta atribuída', 'professor_a', 'POST', S+'/ofertas/1/atividades', 201,
    json={'titulo': 'Exercício', 'descricao': 'Dados fictícios', 'data_entrega': '2099-11-15'}, equals={'data.escola_id': 1, 'data.oferta_id': 1})
api('API-056', 'Atividades', 'Aluno não cria atividade', 'aluno_a', 'POST', S+'/ofertas/1/atividades', 403,
    json={'titulo': 'Indevida'}, error='forbidden')

api('API-057', 'Documentos', 'Secretaria solicita documento de aluno local', 'secretaria_a', 'POST', S+'/solicitacoes-documentos', 201,
    json={'aluno_id': 1, 'titulo': 'Comprovante'}, equals={'data.status': 'pendente', 'data.escola_id': 1})
api('API-058', 'Documentos', 'Aluno envia arquivo da própria solicitação', 'aluno_a', 'POST', S+'/solicitacoes-documentos/1/arquivo', 201,
    upload={'filename': 'comprovante.pdf', 'content_type': 'application/pdf', 'content': pdf('COMPROVANTE-CI')},
    followup={'method': 'GET', 'path': S+'/documentos/{data.id}/arquivo', 'status': 200, 'body_contains': 'COMPROVANTE-CI'},
    db=[{'table': 'solicitacoes_documentos', 'where': {'id': 1, 'status': 'enviado'}, 'count': 1}])
api('API-059', 'Documentos', 'Documento de outra escola não é baixado', 'secretaria_a', 'GET', S+'/documentos/2/arquivo', 404, error='not_found', absent=['DOCUMENTO-BETA'])
api('API-060', 'Documentos', 'Aluno não envia documento de colega', 'aluno_a', 'POST', S+'/solicitacoes-documentos/3/arquivo', 404,
    upload={'filename': 'comprovante.pdf', 'content_type': 'application/pdf', 'content': pdf('COMPROVANTE-CI')}, error='not_found')
api('API-061', 'Documentos', 'Executável disfarçado não é aceito', 'aluno_a', 'POST', S+'/solicitacoes-documentos/1/arquivo', 422,
    upload={'filename': 'documento.pdf', 'content_type': 'application/pdf', 'content': 'MZ-not-a-pdf'}, error='invalid_file')
api('API-062', 'Documentos', 'Arquivo acima de 16 MiB é recusado', 'aluno_a', 'POST', S+'/solicitacoes-documentos/1/arquivo', 413,
    upload={'filename': 'grande.pdf', 'content_type': 'application/pdf', 'size': 16*1024*1024+1}, error='payload_too_large')
api('API-063', 'Documentos', 'Download autorizado entrega bytes e anexo', 'secretaria_a', 'GET', S+'/documentos/1/arquivo', 200,
    body_contains='DOCUMENTO-ALFA', headers_contains={'Content-Disposition': 'attachment'})
api('API-064', 'Documentos', 'Foto de perfil externa também exige escopo', 'secretaria_a', 'GET', S+'/alunos/2/foto', 404, error='not_found')

api('API-065', 'Comunicação', 'Comunicado é criado na escola local', 'secretaria_a', 'POST', S+'/comunicados', 201,
    json={'titulo': 'Reunião', 'mensagem': 'Comunicado de teste', 'destinatario': 'alunos'}, equals={'data.escola_id': 1})
api('API-066', 'Comunicação', 'Aluno não lê comunicado restrito à equipe', 'aluno_a', 'GET', S+'/comunicados/3', 404, error='not_found')
api('API-067', 'Comunicação', 'Listagem não revela comunicado da escola B', 'secretaria_a', 'GET', S+'/comunicados', 200, ids=[1, 3], absent=['Comunicado Beta'])
api('API-068', 'Painel', 'Indicadores contam apenas a escola local', 'secretaria_a', 'GET', S+'/painel', 200,
    equals={'data.alunos': 2, 'data.turmas': 2, 'data.professores': 1, 'data.escola_id': 1})
api('API-069', 'Painel', 'Paginação é executada no servidor', 'secretaria_a', 'GET', S+'/alunos?page=1&per_page=1', 200,
    ids=[1], equals={'meta.total': 2, 'meta.page': 1, 'meta.per_page': 1})
api('API-070', 'Painel', 'Página inválida recebe erro de validação', 'secretaria_a', 'GET', S+'/alunos?page=0', 422, error='invalid_pagination')
api('API-071', 'Exportação', 'Exportação não inclui dados externos', 'secretaria_a', 'GET', S+'/alunos/exportacao', 200,
    body_contains='Aluno Alfa', absent=['Aluno Beta'], headers_contains={'Content-Disposition': 'attachment', 'Content-Type': 'text/csv'})
api('API-072', 'Auditoria', 'Ação administrativa registra ator e escola', 'secretaria_a', 'POST', S+'/turmas/1/arquivar', 200,
    db=[{'table': 'eventos_auditoria', 'where': {'escola_id': 1, 'ator_id': 3, 'acao': 'turma.arquivada', 'recurso_id': 1}, 'count': 1}])
api('API-073', 'Compatibilidade', 'Rota antiga de detalhe não ignora isolamento', 'secretaria_a', 'GET', '/admin/alunos/2', 404, absent=['Aluno Beta'])
api('API-074', 'Compatibilidade', 'Busca antiga também aplica contexto da escola', 'professor_a', 'GET', '/alunos/busca?termo=Aluno', 200, absent=['Aluno Beta'])
api('API-075', 'Compatibilidade', 'Arquivo antigo não fica público pelo nome', None, 'GET', '/arquivos/download/documento-beta.pdf', 401, absent=['DOCUMENTO-BETA'])
api('API-076', 'Compatibilidade', 'Cadastro público não aceita papel privilegiado', None, 'POST', '/cadastro', 400,
    json={'email': 'invasor@example.test', 'senha': 'Senha-ci-123456', 'nome': 'Teste', 'tipo': 'gestor', 'escola_id': 2},
    db=[{'table': 'participacoes_escolas', 'where': {'escola_id': 2}, 'count': 3}])
api('API-077', 'Cache', 'Alternar escola não reaproveita painel privado anterior', 'dupla', 'GET', B+'/painel', 403,
    before=[{'method': 'GET', 'path': S+'/painel', 'status': 200}], error='forbidden')
api('API-078', 'Matrículas', 'Duas requisições concorrentes criam apenas uma matrícula', 'secretaria_a', 'POST', S+'/matriculas', [201, 409],
    json={'aluno_id': 3, 'turma_id': 3, 'periodo_id': 1}, concurrent=2, backends=['mysql'], conflict_error='duplicate_enrollment', db=[{'table': 'matriculas', 'where': {'aluno_id': 3, 'turma_id': 3}, 'count': 1}])
api('API-079', 'Convites', 'Dois aceites concorrentes não duplicam participação', 'convidado', 'POST', '/api/v1/convites/aceitar', [200, 409],
    json={'token': 'convite-ci-valido'}, concurrent=2, backends=['mysql'], conflict_error='invitation_used', db=[{'table': 'participacoes_escolas', 'where': {'usuario_id': 11, 'escola_id': 1}, 'count': 1}])
api('API-080', 'Compatibilidade', 'Foto antiga não fica pública pelo nome', None, 'GET', '/arquivos/perfil/perfil_beta.png', 401, absent=['FOTO-BETA'])
api('API-081', 'Compatibilidade', 'Download antigo autenticado não ignora escola', 'secretaria_a', 'GET', '/arquivos/download/documento-beta.pdf', 404, absent=['DOCUMENTO-BETA'])
api('API-082', 'Compatibilidade', 'Foto antiga autenticada não ignora escola', 'secretaria_a', 'GET', '/arquivos/perfil/perfil_beta.png', 404, absent=['FOTO-BETA'])
api('API-083', 'Pessoas', 'Secretaria cadastra professor apenas na escola local', 'secretaria_a', 'POST', S+'/professores', 201,
    json={'nome': 'Docente Novo', 'email': 'docente.novo@example.test', 'cpf': '12345000350'}, equals={'data.escola_id': 1},
    db=[{'table': 'professores', 'where': {'escola_id': 1, 'cpf': '12345000350'}, 'count': 1}, {'table': 'professores', 'where': {'escola_id': 2, 'cpf': '12345000350'}, 'count': 0}])
api('API-084', 'Compatibilidade', 'Cadastro público de aluno não cria vínculo na escola informada', None, 'POST', '/cadastro', 403,
    json={'email': 'publico@example.test', 'senha': 'Senha-ci-123456', 'nome': 'Teste', 'tipo': 'aluno', 'escola_id': 2, 'matricula': 'PUBLICA'},
    db=[{'table': 'alunos', 'where': {'matricula': 'PUBLICA'}, 'count': 0}, {'table': 'participacoes_escolas', 'where': {'escola_id': 2}, 'count': 3}])
api('API-085', 'Escolas', 'Redução de papel bloqueia token emitido antes da mudança', 'secretaria_a', 'POST', S+'/turmas', 403,
    json={'nome': 'Negada', 'codigo': 'NEGADA', 'periodo_id': 1}, error='forbidden',
    mutate={'table': 'participacoes_escolas', 'where': {'usuario_id': 3, 'escola_id': 1}, 'values': {'papel': 'aluno'}})

member = {'usuario_id': 3, 'escola_id': 1, 'papel': 'secretaria', 'status': 'ativa'}
unit('UNIT-001', 'Permissões', 'Secretaria consulta recurso local', 'authorize', {'member': member, 'resource': {'escola_id': 1, 'tipo': 'aluno'}, 'action': 'read'}, result=True)
unit('UNIT-002', 'Permissões', 'Mesmo papel não permite recurso externo', 'authorize', {'member': member, 'resource': {'escola_id': 2, 'tipo': 'aluno'}, 'action': 'read'}, error='not_found', status=404)
unit('UNIT-003', 'Permissões', 'Vínculo revogado bloqueia acesso', 'authorize', {'member': {**member, 'status': 'revogada'}, 'resource': {'escola_id': 1, 'tipo': 'aluno'}, 'action': 'read'}, error='membership_inactive', status=403)
unit('UNIT-004', 'Permissões', 'Aluno só consulta seu próprio cadastro', 'authorize', {'member': {**member, 'usuario_id': 6, 'papel': 'aluno'}, 'resource': {'escola_id': 1, 'tipo': 'aluno', 'usuario_id': 7}, 'action': 'read'}, error='not_found', status=404)
unit('UNIT-005', 'Permissões', 'Aluno não cria turma', 'authorize', {'member': {**member, 'papel': 'aluno'}, 'resource': {'escola_id': 1, 'tipo': 'turma'}, 'action': 'create'}, error='forbidden', status=403)
unit('UNIT-006', 'Permissões', 'Sem participação não há acesso institucional', 'authorize', {'member': None, 'resource': {'escola_id': 1, 'tipo': 'aluno'}, 'action': 'read'}, error='not_found', status=404)

unit('UNIT-007', 'Períodos', 'Intervalo letivo válido', 'validate_period', {'inicio': '2027-02-01', 'fim': '2027-12-15'}, result=True)
unit('UNIT-008', 'Períodos', 'Datas invertidas são inválidas', 'validate_period', {'inicio': '2027-12-15', 'fim': '2027-02-01'}, error='invalid_period', status=422)
unit('UNIT-009', 'Períodos', 'Data inexistente é inválida', 'validate_period', {'inicio': '2027-02-30', 'fim': '2027-12-15'}, error='invalid_period', status=422)
unit('UNIT-010', 'Períodos', 'Período de um dia é aceito', 'validate_period', {'inicio': '2027-02-01', 'fim': '2027-02-01'}, result=True)

for code, current, target, allowed in [('011', 'ativa', 'transferida', True), ('012', 'ativa', 'cancelada', True), ('013', 'transferida', 'ativa', False), ('014', 'cancelada', 'ativa', False)]:
    unit('UNIT-'+code, 'Matrículas', f'Transição {current} → {target}', 'validate_enrollment_transition',
         {'current': current, 'target': target, 'period_status': 'aberto'}, **({'result': True} if allowed else {'error': 'invalid_enrollment_transition', 'status': 409}))
unit('UNIT-015', 'Matrículas', 'Período fechado bloqueia alteração', 'validate_enrollment_transition', {'current': 'ativa', 'target': 'transferida', 'period_status': 'fechado'}, error='period_closed', status=409)
unit('UNIT-016', 'Integridade', 'Relações locais são válidas', 'validate_scope', {'escola_id': 1, 'resources': [{'escola_id': 1}, {'escola_id': 1}]}, result=True)
unit('UNIT-017', 'Integridade', 'Uma relação externa invalida a operação inteira', 'validate_scope', {'escola_id': 1, 'resources': [{'escola_id': 1}, {'escola_id': 2}]}, error='not_found', status=404)

assignment = {'escola_id': 1, 'professor_id': 1, 'oferta_id': 1, 'ativo': True}
for code, title, changes, expected in [('018', 'Oferta exata permite docência', {}, True), ('019', 'Outra oferta não é inferida por cruzamento', {'oferta_id': 3}, False), ('020', 'Outra escola não permite docência', {'escola_id': 2}, False), ('021', 'Outro professor não recebe acesso', {'professor_id': 2}, False)]:
    unit('UNIT-'+code, 'Docência', title, 'teacher_can_access', {'assignments': [assignment], 'escola_id': 1, 'professor_id': 1, 'oferta_id': 1, **changes}, result=expected)
unit('UNIT-022', 'Docência', 'Atribuição inativa é rejeitada', 'teacher_can_access', {'assignments': [{**assignment, 'ativo': False}], 'escola_id': 1, 'professor_id': 1, 'oferta_id': 1}, result=False)

for code, grade, expected in [('023', 0, True), ('024', 10, True), ('025', 8.5, True), ('026', -1, False), ('027', 11, False), ('028', 'NaN', False)]:
    unit('UNIT-'+code, 'Notas', f'Nota {grade}', 'validate_grade', {'value': grade, 'minimum': 0, 'maximum': 10}, **({'result': True} if expected else {'error': 'invalid_grade', 'status': 422}))

invitation = {'email': 'nova@example.test', 'status': 'pendente', 'expires_at': '2026-11-01T12:00:00Z'}
unit('UNIT-029', 'Convites', 'Convite válido para o destinatário', 'validate_invitation', {'invitation': invitation, 'email': 'nova@example.test', 'now': '2026-11-01T11:59:59Z'}, result=True)
unit('UNIT-030', 'Convites', 'Expiração é inclusiva no instante limite', 'validate_invitation', {'invitation': invitation, 'email': 'nova@example.test', 'now': '2026-11-01T12:00:00Z'}, error='invitation_expired', status=410)
unit('UNIT-031', 'Convites', 'Convite utilizado não pode ser reusado', 'validate_invitation', {'invitation': {**invitation, 'status': 'aceito'}, 'email': 'nova@example.test', 'now': '2026-11-01T11:00:00Z'}, error='invitation_used', status=409)
unit('UNIT-032', 'Convites', 'Email diferente não pode aceitar', 'validate_invitation', {'invitation': invitation, 'email': 'outra@example.test', 'now': '2026-11-01T11:00:00Z'}, error='invitation_recipient_mismatch', status=403)

unit('UNIT-033', 'Paginação', 'Página padrão limita a 25 registros', 'pagination', {'page': None, 'per_page': None}, result={'page': 1, 'per_page': 25})
unit('UNIT-034', 'Paginação', 'Pedido excessivo limita a 100 registros', 'pagination', {'page': 1, 'per_page': 10000}, result={'page': 1, 'per_page': 100})
unit('UNIT-035', 'Paginação', 'Página zero é inválida', 'pagination', {'page': 0, 'per_page': 25}, error='invalid_pagination', status=422)
unit('UNIT-036', 'Paginação', 'Texto arbitrário não vira página válida', 'pagination', {'page': 'abc', 'per_page': 25}, error='invalid_pagination', status=422)

unit('UNIT-037', 'Arquivos', 'PDF dentro do limite é permitido', 'validate_upload_metadata', {'filename': 'documento.pdf', 'size': 1024}, result=True)
unit('UNIT-038', 'Arquivos', 'Extensão executável é rejeitada', 'validate_upload_metadata', {'filename': 'arquivo.exe', 'size': 1024}, error='invalid_file', status=422)
unit('UNIT-039', 'Arquivos', 'Arquivo vazio é rejeitado', 'validate_upload_metadata', {'filename': 'documento.pdf', 'size': 0}, error='invalid_file', status=422)
unit('UNIT-040', 'Arquivos', 'Tamanho acima de 16 MiB é rejeitado', 'validate_upload_metadata', {'filename': 'documento.pdf', 'size': 16*1024*1024+1}, error='payload_too_large', status=413)

key = {'escola_id': 1, 'usuario_id': 7, 'permissions_version': 1, 'resource': 'painel', 'params': {'periodo_id': 1}}
for code, title, changes in [('041', 'Cache separa escolas', {'escola_id': 2}), ('042', 'Cache separa usuários', {'usuario_id': 8}), ('043', 'Cache invalida mudança de permissão', {'permissions_version': 2}), ('044', 'Cache separa filtros de período', {'params': {'periodo_id': 2}})]:
    unit('UNIT-'+code, 'Cache', title, 'private_cache_key', key, different_from={**key, **changes})

unit('UNIT-045', 'Comunicação', 'Aluno recebe comunicado para alunos', 'can_read_notice', {'role': 'aluno', 'audience': 'alunos'}, result=True)
unit('UNIT-046', 'Comunicação', 'Aluno não recebe comunicado restrito à equipe', 'can_read_notice', {'role': 'aluno', 'audience': 'equipe'}, result=False)
unit('UNIT-047', 'Comunicação', 'Professor recebe comunicado para equipe', 'can_read_notice', {'role': 'professor', 'audience': 'equipe'}, result=True)
