"""Cabecalhos de seguranca em toda resposta (S3, S5, S7), na escola e no painel central.

- CSP com nonce por requisicao: scripts so do proprio servidor ou com o nonce da pagina;
  nenhum site pode enquadrar o EduFast (clickjacking); sem plugins; formularios so para
  o proprio dominio. Estilos embutidos continuam permitidos: tokens de tema da escola e
  atributos style= de templates legados (risco baixo; scripts sao o vetor de XSS).
- Respostas que usam a sessao recebem ``Vary: Cookie`` e, com usuario logado,
  ``Cache-Control: private, no-store``: nenhum cache intermediario guarda pagina de usuario
  (contorna o defeito do Flask 3.1.0 e qualquer proxy/CDN futuro).
- Os mesmos cabecalhos basicos valem atras do Caddy, do Nginx da frota ou sem proxy.
"""
from secrets import token_urlsafe

from flask import g, session

VIDEO = 'https://www.youtube-nocookie.com'


def politica(nonce):
    return '; '.join([
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        f'frame-src {VIDEO}',
        "frame-ancestors 'none'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
    ])


FIXOS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
}


def instalar(app, chave_usuario='user_id'):
    @app.before_request
    def _nonce():
        g.csp_nonce = token_urlsafe(18)

    @app.context_processor
    def _nonce_no_template():
        return {'csp_nonce': g.get('csp_nonce', '')}

    @app.after_request
    def _cabecalhos(response):
        nonce = g.get('csp_nonce') or token_urlsafe(18)
        response.headers.setdefault('Content-Security-Policy', politica(nonce))
        for nome, valor in FIXOS.items():
            response.headers.setdefault(nome, valor)
        if session.accessed or session.modified:
            response.vary.add('Cookie')
            # Respeita rotas que ja proibem cache; nas demais, nada de usuario logado e guardado.
            if session.get(chave_usuario) is not None and 'no-store' not in response.headers.get('Cache-Control', ''):
                response.headers['Cache-Control'] = 'private, no-store'
        return response
