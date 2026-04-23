from contextvars import ContextVar, Token

_current_tenant_db: ContextVar[str | None] = ContextVar("current_tenant_db", default=None)


def get_current_tenant_db() -> str | None:
    return _current_tenant_db.get()


def bind_tenant_db(alias: str) -> Token:
    return _current_tenant_db.set(alias)


def reset_tenant_db_token(token: Token) -> None:
    _current_tenant_db.reset(token)
