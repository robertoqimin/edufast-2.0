# Ambientes independentes no mesmo servidor

Para a hospedagem em nuvem com comandos por cliente, revisões incrementais e
backup, use o [guia de operação em nuvem](CLOUD.md) e `manage.cjs`.
O gerador original abaixo permanece compatível para configurações iniciais.

Para testar localmente **Teste 01 e Teste 02**, com 20 alunos, 5 professores e
3 matérias em cada banco, use `node infra/demo.cjs start` e o
[guia das duas escolas](../Documentos/testes/DUAS_ESCOLAS_TESTE_2026-11-11.md).
No Windows, `./iniciar-duas-escolas.ps1` inicia e abre as escolas no navegador
externo nas portas 5081/5082. Para escolas já iniciadas, usar `-SomenteAbrir`.

Base preparatória para Linux + Docker Compose 2.24.4+, Node 20+ e TLS. Uma imagem
comum, instâncias Flask/Gunicorn, bancos, redes internas, uploads e segredos próprios
por escola. Um gateway Nginx atende os domínios na porta 443. Não é isolamento de VM:
escolas compartilham kernel, disco, host e gateway. Não executar junto de outro
proxy que já ocupe a porta 443 sem planejar a entrada única.

## Gerar e revisar

1. Copiar `environments.example.json` para um manifesto local em `.ci-results/`.
2. Informar domínios reais e digest da imagem aprovada pelo CI **contendo**
   `Códigos/gunicorn.conf.py` e estas alterações. O gerador valida formato e
   repositório; não verifica a aprovação criptograficamente. Conferir release pelo
   procedimento de `.github/cicd/README.md`.
3. Na raiz, executar:

```bash
node infra/generate.cjs .ci-results/escolas.json .ci-results/ambientes
docker compose -p edufast-escolas --env-file .ci-results/ambientes/.env -f .ci-results/ambientes/compose.json config --quiet
```

O diretório de saída deve ser novo e o pai deve existir. O gerador recusa
sobrescrever configurações. Não regenerar segredos para atualizar uma instalação.
Guardar `.env`, manifesto, compose e chaves em armazenamento privado, fora do Git;
em Windows, restringir ACLs, pois o modo POSIX 0600 não configura ACLs completas.
Não copiar segredos de outra escola nem perder a chave de criptografia.

4. Revisar memória/CPU, imagem, limites, redes e nomes de projeto. Disponibilizar
   `tls/fullchain.pem` e `tls/privkey.pem` com certificado válido para **todos** os
   domínios e cadeia confiável pelos clientes. Usar CA interna confiável na LAN ou
   certificado público apropriado; não desabilitar verificação TLS. A renovação é
   responsabilidade operacional externa: substituir arquivos e recarregar Nginx.
5. Validar configurações com `bash infra/verify.sh` em ambiente de desenvolvimento.
   Essa verificação cria certificado fictício e valida apenas sintaxe, não o TLS real.
6. Provisionar cada banco somente após revisão humana conforme
   `Códigos/migrations/README.md`. O gerador não cria esquema e não aplica SQL.
   Em banco vazio o app pode reiniciar indicando esquema pendente; isso é esperado
   até concluir o provisionamento revisado. Iniciar banco isoladamente, usar processo
   explícito de provisionamento e só então iniciar app e gateway.
7. Definir um nome Compose único e estável para a instalação. O nome determina
   volumes; trocar `-p` cria outro conjunto de volumes, não move os dados.
8. Depois de TLS, backup e provisionamento revisados, iniciar com o mesmo comando
   Compose e `up -d --wait`. Verificar login, aprovação, upload/download e acesso por
   domínio em cada escola. Criar administrador com `create-admin` pelo serviço da
   escola, sem reutilizar credenciais públicas de demonstração.

O pipeline antigo de deploy continua sendo para uma instalação única. Não usar
`deploy.sh` antigo para esta frota: não conhece os serviços/volumes por escola.
`manage.cjs` oferece operações explícitas de inicialização e atualização por cliente.
Não existe execução automática de migrations ou exclusão de ambientes.

## Controle de tráfego e capacidade

- Gateway: 16 MiB por corpo; cabeçalhos limitados; tempo máximo de espera de
  cabeçalhos/corpo; buffering de upload; buffers de resposta limitados; sem spill
  de respostas para disco; tmpfs de cache limitado a 128 MiB; sem cache de páginas
  privadas e sem repetição automática de requisição ao upstream.
- Taxa inicial por escola: 100 requisições/s com rajada de 100. Por IP e escola:
  20/s com rajada de 40, 30 conexões ativas; excesso recebe 429. Escolas atrás de
  NAT compartilham IP: medir e ajustar antes do piloto, preservando a proteção de
  login existente. Esse mecanismo não distingue usuários autenticados.
- Gzip somente CSS/JavaScript, evitando compressão geral de páginas com tokens.
- Gunicorn: perfil inicial 1 processo, 4 threads, 64 conexões e backlog 64, com
  reciclagem de workers. A configuração é usada explicitamente pelos ambientes
  gerados; o comando padrão da imagem anterior permanece compatível.
- MySQL: até 30 conexões; app com pool de 4 e zero overflow por processo.
  Esgotamento do pool retorna 503 com `Retry-After: 5`, sem repetir gravações.
  Com P processos e R réplicas, reservar pelo menos `P * R * (pool + overflow)`
  conexões, mais manutenção/healthchecks. Réplicas não estão habilitadas neste perfil.
- Memória inicial por escola: app até 512 MiB e banco até 768 MiB; gateway até
  256 MiB para o conjunto. São limites, não garantia de consumo ou capacidade.
  Reservar memória para sistema, Docker, TLS e disco; não lotar o host pela soma.
- Logs rotacionam em 3 arquivos de 10 MiB por serviço. Volumes de dados ainda
  precisam de quotas/monitoramento no host; limites de RAM não limitam disco.

Essas proteções reduzem exaustão de recursos. Não são prova de ausência de falhas
de memória, nem proteção completa contra ataques volumétricos. Não aumentar buffers
sem medir a origem: uploads, headers, conexões, consultas e fila são limites distintos.

`node infra/load.cjs https://escola.exemplo.com 100 4` executa sonda limitada de
`/healthz`, mantém TLS validado e informa códigos, taxa e p50/p95/p99. Usar somente
no ambiente autorizado. Não testa login, gravações, contenção ou carga acadêmica;
homologação requer dataset sintético e cenários funcionais com várias sessões.
Retornos diferentes de 200 encerram com falha; 429 esperado deve ser interpretado
em um ensaio específico de saturação.

## Local, nuvem e híbrido

| Modelo | Escrita principal | Dependências e recuperação |
| --- | --- | --- |
| Local | Banco no servidor local | DNS e CA internos; runtime já disponível; cópia de segurança externa quando houver conexão |
| Nuvem | Banco no servidor de nuvem | Acesso HTTPS pela internet; backup fora do host e recuperação ensaiada |
| Híbrido com principal local | Local | Nuvem recebe backups protegidos e pode hospedar recuperação; operação local não depende da internet |
| Híbrido com principal na nuvem | Nuvem | Servidor local pode guardar backup e ambiente de recuperação; sem escrita offline automática |

A topologia gerada funciona localmente ou em VM de nuvem. Preparar previamente
imagens, certificados e instalação para local sem internet. Redes internas restringem
saída de app/banco; integrações externas exigem revisão de egress e TLS, não abrir
o banco na internet. Manter o proxy como único salto confiável até Flask; adicionar
CDN, túnel ou balanceador requer reavaliar IP real e limites por cliente.

No híbrido, cada escola tem **um único ambiente autorizado a gravar**. Backups na
nuvem ajudam a recuperar, mas não tornam o sistema automaticamente disponível na
queda da internet ou do servidor. Não usar MySQL sobre WAN como caminho síncrono
normal sem projeto específico de latência e segurança.

Procedimento de contingência proposto:

1. Definir RPO (perda máxima aceitável) e RTO (tempo de recuperação), e responsável.
2. Copiar backup consistente de banco e uploads com criptografia, integridade,
   retenção e acesso restrito. Preservar imagem por digest e segredos separadamente.
3. Restaurar e verificar em destino isolado, sem atender gravações de usuários.
4. Antes de promover o destino, impedir gravações no principal antigo, inclusive
   clientes na LAN. Se não for possível garantir isso, não promover automaticamente.
5. Conferir ponto recuperado, habilitar destino e ajustar DNS/roteamento; DNS por si
   só não impede acesso ao servidor antigo. Medir RPO/RTO efetivos.
6. Para retorno, transferir estado do principal vigente e repetir a exclusão de
   escritores. Nunca religar dois bancos divergentes como se estivessem sincronizados.

O código desta etapa não implementa sincronização bidirecional, envio agendado de
backup, failover automático ou escrita offline. Esses serviços exigem decisões de
dados, credenciais, destino, conectividade e operação. Sincronização futura precisará
de IDs globais, eventos duráveis, deduplicação, ordem e regras explícitas de conflito
para notas, matrículas e aprovações; não basta copiar tabelas.

## Operação e suporte

Inventário deve registrar domínio, instalação, versão, proprietário operacional,
capacidade, último backup e último ensaio de recuperação por escola. Alertas devem
cobrir 5xx/429, p95, RAM, disco, conexões MySQL e certificado próximo de expirar.
Ainda não há coletor central de métricas/alertas instalado nesta etapa.

Atualizações são por escola: backup consistente, digest revisado, verificação de
compatibilidade do esquema, piloto e expansão. Não oferecer rollback automático de
banco; preservar gravações posteriores. O gateway é ponto compartilhado e exige
validar configuração antes de reload. Não executar `down -v` em instalação real.

Referências: [Nginx proxy/buffering](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[limites HTTP](https://nginx.org/en/docs/http/ngx_http_core_module.html),
[limites de tráfego](https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http),
[Gunicorn 23](https://docs.gunicorn.org/en/23.0.0/settings.html) e
[pool SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/core/pooling.html).
