"""Execute Postman against a fresh synthetic SQLite HTTP server, then discard it."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--newman", required=True, help="Path to installed Newman bin/newman.js")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="edufast-postman-") as folder:
        os.environ.update(DB_URL="sqlite:///" + (Path(folder) / "postman.sqlite").as_posix(),
                          APP_ENV="testing", EDUFAST_TEST_DISPOSABLE="1",
                          PYTHON_DOTENV_DISABLED="1", SECRET_KEY="synthetic-postman-test-secret-only")
        sys.path.insert(0, str(ROOT / "Códigos"))
        sys.path.insert(0, str(ROOT / ".github/cicd/tests"))
        from test_concurrency import MutationApiTests
        from app.database import engine
        from app.models import (ComunicadoModel, AtividadeModel, DocumentoModel,
                                SolicitacaoDocumentoModel, SolicitacaoAlteracaoModel, NotaModel)
        from app.database import get_session
        from werkzeug.serving import make_server
        MutationApiTests.setUpClass()
        fixture = MutationApiTests()
        fixture.setUp()
        server = make_server("127.0.0.1", 0, fixture.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            environment = json.loads((ROOT / "Documentos/testes/postman/EduFast.postman_environment.json").read_text(encoding="utf-8"))
            for value in environment["values"]:
                if value["key"] == "base_url":
                    value["value"] = f"http://127.0.0.1:{server.server_port}"
                if value["key"] == "password":
                    value["value"] = "test-password-123"
            env_file = Path(folder) / "environment.json"
            env_file.write_text(json.dumps(environment), encoding="utf-8")
            report = ROOT / ".ci-results/mutations"
            report.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(["node", str(Path(args.newman).resolve()), "run",
                                     "Documentos/testes/postman/EduFast.postman_collection.json",
                                     "--environment", str(env_file), "--ignore-redirects", "--reporters", "cli,json",
                                     "--reporter-json-export", str(report / "postman.json")], cwd=ROOT)
            if result.returncode:
                return result.returncode
            with get_session() as db:
                for model, expected in [(ComunicadoModel, 1), (AtividadeModel, 1),
                                        (DocumentoModel, 4), (SolicitacaoDocumentoModel, 4)]:
                    assert db.query(model).count() == expected, model.__tablename__
                proposals = db.query(SolicitacaoAlteracaoModel).all()
                assert len(proposals) == 4 and all(row.estado == 'aprovada' for row in proposals)
                assert float(db.query(NotaModel).one().nota) == 9
            assert len(list(Path(fixture.folder.name).iterdir())) == 5
            print("Postman: persisted records and physical files verified")
            return 0
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
            engine.dispose()
            fixture.doCleanups()


if __name__ == "__main__":
    sys.exit(main())
