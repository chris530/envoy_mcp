#!/bin/bash

curl http://envoy-mcp.kagent:8080/v1/engage --header "Content-Type: application/json" --request POST --data '{"namespace":"web", "podname": "nginx-75d4f4b545-5kvs7", "labels": "app=nginx"  }'
