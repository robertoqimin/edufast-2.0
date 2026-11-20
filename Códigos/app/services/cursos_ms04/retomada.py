"""Ponto de implementação MS04-C: última aula por aluno e oferta.

Retomada e conclusão são registros distintos. Validar acesso atual e pertença da
aula ao curso da oferta antes de gravar. Versão antiga deve conflitar; horário
enviado pelo navegador não decide qual acesso prevalece. Preservar progresso.
"""


from datetime import datetime, timezone
from app.concurrency import insert_if_missing
from app.models import RetomadaCursoModel, ProgressoAulaModel
from app.services import cursos as base
from . import comum


def registrar_abertura(db, *, ator_id, oferta_id, aula_id, versao, chave_envio=None):
    comum.usuario(db,ator_id,('aluno',))
    offer,course,student = base.acesso_oferta(db,oferta_id,ator_id,'aluno')
    lesson = comum.aula(db,course.id,aula_id)
    row = insert_if_missing(db,RetomadaCursoModel,aluno_id=student.id,oferta_id=offer.id,
        defaults={'aula_id':lesson.id,'versao':0})
    comum.exigir_versao(row,{'versao':versao} if versao is not None else {})
    row.aula_id,row.atualizado_em = lesson.id,datetime.now(timezone.utc).replace(tzinfo=None)
    base.auditar(db,ator_id,'ms04_abrir_aula',f'{offer.id}:{lesson.id}')
    return {'oferta_id':offer.id,'aula_id':row.aula_id,'versao':row.versao}


def concluir(db, *, ator_id, oferta_id, aula_id):
    comum.usuario(db,ator_id,('aluno',))
    offer,course,student = base.acesso_oferta(db,oferta_id,ator_id,'aluno')
    lesson = comum.aula(db,course.id,aula_id)
    insert_if_missing(db,ProgressoAulaModel,aluno_id=student.id,oferta_id=offer.id,aula_id=lesson.id)
    return {'oferta_id':offer.id,'aula_id':lesson.id,'concluida':True}
