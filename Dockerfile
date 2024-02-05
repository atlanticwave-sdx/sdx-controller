FROM flask-base

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

<<<<<<< HEAD
COPY ./container-sdx-controller /usr/src/app
=======
WORKDIR /usr/src/app
COPY . /usr/src/app
>>>>>>> main

# In order to make setuptools_scm work during container build, we
# temporarily bind-mount .git.  Via
# https://github.com/pypa/setuptools_scm/issues/77#issuecomment-844927695
RUN --mount=source=.git,target=.git,type=bind \
    pip install --no-cache-dir .[wsgi]

EXPOSE 8080

ENTRYPOINT ["python3"]
CMD ["-m", "uvicorn", "sdx_controller.app:asgi_app", "--host", "0.0.0.0", "--port", "8080"]
