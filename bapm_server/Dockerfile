FROM python:3.9.6-buster

RUN apt-get update \
    && apt-get install -y gcc python-dev

# RUN apt-get install -y python-dev
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app
COPY . /usr/src/app

ENTRYPOINT ["python3"]
CMD ["__main__.py"]

# CMD ["/bin/bash"]
