# Backend Ponto (Django REST)

Backend completo para sistema de controle de ponto com:

- Django REST Framework
- JWT (SimpleJWT)
- Soft delete (`ativo`)
- Multi-tenant por empresa via subdominio (`request.empresa`)
- **Database-per-tenant**: catálogo em `default` (só `companies`); dados em banco dedicado por empresa
- Regras de dominio no backend

## Estrutura

- `companies`: empresa/tenant
- `workforce`: usuario, colaborador, jornada
- `attendance`: ponto e solicitacao de ajuste
- `core`: middleware de tenant e permissoes base
- `docs/modelagem.md`: modelagem tecnica (entidades, relacionamentos, constraints e fluxos)
- `docs/features/`: documentacao de features criticas
  - `auto-fechamento-ponto.md`
  - `ajuste-ponto.md`
  - `ativacao-global-autenticacao.md`
  - `controle-administradores.md`
  - `relatorios-ponto.md`
  - `tenant-resolution.md`

## Requisitos

- Python 3.12+
- PostgreSQL (producao) ou SQLite (dev)

## Setup

### 1) Criar e ativar ambiente virtual

```bash
python3 -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Windows (CMD):

```bat
.venv\Scripts\activate.bat
```

### 2) Instalar dependências e configurar `.env`

```bash
pip install -r requirements.txt
cp .env.example .env
```

### 3) Rodar migrações e subir servidor

```bash
# 1) Catálogo (apenas tabela de empresas no SQLite; outras apps ficam “marcadas” sem criar tabela — normal no Django multi-DB)
python manage.py migrate --database=default
# 2) Para cada empresa cadastrada no catálogo, criar/apontar o banco do tenant e migrar:
python manage.py provision_tenant_db <subdominio>
python manage.py runserver
```

### `.env.example` x `.env` (backend)

- `.env.example`: arquivo versionado com **valores de exemplo** e sem segredos; serve como template para o time.
- `.env`: arquivo **local** usado em runtime; e carregado automaticamente por `python-dotenv` em `config/settings.py`.

Fluxo recomendado:

```bash
cp .env.example .env
# depois ajuste os valores reais no .env local
```

### Job de auto fechamento (independente de usuario)

Fecha entradas abertas ha mais que o limite configurado (em minutos), sem depender de usuario logado.

Processar uma empresa especifica:

```bash
python manage.py auto_close_open_entries <subdominio>
```

Processar todas as empresas ativas:

```bash
python manage.py auto_close_open_entries --all
```

Tempo de fechamento automatico (em minutos) e configurado por `AUTO_CLOSE_OPEN_ENTRY_MINUTES`.
O valor padrao e `1440` (24h), conforme regra de negocio.
Para teste local rapido, reduza temporariamente (ex.: `1`) no `.env`.

#### Recomendacao operacional do job

- Execute o job em processo separado do servidor web.
- Agende em intervalo fixo (ex.: a cada 1 minuto) via **cron** ou **Celery beat**:
  - `python manage.py auto_close_open_entries --all`
- Mantenha apenas **uma instancia agendadora** ativa por ambiente para evitar execucoes concorrentes do mesmo ciclo.
- Monitore logs/metricas de execucao (`empresas processadas`, `pontos fechados`, erros por tenant).
- Em caso de muitos tenants, prefira Celery beat + workers para observabilidade e controle de retry.

### Seed rápida (empresa + MESTRE)

Cria a empresa no catálogo, migra o banco do tenant e o usuário **MESTRE** (fora do fluxo colaborador):

```bash
python manage.py seed_tenant_master <subdominio> <email_mestre> <senha> [--nome "Minha EMP"] [--cnpj 00000000000191]
```

Exemplo:

```bash
python manage.py seed_tenant_master demo mestre@demo.com MinhaSenhaForte123 --nome "Empresa Demo"
```

Se você rodar o seed de novo e o MESTRE já existir, nada é duplicado. Para **só trocar a senha** do MESTRE já criado:

```bash
python manage.py seed_tenant_master demo mestre@demo.com NovaSenhaSegura123 --reset-mestre-password
```

Depois, nas requisições: `X-Company-Subdomain: demo`.

**Nota:** `createsuperuser --database=default` **não** funciona para este projeto: o modelo `User` fica nos bancos **tenant**, não no catálogo. Use `seed_tenant_master` ou crie o MESTRE via shell com `--database=tenant_<subdominio>`.

### Variáveis de banco

- **Catálogo**: `CATALOG_DB_*` (fallback: `DB_*`) — arquivo `catalog.sqlite3` por padrão.
- **Tenants**: `TENANT_DB_*` — por empresa, campo `Empresa.database_name` (PostgreSQL) ou arquivo em `tenants/<subdominio>.sqlite3` se vazio.

Em produção (PostgreSQL), crie o database vazio antes de `provision_tenant_db`.

## Autenticacao

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`

Header recomendado para ambiente local:

`X-Company-Subdomain: empresa`

## Endpoints principais

- `/api/workforce/jornadas/`
- `/api/workforce/colaboradores/`
- `/api/workforce/usuarios/`
- `/api/workforce/usuarios/me/`
- `/api/workforce/usuarios/{id}/promover_admin/`
- `/api/workforce/usuarios/{id}/rebaixar_admin/`
- `/api/attendance/pontos/`
- `/api/attendance/pontos/ultimo/`
- `/api/attendance/pontos/relatorio/?inicio=<iso>&fim=<iso>&colaborador_id=<uuid>`
- `/api/attendance/solicitacoes-ajuste/`
- `/api/attendance/solicitacoes-ajuste/aprovar/`
- `/api/attendance/solicitacoes-ajuste/rejeitar/`
- `/api/attendance/solicitacoes-ajuste/{id}/` (DELETE para cancelamento/soft delete)

## Observacoes de regras

- Ao criar colaborador (`POST /api/workforce/colaboradores/`), envie `senha_inicial` (min. 8 caracteres, validadores Django): o usuario vinculado e criado com essa senha.
- Tipo de ponto e calculado automaticamente
- Entrada aberta por mais de 24h e fechada automaticamente com ponto `SAIDA` auditavel
- Ajuste nunca altera ponto existente: desativa o antigo e cria novo
- Usuario ativo global depende de:
  - `usuario.ativo`
  - `empresa.ativo`
  - `colaborador` ausente ou ativo
