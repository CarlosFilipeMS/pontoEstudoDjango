# Feature: Ativacao Global e Autenticacao por Tenant

## Objetivo

Documentar como o sistema valida se um usuario pode autenticar e acessar recursos protegidos dentro de uma empresa (tenant).

## Arquivos Envolvidos

- `workforce/models.py`
- `workforce/auth.py`
- `core/permissions.py`

## Regra Central

Usuario ativo global:

`usuario.ativo AND empresa.ativo AND (colaborador inexistente OR colaborador.ativo)`

## Implementacao Atual

### `User.is_ativo(...)` (`workforce/models.py`)

- Reune estado do usuario, colaborador e empresa.
- Aceita `empresa_catalog` para evitar consulta adicional quando a empresa ja esta no request.
- Retorna `False` se empresa nao existir no catalogo.

### Login (`workforce/auth.py`)

No serializer de login:

1. exige tenant identificado (`request.empresa`);
2. autentica credenciais;
3. valida se usuario pertence a empresa da request;
4. valida `is_ativo(empresa_catalog=request.empresa)`;
5. somente depois gera JWT.

### Rotas Protegidas (`core/permissions.py`)

`IsUsuarioAtivoGlobal`:

- exige usuario autenticado;
- se houver `request.empresa` compativel com usuario, valida com `empresa_catalog`;
- fallback para `user.is_ativo()` quando necessario.

## Regras Criticas

- Nao liberar token para usuario inativo global.
- Nao permitir autenticacao cruzada entre empresas.
- Nao depender de regra no frontend para bloquear acesso.

## Pontos de Atencao para Alteracoes

- Alteracoes em `is_ativo` afetam login e autorizacao de todo o sistema.
- Alteracoes em login podem abrir brecha de acesso entre tenants.
- Alteracoes em permission class podem quebrar protecao global sem erro visivel imediato.

## Checklist de Atualizacao

Atualize este documento quando mudar:

- composicao da regra de ativacao global;
- validacoes de tenant no login;
- regra base de permissao para usuario ativo;
- payload de retorno de autenticacao relacionado a perfis.
