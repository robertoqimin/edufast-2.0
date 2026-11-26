"""U1/O4: erros de formulário viram página amigável no navegador; clientes de API seguem com JSON.

Mesma regra do tratamento de MutationConflict: se o navegador prefere HTML, mostra a página de
erro com a mensagem e o mesmo código HTTP, e um botão para voltar ao formulário; caso
contrário, responde JSON como antes.
"""
from urllib.parse import urlsplit

from flask import jsonify, render_template, request

TITULO = 'Não foi possível concluir esta ação'


def prefere_html():
    return not request.is_json and request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'text/html'


def voltar_seguro():
    """Caminho de volta ao formulário, só dentro do próprio site."""
    origem = request.referrer
    if not origem:
        return None
    partes = urlsplit(origem)
    if partes.netloc and partes.netloc != request.host:
        return None
    if not partes.path.startswith('/') or partes.path.startswith('//'):
        return None
    return partes.path + ('?' + partes.query if partes.query else '')


def pagina_erro(mensagem, status):
    return render_template('erro.html', codigo=status, titulo=TITULO, mensagem=mensagem, voltar=voltar_seguro()), status


def resposta_erro(body, status):
    if prefere_html():
        mensagem = (body or {}).get('erro') or (body or {}).get('mensagem') or 'Confira os dados e tente novamente.'
        return pagina_erro(mensagem, status)
    return jsonify(body), status
