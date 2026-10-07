#!/bin/bash
# Cluster add-ons used from session 11 onwards, on the kind cluster in
# kind-cluster.yaml. Run once after `kind create cluster --config kind-cluster.yaml`.
set -euo pipefail

# metrics-server - feeds `kubectl top` and the HPA (session 13).
# kind's kubelets use self-signed serving certs, hence --kubelet-insecure-tls.
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

# MetalLB - gives type: LoadBalancer Services a real external IP. On a cloud
# provider the cloud controller does this; on kind nothing does, so without it
# EXTERNAL-IP stays <pending> forever (session 11).
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.16.0/config/manifests/metallb-native.yaml
kubectl -n metallb-system wait --for=condition=Available deployment/controller --timeout=180s
kubectl -n metallb-system rollout status daemonset/speaker --timeout=180s
# Hand out addresses from the top of the docker network kind runs on.
SUBNET=$(docker network inspect kind --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' | tr ' ' '\n' | grep -v ':' | head -1)
PREFIX=$(echo "$SUBNET" | cut -d. -f1-2)
cat <<YAML | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: kind-pool
  namespace: metallb-system
spec:
  addresses:
    - ${PREFIX}.255.200-${PREFIX}.255.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: kind-l2
  namespace: metallb-system
YAML

# ingress-nginx - the Ingress controller for session 12. The kind flavour of
# the manifest binds host ports 80/443 on the node labelled ingress-ready=true.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx wait --for=condition=Ready pod -l app.kubernetes.io/component=controller --timeout=300s

kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
echo "add-ons ready"
