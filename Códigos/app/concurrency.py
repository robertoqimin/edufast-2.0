"""Database guarantees shared by HTTP mutations. No process-local locks."""
import hashlib
import json

from flask import request, session as web_session
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.idempotencia_model import IdempotenciaModel


class MutationConflict(Exception):
    def __init__(self, message, status=409):
        self.message = message
        self.status = status


def check_version(record, data):
    try:
        expected = int(data.get("versao", ""))
    except (ValueError, TypeError):
        raise MutationConflict("Recarregue o formulario antes de salvar: versao obrigatoria", 428)
    if expected != (record.versao if record else 0):
        raise MutationConflict("Registro alterado por outro envio; recarregue antes de salvar")
    if record:
        # Even identical payloads must compete for the submitted version.
        record.versao += 1


def insert_if_missing(db, model, defaults=None, **keys):
    """Unique constraint arbitrates concurrent inserts; current read sees winner."""
    db.flush()
    values = {**keys, **(defaults or {})}
    if db.bind.dialect.name == "mysql":
        statement = mysql_insert(model).values(**values)
        statement = statement.on_duplicate_key_update(id=model.id)
    elif db.bind.dialect.name == "sqlite":
        statement = sqlite_insert(model).values(**values).on_conflict_do_nothing(
            index_elements=list(keys))
    else:
        raise RuntimeError("Unsupported database dialect")
    db.execute(statement)
    return db.query(model).filter_by(**keys).with_for_update().one()


def begin_submission(db, operation, actor=None):
    key = request.headers.get("Idempotency-Key") or request.form.get("idempotency_key")
    if not key or len(key) > 128:
        raise MutationConflict("Informe Idempotency-Key (ate 128 caracteres)", 428)
    # Preserve opaque key identity even under MySQL case/accent-insensitive collations.
    key = hashlib.sha256(key.encode("utf-8")).hexdigest()
    actor = str(actor if actor is not None else web_session.get("user_id", ""))
    if not actor:
        raise MutationConflict("Autenticacao obrigatoria", 401)
    payload = {"form": sorted((k, request.form.getlist(k)) for k in request.form
                              if k not in {"idempotency_key", "csrf_token"}), "files": []}
    payload["json"] = request.get_json(silent=True) if request.is_json else None
    for name, files in sorted(request.files.lists()):
        for file in files:
            position = file.stream.tell()
            digest = hashlib.sha256()
            for chunk in iter(lambda: file.stream.read(65536), b""):
                digest.update(chunk)
            file.stream.seek(position)
            payload["files"].append((name, file.filename, digest.hexdigest()))
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    entry = insert_if_missing(db, IdempotenciaModel, ator=actor, operacao=operation, chave=key,
                              defaults={"fingerprint": fingerprint, "resposta": "{}", "status_http": 0})
    if entry.status_http == 0:
        return entry, None
    if entry.fingerprint != fingerprint:
        raise MutationConflict("Chave de envio reutilizada com conteudo diferente")
    return entry, (json.loads(entry.resposta), entry.status_http)


def finish_submission(db, entry, body, status):
    entry.resposta = json.dumps(body)
    entry.status_http = status
    db.commit()
    return body, status
