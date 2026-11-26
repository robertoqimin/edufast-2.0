"""U2/O7: estudar sem baixar.

- Arquivos (PDF, PNG, JPEG) continuam cifrados e servidos pela mesma rota protegida; o leitor
  da página busca o arquivo com ``?modo=ler`` só para a auditoria distinguir leitura de download.
  A resposta segue como anexo: abrir o endereço direto continua baixando, e o PDF é desenhado
  pelo PDF.js local (static/vendor/pdfjs), sem enquadrar nenhuma página.
- Links do YouTube viram player embutido (youtube-nocookie, já permitido na CSP). Outros links
  continuam abrindo fora, em nova aba.
"""
from flask import request
from werkzeug.exceptions import HTTPException

from app.services.cursos import video_id


def modo_leitura():
    return request.args.get('modo') == 'ler'


def youtube(link):
    """Identificador do vídeo se o link for do YouTube; senão ``None`` (sem erro)."""
    if not link:
        return None
    try:
        return video_id(link)
    except HTTPException:
        return None
