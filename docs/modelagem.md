# Modelagem Tecnica do Backend

Este documento descreve a modelagem tecnica implementada no backend (`backendPonto`) e deve ser atualizado sempre que houver alteracao em modelos, relacionamentos, constraints ou fluxos de dominio.

## Escopo e Fonte de Verdade

- Regras de negocio: `../.cursor/docs/rn.md` (fora do backend, documento principal de negocio).
- Modelagem tecnica: este arquivo.
- Visao original de desenho: diagrama inicial enviado no projeto.

## Visao Geral das Entidades

- `Company` (`empresa`) - catalogo de tenants.
- `User` (`usuario`) - autenticacao e perfis (`MESTRE`, `ADMIN`, `COLABORADOR`).
- `Collaborator` (`colaborador`) - dados do funcionario e vinculo com jornada.
- `WorkSchedule` (`jornada`) - configuracao de carga e horarios.
- `TimeEntry` (`ponto`) - registros de entrada/saida.
- `TimeAdjustmentRequest` (`solicitacao_reajuste`) - solicitacoes de ajuste de ponto.

## Base Comum

### `core.TimeStampedModel`

- `created_at`
- `updated_at`

### `core.ActiveModel`

- `ativo` (soft delete logico)

## Entidades e Campos

### 1) Empresa (`companies.Company`)

Tabela: `empresa` (catalogo `default`)

Campos principais:
- `id` (UUID, PK)
- `cnpj` (char, unico)
- `nome`
- `endereco`
- `email` (unico)
- `contato`
- `subdominio` (unico)
- `timezone` (IANA timezone da empresa, ex.: `America/Sao_Paulo`)
- `database_name` (nome do banco do tenant em producao)
- `ativo`, `created_at`, `updated_at`

Observacoes:
- Opera no banco de catalogo (`default`).
- Possui queryset `.ativos()`.

### 2) Jornada (`workforce.WorkSchedule`)

Tabela: `jornada`

Campos principais:
- `id` (UUID, PK)
- `empresa_id` (UUID, indexado)
- `nome`
- `carga_horaria_semana` (int > 0)
- `hora_inicio`, `hora_fim`
- `hora_inicio_intervalo`, `hora_fim_intervalo`
- `jornada_personalizada` (bool)
- `ativo`, `created_at`, `updated_at`

Constraints:
- Unico por empresa: (`empresa_id`, `nome`)
- Check: `carga_horaria_semana > 0`

### 3) Colaborador (`workforce.Collaborator`)

Tabela: `colaborador`

Campos principais:
- `id` (UUID, PK)
- `matricula`
- `email`
- `cpf`
- `nome`
- `cargo`
- `data_nascimento`
- `empresa_id` (UUID, indexado)
- `jornada_id` (FK -> `jornada`)
- `ativo`, `created_at`, `updated_at`

Constraints:
- Unico por empresa: (`empresa_id`, `matricula`)
- Unico por empresa: (`empresa_id`, `email`)
- Unico por empresa: (`empresa_id`, `cpf`)

Validacao de dominio:
- `colaborador.empresa_id` deve ser igual a `jornada.empresa_id`.

API (criacao via `POST /api/workforce/colaboradores/`):
- Campo extra `senha_inicial` (write-only, obrigatorio no create): define a senha do `User` criado junto (nao persiste no modelo `Colaborador`).
- Validacao com `AUTH_PASSWORD_VALIDATORS` do Django.
- Atualizacao de colaborador nao aceita `senha_inicial` (senha nao muda por este endpoint).

### 4) Usuario (`workforce.User`)

Tabela: `usuario`

Campos principais:
- `id` (UUID, PK)
- `email` (unico global)
- `perfil` (`MESTRE` | `ADMIN` | `COLABORADOR`)
- `empresa_id` (UUID, indexado)
- `colaborador_id` (OneToOne FK -> `colaborador`, opcional)
- `is_staff`
- `ativo`, `created_at`, `updated_at`

Constraints:
- Unico `MESTRE` por empresa:
  - unique condicional em `empresa_id` quando `perfil = MESTRE`
- Regra perfil x colaborador:
  - `MESTRE` exige `colaborador IS NULL`
  - `ADMIN` e `COLABORADOR` exigem `colaborador IS NOT NULL`

Validacoes de dominio:
- Usuario nao pode vincular colaborador de outra empresa.
- Metodo `is_ativo()` aplica ativacao global:
  - `usuario.ativo`
  - `empresa.ativo`
  - colaborador ausente ou `colaborador.ativo`

### 5) Ponto (`attendance.TimeEntry`)

Tabela: `ponto`

Campos principais:
- `id` (UUID, PK)
- `data_hora` (datetime)
- `tipo_ponto` (`ENTRADA` | `SAIDA`)
- `colaborador_id` (FK -> `colaborador`)
- `ponto_original_id` (FK opcional -> `ponto`)
- `gerado_automaticamente` (bool)
- `motivo_geracao` (enum textual; vazio quando manual)
- `ativo`, `created_at`, `updated_at`

Constraints:
- Unicidade: (`colaborador_id`, `data_hora`, `ativo`)
- Check: `tipo_ponto` valido (`ENTRADA` ou `SAIDA`)
- Check: coerencia de geracao automatica:
  - manual: `gerado_automaticamente = false` e `motivo_geracao = ""`
  - automatico: `gerado_automaticamente = true` e `motivo_geracao != ""`

Indices:
- (`colaborador_id`, `-data_hora`)

### 6) Solicitacao de Reajuste (`attendance.TimeAdjustmentRequest`)

Tabela: `solicitacao_reajuste`

Campos principais:
- `id` (UUID, PK)
- `nova_data_hora`
- `status` (`PENDENTE` | `APROVADO` | `REJEITADO`)
- `motivo`
- `ponto_id` (FK opcional -> `ponto`)
- `ponto_resultante_id` (FK opcional -> `ponto`)
- `colaborador_id` (FK -> `colaborador`)
- `aprovado_por_id` (FK opcional -> `usuario`)
- `solicitado_por_id` (FK -> `usuario`)
- `ativo`, `created_at`, `updated_at`

Constraints:
- Check de status valido.

## Relacionamentos

- `Company` 1:N `User` (por `empresa_id` logico no tenant + validacao com catalogo).
- `Company` 1:N `Collaborator` (por `empresa_id`).
- `Company` 1:N `WorkSchedule` (por `empresa_id`).
- `WorkSchedule` 1:N `Collaborator`.
- `Collaborator` 1:1 `User` (lado `User.colaborador`, opcional para suportar `MESTRE`).
- `Collaborator` 1:N `TimeEntry`.
- `TimeEntry` 1:N `TimeEntry` (auto-relacao via `ponto_original` para cadeia de ajuste).
- `TimeEntry` 1:N `TimeAdjustmentRequest` (origem via `ponto`).
- `TimeEntry` 1:N `TimeAdjustmentRequest` (resultado via `ponto_resultante`).
- `User` 1:N `TimeAdjustmentRequest` (solicitante e aprovador).

## Enums de Dominio

- `ProfileChoices`:
  - `MESTRE`
  - `ADMIN`
  - `COLABORADOR`
- `PunchTypeChoices`:
  - `ENTRADA`
  - `SAIDA`
- `AdjustmentStatusChoices`:
  - `PENDENTE`
  - `APROVADO`
  - `REJEITADO`
- `AutoGenerationReasonChoices`:
  - `AUTO_FECHAMENTO_24H`

## Fluxos Criticos (Regra Tecnica)

### Ativacao Global de Usuario

Usuario somente ativo para operacoes protegidas quando:

`usuario.ativo AND empresa.ativo AND (colaborador inexistente OR colaborador.ativo)`

### Registro de Ponto

- Tipo alternado automaticamente conforme ultimo ponto ativo do colaborador.
- Primeiro registro do dia/cadeia inicia como `ENTRADA`.
- Em ajuste aprovado, ponto antigo e desativado e novo ponto e criado.
- Antes da alternancia, o backend verifica entrada aberta por mais de 24h.
- Se houver, cria uma `SAIDA` automatica em `entrada + 24h` usando timezone da empresa.
- O ponto automatico e auditavel (`gerado_automaticamente` + `motivo_geracao`).

### Fechamento Automatico 24h

- Regra aplicada de forma reativa em `registrar_ponto` e de forma proativa por command agendavel.
- Command: `python manage.py auto_close_open_entries <subdominio>`
- O command resolve o tenant pelo catalogo, faz bind do banco da empresa e fecha pontos abertos elegiveis.

### Ajuste de Ponto

1. Solicitacao nasce `PENDENTE`.
2. Quando aprovada:
   - cria `ponto_resultante`;
   - desativa ponto anterior (quando existir);
   - preserva rastreabilidade com `ponto_original`.

### Controle de Administradores

- `ADMIN` e `MESTRE` podem promover `COLABORADOR -> ADMIN`.
- Somente `MESTRE` pode rebaixar `ADMIN -> COLABORADOR`.
- Usuario nao pode alterar o proprio perfil.

### Relatorios

- Endpoint operacional de relatorio usa:
  - pontos ativos;
  - jornada vinculada ao colaborador;
  - filtro por periodo.

## Consistencia com Regras de Negocio (Checklist)

- Multi-tenant por empresa com isolamento de dados.
- Soft delete por `ativo` em entidades criticas.
- 1 `MESTRE` por empresa.
- 1 usuario por colaborador (OneToOne).
- Vinculos sempre na mesma empresa.
- Ajuste de ponto sem alteracao fisica do registro original.

## Manutencao do Documento

Atualize este arquivo quando houver mudanca em:

- campos de models;
- constraints (`UniqueConstraint`, `CheckConstraint`);
- relacionamentos (`FK`, `OneToOne`);
- enums de dominio;
- comportamento dos fluxos de ponto, ajuste e permissao.

Nao registrar alteracoes de regra de negocio aqui; nesse caso, atualizar o `rn.md` mediante aprovacao.
