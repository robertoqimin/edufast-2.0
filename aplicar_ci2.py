from pathlib import Path
import shutil
root = Path(__file__).resolve().parent
target = root.parent / 'SamusChat/Educafast'
assert target.resolve() == Path('C:/Users/SGFer/Documents/ProjetoMk1/SamusChat/Educafast').resolve()
for source in (root / 'ci2').rglob('*'):
    if source.is_file() and '__pycache__' not in source.parts:
        dest = target / source.relative_to(root / 'ci2')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
print('CI/CD preparado em', target)
