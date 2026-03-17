"""Interface for ``python -m indigoapi``."""

import click
import uvicorn

from indigoapi.main import start_api

from ._version import __version__

__all__ = ["main"]


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, message="%(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        print("Please invoke subcommand!")


@main.command(name="serve")
def serve():
    uvicorn.run(start_api(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
