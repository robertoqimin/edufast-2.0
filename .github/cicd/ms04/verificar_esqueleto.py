"""Valida arquivos e contratos do esqueleto; não executa aceite do MS04.

Somente biblioteca padrão, leitura de JSON/AST, sem importar a aplicação/banco.
"""
import argparse
import ast
import json
from pathlib import Path


def repository_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / 'AGENTS.md').is_file() and (candidate / 'api/app').is_dir():
            return candidate
    raise ValueError('Informe --root com o checkout do projeto.')


def validate(root):
    root = root.resolve()

    def local_file(name):
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'Arquivo ausente ou fora do checkout: {name}')
        return path

    catalog = json.loads(local_file('.github/cicd/ms04/catalogo.json').read_text(encoding='utf-8'))
    if catalog['estado'] not in {'esqueleto','backend_api'}:
        raise ValueError('Estado de preparação desconhecido.')
    backend = catalog['estado']=='backend_api'
    if catalog['ativado'] is not backend:
        raise ValueError('Estado do runtime diverge do catálogo.')
    local_file(catalog['roteiro'])
    proposal = json.loads(local_file(catalog['modelo_proposto']).read_text(encoding='utf-8'))
    # Revisao A5 (23/11/2026) aprovou a proposta; aprovar nao executa nada.
    revisao = proposal['revisao_usuario']
    if proposal['sql_executavel'] is not False or not (revisao == 'pendente' or revisao.startswith('aprovada_em_')):
        raise ValueError('O modelo do esqueleto deve continuar como proposta sem execução.')
    if backend:
        local_file(proposal['arquivo_sql'])
        local_file(catalog['contrato'])
        local_file(catalog['testes_backend'])
    models = ast.parse(local_file('api/app/models/curso_model.py').read_text(encoding='utf-8'))
    names = {node.name for node in models.body if isinstance(node,ast.ClassDef)}
    if set(catalog['rotulos']) - names:
        raise ValueError('Mapeamento da hierarquia não corresponde aos modelos existentes.')
    for service in catalog['servicos']:
        tree = ast.parse(local_file(service['arquivo']).read_text(encoding='utf-8'))
        if service['funcao'] not in {n.name for n in tree.body if isinstance(n,ast.FunctionDef)}:
            raise ValueError(f"Ponto de implementação ausente: {service['funcao']}")
    routes = set()
    for source in (root / 'api/app/routes').rglob('*.py'):
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (not isinstance(decorator,ast.Call) or not isinstance(decorator.func,ast.Attribute)
                        or not decorator.args or not isinstance(decorator.args[0],ast.Constant)):
                    continue
                verb = decorator.func.attr
                if verb not in {'get','post','route'}:
                    continue
                methods = [verb.upper()] if verb != 'route' else ['GET']
                for keyword in decorator.keywords:
                    if keyword.arg == 'methods':
                        methods = ast.literal_eval(keyword.value)
                prefix = '/api' if source.name=='cursos_api_routes.py' else ''
                routes.update((method,prefix+decorator.args[0].value) for method in methods)
    identities = [(route['metodo'],route['caminho']) for route in catalog['rotas']]
    if len(identities) != len(set(identities)):
        raise ValueError('Método/caminho repetido no catálogo.')
    for route in catalog['rotas']:
        identity = route['metodo'],route['caminho']
        if route['estado'] not in {'existente','proposta'}:
            raise ValueError(f'Estado de rota inválido: {identity}')
        if (identity in routes) != (route['estado'] == 'existente'):
            raise ValueError(f'Rota diverge do estado declarado: {identity}')
    cases = catalog['aceite']
    if not cases or len({case['id'] for case in cases}) != len(cases):
        raise ValueError('IDs de aceite vazios ou repetidos.')
    for item in catalog['servicos'] + catalog['rotas'] + cases:
        if item['lote'] not in {'MS04-A','MS04-B','MS04-C','MS04-D','MS04-E'}:
            raise ValueError('Lote desconhecido no catálogo.')
    allowed = {'pendente','parcial','implementado_backend'} if backend else {'pendente'}
    if any(case['estado'] not in allowed or not case['cenario'].strip() for case in cases):
        raise ValueError('O catálogo não pode substituir os testes de aceite por estado manual.')
    for source in (root / 'api/app').rglob('*.py'):
        if backend:
            break
        if 'cursos_ms04' in source.parts:
            continue
        tree = ast.parse(source.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            imports = ([node.module or ''] if isinstance(node,ast.ImportFrom) else
                       [alias.name for alias in node.names] if isinstance(node,ast.Import) else [])
            if any('cursos_ms04' in module.split('.') for module in imports):
                raise ValueError(f'Esqueleto conectado ao runtime antes da implementação: {source.name}')
            if isinstance(node,ast.ImportFrom) and any(alias.name == 'cursos_ms04' for alias in node.names):
                raise ValueError(f'Esqueleto importado pelo runtime: {source.name}')
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True)
    parser.add_argument('--root',type=Path)
    args = parser.parse_args()
    try:
        catalog = validate(args.root or repository_root())
    except (ValueError,KeyError,TypeError,OSError,SyntaxError) as error:
        print(f'Falha estrutural MS04: {error}')
        return 1
    existing = sum(route['estado'] == 'existente' for route in catalog['rotas'])
    print(f"Catálogo conferido: {len(catalog['servicos'])} serviços, {existing} rotas existentes, "
          f"{len(catalog['rotas'])-existing} rotas propostas e {len(catalog['aceite'])} cenários descritos.")
    print('Sem conexão a banco. Verificação de organização; resultados funcionais estão no relatório da suíte.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
