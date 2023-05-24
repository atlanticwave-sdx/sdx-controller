# SDX Controller Service

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


### BAPM

The Behavior, Anomaly, and Performance Manager (BAPM) is a
self-driving, multi-layer system. It collects fine-grained measurement
data from the SDX's underlying infrastructures, and send data reports
to the SDX controller. The SDX controller BAPM server included in this
project is responsible for receiving and processing the BAPM data.


## Run with Python

You will need:

* Python 3.9.6+
* RabbitMQ
* MongoDB

The communication between SDX controller and Local controller is
enabled by RabbitMQ.  RabbitMQ can either run on the SDX controller,
or run on a separate node.  See notes under testing for some hints
about running RabbitMQ and MongoDB.

Prior to running SDX Server, you will need to copy `env.template` to
`.env`, adjust it to your environment, and source it.

```console
$ source .env
```

To run the SDX controller server, do this from the project root
directory:

```console
$ pip3 install -r requirements.txt
$ python3 -m swagger_server
```

Navigate to http://localhost:8080/SDX-Controller/1.0.0/ui/ for testing
the API.  The OpenAPI/Swagger definition should be available at
http://localhost:8080/SDX-Controller/1.0.0/swagger.json.


## Running with Docker Compose (recommended)

Copy `env.template` to `.env`, and adjust it according to your
environment.  And then, from the project root directory, do:

```
$ docker compose up
```

If you have made some local changes that you need to test, use:

```
$ docker compose up --build
```

You might need to install Elastic Search too.  The script
`elastic-search-setup.sh` should be useful on Rocky Linux systems:

```
$ sudo sh elastic-search-setup.sh
```

### Building the container images

We have two container images: sdx-server and `bapm-server. Do this to
build them:

```bash
$ docker build -t sdx-controller .
$ cd bapm_server
$ docker build -t bapm-server .
```

To run sdx-controller alone:

```
$ docker run -p 8080:8080 sdx-controller --env-file=.env
```


## Communication between SDX Controller and Local Controller

The SDX controller and local controller communicate using
RabbitMQ. All the topology and connectivity related messages are sent
with RPC, with receiver confirmation. The monitoring related messages
are sent without receiver confirmation.

Below are two sample scenarios for RabbitMQ implementation:

SDX controller breaks down the topology and sends connectivity
information to local controllers: ![SDX controller to local
controller](https://user-images.githubusercontent.com/29924060/139588273-100a0bb2-14ba-496f-aedf-a122b9793325.jpg)

Local controller sends domain information to SDX controller: ![Local
controller to SDX
controller](https://user-images.githubusercontent.com/29924060/139588283-2ea32803-92e3-4812-9e8a-3d829549ae40.jpg)

## Testing

Some of the tests expects MongoDB and RabbitMQ, which can be launched
with Docker (or Podman):

```
$ docker run -rm -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:latest
$ docker run -rm -d --name mongo -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=guest -e MONGO_INITDB_ROOT_PASSWORD=guest mongo:3.7
```

Some environment variables are expected to be set for the tests to
work as expected. Copy `env.template` to `.env` and edit it according
to your environment, and make sure the env vars are present in your
shell:

```console
$ source .env
```

And now run [tox]:

```console
$ tox
```


<!-- References -->

[tox]: https://tox.wiki/en/latest/
