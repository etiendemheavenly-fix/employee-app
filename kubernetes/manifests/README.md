# Kubernetes Manifests — Teaching Progression

Raw YAML files to teach Kubernetes objects one at a time, from the simplest unit (Pod) to a full production-grade deployment.

## Apply order

```bash
kubectl apply -f 02-namespace.yaml
kubectl apply -f 03-configmap.yaml
kubectl apply -f 04-secret.yaml          # local only — on EKS use 10-externalsecret.yaml
kubectl apply -f 05-postgres.yaml        # local only — on EKS use RDS
kubectl apply -f 09-serviceaccount.yaml
kubectl apply -f 06-deployment.yaml
kubectl apply -f 07-service.yaml
kubectl apply -f 08-ingress.yaml         # requires AWS Load Balancer Controller
kubectl apply -f 10-externalsecret.yaml  # EKS only — requires ESO
kubectl apply -f 11-hpa.yaml             # requires metrics-server
kubectl apply -f 12-resourcequota.yaml
```

Or apply everything at once:

```bash
kubectl apply -f .
```

## Object reference

| File | Object | What it teaches |
|------|--------|----------------|
| `01-pod.yaml` | Pod | Smallest unit — one container, no self-healing |
| `02-namespace.yaml` | Namespace | Logical isolation within the cluster |
| `03-configmap.yaml` | ConfigMap | Non-sensitive config injected as env vars |
| `04-secret.yaml` | Secret | Sensitive data stored base64-encoded |
| `05-postgres.yaml` | PVC + Deployment + Service | Stateful workload with persistent storage |
| `06-deployment.yaml` | Deployment | Self-healing, rolling updates, scaling |
| `07-service.yaml` | Service | Stable DNS name for a set of pods |
| `08-ingress.yaml` | Ingress | External HTTP routing via ALB |
| `09-serviceaccount.yaml` | ServiceAccount | Pod identity + IRSA for AWS access |
| `10-externalsecret.yaml` | SecretStore + ExternalSecret | Sync secrets from AWS Secrets Manager |
| `11-hpa.yaml` | HorizontalPodAutoscaler | Auto-scale pods on CPU/memory |
| `12-resourcequota.yaml` | ResourceQuota + LimitRange | Namespace resource caps |

## Useful commands

```bash
# Watch all resources in the namespace
kubectl get all -n employee-app

# Watch pods in real time
kubectl get pods -n employee-app --watch

# Describe a pod (events, errors)
kubectl describe pod <pod-name> -n employee-app

# Exec into a pod
kubectl exec -it <pod-name> -n employee-app -- bash

# View logs
kubectl logs <pod-name> -n employee-app --follow

# Get the ALB URL
kubectl get ingress employee-app -n employee-app

# Delete everything in the namespace
kubectl delete all --all -n employee-app
```
