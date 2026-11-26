"""Generate the reviewable Postman 2.1 collection without external services."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/testes/postman"


def request(name, method, path, status, *, form=None, raw=None, file=False, script=None, pre=None, extra_headers=None):
    headers = []
    body = None
    if raw is not None:
        headers = [{"key": "Content-Type", "value": "application/json"}]
        body = {"mode": "raw", "raw": json.dumps(raw)}
    if form is not None:
        if file:
            values = [{"key": k, "value": v, "type": "text"} for k, v in form.items()]
            values.append({"key": "arquivo", "type": "file", "src": "docs/testes/postman/arquivo.txt"})
            body = {"mode": "formdata", "formdata": values}
        else:
            body = {"mode": "urlencoded", "urlencoded": [{"key": k, "value": v} for k, v in form.items()]}
    headers += extra_headers or []
    result = {"name": name, "request": {"method": method, "header": headers, "url": "{{base_url}}" + path},
              "protocolProfileBehavior": {"followRedirects": False},
              "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
                  f"pm.test('HTTP {status}', function () {{ pm.expect(pm.response.code).to.eql({status}); }});",
                  *(script or [])]}}]}
    if body:
        result["request"]["body"] = body
    if pre:
        result["event"].append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": pre}})
    return result


def login(role, reset=False):
    return request("Login " + role, "POST", "/login", 200,
                   raw={"email": "{{" + role + "_email}}", "senha": "{{password}}"},
                   script=["const body = pm.response.json();",
                           f"if (body.token) pm.collectionVariables.set('{role}_token', body.token);"],
                   pre=["pm.collectionVariables.set('run_key', pm.variables.replaceIn('{{$guid}}')); "] if reset else None)


def diary(name, path, status, body, key, script=None):
    # Diario academico (B1): o professor envia JSON com token; cada acao vira solicitacao.
    return request(name, "POST", path, status, raw=body, script=script, extra_headers=[
        {"key": "Authorization", "value": "Bearer {{professor_token}}"},
        {"key": "Idempotency-Key", "value": "{{run_key}}-" + key}])


def approve(kind):
    return [login("admin"), request("Localizar proposta " + kind, "GET", "/solicitacoes/alteracoes", 200, script=[
        "const body = pm.response.json();",
        "const rows = Array.isArray(body) ? body : body.solicitacoes;",
        f"const row = rows.find(r => r.tipo === '{kind}' && r.estado === 'pendente');",
        "pm.test('Proposta pendente existe', () => pm.expect(row).to.be.ok);",
        "if (row) pm.collectionVariables.set('proposal_id', String(row.id));"]),
        request("Autorizar " + kind, "POST", "/solicitacoes/alteracoes/{{proposal_id}}/decidir", 200,
                raw={"decisao": "aprovar"})]


def build():
    items = [request("Saude", "GET", "/healthz", 200), login("admin", reset=True)]
    comunicado = {"titulo": "Aviso de teste", "mensagem": "Mensagem sintetica", "idempotency_key": "{{run_key}}-aviso"}
    items += [request("Criar comunicado", "POST", "/admin/comunicados", 302, form=comunicado),
              request("Repetir comunicado", "POST", "/admin/comunicados", 302, form=comunicado),
              request("Mesma chave com conteudo diferente", "POST", "/admin/comunicados", 409, form={**comunicado, "mensagem": "Outra"}),
              request("Sem chave", "POST", "/admin/comunicados", 428, form={"titulo": "Aviso", "mensagem": "Texto"})]
    for owner in ["aluno", "professor"]:
        plural = "alunos" if owner == "aluno" else "professores"
        path = f"/admin/{plural}/{{{{{owner}_id}}}}"
        items.append(request("Ler versao " + owner, "GET", path, 200, script=[
            r'const match = pm.response.text().match(/name="versao" value="(\d+)"/);',
            "pm.test('Versao no formulario', function () { pm.expect(match).not.to.eql(null); });",
            f"if (match) pm.collectionVariables.set('{owner}_version', match[1]);"]))
        data = {"nome": "Cadastro sintetico", "email": "{{" + owner + "_email}}", "versao": "{{" + owner + "_version}}"}
        data.update({"matricula": "M1"} if owner == "aluno" else {"cpf": "11111111111"})
        items += [request("Editar " + owner, "POST", path + "/editar", 302, form=data),
                  request("Rejeitar versao antiga " + owner, "POST", path + "/editar", 409, form=data)]
        solic = {"titulo": "Documento de teste", "idempotency_key": "{{run_key}}-solic-" + owner}
        items += [request("Solicitar documento " + owner, "POST", path + "/documentos/solicitar", 302, form=solic),
                  request("Repetir solicitacao " + owner, "POST", path + "/documentos/solicitar", 302, form=solic)]
    items.append(login("aluno"))
    for label, status in [("Responder solicitacao aluno", 302), ("Repetir resposta aluno", 409)]:
        items.append(request(label, "POST", "/aluno/documentos/upload", status,
                             form={"solicitacao_id": "{{aluno_request_id}}"}, file=True))
    items.append(login("professor"))
    grade = {"aluno_id": "{{aluno_id}}", "turma_id": "{{turma_id}}", "disciplina_id": "{{disciplina_id}}", "nota": "8", "versao": "0", "idempotency_key": "{{run_key}}-nota0"}
    launch = "/academico/avaliacoes/{{avaliacao_id}}/alunos/{{aluno_id}}"
    items += [request("Formulario antigo de nota aposentado", "POST", "/professor/notas/salvar", 410, form=grade),
              diary("Propor nota no diario", launch, 202, {"valor": "8", "versao": 0}, "diario0"),
              diary("Repetir proposta no diario", launch, 202, {"valor": "8", "versao": 0}, "diario0")]
    items += approve("operacao_restaurada") + [login("professor"),
              diary("Versao antiga no diario rejeitada", launch, 409, {"valor": "4", "versao": 0}, "diario-antiga"),
              diary("Propor correcao versao 1", launch, 202, {"valor": "9", "versao": 1}, "diario1")]
    items += approve("operacao_restaurada") + [login("professor"),
              diary("Propor publicacao da avaliacao", "/academico/avaliacoes/{{avaliacao_id}}/publicar", 202, {}, "publicar")]
    items += approve("operacao_restaurada") + [login("aluno"),
              request("Boletim do aluno mostra nota publicada", "GET", "/boletim?formato=json", 200, script=[
                  "const notas = pm.response.json().periodos.flatMap(p => p.avaliacoes.map(a => a.nota));",
                  "pm.test('Nota aprovada e publicada', () => pm.expect(notas).to.eql(['9.00']));"]),
              login("professor")]
    activity = {"turma_id": "{{turma_id}}", "disciplina_id": "{{disciplina_id}}", "titulo": "Atividade sintetica", "idempotency_key": "{{run_key}}-atividade"}
    for label in ["Criar atividade", "Repetir atividade"]:
        items.append(request(label, "POST", "/professor/atividades/lancar", 302, form=activity, file=True))
    for label, status in [("Responder solicitacao professor", 302), ("Repetir resposta professor", 302)]:
        items.append(request(label, "POST", "/professor/documentos/upload", status,
                             form={"solicitacao_id": "{{professor_request_id}}", "idempotency_key": "{{run_key}}-resposta-prof"}, file=True))
    items += approve("lancar_atividade") + approve("responder_documento")
    items += [login("professor"), request("Repetir resposta ja autorizada", "POST", "/professor/documentos/upload", 302,
        form={"solicitacao_id": "{{professor_request_id}}", "idempotency_key": "{{run_key}}-resposta-prof"}, file=True),
        request("Nova tentativa de responder documento concluido", "POST", "/professor/documentos/upload", 409,
        form={"solicitacao_id": "{{professor_request_id}}", "idempotency_key": "{{run_key}}-outra-resposta-prof"}, file=True)]
    items.append(login("admin"))
    for owner, path, data in [("aluno", "/arquivos/upload", {"aluno_id": "{{aluno_id}}"}),
                              ("professor", "/professores/{{professor_id}}/arquivos/upload", {})]:
        form = {**data, "idempotency_key": "{{run_key}}-upload-" + owner}
        for label in ["Upload avulso ", "Repetir upload avulso "]:
            script = None
            if owner == "aluno":
                script = (["pm.collectionVariables.set('document_id', String(pm.response.json().documento.id));"]
                          if label.startswith("Upload") else
                          ["pm.test('Mesmo documento', function () { pm.expect(String(pm.response.json().documento.id)).to.eql(pm.collectionVariables.get('document_id')); });"])
            items.append(request(label + owner, "POST", path, 201, form=form, file=True, script=script))
    items += [request('Admin nao acessa gestao de usuarios', 'GET', '/super/usuarios', 403), login('superadmin'),
        request('Painel original de usuarios e CSRF', 'GET', '/super/usuarios', 200, script=[
            r'const token = pm.response.text().match(/name="csrf_token" value="([^"]+)"/);',
            "pm.test('Formulario protegido', () => pm.expect(token).to.be.ok);",
            "if (token) pm.collectionVariables.set('csrf', token[1]);"]),
        request('Criar administrador pelo superperfil', 'POST', '/super/usuarios', 302, form={
            'tipo':'admin','nome':'Admin sintetico','email':'new-{{run_key}}@example.test','senha':'{{password}}',
            'csrf_token':'{{csrf}}','idempotency_key':'{{run_key}}-admin'}),
        request('Repetir criacao de administrador', 'POST', '/super/usuarios', 302, form={
            'tipo':'admin','nome':'Admin sintetico','email':'new-{{run_key}}@example.test','senha':'{{password}}',
            'csrf_token':'{{csrf}}','idempotency_key':'{{run_key}}-admin'}),
        request('Configuracao institucional original', 'GET', '/super/escola?formato=json', 200),
        request('Salvar identidade validada', 'POST', '/super/escola/identidade', 200,
            raw={'nome':'Escola sintetica','sigla':'ef','subtitulo':'GESTAO ESCOLAR','modo':'escuro','fundo':'#06385d',
                 'destaque':'#22d3ee','superficie':'#111c2b','texto':'#ecf1f8','muted':'#a4bdce',
                 'raio':'12','densidade':'confortavel','fonte':'dm-sans','versao':0},
            extra_headers=[{'key':'X-CSRF-Token','value':'{{csrf}}'}]),
        request('Versao anterior de identidade rejeitada', 'POST', '/super/escola/identidade', 409,
            raw={'versao':0}, extra_headers=[{'key':'X-CSRF-Token','value':'{{csrf}}'}])]
    collection = {"info": {"name": "EduFast - concorrencia e idempotencia",
                            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                            "description": "Usar apenas em banco sintetico conforme README. Nao executa migrations. Concorrencia e verificada pela suite PostgreSQL; este fluxo verifica contratos HTTP e repeticao sequencial."},
                  "variable": [{"key": "run_key", "value": ""}], "item": items}
    values = {"base_url": "http://127.0.0.1:5000", "admin_email": "u1@example.test",
              "aluno_email": "u2@example.test", "professor_email": "u3@example.test", "superadmin_email": "u5@example.test", "password": "",
              "aluno_id": "1", "professor_id": "1", "turma_id": "1", "disciplina_id": "1", "avaliacao_id": "1",
              "aluno_request_id": "1", "professor_request_id": "2"}
    environment = {"name": "EduFast - somente dados sinteticos", "values": [
        {"key": key, "value": value, "enabled": True, "type": "secret" if key == "password" else "default"}
        for key, value in values.items()], "_postman_variable_scope": "environment"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "EduFast.postman_collection.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "EduFast.postman_environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
