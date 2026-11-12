"""Perfil inicial limitado; dimensionar por medições, não pelo número de contas."""
from runtime_limits import bounded_int

bind = "0.0.0.0:8000"
worker_class = "gthread"
workers = bounded_int("WEB_WORKERS", 1, 1, 16)
threads = bounded_int("WEB_THREADS", 4, 1, 32)
worker_connections = bounded_int("WEB_CONNECTIONS", 64, 8, 1024)
backlog = bounded_int("WEB_BACKLOG", 64, 8, 1024)
timeout = bounded_int("WEB_TIMEOUT", 60, 10, 300)
graceful_timeout = 30
keepalive = 2
max_requests = 2000
max_requests_jitter = 200
limit_request_line = 4094
limit_request_fields = 64
limit_request_field_size = 8190
# ProxyFix valida a topologia do proxy; não confiar em headers no Gunicorn.
forwarded_allow_ips = ""
# Não registrar query strings com possíveis dados pessoais.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
accesslog = "-"
errorlog = "-"
