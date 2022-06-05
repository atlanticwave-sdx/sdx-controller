#FROM python:3.6-alpine
FROM python:3.9.6-buster

RUN apt-get update \
    && apt-get install -y gcc python-dev

# RUN apt-get install -y python-dev
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install "connexion[swagger-ui]"

RUN git clone https://github.com/atlanticwave-sdx/datamodel.git
WORKDIR /usr/src/app/datamodel
RUN git checkout develop && git pull
RUN pip3 install -r requirements.txt
RUN python3 setup.py install

WORKDIR /usr/src/app/
RUN git clone https://github.com/atlanticwave-sdx/pce.git
WORKDIR /usr/src/app/pce
RUN pip3 install -r requirements.txt
RUN python3 setup.py install

ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/datamodel"
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/pce"

WORKDIR /usr/src/app
COPY . /usr/src/app

EXPOSE 8080

ENTRYPOINT ["python3"]
CMD ["-m", "swagger_server"]

# CMD ["/bin/bash"]
