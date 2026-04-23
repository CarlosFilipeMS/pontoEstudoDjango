# Feature: Resolucao de Tenant

## Objetivo

Documentar como a empresa (tenant) e identificada em cada request e como o banco do tenant e associado ao contexto de execucao.

## Arquivos Envolvidos

- `core/middleware/tenant.py`
- `companies/models.py`
- `core/tenant_database.py`
- `core/tenant_context.py`

## Entradas de Identificacao

Prioridade atual:

1. Header `X-Company-Subdomain`
2. Subdominio do host (quando aplicavel)

## Fluxo Atual do Middleware

1. Le host e header para descobrir `subdomain`.
2. Inicializa `request.empresa`, `request.company` e `request.tenant_db` como `None`.
3. Busca empresa ativa no catalogo (`Company.objects.ativos().get(...)`).
4. Resolve nome de banco do tenant.
5. Garante registro dinamico da conexao do tenant.
6. Faz bind do alias no contexto (`contextvar`).
7. Preenche `request.empresa`/`request.tenant_db`.
8. Ao fim da request, reseta o token do contexto no `finally`.

## Regras Criticas

- Tenant precisa ser resolvido antes da camada de autenticacao/autorizacao.
- Empresa inativa nao pode ser resolvida para uso da API.
- Contexto do tenant deve ser limpo ao final da request para evitar vazamento entre requisicoes.

## Pontos de Atencao para Alteracoes

- Mudancas na ordem de resolucao (header vs host) impactam ambientes locais e proxy reverso.
- Mudancas no bind/reset de contexto podem causar acesso ao banco errado.
- Mudancas na busca de empresa ativa impactam toda a protecao multi-tenant.

## Checklist de Atualizacao

Atualize este documento quando mudar:

- estrategia de identificacao de tenant (header/subdominio);
- semantica de empresa ativa/inativa na resolucao;
- mecanismo de registro/alias de banco por tenant;
- variaveis do request utilizadas pelas views (`request.empresa`, `request.tenant_db`).
