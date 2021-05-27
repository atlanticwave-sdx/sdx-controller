# sdx-controller

## SDX RabbitMQ architecture. 

RabbitMQ is a message broker: it accepts and forwards messages. The SDX 2.0 system will use RabbitMQ for any communication among the SDX controller, and the local controllers.

![SDX RabbitMQ architecture](https://user-images.githubusercontent.com/29924060/119758505-a776da00-be74-11eb-924d-9aade279ebcf.jpg)

## Queue and Router design
In the RabbitMQ world, the producers send messages to the consumers. In this case SDX controller is the producer and local controllers are the consumers.

A queue is essentially a large message buffer that forwards messages to consumers in a FIFO manor. To avoid collision among multiple consumers, we assign a different queue for each of the local controllers.

An exchange (router) sits between the producer and consumers, to route a message with a particular routing key will be delivered to all the queues that are bound with a matching binding key. Binding keys can contain wildcard matching patterns, such as \* (star) and \# (hash).

\* (star) can substitute for exactly one word.

\# (hash) can substitute for zero or more words.

The table below summarizes the SDX message queue design.

**A separate queue is assigned for each of the local controllers.**

Router | Topic | Description
------------ | ------------- | ------------- 
*LinkState* | Link state | Route link state related messages (such as link failure/up)
*NodeState* | Node state | Route link state related messages (such as node join/leave)
*Manifest*  | manifest | Route manifest (new or updated) to corresponding local controllers
*Log*       | Log | Route log related messages
*FailureRecovery* | Failure_recovery | Route failure handling related messages (such as link failure/up, port/VLAN changes)
*HeartBeat* | Heartbeat | Route heartbeat messages (heartbeat request/response)
