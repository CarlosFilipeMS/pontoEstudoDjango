# Feature: Ajuste de Ponto

## Objetivo

Documentar o fluxo de solicitacao e aprovacao de ajuste de ponto, com foco em integridade da cadeia de pontos e regras de permissao.

## Arquivos Envolvidos

- `attendance/models.py`
- `attendance/serializers.py`
- `attendance/services.py`
- `attendance/views.py`

## Modelos e Campos Relevantes

### `TimeAdjustmentRequest`

- `status`: `PENDENTE`, `APROVADO`, `REJEITADO`
- `ponto`: ponto original (pode ser nulo para criacao de novo ponto)
- `ponto_resultante`: ponto criado na aprovacao
- `colaborador`: colaborador alvo do ajuste
- `solicitado_por`: usuario que abriu a solicitacao
- `aprovado_por`: usuario que aprovou

### `TimeEntry`

- `tipo_ponto`: `ENTRADA` ou `SAIDA`
- `ponto_original`: referencia para rastrear cadeia de ajuste
- `ativo`: soft delete do ponto anterior quando ajustado

## Fluxo Atual

1. Solicitacao e criada com `status = PENDENTE`.
2. Endpoint de aprovacao recebe `solicitacao_id`.
3. Regra de permissao:
   - `COLABORADOR` nao pode aprovar.
   - `ADMIN` nao pode aprovar solicitacao feita por ele mesmo.
   - `MESTRE` pode aprovar.
4. Se houver `ponto` ativo, ele e desativado.
5. Novo ponto e criado via `TimeEntryService.registrar_ponto`.
6. Novo ponto recebe `ponto_original` para preservar a cadeia.
7. Regra de consistencia valida que a cadeia possui no maximo 1 ponto ativo.
8. Solicitacao passa para `APROVADO` e grava `aprovado_por` e `ponto_resultante`.

## Regras Criticas

- Nao alterar ponto historico fisicamente: ajustar = criar novo + desativar antigo.
- Garantir rastreabilidade da cadeia com `ponto_original`.
- Garantir uma unica versao ativa por cadeia.
- Garantir aprovacao somente por perfis permitidos.

## Pontos de Atencao para Alteracoes

- Mudancas em `AdjustmentService.aprovar_solicitacao` podem impactar:
  - consistencia de dados;
  - permissao de aprovacao;
  - alternancia de tipo (`ENTRADA`/`SAIDA`).
- Se alterar estrutura de cadeia, revisar validacao de ativos na cadeia.
- Se alterar regras de permissao, manter alinhamento com `rn.md`.

## Checklist de Atualizacao

Atualize este documento quando mudar:

- enums de status de solicitacao;
- regra de quem pode aprovar;
- estrategia de criacao/desativacao de pontos no ajuste;
- regra de encadeamento (`ponto_original`);
- contrato do endpoint `aprovar`.
