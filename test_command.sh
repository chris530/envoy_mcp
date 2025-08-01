#!/bin/bash 

curl -X POST http://localhost:8080/config_dump -d "POD_NAME=envoy-mcp-6947898457-jt8b" -d "NAMESPACE=web"
