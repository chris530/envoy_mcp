# Chris Haessig  7/31/25

from flask import Flask, request, jsonify
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import requests
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DEBUG_CONTAINER_NAME = "socat-debug"
SOCAT_IMAGE = "alpine/socat"
SERVICE_NAME = "envoy-debug"
SERVICE_PORT = 5555
config.load_incluster_config()
#config.load_kube_config()
core_api = client.CoreV1Api()


# Kubernetes logic 

def patch_ephemeral_container(namespace, podname, lk, lv):
    patch = {
        "spec": {
            "ephemeralContainers": [
                {
                    "name": DEBUG_CONTAINER_NAME,
                    "image": SOCAT_IMAGE,
                    "command": ["socat", f"TCP-LISTEN:{SERVICE_PORT},fork", "TCP:localhost:15000"],
                    "stdin": True,
                    "tty": True,
                    "securityContext": {"privileged": True}
                }
            ]
        }
    }

    try:
        core_api.patch_namespaced_pod_ephemeralcontainers(
            name=podname,
            namespace=namespace,
            body=patch
        )
        return f"Ephemeral container added to pod '{podname}'."
    except ApiException as e:
        return f"Error patching pod: {e.status} {e.reason} {e.body}"


def create_service(namespace, lk, lv):
    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name=SERVICE_NAME,
            namespace=namespace
        ),
        spec=client.V1ServiceSpec(
            selector={lk: lv},
            ports=[
                client.V1ServicePort(
                    name="debug",
                    port=SERVICE_PORT,
                    target_port=SERVICE_PORT,
                    protocol="TCP"
                )
            ]
        )
    )
    try:
        core_api.create_namespaced_service(namespace=namespace, body=service)
        return f"Service '{SERVICE_NAME}' created in namespace '{namespace}'."
    except ApiException as e:
        if e.status == 409:
            return f"ℹ️ Service '{SERVICE_NAME}' already exists."
        else:
            return f"Error creating service: {e.status} {e.reason} {e.body}" 

def restart_pod(podname, namespace):

    try:
        core_api.delete_namespaced_pod(name=podname, namespace=namespace)
        return f"Pod '{podname}' deleted for restart."
    except ApiException as e:
        return f"Failed to delete pod: {e.status} {e.reason} {e.body}", 500



def delete_service(namespace):
    try:
        core_api.delete_namespaced_service(name=SERVICE_NAME, namespace=namespace)
        return f"Service '{SERVICE_NAME}' deleted from namespace '{namespace}'."
    except ApiException as e:
        if e.status == 404:
            return f"ℹ️ Service '{SERVICE_NAME}' not found.", 200
        return f"Failed to delete service: {e.status} {e.reason} {e.body}", 500

def query_service(namespace):

    HIT_URL = "http://"+SERVICE_NAME+"."+namespace+":"+str(SERVICE_PORT)+"/config_dump"

    return requests.get(HIT_URL).text


# Flask 

@app.route('/v1', methods=['GET'])
def root():
    return jsonify({
        "name": "Envoy MCP Server",
        "version": "1.0.0",
        "type": "model"
    })

@app.route('/v1/schema', methods=['GET'])
def schema():
    return jsonify({
        "input": {
            "type": "object",
            "properties": {
                "podname": {"type": "string"},
                "namespace": {"type": "string"},
                "labels": {"type": "string"}
            },
            "required": ["podname", "namespace", "labels"]
        },
        "output": {
            "type": "object",
            "properties": {
                "config": {"type": "string", "description": "Generated configuration file from envoy"}
            }
        }
    })

@app.route('/v1/engage', methods=['POST'])
def engage():

    # need the pod name , labels and namespace 

    input_data = request.json
    podname = input_data.get("podname", "")
    namespace = input_data.get("namespace", "")
    labels = input_data.get("labels", "")
    lk = labels.split("=")[0]
    lv = labels.split("=")[1]

    # Seems we need to add a little time to create the service so a delay was added.  

    app.logger.info("Patching pod "+podname)
    patch_ephemeral_container(namespace, podname, lk, lv)
    app.logger.info("Creating service with labels"+lk+"="+lv)
    create_service(namespace, lk, lv)
    time.sleep(3)
    data = query_service(namespace)
    app.logger.info("Delete service "+namespace)
    delete_service(namespace)

    return jsonify({"config": data})
    


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

