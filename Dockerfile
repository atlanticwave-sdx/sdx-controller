# FROM python:3.9.6-buster

FROM python:3.9-slim-bullseye

RUN apt-get -y upgrade

RUN apt-get update \
    && apt-get install -y gcc python3-dev git

# RUN apt-get install -y python-dev
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app
COPY . /usr/src/app

EXPOSE 8080

ENTRYPOINT ["python3"]
CMD ["-m", "swagger_server"]
