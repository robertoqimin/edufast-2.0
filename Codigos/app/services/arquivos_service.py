import os
from uuid import uuid4
from flask import current_app
from werkzeug.utils import secure_filename
from config import caminho_uploads

PROFILE_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024

def _save_profile_photo(files):
    if not files or "foto_perfil" not in files:
        return None, None

    foto = files["foto_perfil"]
    if not foto or not foto.filename:
        return None, None

    original_filename = secure_filename(foto.filename)
    if not original_filename or "." not in original_filename:
        return None, ({"erro": "Nome da foto invalido"}, 400)

    extension = original_filename.rsplit(".", 1)[1].lower()
    if extension not in PROFILE_PHOTO_EXTENSIONS:
        return None, ({"erro": "A foto deve estar em JPG ou PNG"}, 400)

    foto.stream.seek(0, os.SEEK_END)
    file_size = foto.stream.tell()
    foto.stream.seek(0)
    if file_size > MAX_PROFILE_PHOTO_BYTES:
        return None, ({"erro": "A foto deve ter no maximo 2MB"}, 400)

    upload_folder = caminho_uploads(current_app.config["UPLOAD_FOLDER"])
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"perfil_{uuid4().hex}_{original_filename}"
    saved_path = os.path.join(upload_folder, filename)
    foto.save(saved_path)
    return filename, None

def _remove_saved_file(filename):
    if not filename:
        return

    path = os.path.join(caminho_uploads(current_app.config["UPLOAD_FOLDER"]), filename)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
