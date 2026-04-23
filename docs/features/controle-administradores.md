# Feature: Controle de Administradores

## Objetivo

Documentar as regras de promocao e rebaixamento de perfil entre `COLABORADOR`, `ADMIN` e `MESTRE`.

## Arquivos Envolvidos

- `workforce/views.py`
- `workforce/services.py`
- `workforce/models.py`

## Endpoints

- `POST /api/workforce/usuarios/{id}/promover_admin/`
- `POST /api/workforce/usuarios/{id}/rebaixar_admin/`

## Regras de Promocao

- Quem pode promover: `ADMIN` e `MESTRE`.
- Alvo obrigatorio: usuario com perfil `COLABORADOR`.
- Restricao: usuario nao pode alterar o proprio perfil.

## Regras de Rebaixamento

- Quem pode rebaixar: somente `MESTRE`.
- Alvo obrigatorio: usuario com perfil `ADMIN`.
- Restricao: usuario nao pode alterar o proprio perfil.

## Pontos de Atencao para Alteracoes

- Alteracoes em regras de permissao devem manter aderencia ao `rn.md`.
- Mudancas de perfil impactam autorizacao em toda API.
- Sempre validar empresa/tenant via queryset da view.
