# Feature: Relatorios de Ponto

## Objetivo

Documentar o endpoint de relatorio operacional baseado em pontos ativos e jornada do colaborador.

## Arquivos Envolvidos

- `attendance/views.py`
- `attendance/serializers.py`
- `attendance/models.py`

## Endpoint

- `GET /api/attendance/pontos/relatorio/?inicio=<iso>&fim=<iso>&colaborador_id=<uuid>`

## Regras de Consulta

- `COLABORADOR` consulta apenas o proprio relatorio.
- `ADMIN` e `MESTRE` devem informar `colaborador_id`.
- Apenas pontos ativos sao considerados.
- O periodo precisa ser valido (`inicio <= fim`).

## Dados de Saida

- Identificacao do colaborador.
- Periodo consultado.
- Jornada associada ao colaborador.
- Resumo com total de segundos trabalhados e quantidade de pontos.
- Lista de pontos usados no calculo.

## Logica de Calculo Atual

- Ordena pontos ativos por data.
- Soma tempo somente em pares `ENTRADA -> SAIDA`.
- Entradas sem saida no periodo nao geram acumulacao parcial.
