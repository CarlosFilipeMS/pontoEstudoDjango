# Feature: Auto Fechamento de Ponto Aberto (24h)

## Objetivo

Fechar automaticamente pontos em aberto quando o ultimo ponto ativo do colaborador permanecer como `ENTRADA` por mais de 24 horas.

## Arquivos Envolvidos

- `attendance/models.py`
- `attendance/services.py`
- `attendance/management/commands/auto_close_open_entries.py`
- `companies/models.py`

## Regras de Dominio

- Nao alterar ponto existente (imutabilidade).
- Fechamento automatico cria novo ponto `SAIDA`.
- Timestamp de fechamento: `entrada + 24h`.
- Regra de 24h usa timezone da empresa (`Company.timezone`).
- Ponto automatico deve ser auditavel:
  - `gerado_automaticamente = true`
  - `motivo_geracao = AUTO_FECHAMENTO_24H`

## Aplicacao da Regra

### Reativa (no registro de ponto)

- Fluxo `TimeEntryService.registrar_ponto` verifica e fecha entrada aberta >24h antes de calcular o proximo tipo.

### Proativa (job agendavel)

- Command: `python manage.py auto_close_open_entries <subdominio>`
- Command global: `python manage.py auto_close_open_entries --all`
- Uso esperado com scheduler (cron/Celery beat), sem depender de usuario logado.

## Recomendacao de Operacao

- Rodar o scheduler em processo separado do servidor web.
- Executar o job em frequencia curta (ex.: a cada 1 minuto) para reduzir atraso de fechamento.
- Garantir apenas um scheduler ativo por ambiente.
- Registrar logs com total de empresas processadas e pontos fechados por execucao.
- Default de negocio: `AUTO_CLOSE_OPEN_ENTRY_MINUTES = 1440` (24h).
- Em ambiente de homologacao/dev, pode reduzir temporariamente esse valor para testes.

## Garantias de Integridade

- Fluxos transacionais com `transaction.atomic`.
- Leitura do ultimo ponto com `select_for_update` para reduzir risco em concorrencia.
- Mantem alternancia valida (`ENTRADA`/`SAIDA`) apos o fechamento automatico.

## Testes Minimos

- Ao registrar novo ponto, entrada aberta ha >24h gera `SAIDA` automatica.
- Job de fechamento retorna quantidade de pontos fechados.
- Ponto automatico precisa registrar motivo de auditoria.
