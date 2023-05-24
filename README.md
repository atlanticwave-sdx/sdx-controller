# SDX Controller Service

## Overview
The SDX controller is the central point of the AW-SDX system. It coordinates among local controllers (LCs), datamodels, Path Computation Engine (PCE), as well as domain managers, such as Kytos and OESS. Its major responsibilities include:

* Collect domain topology from all the LCs.
* Assumble domain topology into global network topology.
* Handle user SDX end-to-end connection request.
* Call Path Computation Engine (PCE) to compute optimal path, and break down topology into per-LC topology.
* Distribute connection requests to corresponding LCs.
* Receive and process measurement data from Behavior, Anomaly and Performance Manager (BAPM).

### BAPM
The Behavior, Anomaly, and Performance Manager (BAPM) is a self-driving, multi-layer system. It collects fine-grained measurement data from the SDX's underlying infrastructures, and send data reports to the SDX controller. The SDX controller BAPM server included in this project is responsible for receiving and processing the BAPM data.

## Prerequisites 

- run the RabbitMQ server
 The easiest way to run RabbitMQ is using docker:

```
sudo docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:latest
```

Then in `env` and `docker-compose.yml` files, change `MQ_HOST` host to the corresponding IP address or hostname of the RabbitMQ server

## Run with Python

You will need:

 - Python 3.9.6+
 - RabbitMQ
 - MongoDB

The communication between SDX controller and Local controller is
enabled by RabbitMQ.  RabbitMQ can either run on the SDX controller,
or run on a separate node.

See notes under testing for some hints about running RabbitMQ and
MongoDB.


The SDX controller server is a swagger-enabled Flask server based on the [swagger-codegen](https://github.com/swagger-api/swagger-codegen) project.
To run the SDX controller server, please execute the following from the project root directory:

```
pip3 install -r requirements.txt
python3 -m swagger_server
```

and open your browser to here:

```
http://localhost:8080/SDX-Controller/1.0.0/ui/
```

The Swagger definition lives here:

```
http://localhost:8080/SDX-Controller/1.0.0/swagger.json
```

## Running with Docker (Recommended)

Running with Docker provides clean and integrated environment for each server instance, and provide easy scalability capabilities. Therefore, we recommend using Docker to run the SDX controller. 

To run the server on a Docker container, execute the following from the project root directory:

```bash
# building the image
docker build -t sdx-controller .

# starting up a container
docker run -p 8080:8080 sdx-controller
```

To run the SDX Controller server and BAPM server, Docker is required. 
Execute the following from the project root directory:

```bash
# install ElasticSearch
sh elastic-search-setup.sh

# building SDX Controller image
docker build -t sdx-controller .

# build BAPM server image
cd bapm_server
docker build -t bapm-server .

# run both SDX controller and BAPM server with docker-compose
docker-compose up
```

MongoDB is included in `docker-compose`, so running `docker-compose up` will bring up MongoDB as well. But if it's preferred to run MongoDB separately from `docker-compose`, here is the way:

```
$ docker run -it --rm --name mongo \
    -p 27017:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=guest \
    -e MONGO_INITDB_ROOT_PASSWORD=guest \
    mongo:3.7
```

## Communication between SDX Controller and Local Controller

The SDX controller and local controller communicate using RabbitMQ. All the topology and connectivity related messages are sent with RPC, with receiver confirmation. The monitoring related messages are sent without receiver confirmation.

Below are two sample scenarios for RabbitMQ implementation:

SDX controller breaks down the topology and sends connectivity information to local controllers:
![SDX controller to local controller](https://user-images.githubusercontent.com/29924060/139588273-100a0bb2-14ba-496f-aedf-a122b9793325.jpg)

Local controller sends domain information to SDX controller:
![Local controller to SDX controller](https://user-images.githubusercontent.com/29924060/139588283-2ea32803-92e3-4812-9e8a-3d829549ae40.jpg)

## Testing

The test suite expects MongoDB and RabbitMQ, which can be launched
with Docker (or Podman), as shown in the earlier examples.

Some environment variables are expected to be set for the tests to
work as expected. Edit `env.local` according to your environment, and
make sure the env vars are present in your shell:

```console
$ source env.local
```

And now run [tox]:

```console
$ tox
```


<!-- References -->

[tox]: https://tox.wiki/en/latest/
