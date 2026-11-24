"""Mede as jornadas por perfil (B3/MS05) num banco descartável. Roda dentro do container.

Por página: tempo de resposta (p50/p95 de N amostras após aquecimento), consultas SQL por
requisição, bytes do HTML e peso inicial (HTML + CSS + JS próprios, comprimidos com gzip).
O tempo é medido no processo da aplicação (cliente de teste do Flask): exclui rede e o
servidor WSGI, inclui rotas, banco, templates e serialização. Não mede o navegador.
"""
import argparse
import gzip
import json
import os
import re
import resource
import statistics
import sys
import time
from pathlib import Path

from sqlalchemy import event

CSRF = 'medicao-csrf'


def percentil(valores, fracao):
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, max(0, int(len(ordenados) * fracao + 0.999999) - 1))]


def jornadas(db):
    """Páginas de cada perfil, com IDs reais da massa."""
    from app.models import AlunoModel, ProfessorModel
    from app.models.academico_model import AvaliacaoModel
    from app.models.curso_model import OfertaCursoModel
    aluno = db.query(AlunoModel).order_by(AlunoModel.id).first()
    prof = db.query(ProfessorModel).order_by(ProfessorModel.id).first()
    avaliacao = db.query(AvaliacaoModel).filter(AvaliacaoModel.turma_disciplina_id == 101).order_by(AvaliacaoModel.id).first()
    oferta = db.query(OfertaCursoModel).filter_by(turma_disciplina_id=101).first()
    return {
        'secretaria': (1, [
            '/admin/dashboard', '/admin/banco-de-dados', '/admin/turmas', '/admin/disciplinas',
            f'/admin/alunos/{aluno.id}', f'/admin/professores/{prof.id}', '/solicitacoes', '/academico',
            f'/academico/avaliacoes/{avaliacao.id}', f'/academico/alunos/{aluno.id}/boletim', '/frequencia',
            '/frequencia/relatorio', '/aprendizagem', '/admin/comunicados', '/mensagens']),
        'professor': (prof.usuario_id, [
            '/professor/dashboard', '/academico', f'/academico/avaliacoes/{avaliacao.id}', '/frequencia',
            '/frequencia/turmas/101/chamada', '/estudos', '/aprendizagem', '/solicitacoes']),
        'aluno': (aluno.usuario_id, [
            '/aluno/dashboard', '/boletim', '/frequencia', '/aprendizagem', f'/aprendizagem/ofertas/{oferta.id}',
            '/estudos', '/aluno/disciplinas/1']),
    }


def cliente(app, db, usuario_id):
    from app.models import UsuarioModel
    user = db.get(UsuarioModel, usuario_id)
    client = app.test_client()
    client.environ_base['wsgi.url_scheme'] = 'https'  # cookie de sessão seguro, como em produção
    with client.session_transaction() as state:
        state.update(user_id=user.id, user_role=user.tipo, user_email=user.email,
                     auth_version=user.auth_version, csrf_token=CSRF)
    return client


ATIVOS = re.compile(r'<(?:link[^>]+href|script[^>]+src)="(/static/[^"?]+)(?:\?[^"]*)?"')


def peso_ativos(client, html, cache):
    total = 0
    arquivos = []
    for caminho in sorted(set(ATIVOS.findall(html))):
        if caminho not in cache:
            resposta = client.get(caminho)
            corpo = resposta.get_data()
            cache[caminho] = (len(corpo), len(gzip.compress(corpo, 6)))
            resposta.close()
        bruto, comprimido = cache[caminho]
        total += comprimido
        arquivos.append({'arquivo': caminho, 'bytes': bruto, 'gzip': comprimido})
    return total, arquivos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--saida', required=True)
    parser.add_argument('--amostras', type=int, default=30)
    parser.add_argument('--escala', default='padrao')
    args = parser.parse_args()
    if os.getenv('EDUFAST_TEST_DISPOSABLE') != '1':
        raise SystemExit('Somente em banco descartável.')
    from app.database import engine, get_session
    if engine.dialect.name != 'postgresql':
        raise SystemExit('A medição exige PostgreSQL descartável.')
    # Como numa escola nova: esquema base v8 revisado (A5) antes de iniciar a aplicação.
    from schema_base import criar_esquema_base
    criar_esquema_base(engine)
    from app import create_app
    import massa
    app = create_app()
    inicio = time.perf_counter()
    contagem = massa.popular(args.escala)
    tempo_massa = time.perf_counter() - inicio
    consultas = {'n': 0}

    def contar(*_):
        consultas['n'] += 1
    event.listen(engine, 'before_cursor_execute', contar)
    resultado = {'escala': args.escala, 'massa': contagem, 'tempo_massa_s': round(tempo_massa, 1),
                 'amostras': args.amostras, 'paginas': []}
    cache = {}
    with get_session() as db:
        roteiro = jornadas(db)
        clientes = {perfil: cliente(app, db, uid) for perfil, (uid, _) in roteiro.items()}
    for perfil, (_, caminhos) in roteiro.items():
        client = clientes[perfil]
        for caminho in caminhos:
            for _ in range(3):  # aquecimento
                client.get(caminho).close()
            tempos, sql = [], []
            status, corpo = None, b''
            for _ in range(args.amostras):
                consultas['n'] = 0
                t0 = time.perf_counter()
                resposta = client.get(caminho)
                corpo = resposta.get_data()
                tempos.append((time.perf_counter() - t0) * 1000)
                sql.append(consultas['n'])
                status = resposta.status_code
                resposta.close()
            html = corpo.decode('utf-8', errors='replace')
            ativos, arquivos = peso_ativos(client, html, cache) if status == 200 else (0, [])
            html_gz = len(gzip.compress(corpo, 6))
            item = {'perfil': perfil, 'pagina': caminho, 'status': status,
                    'p50_ms': round(statistics.median(tempos), 1), 'p95_ms': round(percentil(tempos, 0.95), 1),
                    'max_ms': round(max(tempos), 1), 'consultas_sql': max(sql),
                    'html_bytes': len(corpo), 'html_gzip': html_gz, 'ativos_gzip': ativos,
                    'peso_inicial_kib': round((html_gz + ativos) / 1024, 1), 'ativos': arquivos}
            resultado['paginas'].append(item)
            print(f"{perfil:10} {caminho:45} {status} p50={item['p50_ms']:7.1f} p95={item['p95_ms']:7.1f} "
                  f"sql={item['consultas_sql']:4} html={len(corpo) // 1024:5}KiB peso={item['peso_inicial_kib']:6.1f}KiB", flush=True)
    resultado['memoria_pico_app_mib'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / 'medicao.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print('memoria pico app (MiB):', resultado['memoria_pico_app_mib'])
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
