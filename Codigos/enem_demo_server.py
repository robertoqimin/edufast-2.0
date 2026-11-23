"""Demo MS04 nova e descartável. Recusa banco existente e qualquer outro destino."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4
from sqlalchemy import inspect
from app.database import engine, get_session
from app.models import UsuarioModel, TurmaModel
from config import Config
from two_school_test_data import initialize


def seed(app):
    accounts = {}
    with get_session() as db:
        for name in ('professor01','admin'):
            u = db.query(UsuarioModel).filter_by(email=name+'@teste01.local').one()
            accounts[name] = (u.id,u.tipo,u.auth_version)
        db.get(TurmaModel,1).nome = 'Preparatório ENEM — 2026'
        db.commit()
    def client(name):
        uid,role,version = accounts[name]
        c = app.test_client()
        with c.session_transaction() as session:
            session.update(user_id=uid,user_role=role,auth_version=version,csrf_token='demo-bootstrap')
        return c
    teacher,admin = client('professor01'),client('admin')
    def post(c,path,data):
        r = c.post(path,json=data,headers={'X-CSRF-Token':'demo-bootstrap','Idempotency-Key':uuid4().hex})
        if r.status_code not in (200,201,202):
            raise RuntimeError(f'Falha ao preparar {path}: {r.status_code} {r.text}')
        return r.json
    content = json.loads((Path(__file__).parent/'demo/matematica_enem.json').read_text(encoding='utf-8'))
    cid = post(teacher,'/api/cursos',{'disciplina_id':1,'titulo':content['titulo'],'descricao':content['descricao']})['curso_id']
    version = 1
    def edit(**fields):
        nonlocal version
        r = post(teacher,f'/api/cursos/{cid}/estrutura',{'versao':version,**fields})
        version = r['versao']
        return r['item_id']
    for module in content['modulos']:
        mid = edit(acao='adicionar',tipo='capitulo',titulo=module['titulo'])
        for chapter in module['capitulos']:
            chapter_id = edit(acao='adicionar',tipo='tema',pai_id=mid,titulo=chapter['titulo'])
            for lesson in chapter['aulas']:
                aid = edit(acao='adicionar',tipo='aula',pai_id=chapter_id,titulo=lesson['titulo'],tipo_aula='texto',corpo=lesson['corpo'])
                if lesson['titulo']=='Leitura de gráficos e pontos':
                    graph = Path(__file__).parent/'demo/funcao_afim.png'
                    r = teacher.post(f'/api/cursos/{cid}/aulas/{aid}/recursos',data={
                        'versao':str(version),'tipo':'arquivo','titulo':'Gráfico de f(x) = 2x + 3',
                        'arquivo':(io.BytesIO(graph.read_bytes()),'funcao_afim.png')},headers={
                        'X-CSRF-Token':'demo-bootstrap','Idempotency-Key':uuid4().hex})
                    if r.status_code!=201:
                        raise RuntimeError(r.text)
                    version = r.json['versao']
    proposal = post(teacher,f'/api/cursos/{cid}/solicitar-publicacao',{'versao':version})
    post(admin,f'/solicitacoes/alteracoes/{proposal["id"]}/decidir',{'decisao':'aprovar'})
    version = teacher.get(f'/api/cursos/{cid}').json['curso']['versao']
    offer = post(admin,f'/api/cursos/{cid}/ofertas',{'versao':version,'turma_disciplina_id':1})
    draft = post(teacher,f'/api/cursos/{cid}/duplicar',{'versao':offer['versao']})['curso_id']
    post(teacher,f'/api/cursos/{draft}/estrutura',{'versao':1,'acao':'curso',
        'titulo':'Matemática para o ENEM — laboratório do professor',
        'descricao':'Cópia em rascunho para testar organização, aulas e publicação. O curso dos alunos permanece preservado.'})
    print(json.dumps({'curso':cid,'oferta':offer['id'],'rascunho':draft,'aulas':12},ensure_ascii=False),flush=True)


def main():
    local = sys.argv[1:]==['--local']
    expected = 'sqlite:///:memory:' if local else 'sqlite:////tmp/edufast-enem-demo.sqlite'
    if (os.getenv('EDUFAST_ENEM_DEMO')!='1' or Config.APP_ENV!='development'
            or str(engine.url)!=expected or sys.argv[1:] not in ([],['--local'])
            or inspect(engine).get_table_names()):
        raise RuntimeError('Use somente uma demonstração MS04 nova, vazia e descartável.')
    initialize(engine,'teste01')
    from app import create_app
    app = create_app()
    with tempfile.TemporaryDirectory(prefix='edufast-enem-') as folder:
        app.config['UPLOAD_FOLDER'] = folder
        seed(app)
        if local and os.getenv('EDUFAST_ENEM_QA_LIGHT')=='1':
            from app.services.escola import IDENTIDADE_PADRAO,validar_identidade
            from app.models.escola_model import IdentidadeEscolaModel
            with app.app_context(),get_session() as db:
                light = validar_identidade({**IDENTIDADE_PADRAO,'nome':'Escola Teste 01','modo':'claro',
                    'fundo':'#f1f5f9','superficie':'#ffffff','texto':'#132e28','muted':'#425e55','destaque':'#087443'})
                db.get(IdentidadeEscolaModel,1).dados = json.dumps(light)
                db.commit()
        app.run(host='127.0.0.1' if local else '0.0.0.0',port=5093 if local else 8000,
            threaded=False,debug=False,use_reloader=False)


if __name__=='__main__':
    main()
