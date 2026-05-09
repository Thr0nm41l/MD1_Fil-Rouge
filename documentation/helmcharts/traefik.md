# Traefik Ingress Controller

**Helm chart:** `traefik/traefik`
**Namespace:** `traefik`
**Values file:** `helmcharts/traefik-values.yaml`

---

## Overview

Traefik is the ingress controller for the cluster. It acts as the single entry point for all HTTP traffic, routing requests to the appropriate service based on the hostname.

It is installed **first** in `start_infra.sh` and the script waits for its pod to be ready before deploying any other service — this ensures the `traefik` IngressClass exists when Ingress resources are later applied.

---

## Configuration

| Parameter | Value |
|---|---|
| Helm chart | `traefik/traefik` |
| Release name | `traefik` |
| Service type | `LoadBalancer` |
| IngressClass name | `traefik` |
| Default IngressClass | No |
| Dashboard | Enabled (insecure mode) |

### Providers

| Provider | Enabled | Notes |
|---|---|---|
| `kubernetesIngress` | Yes | Watches standard `Ingress` resources; publishes the LoadBalancer IP back to Ingress status |
| `kubernetesCRD` | Yes | Enables Traefik-native `IngressRoute` CRDs; `allowCrossNamespace: true` lets routes target services in other namespaces |

RBAC is enabled so Traefik has the cluster-level permissions needed to watch Ingress and CRD resources across all namespaces.

---

## Routing Table

All routes use the `web` entrypoint (port 80). Hostnames resolve to `127.0.0.1` via Minikube tunnel.

| Host | Target service | Namespace | Kind |
|---|---|---|---|
| `traefik.localhost/dashboard/` | `api@internal` | `traefik` | `IngressRoute` (CRD) |
| `airflow.localhost` | `airflow-api-server:8080` | `airflow` | `Ingress` |
| `pgadmin.localhost` | `pgadmin-pgadmin4:80` | `datalake` | `Ingress` |
| `api.localhost` | `apiservice:8000` | `datalake` | `Ingress` |
| `grafana.localhost` | `grafana:80` | `monitoring` | `Ingress` |
| `prometheus.localhost` | `prometheus-kube-prometheus-prometheus:9090` | `monitoring` | `Ingress` |
| `docs.localhost` | `mkdocs:8000` | `documentation` | `Ingress` |

The Traefik dashboard uses an `IngressRoute` (Traefik CRD) instead of a standard `Ingress` because the target `api@internal` is a virtual Traefik service, not a real Kubernetes service.

All other services use standard `networking.k8s.io/v1` `Ingress` resources with `ingressClassName: traefik`.

---

## Accessing the Dashboard

The dashboard is exposed at [http://traefik.localhost/dashboard/](http://traefik.localhost/dashboard/) (note the trailing slash).

It runs in **insecure mode** — no authentication is required. Do not expose this to a public network.

Requires Minikube tunnel to be running:

```bash
sudo minikube tunnel
```

---

## Installation

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --values helmcharts/traefik-values.yaml \
  -n traefik
```

Wait for readiness:

```bash
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=traefik -n traefik --timeout=120s
```

Apply ingress rules after all services are deployed:

```bash
kubectl apply -f helmcharts/ingress.yaml
```

---

## Teardown

```bash
helm uninstall traefik -n traefik
kubectl delete namespace traefik
```
