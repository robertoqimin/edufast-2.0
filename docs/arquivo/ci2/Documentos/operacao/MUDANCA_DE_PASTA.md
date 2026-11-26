> Documento historico de outra base. Use o [CI/CD atual](../../../../../.github/cicd/README.md) como procedimento operacional.

# Pasta local e repositório — EduFast 2.0

Pasta principal: `C:\Users\SGFer\Documents\ProjetoMk1\SamusChat\Educafast`.

O código e os arquivos locais foram movidos da pasta `Projeto-Educa-Fast`, incluindo histórico Git, ambiente virtual e caches locais. Segredos, uploads e caches continuam fora do versionamento conforme `.gitignore`; não são enviados ao repositório novo. O histórico da branch principal é preservado.

O Windows impediu substituir a antiga pasta inteira por uma junção por causa da proteção de uma estrutura `.git` vazia remanescente. Foram mantidas junções dos diretórios `.venv`, `.cache`, `Códigos`, `Documentos` e `Protótipo` e um inicializador de encaminhamento no caminho anterior. Isso preserva caminhos usados por executores, ambiente virtual e volumes de demonstração. A pasta antiga é de compatibilidade: **abra Educafast para trabalhar com Git**.

O inicializador na pasta `Teste-de-software` procura primeiro `SamusChat/Educafast` e mantém fallback para o nome anterior. Scripts dentro do projeto usam caminhos relativos a sua própria raiz. O ambiente Docker manual mantém o projeto `educafast-manual` e a porta 5050; o CI usa outro projeto e bancos descartáveis.

O novo `origin` aponta para `Samucau1/edufast-2.0`. A conexão com `Samucau1/Projeto-Educa-Fast` é preservada como remoto `legado`; o remoto `upstream` anterior permanece. Pushes de continuidade devem usar `origin`.

Ao clonar em outro computador:

```powershell
git clone https://github.com/Samucau1/edufast-2.0.git Educafast
cd Educafast
.\iniciar-educafast.ps1
```

A criação de vínculos antigos foi necessária apenas nesta instalação. Um clone novo não precisa da antiga estrutura de pastas. A autenticação no repositório privado e o Docker Desktop são necessários.
