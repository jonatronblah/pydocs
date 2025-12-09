import click
import asyncio
from functools import wraps
from uuid import uuid4
import alembic.config
import os
from pydocs.cli import create_user

alembicArgs = [
    "upgrade",
    "head",
]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.group()
def cli():
    pass


@click.command(name="init")
def init_admin():
    os.chdir("pydocs")
    alembic.config.main(argv=alembicArgs)
    pw = uuid4().hex
    asyncio.run(
        create_user(
            username="jonatron",
            email="jonatron@gmail.com",
            password=pw,
            is_superuser=True,
        )
    )
    click.echo(pw)


cli.add_command(init_admin)

if __name__ == "__main__":
    cli()
