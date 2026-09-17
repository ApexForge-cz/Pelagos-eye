from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from oceanscope_api.core.settings import get_settings
from oceanscope_api.db.base import Base
from oceanscope_api.ports import models as port_models  # noqa: F401
from oceanscope_api.provenance import models as provenance_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
if not config.get_main_option("sqlalchemy.url") and settings.database_url is not None:
    config.set_main_option(
        "sqlalchemy.url",
        settings.database_url.get_secret_value().replace("%", "%%"),
    )

target_metadata = Base.metadata


def include_object(
    _object: object,
    name: str | None,
    type_: str,
    reflected: bool,
    _compare_to: object,
) -> bool:
    """Exclude tables managed internally by the PostGIS extension."""
    return not (reflected and type_ == "table" and name == "spatial_ref_sys")


def require_database_url() -> None:
    if not config.get_main_option("sqlalchemy.url"):
        message = "OCEANSCOPE_DATABASE_URL is required for migration commands"
        raise RuntimeError(message)


def run_migrations_offline() -> None:
    require_database_url()
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    require_database_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
