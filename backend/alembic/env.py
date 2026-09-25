from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config.settings import settings
from app.database import Base
from app import models

config = context.config
# Alembic and the running application must always migrate the same database.
# Escape percent signs because ConfigParser treats them as interpolation tokens.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
