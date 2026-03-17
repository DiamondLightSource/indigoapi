# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
FROM ghcr.io/diamondlightsource/ubuntu-devcontainer:noble AS developer

# Add any system dependencies for the developer/build environment here
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    graphviz \
    && apt-get dist-clean 


# Install helm for the dev container. This is the recommended 
# approach per the docs: https://helm.sh/docs/intro/install
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3; \
    chmod 700 get_helm.sh; \
    ./get_helm.sh; \
    rm get_helm.sh
RUN helm plugin install https://github.com/losisin/helm-values-schema-json.git --version 2.3.1

# The build stage installs the context into the venv
FROM developer AS build

# Change the working directory to the `app` directory
# and copy in the project
WORKDIR /app
COPY . /app
RUN chmod o+wrX .
RUN apk add libc6-compat

# Tell uv sync to install python in a known location so we can copy it out later
ENV UV_PYTHON_INSTALL_DIR=/python

RUN uv add debugpy

# Sync the project without its dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev


# The runtime stage copies the built venv into a runtime container
FROM ubuntu:noble AS runtime

# Add apt-get system dependecies for runtime here if needed
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git \
    && apt-get dist-clean

# Copy the python installation from the build stage
COPY --from=build /python /python

# Copy the environment, but not the source code
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH



# Copy the python installation from the build stage
COPY --from=build /python /python


# Add copy of indigoapi source to container for debugging
WORKDIR /workspaces
COPY --chown=1000:1000 . indigoapi
# Make allowance for non-1000 uid
RUN chmod o+wrX indigoapi

# Switch user 1000
USER ubuntu

ENTRYPOINT ["indigoapi"]
CMD ["serve"]

# # change this entrypoint if it is not the same as the repo
# ENTRYPOINT ["indigoapi"]
# CMD ["--version"]
