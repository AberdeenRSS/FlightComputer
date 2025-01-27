# Mqtt

## Why

Mqtt is a protocol build to send small messages over unreliable networks. It is therfore ideal for a uscase such as exchanging
measurment data and commands for the flight computer.   

In the mqtt world there are two types of entities:
- Brokers
- Clients

brokers distribute the messages and are run on a server somewhere, with a well known public ip.
Clients is anyone sending or receiving messages, these can be the vessels, the users or any other component interacting
with the two.

## Requirements for our mqtt broker

There is a lot of mqtt brokers available online. The mqtt broker for our usecase needs to support jwt token validation to make
sure that only authroized users can send/receive messgas for a specific vessel. Jwt/oauth is used as it is the industry standard
and has very good security. More importantly though it makes it possible to verify keys through public/private key validation. This
means a token (and the info contained) can be validated without having to read from a database or call up a authentication server.   

## Explored brokers

Ther eare lots of different mqtt brokers available. 
