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

The structure of this app is defined below. IndigoAPI can add jobs to the queue in one of two ways. 
Either you send a request, via the client or any http request to the API endpoint which adds it to the queue. 

Alternatively jobs can be added automatically by listening to a RabbitMQ message stream. 

Either way jobs are added to the queue and run first-in-first-out. 
Once jobs are run, results can be returned to the client or via a reuqest with the specific job uuid.

Results are kept for a defined period of time, periodically the expired results are checked and removed.


             HTTP Client ────────
                  │             │
                  ▼             │
              IndigoAPI         │
                  │             │
                  ▼             ▼
            QueueManager ──► Results
                  │             
                  │          
                  │         
                  │
                  ▼
                Workers
                  ▲
                  │
RabbitMQ ──► RabbitListener

```
python -m indigoapi --version
```

1. Build and push your Docker image

Your chart references an image like:

image:
  repository: ghcr.io/your-org/indigoapi
  tag: latest

So first build and push it.

Example:

docker build -t ghcr.io/your-org/indigoapi:latest .
docker push ghcr.io/your-org/indigoapi:latest

If you use a private registry you may also need a Kubernetes imagePullSecret.

2. Check the chart renders correctly

Before installing, render the templates:

helm template indigoapi ./helm/indigoapi

You should see:

Deployment

Service

ConfigMap

You can also validate against Kubernetes:

helm template indigoapi ./helm/indigoapi | kubectl apply --dry-run=client -f -
3. Install the chart

From the root of your repo:

helm install indigoapi ./helm/indigoapi

indigoapi here is the release name.

Helm will create:

Deployment
Service
ConfigMap

in your cluster.

4. Check the deployment

Check pods:

kubectl get pods

Example result:

indigoapi-0.1.0-7f6c5c9fbb-abcde   Running

Check services:

kubectl get svc
5. Test the API

Port forward the service:

kubectl port-forward svc/indigoapi-0.1.0 8000:8000

http://localhost:8000/docs
