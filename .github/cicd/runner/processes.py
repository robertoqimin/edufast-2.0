import subprocess

def run(args, *, capture=False, input=None, root=None, env=None):
    print('+', ' '.join(map(str, args)), flush=True)
    result = subprocess.run(list(map(str, args)), cwd=root, env=env, input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT if input is None else subprocess.PIPE)
    if not capture and result.stdout:
        print(result.stdout.decode('utf-8', errors='replace'), flush=True)
    if result.returncode:
        if capture:
            print(result.stdout.decode('utf-8', errors='replace'), flush=True)
        raise RuntimeError(f'Command failed ({result.returncode}): {args[0:3]}')
    return result.stdout

def compose(*args, command, execute, **kwargs):
    return execute(command + list(args), **kwargs)
