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

A `compose.yaml` is provided for bringing up SDX Controller and a
MongoDB instance, and a separate `compose.bapm.yml` is provided for
bringing up bapm-server and a single-node ElasticSearch instance.

To start/stop SDX Controller, from the project root directory, do:

```console
$ source .env
$ docker compose up --build
$ docker compose down
```

Navigate to http://localhost:8080/SDX-Controller/1.0.0/ui/ for testing
the API.  The OpenAPI/Swagger definition should be available at
http://localhost:8080/SDX-Controller/1.0.0/openapi.json.

Similarly, to start/stop BAPM Server, do:

```
$ source .env
$ docker compose -f compose.bapm.yml up --build
$ docker compose -f compose.bapm.yml down
```

To start/stop all the services together:

```
$ source .env
$ docker compose -f compose.yml -f compose.bapm.yml up --build
$ docker compose -f compose.yml -f compose.bapm.yml down
```

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
$ pip3 install [--editable] .
$ source .env
$ flask --app sdx_controller.app:app run --debug
```

### Test topology files and connection requests

During normal course of operation, SDX Controller receives topology
data from Local Controllers, which are dynamically created based on
real network topology. We have developed some static topology files
and connection requests that can be used during development and
testing. Since they are used in several places during SDX development,
they are all consolidated in the lower-layer [datamodel] library's
repository:

- [AmLight topology][amlight.json] ([raw][amlight_raw])
- [SAX topology][sax.json] ([raw][sax_raw])
- [ZAOXI topology][zaoxi.json] ([raw][zaoxi_raw])
- [Sample connection request][test_request] ([raw][test_request_raw])
- [Sample AmLight topology with link failure][amlight_link_failure.json] ([raw][amlight_link_failure_raw])

## Running the test suite

### With tox

You will need [tox] and [tox-docker]:

```console
$ python3 -m venv venv --upgrade-deps
$ source ./venv/bin/activate
$ pip install tox tox-docker
```

Once you have `tox` and `tox-docker` installed, you can run tests:

```console
$ tox
```

You can also run a single test:

```console
$ tox -- -s sdx_controller/test/test_connection_controller.py::TestConnectionController::test_getconnection_by_id
```

If you want to examine Docker logs after the test suite has exited,
run tests with `tox --docker-dont-stop [mongo|rabbitmq]`, and then use
`docker logs <container-name>`.

### With pytest

If you want to avoid tox and run [pytest] directly, that is possible
too.  You will need to run MongoDB and RabbitMQ, which can be launched
with Docker:

```console
$ docker run --rm -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:latest
$ docker run --rm -d --name mongo -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=guest -e MONGO_INITDB_ROOT_PASSWORD=guest mongo:7.0.5
```

Some environment variables are expected to be set for the tests to
work as expected, so you may want to copy `env.template` to `.env` and
edit it according to your environment, and make sure the env vars are
present in your shell:

```console
$ cp env.template .env 
$ # and then edit .env to suit your environment
$ source .env
$ pytest```console
```


<!-- References -->

[tox]: https://tox.wiki/en/latest/
[tox-docker]: https://tox-docker.readthedocs.io/
[pytest]: https://docs.pytest.org/

[sdx-to-lc-img]: https://user-images.githubusercontent.com/29924060/139588273-100a0bb2-14ba-496f-aedf-a122b9793325.jpg
[lc-to-sdx-img]: https://user-images.githubusercontent.com/29924060/139588283-2ea32803-92e3-4812-9e8a-3d829549ae40.jpg

[controller-ci-badge]: https://github.com/atlanticwave-sdx/sdx-controller/actions/workflows/test.yml/badge.svg
[controller-ci]: https://github.com/atlanticwave-sdx/sdx-controller/actions/workflows/test.yml

[controller-cov-badge]: https://coveralls.io/repos/github/atlanticwave-sdx/sdx-controller/badge.svg?branch=main (Coverage Status)
[controller-cov]: https://coveralls.io/github/atlanticwave-sdx/sdx-controller?branch=main

[datamodel]: https://github.com/atlanticwave-sdx/datamodel

[amlight.json]: https://github.com/atlanticwave-sdx/datamodel/blob/main/src/sdx_datamodel/data/topologies/amlight.json
[amlight_raw]: https://raw.githubusercontent.com/atlanticwave-sdx/datamodel/main/src/sdx_datamodel/data/topologies/amlight.json

[sax.json]: https://github.com/atlanticwave-sdx/datamodel/blob/main/src/sdx_datamodel/data/topologies/sax.json
[sax_raw]: https://raw.githubusercontent.com/atlanticwave-sdx/datamodel/main/src/sdx_datamodel/data/topologies/sax.json

[zaoxi.json]: https://github.com/atlanticwave-sdx/datamodel/blob/main/src/sdx_datamodel/data/topologies/zaoxi.json
[zaoxi_raw]: https://raw.githubusercontent.com/atlanticwave-sdx/datamodel/main/src/sdx_datamodel/data/topologies/zaoxi.json

[test_request]: https://github.com/atlanticwave-sdx/datamodel/blob/main/src/sdx_datamodel/data/requests/test_request.json
[test_request_raw]: https://raw.githubusercontent.com/atlanticwave-sdx/datamodel/main/src/sdx_datamodel/data/requests/test_request.json

[amlight_link_failure.json]: https://github.com/atlanticwave-sdx/datamodel/blob/main/src/sdx_datamodel/data/topologies/amlight_link_failure.json
[amlight_link_failure_raw]: https://raw.githubusercontent.com/atlanticwave-sdx/datamodel/main/src/sdx_datamodel/data/topologies/amlight_link_failure.json
