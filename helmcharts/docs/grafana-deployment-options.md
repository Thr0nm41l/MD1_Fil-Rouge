# Grafana Deployment Options

## Overview

You have multiple ways to deploy Grafana in your Kubernetes cluster. Here's a comparison to help you choose.

## Options Comparison

| Feature | Helm Chart (Current) | Grafana Operator | Bundled with Prometheus |
|---------|---------------------|------------------|------------------------|
| **Status** | ⚠️ Deprecated | ✅ Active | ✅ Active |
| **Complexity** | 🟢 Simple | 🟡 Moderate | 🟢 Very Simple |
| **Flexibility** | 🟢 High | 🟢 Very High | 🔴 Low |
| **GitOps Ready** | 🟡 Partial | 🟢 Native | 🟡 Partial |
| **Learning Curve** | 🟢 Easy | 🟡 Moderate | 🟢 Easy |
| **Best For** | Development | Production | Quick Setup |
| **Maintenance** | 🟡 Security only | 🟢 Active dev | 🟢 Active dev |

## Option 1: Grafana Helm Chart (Current Setup)

**What we're using now.**

### Pros
✅ Simple and straightforward
✅ Well-documented
✅ Works perfectly for development
✅ Easy to customize
✅ Familiar Helm workflow

### Cons
⚠️ Shows deprecation warning
⚠️ Maintenance mode only
⚠️ No new features

### Use This If:
- You're learning Kubernetes/Grafana
- Running in development/test environment
- Want simple setup with Helm
- Don't need cutting-edge features

### Files:
- `grafana-values.yaml`
- `start_infra.sh`

### Installation:
```bash
./start_infra.sh
```

---

## Option 2: Grafana Operator (Recommended for Production)

**Modern, cloud-native approach using Kubernetes CRDs.**

### Pros
✅ Not deprecated - actively maintained
✅ Kubernetes-native (CRDs)
✅ GitOps friendly
✅ Dashboards as code
✅ Auto-discovery of datasources
✅ Production-ready
✅ Official Grafana Labs approach

### Cons
⚠️ More complex setup
⚠️ Requires understanding of CRDs
⚠️ Different workflow than Helm

### Use This If:
- Deploying to production
- Want modern cloud-native approach
- Using GitOps (ArgoCD/Flux)
- Need dashboards in version control
- Want automatic datasource discovery

### Files:
- `grafana-operator-values.yaml` - Operator configuration
- `grafana-instance.yaml` - Grafana deployment
- `grafana-datasources.yaml` - Datasource configuration
- `start_infra_operator.sh` - Installation script

### Installation:
```bash
./start_infra_operator.sh
```

### How It Works:

1. **Add Helm repository:**
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

2. **Install Operator:**
```bash
helm install grafana-operator grafana/grafana-operator \
  --values grafana-operator-values.yaml \
  -n monitoring
```

2. **Create Grafana Instance (CRD):**
```yaml
apiVersion: grafana.integreatly.org/v1beta1
kind: Grafana
metadata:
  name: grafana
spec:
  config:
    security:
      admin_user: admin
```

3. **Create Datasources (CRD):**
```yaml
apiVersion: grafana.integreatly.org/v1beta1
kind: GrafanaDatasource
metadata:
  name: prometheus-datasource
spec:
  datasource:
    type: prometheus
    url: http://prometheus:9090
```

4. **Create Dashboards (CRD):**
```yaml
apiVersion: grafana.integreatly.org/v1beta1
kind: GrafanaDashboard
metadata:
  name: my-dashboard
spec:
  json: |
    {
      "dashboard": {...}
    }
```

### Key Differences:

**Helm Chart Approach:**
```bash
# Everything in one values file
helm install grafana grafana/grafana --values values.yaml
```

**Operator Approach:**
```bash
# Install operator once
helm install grafana-operator grafana-operator/grafana-operator

# Create instances declaratively
kubectl apply -f grafana-instance.yaml
kubectl apply -f grafana-datasources.yaml
kubectl apply -f grafana-dashboards.yaml
```

---

## Option 3: Bundled with Prometheus (Simplest)

**Re-enable Grafana bundled in kube-prometheus-stack.**

### Pros
✅ One-command installation
✅ Pre-configured for Prometheus
✅ No deprecation warnings
✅ Simplest setup

### Cons
⚠️ Less flexible
⚠️ Tied to Prometheus lifecycle
⚠️ Harder to customize
⚠️ Can't update independently

### Use This If:
- You only need basic monitoring
- Don't care about Grafana independence
- Want absolute simplest setup

### Configuration:

Edit `prometheus-values.yaml`:
```yaml
grafana:
  enabled: true  # Change from false to true
  adminPassword: Gr@f@n@Admin123
  persistence:
    enabled: true
    size: 5Gi
```

Then:
```bash
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --values prometheus-values.yaml \
  -n monitoring
```

---

## Decision Guide

### Choose **Helm Chart** (Current) if:
- 🎓 Learning environment
- 🧪 Development/testing
- ⚡ Quick setup needed
- 📝 Deprecation warning acceptable

### Choose **Grafana Operator** if:
- 🏭 Production environment
- 🔄 Using GitOps
- 📊 Need dashboards in Git
- 🚀 Want modern cloud-native approach
- ⚙️ Comfortable with CRDs

### Choose **Bundled** if:
- 🎯 Simplicity is priority
- 📦 Only monitoring infrastructure
- 🔗 Don't need Grafana independence

---

## Migration Path

### From Helm Chart to Operator

1. **Export existing dashboards:**
```bash
# In Grafana UI: Dashboards → Export → Save as JSON
```

2. **Install Operator:**
```bash
./start_infra_operator.sh
```

3. **Import dashboards as CRDs:**
```yaml
apiVersion: grafana.integreatly.org/v1beta1
kind: GrafanaDashboard
metadata:
  name: my-dashboard
spec:
  json: |
    {
      # Paste exported JSON here
    }
```

4. **Remove old Grafana:**
```bash
helm uninstall grafana -n monitoring
```

### From Bundled to Separate

1. **Export dashboards** from current Grafana

2. **Disable bundled Grafana:**
```yaml
# prometheus-values.yaml
grafana:
  enabled: false
```

3. **Install standalone** (Helm or Operator)

4. **Import dashboards**

---

## Recommended Setup by Use Case

### Local Development (Minikube)
**→ Current Helm Chart** ✅
- Deprecation warning is fine
- Simple and fast
- What you have now

### Production (Small/Medium)
**→ Grafana Operator** ✅
- Modern approach
- Better lifecycle management
- GitOps ready

### Production (Large Scale)
**→ Grafana Cloud** or **Grafana Operator**
- Consider managed service
- Or self-hosted with Operator
- High availability setup

### Quick Demo/POC
**→ Bundled with Prometheus** ✅
- Fastest setup
- One command
- Good enough for demos

---

## Current Project Status

**We're using:** Helm Chart (deprecated)
**Provided alternative:** Grafana Operator setup ready to use

### To Switch to Operator:

1. **Stop current infrastructure:**
```bash
./stop_infra.sh
```

2. **Start with Operator:**
```bash
./start_infra_operator.sh
```

3. **Access Grafana:**
```bash
kubectl port-forward svc/grafana-service 3000:3000 -n monitoring
```

Both scripts are ready to use - your choice!

---

## FAQ

### Q: Should I worry about the deprecation warning?
**A:** Not for development. The chart works fine and gets security updates.

### Q: What's the main benefit of the Operator?
**A:** Dashboards and datasources as Kubernetes resources (GitOps-friendly).

### Q: Is the Operator harder to use?
**A:** Slightly more complex initially, but more powerful for production.

### Q: Can I try the Operator without losing my setup?
**A:** Yes! Export your dashboards first, then switch. Or test in a separate namespace.

### Q: Which should I learn?
**A:** Start with Helm chart (simpler). Move to Operator when you need production features.

---

## Resources

- [Grafana Operator Documentation](https://grafana-operator.github.io/grafana-operator/)
- [Grafana Operator GitHub](https://github.com/grafana-operator/grafana-operator)
- [Grafana Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/grafana)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
