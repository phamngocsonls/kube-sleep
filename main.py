import kubernetes
from kubernetes import client, config
import json
import time
from datetime import datetime,timezone
import math

def read_configmap(name, namespace):
    """
    Reads a ConfigMap in the specified namespace.
    """
    config.load_incluster_config()  # Use config.load_incluster_config() if running inside a cluster

    v1 = client.CoreV1Api()
    try:
        # Get the ConfigMap
        configmap = v1.read_namespaced_config_map(name=name, namespace=namespace)
        return configmap.data
    except client.exceptions.ApiException as e:
        print(f"Failed to read ConfigMap: {e.reason}")
        print(e.body)
        return None

def add_file_to_configmap(name, namespace, key_name, file_content):
    """
    Adds a new file's content as a key-value pair to an existing ConfigMap.
    """
    config.load_incluster_config()  # Use config.load_incluster_config() if running inside a cluster

    v1 = client.CoreV1Api()
    try:
        # Retrieve the existing ConfigMap
        configmap = v1.read_namespaced_config_map(name=name, namespace=namespace)
        # Add the new file content as a key
        configmap.data[key_name] = file_content

        # Replace the ConfigMap in the cluster
        updated_configmap = v1.replace_namespaced_config_map(
            name=name,
            namespace=namespace,
            body=configmap
        )
        #print(f"ConfigMap '{name}' updated successfully with new key '{key_name}'!")
    except client.exceptions.ApiException as e:
        print(f"Failed to update ConfigMap: {e.reason}")
        print(e.body)

def update_hpa_min_replicas(hpa_name, namespace, new_min_replicas):
    # Load kubeconfig from default location or in-cluster configuration
    config.load_incluster_config()  # Use config.load_incluster_config() if running inside a cluster
    # Create an instance of the Autoscaling V1 API
    autoscaling_v1 = client.AutoscalingV1Api()

    try:
        # Retrieve the existing HPA
        hpa = autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(
            name=hpa_name,
            namespace=namespace
        )

        # Update the minReplicas value
        hpa.spec.min_replicas = new_min_replicas

        # Apply the updated HPA
        updated_hpa = autoscaling_v1.replace_namespaced_horizontal_pod_autoscaler(
            name=hpa_name,
            namespace=namespace,
            body=hpa
        )

        print(f"Updated HPA '{updated_hpa.metadata.name}', namespace: '{namespace} minReplicas to {new_min_replicas}")
    except client.exceptions.ApiException as e:
        print(f"Failed to update HPA: {e.reason}")
        print(e.body)

def get_all_hpas():
    """
    Retrieves all Horizontal Pod Autoscaler (HPA) configurations from the cluster.

    Returns:
        A list of HPA objects.
    """
    config.load_incluster_config()  # Load the kubeconfig file
    v1 = client.AutoscalingV1Api()
    return_data = {}
    try:
        hpas = v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        for hpa in hpas.items:
            return_data[hpa.metadata.name + "_" + hpa.metadata.namespace] =hpa.spec.min_replicas
        return return_data
        #return hpas.items
    except kubernetes.client.exceptions.ApiException as e:
        print("Exception when calling AutoscalingV1Api->list_horizontal_pod_autoscaler_for_all_namespaces: %s\n" % e)  

def scale_down(config_data):
    #snapshot
    exclude_namespace = []
    exclude_hpa = []
    processed_list = []
    target_hpa_namespace = []
    target_hpa_namespace_adv = []
    exclude_day = []
    hpas = get_all_hpas()
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    namespace_list = []
    try:
        # Get the list of namespaces
        namespaces = v1.list_namespace()
        for ns in namespaces.items:
            namespace_list.append(ns.metadata.name)
    except client.exceptions.ApiException as e:
        print(f"Error listing namespaces: {e.reason}")
        print(e.body)
    
    if "exclude_day" in config_data:
        if config_data["exclude_day"].find(",") > -1:
            exclude_day = config_data["exclude_day"].split(",")
    day_of_week = datetime.now(timezone.utc).strftime("%a")
    day_of_month = datetime.now(timezone.utc).strftime("%d")
    if "target_hpa_namespace" in config_data:
        if config_data["target_hpa_namespace"].find(",") > -1:
            target_hpa_namespace = config_data["target_hpa_namespace"].split(",")
            if len(target_hpa_namespace) > 0:
                for i in target_hpa_namespace:
                    temp = i.split("_")
                    if temp[1] not in target_hpa_namespace_adv:
                        target_hpa_namespace_adv.append(temp[1])

    if "exclude_namespace" in config_data:
        if config_data["exclude_namespace"].find(",") > -1:
            exclude_namespace = config_data["exclude_namespace"].split(",")
    if config_data["target_namespace"] == "*": #all namespace:
        target_namespace = namespace_list
    else:
        target_namespace = config_data["target_namespace"].split(",")
    if "exclude_hpa" in config_data:
        if config_data["exclude_namespace"].find(",") > -1:
            exclude_hpa = config_data["exclude_hpa"].split(",")
    for hpa in hpas:
        hpa_name = hpa.split("_")[0]
        namespace = hpa.split("_")[1]

        if namespace in target_namespace and namespace not in exclude_namespace and hpa not in exclude_hpa and day_of_month not in exclude_day and day_of_week not in exclude_day:
            if namespace in target_hpa_namespace_adv: #check config target_hpa_namespace
                if hpa not in target_hpa_namespace:
                    continue
            min_rep_list = config_data['min_replicas'].split(",")
            if math.ceil(float(min_rep_list[0])*hpas[hpa]) < int(min_rep_list[1]):
                target_scale = int(min_rep_list[1])
            else:
                target_scale = math.ceil(float(min_rep_list[0])*hpas[hpa])
            if hpas[hpa] <= target_scale:
                processed_list.append(hpa)
                continue

            update_hpa_min_replicas(hpa_name,namespace,target_scale)
            temp_config = {hpa:hpas[hpa]}
            configmap = read_configmap('kube-sleep','kube-sleep')
            hpa_config = json.loads(configmap['hpa.json'].replace("'", "\""))
            hpa_config.update(temp_config)
            add_file_to_configmap('kube-sleep', "kube-sleep", 'hpa.json', str(hpa_config))
            processed_list.append(hpa)
    configmap = read_configmap('kube-sleep','kube-sleep')
    hpa_config = json.loads(configmap['hpa.json'].replace("'", "\""))
    is_change = False
    for i in list(hpa_config):
        if i not in processed_list:
            hpa_config.pop(i,'None')
            is_change = True
    if is_change:
        add_file_to_configmap('kube-sleep', "kube-sleep", 'hpa.json', str(hpa_config))

def scale_up(config_data):
    configmap = read_configmap('kube-sleep','kube-sleep')
    try:
        hpa_config = json.loads(configmap['hpa.json'].replace("'", "\""))
    except:
        return
    sleep_time = config_data["scale_up_delay"]
    if len(hpa_config) == 0:
        return
    total_time = 0
    if "scale_up_timeout" in config_data:
        total_time = len(hpa_config)*config_data["scale_up_delay"]
        if total_time > config_data['scale_up_timeout']:
            sleep_time = config_data['scale_up_timeout']/len(hpa_config)
    for i in hpa_config:
        update_hpa_min_replicas(i.split("_")[0],i.split("_")[1],hpa_config[i])
        time.sleep(sleep_time)
        total_time+=sleep_time
    add_file_to_configmap('kube-sleep', "kube-sleep", 'hpa.json', "{}") #clear config after scale up

def main():
    while True:
        with open('./config/config.json', 'r') as file:
            config_data = json.load(file)
        time_now = datetime.now(timezone.utc).strftime("%H:%M")
        if config_data['exclude_namespace'] == "*": #skip
            time.sleep(58)
        elif config_data['scale_down'] == time_now:
            configmap = read_configmap('kube-sleep','kube-sleep')
            if 'hpa.json' not in configmap:
                add_file_to_configmap('kube-sleep', "kube-sleep", 'hpa.json', '{}')
            scale_down(config_data)
            time.sleep(61)
        elif config_data['scale_up'] == time_now:
            scale_up(config_data)
            time.sleep(61)
        else:
            time.sleep(28)

if __name__ == "__main__":
    main()