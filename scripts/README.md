# Scripts

Para regenerar as quatro pranchas SVG de apresentação, execute na raiz com Python 3.10 ou superior:

```bash
python scripts/gerar_prototipos.py
```

O gerador usa somente a biblioteca padrão e escreve em `Protótipo/edufast/`. Os textos e dados fictícios estão no dicionário `SCREENS`. Não acessa banco, rede ou dados da escola.

Os utilitários de [legado](legado/README.md) têm outra finalidade e não fazem parte da execução atual.
