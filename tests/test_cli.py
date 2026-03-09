import subprocess
import sys

from indigoapi import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "indigoapi", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
