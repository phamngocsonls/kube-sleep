
# kube-sleep
<img src="https://raw.githubusercontent.com/phamngocsonls/kube-sleep/refs/heads/main/image/logo.png" width="210" height="200">

## Overview
_kube-sleep_ is a simple script that automatically scale down K8S resources in during off-peak hours by change HPA `min_replicas` config. You can save infrastructure costs up to 25% with _kube-sleep_.

## How it work?
_kube-sleep_ schedule scale down and scale up your Deployment/StatefulSet by change HPA `min_replicas` config. _kube-sleep_ keeps HPA in configmap
## Deployment

To deploy *kube-sleep*:
```sh
kubectl create namespace kube-sleep
kubectl apply -k deploy
```
## Usage

By change configmap  `kube-sleep` in namespace `kube-sleep`:
```yaml
{"scale_up":"02:35", #schedule scale up time. UTC timezone
"scale_down":"02:33", #schedule scale down time. UTC timezone
"min_replicas":"0.1,2", #keep 10% replica (math.ceil). But if 10% replica is lower than 2 -> min_replicas = 2 
"target_namespace": "default", #target_namespace to scale down. use "*" to target all namespace. Use " default,default1" to target multi namespace
"exclude_namespace": "kube-system", #excule namespace, use "*" to execule all namespace (turn off toll). Use " kube-system,kube-system2" to exclude multi namespace
"exclude_hpa":"nginx2_default", # exclude specific hpa name. nginx2_default -> hpa name: nginx2 and namespace is default. use " nginx2_default,nginx3_default" to exclude multi HPA
"scale_up_delay":15, #sleep time for each time scale up HPA
"scale_up_timeout":1800} #if total of scale_up_delay > scale_up_timeout. scale_up_delay = scale_up_timeout/count(HPA).
```
