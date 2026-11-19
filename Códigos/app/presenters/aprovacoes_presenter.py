"""User-facing descriptions; dispatch details remain a server implementation."""
OPERATIONS = {'cursos.criar': 'Criar curso', 'cursos.editar_estrutura': 'Editar material do curso',
    'cursos.duplicar': 'Reutilizar curso', 'cursos.estado': 'Alterar publicacao do curso',
    'academico.criar_avaliacao': 'Criar avaliacao', 'academico.lancar': 'Alterar nota de avaliacao',
    'academico.publicar': 'Publicar avaliacao', 'academico.configurar_avaliacao': 'Configurar avaliacao'}


def present(kind, payload):
    if kind == 'publicar_material':
        return 'Publicar aviso ou material de estudo', {'conteudo':payload.get('conteudo_id'),'versao':payload.get('versao')}
    if kind != 'operacao_restaurada':
        return kind.replace('_', ' ').capitalize(), payload
    return OPERATIONS.get(payload.get('endpoint'), 'Alteracao academica'), {
        **payload.get('params', {}), **payload.get('payload', {})}
