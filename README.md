[![CI](https://github.com/DiamondLightSource/indigoapi/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/indigoapi/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/indigoapi/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/indigoapi)
[![PyPI](https://img.shields.io/pypi/v/indigoapi.svg)](https://pypi.org/project/indigoapi)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# indigoapi

An API for small fast data analysis jobs at Diamond Light Source.

`indigoapi` exposes an HTTP API to submit analysis jobs, return queued results, and optionally consume messages from RabbitMQ.

Source          | <https://github.com/DiamondLightSource/indigoapi>
:---:           | :---:
PyPI            | `pip install indigoapi`
Docker          | `docker run ghcr.io/diamondlightsource/indigoapi:latest`
Releases        | <https://github.com/DiamondLightSource/indigoapi/releases>

Example Python usage:

```python
from indigoapi import __version__

print(f"Hello indigoapi {__version__}")
```

Example server start command:

```bash
uvicorn indigoapi.main:start_api --reload --factory --host 127.0.0.1 --port 8000
```

Or if it is a commandline tool then you might put some example commands here:

To start the api server run in dev mode:

uvicorn indigoapi.main:start_api --reload --factory --host 127.0.0.1 --port 8000

## Overview

The app accepts analysis jobs via HTTP and stores results in memory for a configurable TTL. Jobs can also be ingested from RabbitMQ if `rabbitmq.enabled` is set.

### Request flow

- HTTP client submits jobs to `/analyse`
- Jobs are queued in `QueueManager`
- Workers process jobs in FIFO order
- Results are returned via `/result/id/{request_id}`
- Optional RabbitMQ listener can enqueue jobs automatically

                     HTTP Client ────────--
                          │                │
                          ▼                ▼
                      IndigoAPI ──---►   Results
                          │                ▲
                          ▼                │
                    QueueManager           │
                          │                │   
                          ▼                │
                        Workers            │
                          ▲                │
                          │                │               
                    RabbitListener <-── RabbitMQ

## Kubernetes deployment

This repository includes a Helm chart under `./helm/helm/indigoapi`.

### Config support

The service supports configuration from one of these sources:

- `CONFIG_PATH` environment variable
- mounted config file at `/etc/config/config.yaml`
- local `config.yaml` file in the current working directory

In Kubernetes, the Helm chart mounts `config.yaml` from a `ConfigMap` and sets:

```yaml
env:
  - name: CONFIG_PATH
    value: "/etc/config/config.yaml"
```

### RabbitMQ config

The Helm values now expose RabbitMQ settings in the same shape as the app expects:

```yaml
config:
  rabbitmq:
    enabled: true
    host: localhost
    username: guest
    password: guest
    port: 61613
    destinations:
      - "/topic/public.worker.event"
      - "/topic/gda.messages.scan"
      - "/topic/gda.messages.processing"
```

## Helm usage

1. Build and push your Docker image

```bash
podman build -t ghcr.io/diamondlightsource/indigoapi:latest .
podman push ghcr.io/diamondlightsource/indigoapi:latest
```

2. Render the chart

```bash
helm template indigoapi ./helm/helm/indigoapi
```

3. Dry-run validation

```bash
helm template indigoapi ./helm/helm/indigoapi | kubectl apply --dry-run=client -f -
```

4. Install the chart

```bash
helm install indigoapi ./helm/helm/indigoapi
```

5. Verify the deployment

```bash
kubectl get pods
kubectl get svc
```

6. Test the API

```bash
kubectl port-forward svc/indigoapi 8000:8000
```

Then open:

```text
http://localhost:8000/docs
```

## Notes

- The chart name has been updated to `indigoapi`.
- The config file is mounted via a `ConfigMap` and loaded from `/etc/config/config.yaml`.
- The Helm chart currently creates a `Deployment`, `Service`, and `ConfigMap`.
