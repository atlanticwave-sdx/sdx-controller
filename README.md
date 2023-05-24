# SDX Controller Service

[![controller-ci-badge]][controller-ci] [![controller-cov-badge]][controller-cov]

## Overview

The SDX controller is the central point of the AW-SDX system. It
coordinates among local controllers (LCs), datamodels, Path
Computation Engine (PCE), as well as domain managers, such as Kytos
and OESS. Its major responsibilities include:

* Collect domain topology from all the LCs.
* Assumble domain topology into global network topology.
* Handle user SDX end-to-end connection request.
* Call Path Computation Engine (PCE) to compute optimal path, and
  break down topology into per-LC topology.
* Distribute connection requests to corresponding LCs.
* Receive and process measurement data from Behavior, Anomaly and
  Performance Manager (BAPM).

The SDX controller server is a swagger-enabled Flask server based on
the [swagger-codegen](https://github.com/swagger-api/swagger-codegen)
project.


## BAPM

The Behavior, Anomaly, and Performance Manager (BAPM) is a
self-driving, multi-layer system. It collects fine-grained measurement
data from the SDX's underlying infrastructures, and send data reports
to the SDX controller. The SDX controller BAPM server included in this
project is responsible for receiving and processing the BAPM data.


## Communication between SDX Controller and Local Controller

The SDX controller and local controller communicate using
RabbitMQ. All the topology and connectivity related messages are sent
with RPC, with receiver confirmation. The monitoring related messages
are sent without receiver confirmation.

Below are two sample scenarios for RabbitMQ implementation.

SDX controller breaks down the topology and sends connectivity
information to local controllers: 

![SDX controller to local controller][sdx-to-lc-img]

Local controller sends domain information to SDX controller: 

![Local controller to SDX controller][lc-to-sdx-img]


## Running SDX Controller

### Configuration

Copy the provided `env.template` file to `.env`, and adjust it
according to your environment.

The communication between SDX controller and Local controller is
enabled by RabbitMQ, which can either run on the same node as SDX
controller, or on a separate node.  See notes under testing for some
hints about running RabbitMQ.

You might need to install Elastic Search too.  The script
`elastic-search-setup.sh` should be useful on Rocky Linux systems:

```console
$ sudo sh elastic-search-setup.sh
```

### Running with Docker Compose (recommended)

A `docker-compose.yaml` is provided for bringing up run
sdx-controller, bapm-server, and a MongoDB instance used by
sdx-controller.  From the project root directory, do:

```console
$ source .env
$ docker compose up --build
```

Navigate to http://localhost:8080/SDX-Controller/1.0.0/ui/ for testing
the API.  The OpenAPI/Swagger definition should be available at
http://localhost:8080/SDX-Controller/1.0.0/openapi.json.

Use `docker compose down` to shut down the services.


#### Building the container images

We have two container images: sdx-server and `bapm-server. Do this to
build them:

```console
$ docker build -t sdx-controller .
$ cd bapm_server
$ docker build -t bapm-server .
```

To run sdx-controller alone:

```console
$ docker run -p 8080:8080 sdx-controller --env-file=.env
```

### Running with Python

You will need:

* Python 3.9.6+
* RabbitMQ
* MongoDB

See notes under testing for some hints about running RabbitMQ and
MongoDB.

To run the SDX controller server, do this from the project root
directory:

```console
$ python3 -m venv venv --upgrade-deps
$ source ./venv/bin/activate
$ pip3 install -r requirements.txt
$ source .env
$ python3 -m swagger_server
```

## Running the test suite

Some of the tests expects MongoDB and RabbitMQ, which can be launched
with Docker:

```console
$ docker run --rm -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:latest
$ docker run --rm -d --name mongo -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=guest -e MONGO_INITDB_ROOT_PASSWORD=guest mongo:3.7
```

Some environment variables are expected to be set for the tests to
work as expected, so you may want to copy `env.template` to `.env` and
edit it according to your environment, and make sure the env vars are
present in your shell:

```console
$ source .env
```

And now run [tox]:

```console
$ tox
```


<!-- References -->

[tox]: https://tox.wiki/en/latest/

[sdx-to-lc-img]: https://user-images.githubusercontent.com/29924060/139588273-100a0bb2-14ba-496f-aedf-a122b9793325.jpg
[lc-to-sdx-img]: https://user-images.githubusercontent.com/29924060/139588283-2ea32803-92e3-4812-9e8a-3d829549ae40.jpg

[controller-ci-badge]: https://github.com/atlanticwave-sdx/sdx-controller/actions/workflows/test.yml/badge.svg
[controller-ci]: https://github.com/atlanticwave-sdx/sdx-controller/actions/workflows/test.yml

[controller-cov-badge]: https://coveralls.io/repos/github/atlanticwave-sdx/sdx-controller/badge.svg?branch=main (Coverage Status)
[controller-cov]: https://coveralls.io/github/atlanticwave-sdx/sdx-controller?branch=main
