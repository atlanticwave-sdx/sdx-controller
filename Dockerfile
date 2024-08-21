# We specify a multi-stage build here.  Some of the packages we use
# need a compiler to install, but not at runtime.  Using a multi-stage
# build results in smaller final images, since we won't be install
# things we don't need in them.

# The builder image.
FROM python:3.9-slim-bullseye AS sdx-builder-image

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends gcc python3-dev git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /usr/src/app

WORKDIR /usr/src/app

# create a venv.
RUN python -m venv /opt/venv --upgrade-deps

# Make sure we use the venv.
ENV PATH="/opt/venv/bin:$PATH"

COPY . /usr/src/app

# The final image.
FROM python:3.9-slim-bullseye AS sdx-runtime-image

COPY --from=sdx-builder-image /opt/venv /opt/venv

# Make sure we use the venv.
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8080

ENTRYPOINT ["python3"]
CMD ["-m", "uvicorn", "sdx_controller.app:asgi_app", "--host", "0.0.0.0", "--port", "8080"]
