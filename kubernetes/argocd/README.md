# ArgoCD

GitOps continuous delivery for the Employee Directory app.
A single ArgoCD Application manages everything — backend, frontend, monitoring (Prometheus + Grafana), and secrets.

## Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=120s

# Get the initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 --decode

# Port-forward to access the UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open https://localhost:8080  (admin / <password above>)
```

## Deploy

```bash
kubectl apply -f employee-app.yaml
```

ArgoCD will:
1. Pull `kubernetes/helm/` from the repo
2. Run `helm dependency update` to fetch `kube-prometheus-stack`
3. Deploy backend, frontend, Prometheus, Grafana, node-exporter, kube-state-metrics, ServiceMonitor, and custom dashboards — all in one release

## Check sync status

```bash
kubectl get applications -n argocd
kubectl describe application employee-app -n argocd
```

## Files

| File | What it deploys |
|------|----------------|
| `employee-app.yaml` | Everything — app + monitoring via `kubernetes/helm/` |

## How it works

```
Git push to main
      │
      ▼
ArgoCD detects change (polls every 3 minutes or via webhook)
      │
      ▼
helm dependency update  →  fetches kube-prometheus-stack subchart
      │
      ▼
helm install/upgrade kubernetes/helm/  →  EKS cluster
      │
      ├── backend (2 replicas)
      ├── frontend (2 replicas)
      ├── Prometheus + Grafana (kube-prometheus-stack subchart)
      ├── node-exporter (DaemonSet)
      ├── kube-state-metrics
      ├── ServiceMonitor (scrapes backend /metrics)
      └── grafana-custom-dashboards ConfigMap (platform, application, cloudwatch)
```

`automated.selfHeal: true` — manual cluster changes are reverted to match Git.
`automated.prune: true` — resources removed from Git are deleted from the cluster.
