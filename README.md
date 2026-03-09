[![CI](https://github.com/DiamondLightSource/indigoapi/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/indigoapi/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/indigoapi/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/indigoapi)
[![PyPI](https://img.shields.io/pypi/v/indigoapi.svg)](https://pypi.org/project/indigoapi)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# indigoapi

An API for small fast data analysis jobs at Diamond Light Source

This is where you should write a short paragraph that describes what your module does,
how it does it, and why people should use it.

Source          | <https://github.com/DiamondLightSource/indigoapi>
:---:           | :---:
PyPI            | `pip install indigoapi`
Docker          | `docker run ghcr.io/diamondlightsource/indigoapi:latest`
Releases        | <https://github.com/DiamondLightSource/indigoapi/releases>

This is where you should put some images or code snippets that illustrate
some relevant examples. If it is a library then you might put some
introductory code here:

```python
from indigoapi import __version__

print(f"Hello indigoapi {__version__}")
```

Or if it is a commandline tool then you might put some example commands here:

To start the api server run in dev mode:

uvicorn indigoapi.main:start_api --reload --factory --host 127.0.0.1 --port 8000

```
python -m indigoapi --version
```
