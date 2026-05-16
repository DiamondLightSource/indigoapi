# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
FROM ghcr.io/diamondlightsource/ubuntu-devcontainer:noble AS developer

# Add any system dependencies for the developer/build environment here
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    graphviz \
    && apt-get dist-clean 

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 libgl1 libegl1 -y
RUN apt-get update && apt-get install -y \
    libx11-xcb-dev \
    libglu1-mesa-dev \
    libxrender-dev \
    libxi-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    libegl1 \
    libxcb-cursor0 -y

RUN apt-get update && apt-get install -y \
    libxcb-icccm4 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0

RUN apt-get install fonts-noto-color-emoji -y

# The build stage installs the context into the venv
FROM developer AS build

# Change the working directory to the `app` directory
# and copy in the project
WORKDIR /app
COPY . /app
RUN chmod o+wrX .

# Tell uv sync to install python in a known location so we can copy it out later
ENV UV_PYTHON_INSTALL_DIR=/python

# Sync the project without its dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev --managed-python


# The runtime stage copies the built venv into a runtime container
FROM ubuntu:resolute AS runtime

# Add apt-get system dependecies for runtime here if needed
# RUN apt-get update -y && apt-get install -y --no-install-recommends \
#     some-dependecies \
#     && apt-get dist-clean

# Copy the python installation from the build stage
COPY --from=build /python /python

# Copy the environment, but not the source code
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

# change this entrypoint if it is not the same as the repo
ENTRYPOINT ["indigoapi"]
CMD ["serve"]

# # change this entrypoint if it is not the same as the repo
# ENTRYPOINT ["indigoapi"]
# CMD ["--version"]


ENV MPLCONFIGDIR=/tmp/matplotlib
RUN export DISPLAY=:0
