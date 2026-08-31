# Kubernetes

## From Containers to Container Orchestration

Docker solved the "it works on my machine" problem — you package your app and its dependencies into an image and run it as a container anywhere.

But in production, one container is not enough. You need:

- Multiple instances of your app for high availability
- Automatic restarts when a container crashes
- Rolling updates with zero downtime
- Traffic routing across healthy instances
- Secrets and config management
- Auto-scaling under load
- Storage that survives container restarts

Running `docker run` manually doesn't scale. You'd need to SSH into servers, track which containers are running where, restart failures by hand, and manually balance traffic. That's container management — not orchestration.

**Container orchestration** automates all of that. You declare the desired state ("I want 3 replicas of this app, always running, exposed on port 80") and the orchestrator continuously works to make reality match that declaration.

Kubernetes (K8s) is the industry-standard container orchestrator. You stop thinking about individual containers and start thinking about workloads, and Kubernetes handles the rest.

---

## Kubernetes Architecture

A Kubernetes cluster is made up of two types of machines: **control plane nodes** and **worker nodes**.

```
┌─────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                        │
│                                                             │
│   ┌─────────────┐  ┌─────────┐  ┌──────────────────────┐  │
│   │ API Server  │  │  etcd   │  │  Controller Manager  │  │
│   └─────────────┘  └─────────┘  └──────────────────────┘  │
│          │                              │                   │
│   ┌─────────────┐                       │                   │
│   │  Scheduler  │───────────────────────┘                   │
│   └─────────────┘                                           │
└────────────────────────────┬────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   WORKER NODE   │ │   WORKER NODE   │ │   WORKER NODE   │
│                 │ │                 │ │                 │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │  kubelet  │  │ │  │  kubelet  │  │ │  │  kubelet  │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │ kube-proxy│  │ │  │ kube-proxy│  │ │  │ kube-proxy│  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │  Pods...  │  │ │  │  Pods...  │  │ │  │  Pods...  │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Control Plane Components

The control plane is the brain of the cluster. It makes global decisions about scheduling, scaling, and healing. On EKS, AWS manages the control plane for you.

### API Server (`kube-apiserver`)

The single entry point for all cluster operations. Every `kubectl` command, every controller, every node — they all talk to the API server. It validates requests, authenticates them, and persists the resulting state to etcd.

```bash
# Everything you do goes through the API server
kubectl get pods          # GET  /api/v1/namespaces/default/pods
kubectl apply -f app.yaml # POST /api/v1/namespaces/default/deployments
```

### etcd

A distributed key-value store that holds the entire cluster state — every object, every config, every status. If etcd is lost without a backup, the cluster is gone. On EKS, AWS manages and backs up etcd automatically.

### Scheduler (`kube-scheduler`)

Watches for newly created Pods that have no node assigned, then picks the best node based on resource requests, node affinity, taints/tolerations, and available capacity.

### Controller Manager (`kube-controller-manager`)

Runs a collection of controllers in a single process. Each controller watches a specific resource type and reconciles actual state toward desired state:

| Controller | What it does |
|------------|-------------|
| Deployment controller | Creates/updates ReplicaSets when a Deployment changes |
| ReplicaSet controller | Ensures the correct number of Pod replicas are running |
| Node controller | Detects and responds to node failures |
| Job controller | Tracks Jobs to completion |
| ServiceAccount controller | Creates default ServiceAccounts in new namespaces |

### Cloud Controller Manager

On EKS, this bridges Kubernetes and AWS — it provisions load balancers when you create a Service of type `LoadBalancer`, attaches EBS volumes for PersistentVolumeClaims, and manages node lifecycle with EC2.

---

## Worker Node Components

### kubelet

An agent running on every node. It receives Pod specs from the API server and ensures the containers described in those specs are running and healthy. It reports node and Pod status back to the control plane.

### kube-proxy

Maintains network rules on each node. It implements the Service abstraction — when traffic arrives for a Service's ClusterIP, kube-proxy routes it to one of the backing Pods using iptables or IPVS rules.

### Container Runtime

The software that actually runs containers — on EKS this is `containerd`. kubelet talks to it via the Container Runtime Interface (CRI).

---

## Kubernetes Objects

Everything in Kubernetes is an **object** — a persistent record of desired state stored in etcd. You declare what you want, and Kubernetes works to make it real.

```bash
kubectl apply -f object.yaml   # create or update
kubectl get <kind>             # list
kubectl describe <kind> <name> # inspect
kubectl delete <kind> <name>   # remove
```

---

### Pod

The smallest deployable unit. A Pod wraps one or more containers that share a network namespace (same IP) and can share storage volumes. Pods are ephemeral — when they die, they're gone. You almost never create Pods directly in production.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backend
  namespace: employee-app
spec:
  containers:
    - name: backend
      image: 075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1
      ports:
        - containerPort: 5000
```

```bash
kubectl get pods -n employee-app
kubectl logs backend -n employee-app
kubectl exec -it backend -n employee-app -- bash
```

---

### Namespace

A virtual cluster inside the physical cluster. Namespaces scope names — two Deployments named `backend` can coexist in different namespaces. They also scope RBAC, ResourceQuotas, and NetworkPolicies.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: employee-app
```

```bash
kubectl get namespaces
kubectl get all -n employee-app
```

---

### ConfigMap

Stores non-sensitive configuration as key-value pairs. Injected into Pods as environment variables or mounted as files. Decouples config from the container image.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: employee-app
data:
  APP_ENV: production
  LOG_LEVEL: info
```

```bash
kubectl get configmap backend-config -n employee-app -o yaml
```

---

### Secret

Stores sensitive data (passwords, tokens, keys) base64-encoded. Kubernetes keeps Secrets separate from ConfigMaps so they can be handled with tighter RBAC and audit controls. Base64 is encoding, not encryption — use External Secrets for real security.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: employee-app
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbDovLy4uLg==   # base64
```

```bash
kubectl get secret db-secret -n employee-app -o jsonpath='{.data.DATABASE_URL}' | base64 -d
```

---

### Deployment

The standard way to run stateless workloads. A Deployment manages a ReplicaSet, which manages Pods. It gives you:

- Desired replica count — always running
- Rolling updates — new version rolls out gradually, old version rolls in if health checks fail
- Rollback — one command to go back

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: employee-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: 075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1
          ports:
            - containerPort: 5000
          envFrom:
            - secretRef:
                name: db-secret
```

```bash
kubectl rollout status deployment/backend -n employee-app
kubectl rollout history deployment/backend -n employee-app
kubectl rollout undo deployment/backend -n employee-app
kubectl scale deployment backend --replicas=4 -n employee-app
```

---

### Service

Pods come and go — their IPs change. A Service gives a stable DNS name and IP that always routes to healthy Pods matching its selector. kube-proxy handles the actual load balancing.

| Type | Use case |
|------|----------|
| `ClusterIP` | Internal traffic only (default) |
| `NodePort` | Expose on a static port on every node |
| `LoadBalancer` | Provision a cloud load balancer (NLB on EKS) |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: employee-app
spec:
  selector:
    app: backend       # routes to Pods with this label
  ports:
    - port: 5000
      targetPort: 5000
  type: ClusterIP
```

```bash
kubectl get svc -n employee-app
kubectl describe svc backend -n employee-app
```

---

### Ingress

Routes external HTTP/HTTPS traffic into the cluster based on hostname and path rules. Requires an Ingress Controller — on EKS we use the AWS Load Balancer Controller, which provisions an ALB per Ingress.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: employee-app
  namespace: employee-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
    - http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 5000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

```bash
kubectl get ingress -n employee-app   # ADDRESS column = ALB DNS name
```

---

### ServiceAccount

Every Pod in Kubernetes runs as a ServiceAccount — it's the Pod's identity inside the cluster. By default, Pods use the `default` ServiceAccount in their namespace, which has no permissions.

On EKS, ServiceAccounts are the foundation of **IRSA (IAM Roles for Service Accounts)**. Here's how it works:

1. EKS creates an OIDC identity provider for the cluster
2. You create an IAM role with a trust policy that allows a specific ServiceAccount to assume it
3. You annotate the ServiceAccount with the IAM role ARN
4. When the Pod starts, EKS injects a projected token into the Pod
5. The AWS SDK automatically exchanges that token for temporary STS credentials

No static access keys. No secrets to rotate. Credentials are scoped to exactly what the role allows.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: employee-app
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::075120018043:role/landmark-cluster-dev-app-sa"
```

The backend Pod references this ServiceAccount:

```yaml
spec:
  serviceAccountName: app-sa
  containers:
    - name: backend
      ...
```

```bash
kubectl get serviceaccount -n employee-app
kubectl describe serviceaccount app-sa -n employee-app
```

---

### Role and ClusterRole

Kubernetes RBAC (Role-Based Access Control) controls who can do what in the cluster. It has two parts: defining permissions (Role/ClusterRole) and assigning them (RoleBinding/ClusterRoleBinding).

A `Role` grants permissions within a single namespace. A `ClusterRole` grants permissions cluster-wide — used for resources that aren't namespaced (nodes, PersistentVolumes) or when you need the same permissions across all namespaces.

Permissions are additive — there is no deny. You grant only what's needed.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: employee-app
rules:
  - apiGroups: [""]           # "" = core API group (pods, services, secrets...)
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
```

```bash
kubectl get roles -n employee-app
kubectl describe role pod-reader -n employee-app
```

---

### RoleBinding and ClusterRoleBinding

A `RoleBinding` attaches a Role to a subject — a user, a group, or a ServiceAccount. This is the **who** side of RBAC. A `ClusterRoleBinding` does the same but cluster-wide.

Common pattern: create a `ClusterRole` with read-only permissions, then use a `RoleBinding` (not ClusterRoleBinding) to grant it only within a specific namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: employee-app
subjects:
  - kind: ServiceAccount
    name: app-sa
    namespace: employee-app
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl get rolebinding -n employee-app
kubectl auth can-i list pods --as=system:serviceaccount:employee-app:app-sa -n employee-app
```

---

### PersistentVolume and PersistentVolumeClaim

Pods are stateless by default — their filesystem is destroyed when the Pod dies. For stateful workloads like databases, you need storage that outlives the Pod.

- **PersistentVolume (PV)** — a piece of actual storage in the cluster. On EKS this is an EBS volume. It exists independently of any Pod.
- **PersistentVolumeClaim (PVC)** — a request for storage made by a Pod. You specify how much storage you need and the access mode. Kubernetes finds a matching PV and binds them together.
- **StorageClass** — defines how PVs are dynamically provisioned. On EKS, the `gp2` or `gp3` StorageClass provisions EBS volumes automatically when a PVC is created — you never have to create PVs manually.

Access modes:

| Mode | Meaning |
|------|---------|
| `ReadWriteOnce` | Mounted read-write by a single node (EBS) |
| `ReadOnlyMany` | Mounted read-only by many nodes |
| `ReadWriteMany` | Mounted read-write by many nodes (EFS) |

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: employee-app
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

The PVC is referenced in the Pod spec:

```yaml
volumes:
  - name: postgres-storage
    persistentVolumeClaim:
      claimName: postgres-pvc
containers:
  - name: postgres
    volumeMounts:
      - name: postgres-storage
        mountPath: /var/lib/postgresql/data
```

```bash
kubectl get pvc -n employee-app          # check Bound status
kubectl get pv                           # see the provisioned EBS volume
kubectl describe pvc postgres-pvc -n employee-app
```

---

### StatefulSet

A Deployment treats all its Pods as identical and interchangeable. A StatefulSet gives each Pod a stable, unique identity that persists across rescheduling:

- Stable pod names: `postgres-0`, `postgres-1`, `postgres-2` — always in that order
- Stable DNS: `postgres-0.postgres.employee-app.svc.cluster.local`
- Each Pod gets its own PVC via `volumeClaimTemplates` — `postgres-0` always gets the same volume
- Pods are created in order (0, 1, 2) and deleted in reverse order

Use StatefulSet for databases, message queues, and any workload that needs stable storage or stable network identity. In this project, we use a StatefulSet for in-cluster Postgres (local/teaching). On EKS in production, we use RDS instead.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: employee-app
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15
          env:
            - name: POSTGRES_USER
              value: postgres
            - name: POSTGRES_PASSWORD
              value: postgres
            - name: POSTGRES_DB
              value: employees
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
```

```bash
kubectl get statefulset -n employee-app
kubectl get pods -n employee-app          # postgres-0
kubectl get pvc -n employee-app           # data-postgres-0 created automatically
kubectl exec -it postgres-0 -n employee-app -- psql -U postgres -d employees
```

---

### ExternalSecret

Storing secrets directly in Kubernetes — even as base64 Secrets — means your sensitive data lives in etcd. Anyone with cluster access can read them. The **External Secrets Operator (ESO)** solves this by keeping the source of truth in AWS Secrets Manager and syncing into Kubernetes automatically.

Two resources work together:

- **SecretStore** — tells ESO how to connect to AWS Secrets Manager. It uses the `app-sa` ServiceAccount (IRSA) — no static credentials.
- **ExternalSecret** — tells ESO which secret to fetch from AWS and what Kubernetes Secret to create from it. ESO re-syncs on the `refreshInterval`.

The flow:
```
AWS Secrets Manager  →  ESO (via IRSA)  →  Kubernetes Secret  →  Pod env var
```

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: employee-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: app-sa
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: employee-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: landmark-cluster-dev/employee-app
        property: database_url
```

```bash
kubectl get secretstore -n employee-app
kubectl get externalsecret -n employee-app
kubectl describe externalsecret db-credentials -n employee-app   # check sync status
kubectl get secret db-credentials -n employee-app                # created by ESO
```

---

### HorizontalPodAutoscaler (HPA)

Manually scaling with `kubectl scale` doesn't respond to real traffic. The HPA watches actual resource utilization and automatically adjusts the replica count — scaling out when load increases, scaling back in when it drops.

Requires `metrics-server` to be installed in the cluster:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

The HPA checks metrics every 15 seconds. It scales up immediately when thresholds are breached, but waits 5 minutes before scaling down (to avoid flapping).

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend
  namespace: employee-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # scale out when avg CPU > 70%
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80   # scale out when avg memory > 80%
```

```bash
kubectl get hpa -n employee-app
kubectl describe hpa backend -n employee-app   # shows current vs target metrics
kubectl get hpa -n employee-app --watch        # watch scaling events live
```

---

### ResourceQuota and LimitRange

Without resource controls, a single Pod can consume all CPU and memory on a node, starving every other workload. Two objects address this at different levels:

**ResourceQuota** — enforced at the namespace level. Sets a hard ceiling on the total resources all Pods in the namespace can request or consume combined. Also caps the number of objects (Pods, Services, Secrets, etc.).

**LimitRange** — enforced at the container level. Sets defaults and maximums for individual containers. If a container doesn't specify resource requests/limits, LimitRange fills them in automatically. This also ensures the HPA has something to measure against.

CPU is measured in millicores: `100m` = 0.1 CPU core, `1000m` = 1 core.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: employee-app-quota
  namespace: employee-app
spec:
  hard:
    requests.cpu: "4"       # total CPU requests across all pods
    requests.memory: 4Gi
    limits.cpu: "8"         # total CPU limits across all pods
    limits.memory: 8Gi
    pods: "20"              # max number of pods in this namespace
---
apiVersion: v1
kind: LimitRange
metadata:
  name: employee-app-limits
  namespace: employee-app
spec:
  limits:
    - type: Container
      defaultRequest:       # applied if container omits requests
        cpu: 100m
        memory: 128Mi
      default:              # applied if container omits limits
        cpu: 500m
        memory: 512Mi
      max:                  # hard ceiling per container
        cpu: "2"
        memory: 2Gi
```

```bash
kubectl get resourcequota -n employee-app
kubectl describe resourcequota employee-app-quota -n employee-app   # shows used vs hard
kubectl get limitrange -n employee-app
```

---

## Object Summary

| Object | Kind | What it does |
|--------|------|-------------|
| Pod | core | Smallest unit — one or more containers |
| Namespace | core | Logical isolation within the cluster |
| ConfigMap | core | Non-sensitive config as env vars or files |
| Secret | core | Sensitive data, base64-encoded |
| Deployment | apps | Stateless workloads — self-healing, rolling updates |
| StatefulSet | apps | Stateful workloads — stable names and persistent storage |
| Service | core | Stable DNS + load balancing across Pods |
| Ingress | networking | External HTTP routing via ALB |
| PersistentVolumeClaim | core | Request for persistent storage |
| PersistentVolume | core | Actual storage provisioned in the cluster |
| ServiceAccount | core | Pod identity — used for IRSA on EKS |
| Role / ClusterRole | rbac | What actions are allowed on which resources |
| RoleBinding / ClusterRoleBinding | rbac | Who gets which Role |
| ExternalSecret | external-secrets.io | Sync secrets from AWS Secrets Manager |
| HorizontalPodAutoscaler | autoscaling | Auto-scale Pods on CPU/memory |
| ResourceQuota | core | Cap total resources per namespace |
| LimitRange | core | Default and max resources per container |

---

## Essential kubectl Commands

```bash
# Context and cluster
kubectl config get-contexts
kubectl config use-context <context>
kubectl cluster-info

# Namespace overview
kubectl get all -n employee-app

# Pods
kubectl get pods -n employee-app -o wide
kubectl describe pod <name> -n employee-app
kubectl logs <name> -n employee-app --follow
kubectl exec -it <name> -n employee-app -- bash

# Apply / delete
kubectl apply -f <file-or-dir>
kubectl delete -f <file-or-dir>
kubectl delete all --all -n employee-app

# Rollouts
kubectl rollout status deployment/backend -n employee-app
kubectl rollout undo deployment/backend -n employee-app

# Scaling
kubectl scale deployment backend --replicas=4 -n employee-app

# Debugging
kubectl get events -n employee-app --sort-by='.lastTimestamp'
kubectl top pods -n employee-app
kubectl top nodes
```
