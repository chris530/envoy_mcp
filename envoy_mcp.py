from kubernetes import client, config
from kubernetes.client.rest import ApiException
import requests
import time
import logging
from mcp.server.fastmcp import FastMCP

DEBUG_CONTAINER_NAME = "socat-debug"
SOCAT_IMAGE = "alpine/socat"
SERVICE_NAME = "envoy-debug"
SERVICE_PORT = 5555
config.load_incluster_config()
#config.load_kube_config()
core_api = client.CoreV1Api()

# Logging 

logger = logging.getLogger("envoy_mcp")

# Kubernetes logic 

def patch_ephemeral_container_by_label(namespace, lk, lv):
    label_selector = f"{lk}={lv}"
    
    try:
        # Step 1: List pods with label
        pods = core_api.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector
        )

        if not pods.items:
            return f"No pods found in namespace '{namespace}' with label {lk}={lv}."

        responses = []

        for pod in pods.items:
            podname = pod.metadata.name
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
                responses.append(f"Ephemeral container added to pod '{podname}'.")
            except ApiException as e:
                responses.append(f"Error patching pod '{podname}': {e.status} {e.reason} {e.body}")

        return "\n".join(responses)

    except ApiException as e:
        return f"Error listing pods: {e.status} {e.reason} {e.body}"

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


def delete_service(namespace):
    try:
        core_api.delete_namespaced_service(name=SERVICE_NAME, namespace=namespace)
        return f"Service '{SERVICE_NAME}' deleted from namespace '{namespace}'."
    except ApiException as e:
        if e.status == 404:
            return f"ℹ️Service '{SERVICE_NAME}' not found.", 200
        return f"Failed to delete service: {e.status} {e.reason} {e.body}", 500

mcp = FastMCP(name="EnvoyQueryServer")

@mcp.tool()
def query_envoy(namespace: str, labels: str):

   logger.info("Query envoy with: %s", namespace + " " + labels )

   lk = labels.split("=")[0]
   lv = labels.split("=")[1]

   patch_ephemeral_container_by_label(namespace, lk, lv)
   create_service(namespace, lk, lv)
   time.sleep(3) 

   try:

        HIT_URL = "http://"+SERVICE_NAME+"."+namespace+":"+str(SERVICE_PORT)+"/memory"
        response = requests.get(HIT_URL, timeout=5)
        return response.text

   except Exception as e:
        return f"query_envoy failed: {str(e)}" 
 

if __name__ == "__main__":
    mcp.run()
