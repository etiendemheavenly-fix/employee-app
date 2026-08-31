# Docker — From Build to Containers

---

## Where We Are in the SDLC

```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌──────────────┐   ┌────────┐   ┌─────────┐
│  PLAN  │──▶│  CODE  │──▶│ BUILD  │──▶│  TEST  │──▶│   RELEASE    │──▶│ DEPLOY │──▶│ MONITOR │
│        │   │        │   │        │   │        │   │   (Docker)   │   │  (K8s) │   │Grafana  │
└────────┘   └────────┘   └────────┘   └────────┘   └──────────────┘   └────────┘   └─────────┘
                                                              ↑
                                                        You are here
```

In the **Build** phase we:
- Identified the programming language from the dependency file
- Installed dependencies (`pip install`, `npm install`, `mvn package`)
- Ran the application directly on our machine
- Ran automated tests

The problem we are left with:

> The app runs on your machine. But it only runs on your machine.

If someone else clones the repo, they need to:
- Install the exact same version of Python, Node.js, or Java
- Install all the same dependencies
- Set the same environment variables
- Have the same OS configuration

This is fragile, slow, and does not scale. This is the problem Docker solves.

---

## The Problem Docker Solves

In the build phase, you ran:

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://... python app.py
```

This works because your machine has Python 3.13 installed. But:

- A server running Amazon Linux 2023 might have Python 3.9
- A colleague's laptop might have Python 3.10
- The CI/CD pipeline might have Python 3.12

Different versions behave differently. Dependencies compiled for one OS may not work on another. The classic problem in software:

> **"It works on my machine"**

Docker eliminates this by packaging the application together with its entire environment — the runtime, the dependencies, the configuration — into a single portable unit called a **container image**.

---

## Virtualisation vs Containerisation

Before Docker, the solution to "it works on my machine" was **virtualisation**. To understand why Docker is better, you need to understand both.

### Traditional Virtualisation (Virtual Machines)

A **Virtual Machine (VM)** emulates an entire computer — CPU, memory, storage, and a full operating system — inside your physical machine.

```
┌─────────────────────────────────────────────────┐
│                Physical Server                   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │           Hypervisor (VMware / KVM)       │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │     VM 1    │  │     VM 2    │  │   VM 3  │  │
│  │  Guest OS   │  │  Guest OS   │  │Guest OS │  │
│  │  (Linux)    │  │  (Windows)  │  │(Linux)  │  │
│  │    App A    │  │    App B    │  │  App C  │  │
│  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────┘
```

Each VM includes a full operating system — kernel, system libraries, everything. This makes VMs:
- **Heavy** — each VM can be gigabytes in size
- **Slow to start** — booting a full OS takes minutes
- **Resource intensive** — each VM needs its own CPU and memory allocation

### Containerisation

A **container** does not virtualise hardware or run a full OS. Instead, it shares the host OS kernel and isolates only the application and its dependencies.

```
┌─────────────────────────────────────────────────┐
│                Physical Server                   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │              Host OS (Linux)              │   │
│  │                                          │   │
│  │  ┌──────────────────────────────────┐    │   │
│  │  │        Docker Engine             │    │   │
│  │  └──────────────────────────────────┘    │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │ Container 1 │  │ Container 2 │  │  Cont 3 │  │
│  │  App + Deps │  │  App + Deps │  │App+Deps │  │
│  │  (no OS)    │  │  (no OS)    │  │ (no OS) │  │
│  └─────────────┘  └─────────────┘  └─────────┘  │
└─────────────────────────────────────────────────┘
```

Containers are:
- **Lightweight** — megabytes, not gigabytes
- **Fast to start** — milliseconds, not minutes
- **Efficient** — share the host OS kernel, no duplication

### VM vs Container — Side by Side

| | Virtual Machine | Container |
|---|---|---|
| Includes | Full OS + App | App + dependencies only |
| Size | Gigabytes | Megabytes |
| Startup time | Minutes | Seconds |
| Isolation | Full hardware isolation | Process-level isolation |
| Portability | Limited | Runs anywhere Docker runs |
| Use case | Run different OS types | Package and ship applications |

### Do VMs and Containers replace each other?

No — they are complementary. In production (which you will see in the Kubernetes phase), containers run **inside** VMs:

```
AWS EC2 Instance (VM)
  └── Docker Engine
        ├── Container: backend
        ├── Container: frontend
        └── Container: database
```

The VM gives you an isolated server. Docker gives you isolated, portable applications running on that server.

---

## What is Docker?

**Docker** is a platform for building, shipping, and running containers.

It has three core components:

| Component | What it is | Analogy |
|-----------|-----------|---------|
| **Dockerfile** | A text file with instructions to build an image | A recipe |
| **Image** | A read-only snapshot built from a Dockerfile | A packaged meal kit |
| **Container** | A running instance of an image | The meal being eaten |

```
Dockerfile  ──▶  docker build  ──▶  Image  ──▶  docker run  ──▶  Container
(instructions)                    (snapshot)                     (running process)
```

You can run many containers from the same image, just like you can cook the same recipe many times.

### Docker Hub

**Docker Hub** is a public registry where Docker images are stored and shared. When you run:

```bash
docker pull postgres:15
```

Docker downloads the `postgres` image tagged `15` from Docker Hub. Anyone in the world can pull and run it.

You can also push your own images to Docker Hub or a private registry like **AWS ECR**.

---

## Docker Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Client (CLI)                   │
│              docker build / run / push / pull            │
└─────────────────────────┬───────────────────────────────┘
                          │  REST API
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Docker Daemon (dockerd)               │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Images    │  │  Containers  │  │   Networks   │  │
│  │              │  │              │  │   Volumes    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                Docker Registry (Docker Hub / ECR)        │
└─────────────────────────────────────────────────────────┘
```

- The **Docker Client** is the `docker` command you type in the terminal
- The **Docker Daemon** is the background service that does the actual work
- The **Registry** is where images are stored and shared

---

## Installing Docker on Amazon Linux 2023

Amazon Linux 2023 is the OS used on AWS EC2 instances. This is how you install Docker on a fresh server.

```bash
# Update the package manager
sudo dnf update -y

# Install Docker
sudo dnf install -y docker

# Start the Docker service
sudo systemctl start docker

# Enable Docker to start automatically on reboot
sudo systemctl enable docker

# Add your user to the docker group so you don't need sudo every time
sudo usermod -aG docker $USER

# Apply the group change without logging out
newgrp docker

# Verify Docker is running
docker --version
docker ps
```

Verify the installation:

```bash
docker run hello-world
```

You should see: `Hello from Docker!`

---

## Core Docker Commands

### Images

```bash
# Download an image from Docker Hub
docker pull nginx:alpine

# List all images on your machine
docker images

# Remove an image
docker rmi nginx:alpine

# Search for images on Docker Hub
docker search postgres
```

### Containers

```bash
# Run a container (downloads image if not present)
docker run nginx:alpine

# Run in detached mode (background)
docker run -d nginx:alpine

# Run with a name
docker run -d --name my-nginx nginx:alpine

# Run with port mapping  host:container
docker run -d -p 8080:80 --name my-nginx nginx:alpine

# List running containers
docker ps

# List all containers including stopped
docker ps -a

# Stop a container
docker stop my-nginx

# Start a stopped container
docker start my-nginx

# Remove a container
docker rm my-nginx

# Remove a running container forcefully
docker rm -f my-nginx
```

### Logs and Exec

```bash
# View container logs
docker logs my-nginx

# Follow logs in real time
docker logs -f my-nginx

# Open a shell inside a running container
# backend (Debian) uses bash, frontend (Alpine) uses sh
docker exec -it backend bash
docker exec -it frontend sh

# Run a one-off command inside a container
docker exec my-nginx ls /usr/share/nginx/html
```

### Cleanup

```bash
# Remove all stopped containers
docker container prune

# Remove all unused images
docker image prune

# Remove everything unused (containers, images, networks, volumes)
docker system prune -a
```

---

## Container Restart Policies

By default, if a container crashes or the server reboots, the container stays stopped. A **restart policy** tells Docker when to automatically restart a container.

### Restart policy options

| Policy | Behaviour |
|--------|-----------|
| `no` | Never restart (default) |
| `always` | Always restart — even if you manually stopped it |
| `unless-stopped` | Restart on crash or reboot, but not if you manually stopped it |
| `on-failure` | Only restart if the container exited with a non-zero error code |

`unless-stopped` is the right choice for production containers on a server — they survive reboots and crashes, but `docker stop` still works as expected.

### Add restart policy to a container

```bash
docker run -d \
  --name backend \
  --restart unless-stopped \
  --network employee-network \
  -p 5000:5000 \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
  employee-backend:v1
```

### Update restart policy on an existing container

If you already have containers running without a restart policy:

```bash
docker update --restart unless-stopped db
docker update --restart unless-stopped backend
docker update --restart unless-stopped frontend
```

### Verify the restart policy is set

```bash
docker inspect backend --format '{{.HostConfig.RestartPolicy.Name}}'
# unless-stopped
```

### Test it works

```bash
# Check containers are running
docker ps

# Simulate a reboot by restarting the Docker daemon
sudo systemctl restart docker

# Wait a few seconds, then check — containers should be back up
docker ps
```

---

## The Dockerfile

A **Dockerfile** is a text file that contains step-by-step instructions for building a Docker image. Each instruction creates a new layer in the image.

### Dockerfile Instructions

| Instruction | Purpose |
|-------------|---------|
| `FROM` | Base image to start from |
| `WORKDIR` | Set the working directory inside the container |
| `COPY` | Copy files from your machine into the image |
| `RUN` | Execute a command during the build (install dependencies, etc.) |
| `ENV` | Set environment variables |
| `EXPOSE` | Document which port the container listens on |
| `CMD` | The default command to run when the container starts |
| `ENTRYPOINT` | Like CMD but not overridable |

### How layers work

Every instruction in a Dockerfile creates a layer. Docker caches layers — if a layer has not changed, Docker reuses the cached version instead of rebuilding it. This makes builds fast.

```
FROM python:3.11-slim          ← Layer 1 (base OS + Python)
WORKDIR /app                   ← Layer 2 (set directory)
COPY requirements.txt .        ← Layer 3 (copy dependency file)
RUN pip install -r ...         ← Layer 4 (install dependencies) ← CACHED if requirements.txt unchanged
COPY app.py .                  ← Layer 5 (copy source code)     ← rebuilds when code changes
CMD ["gunicorn", ...]          ← Layer 6 (set start command)
```

This is why `COPY requirements.txt` comes before `COPY app.py` — dependencies change less often than code, so the expensive `pip install` layer stays cached.

---

## Practical — Dockerfile for the Employee Directory App

### Backend Dockerfile

```
employee-app/backend/Dockerfile
```

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping curl netcat-openbsd dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

Line by line:

| Line | What it does |
|------|-------------|
| `FROM python:3.11-slim` | Start from an official Python 3.11 image (slim = smaller size) |
| `RUN apt-get install ...` | Install `ping`, `curl`, `nc`, `dig` for network debugging inside the container |
| `WORKDIR /app` | All subsequent commands run from `/app` inside the container |
| `COPY requirements.txt .` | Copy the dependency file first (for layer caching) |
| `RUN pip install ...` | Install all Python dependencies inside the image |
| `COPY app.py .` | Copy the application code |
| `EXPOSE 5000` | Document that the app listens on port 5000 |
| `CMD [...]` | Start the app with Gunicorn (production web server) |

### Frontend Dockerfile

```
employee-app/frontend/Dockerfile
```

```dockerfile
FROM nginx:alpine

RUN apk add --no-cache iputils curl bind-tools

COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

Line by line:

| Line | What it does |
|------|-------------|
| `FROM nginx:alpine` | Start from official Nginx image (alpine = very small) |
| `RUN apk add ...` | Install `ping`, `curl`, `dig` for network debugging inside the container |
| `COPY index.html ...` | Copy the HTML file into the Nginx web root |
| `COPY nginx.conf ...` | Replace the default Nginx config with ours |
| `EXPOSE 80` | Document that Nginx listens on port 80 |

### Build the images

```bash
# Build the backend image
cd employee-app/backend
docker build -t employee-backend:v1 .

# Build the frontend image
cd ../frontend
docker build -t employee-frontend:v1 .

# Verify both images exist
docker images | grep employee
```

The `.` at the end means "use the current directory as the build context" — Docker sends all files in that directory to the daemon.

### Run the images as containers

```bash
# Run the backend (needs a running postgres)
docker run -d \
  --name backend \
  -p 5000:5000 \
  -e DATABASE_URL=postgresql://postgres:postgres@localhost:5432/employees \
  employee-backend:v1

# Run the frontend
docker run -d \
  --name frontend \
  -p 8080:80 \
  employee-frontend:v1
```

### Run the full stack manually

The backend needs a database to connect to. Start all three containers on the same network so they can reach each other by name.

**Step 1 — Create a network:**

```bash
docker network create employee-network
```

**Step 2 — Start PostgreSQL:**

```bash
docker run -d \
  --name db \
  --restart unless-stopped \
  --network employee-network \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=employees \
  -p 5432:5432 \
  postgres:15
```

Wait for Postgres to be ready before starting the backend — it takes a few seconds to initialise:

```bash
# Poll until Postgres accepts connections
until docker exec db pg_isready -U postgres; do
  echo "Waiting for database..."
  sleep 2
done
echo "Database is ready."
```

Or check manually:

```bash
docker exec db pg_isready -U postgres
# /var/run/postgresql:5432 - accepting connections
```

Do not proceed to the next step until you see `accepting connections`.

**Step 3 — Start the backend:**

```bash
docker run -d \
  --name backend \
  --restart unless-stopped \
  --network employee-network \
  -p 5000:5000 \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
  employee-backend:v1
```

Verify the backend is up:

```bash
curl http://localhost:5000/api/health
# {"status": "healthy", "db": "connected"}
```

**Step 4 — Start the frontend:**

```bash
docker run -d \
  --name frontend \
  --restart unless-stopped \
  --network employee-network \
  -p 8080:80 \
  employee-frontend:v1
```

**Step 5 — Open in your browser:**

The frontend is mapped to port `8080` on your machine and the backend to port `5000`. Open:

```
http://localhost:8080
```

You will see the Employee Directory UI. Add employees using the form — the frontend calls the backend API which stores records in PostgreSQL.

If you are running this on an EC2 instance instead of your local machine, replace `localhost` with the EC2 public IP:

```
http://<EC2_PUBLIC_IP>:8080
```

Make sure port `8080` is open in the EC2 security group.

**Step 6 — Port forward (alternative access without opening ports):**

If you cannot open ports on the host or want to access a container running on a remote machine through your local browser, use SSH port forwarding:

```bash
# Run this on your LOCAL machine (not the server)
ssh -i your-key.pem \
  -L 8080:localhost:8080 \
  -L 5000:localhost:5000 \
  ec2-user@<EC2_PUBLIC_IP>
```

This tunnels:
- `localhost:8080` on your laptop → port `8080` on the EC2 instance (frontend)
- `localhost:5000` on your laptop → port `5000` on the EC2 instance (backend)

Then open `http://localhost:8080` in your browser — traffic travels through the SSH tunnel to the containers on the remote server. No need to open any ports in the security group beyond port `22`.

**Verify all three containers are running:**

```bash
docker ps
```

You should see `db`, `backend`, and `frontend` all with status `Up`.

**Watch the backend logs as you use the app:**

```bash
docker logs -f backend
```

Every request you make in the browser appears here in real time.

**Connect to the database directly:**

```bash
docker exec -it db psql -U postgres -d employees
```

```sql
-- List all employees
SELECT * FROM employees;

-- Exit
\q
```

**Clean up:**

```bash
docker rm -f frontend backend db
docker network rm employee-network
```

---

## Docker Networking

By default, containers are isolated — they cannot talk to each other or to the host. Docker networking controls how containers communicate.

### Network types

| Type | Description | Use case |
|------|-------------|---------|
| `bridge` | Default. Containers on the same bridge can communicate by container name | Local development |
| `host` | Container shares the host's network stack | Performance-sensitive apps |
| `none` | No networking | Fully isolated containers |
| `overlay` | Multi-host networking | Docker Swarm / Kubernetes |

### The default bridge network

When you run a container without specifying a network, it joins the default `bridge` network. Containers on the default bridge **cannot** reach each other by name — only by IP address.

### User-defined bridge networks

When you create your own bridge network, containers on it can reach each other **by container name**. This is how the Employee Directory app works — the backend connects to the database using the hostname `db`.

```bash
# Create a custom network
docker network create employee-network

# List networks
docker network ls

# Inspect a network
docker network inspect employee-network

# Run containers on the same network
docker run -d \
  --name db \
  --restart unless-stopped \
  --network employee-network \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=employees \
  postgres:15

docker run -d \
  --name backend \
  --restart unless-stopped \
  --network employee-network \
  -p 5000:5000 \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
  employee-backend:v1

docker run -d \
  --name frontend \
  --restart unless-stopped \
  --network employee-network \
  -p 8080:80 \
  employee-frontend:v1
```

Now `backend` can reach `db` by name because they are on the same user-defined network. Open `http://localhost:8080` — the full app is running.

### Testing container communication

Once containers are on the same network, verify they can actually reach each other:

```bash
# Ping db from inside the backend container (by name)
# backend is Debian-based — use bash
docker exec -it backend bash
ping -c 3 db
exit

# Ping backend from inside the frontend container
# frontend is Alpine-based — use sh
docker exec -it frontend sh
ping -c 3 backend
exit

# One-liner versions (no interactive shell needed)
docker exec backend ping -c 3 db
docker exec frontend ping -c 3 backend

# curl the backend health endpoint from inside the frontend container
docker exec frontend curl -s http://backend:5000/api/health

# DNS lookup — verify container name resolves correctly
docker exec backend nslookup db
docker exec frontend nslookup backend

# Test raw TCP port reachability (nc = netcat)
docker exec backend nc -zv db 5432

# Test DB connection from inside the backend container
docker exec -it backend bash
python -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@db:5432/employees'); print('connected')"
exit
```

### Inspecting the network

```bash
# See which containers are connected and their IP addresses
docker network inspect employee-network

# Check which networks a specific container is on
docker inspect backend --format '{{json .NetworkSettings.Networks}}'

# Connect a running container to a network
docker network connect employee-network some-other-container

# Disconnect a container from a network
docker network disconnect employee-network some-other-container
```

### What to look for

| Test | Expected result | Problem if it fails |
|------|----------------|--------------------|
| `ping db` from backend | `3 packets transmitted, 3 received` | Containers not on same network |
| `curl backend:5000/api/health` from frontend | `{"status":"healthy"}` | Backend not started or wrong port |
| `docker network inspect` | Both containers listed under `Containers` | Container started without `--network` flag |

```bash
# Remove a network (all containers must be disconnected first)
docker network rm employee-network
```

---

## Docker Volumes

Containers are **ephemeral** — when a container is removed, all data inside it is lost. If you remove the `db` container, all your employee records are gone.

**Volumes** solve this by storing data outside the container, on the host machine. The data persists even when the container is removed.

### Volume types

| Type | Description | Use case |
|------|-------------|---------|
| **Named volume** | Docker manages the storage location | Databases, persistent app data |
| **Bind mount** | You specify the exact path on the host | Development — live code reload |
| **tmpfs** | Stored in memory only | Sensitive data that should not persist |

### Named volumes

```bash
# Create a named volume
docker volume create postgres-data

# List volumes
docker volume ls

# Inspect a volume (shows where data is stored on the host)
docker volume inspect postgres-data

# Run postgres with a volume so data persists
docker run -d \
  --name db \
  --restart unless-stopped \
  --network employee-network \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=employees \
  postgres:15

# Remove a volume
docker volume rm postgres-data

# Remove all unused volumes
docker volume prune
```

Now if you stop and remove the `db` container and start a new one with the same volume, all your data is still there.

### Testing that volumes work

```bash
# 1. Start postgres with a named volume
docker run -d \
  --name db \
  --network employee-network \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=employees \
  postgres:15

# 2. Wait for it to be ready
until docker exec db pg_isready -U postgres; do sleep 1; done

# 3. Insert a test record
docker exec db psql -U postgres -d employees \
  -c "CREATE TABLE IF NOT EXISTS test (id SERIAL, val TEXT); INSERT INTO test (val) VALUES ('persisted');"

# 4. Remove the container
docker rm -f db

# 5. Start a brand new container with the SAME volume
docker run -d \
  --name db \
  --network employee-network \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=employees \
  postgres:15

until docker exec db pg_isready -U postgres; do sleep 1; done

# 6. Query — data is still there
docker exec db psql -U postgres -d employees -c "SELECT * FROM test;"
# val
# -----------
# persisted
```

If you see `persisted` in the output, the volume is working correctly.

### Inspecting volumes

```bash
# See where Docker stores the volume data on the host
docker volume inspect postgres-data
# "Mountpoint": "/var/lib/docker/volumes/postgres-data/_data"

# List all volumes
docker volume ls

# See what files are inside the volume (via a temporary container)
docker run --rm -v postgres-data:/data alpine ls /data
```

### Bind mounts — for development

A bind mount maps a directory on your host machine directly into the container. Changes you make to files on your host are immediately reflected inside the container — no rebuild needed.

```bash
# Mount local backend code into the container
docker run -d \
  --name backend-dev \
  --network employee-network \
  -p 5000:5000 \
  -v $(pwd)/backend:/app \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
  employee-backend:v1
```

Now you can edit `app.py` on your machine and the container sees the changes immediately.

---

## Environment Variables in Docker

Applications need configuration — database URLs, API keys, ports. You should never hardcode these into your image. Pass them in at runtime using environment variables.

```bash
# Pass a single env var
docker run -e DATABASE_URL=postgresql://... employee-backend:v1

# Pass multiple env vars
docker run \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
  -e AWS_REGION=us-east-1 \
  -e ENVIRONMENT=dev \
  employee-backend:v1

# Pass env vars from a file
docker run --env-file .env employee-backend:v1
```

Example `.env` file:

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/employees
AWS_REGION=us-east-1
ENVIRONMENT=dev
```

---

## Docker Image Registries

Once you build an image, you need somewhere to store it so other machines (CI/CD pipelines, servers, Kubernetes nodes) can pull it. That place is called a **registry**.

```
docker build  →  image (local only)
docker push   →  image stored in registry (accessible anywhere)
docker pull   →  image downloaded from registry onto any machine
```

### Image tag format

A tag identifies exactly which image and version to use:

```
registry/repository:tag
```

| Example | Registry | Repository | Tag |
|---------|----------|------------|-----|
| `postgres:15` | Docker Hub (default) | `postgres` | `15` |
| `nginx:alpine` | Docker Hub | `nginx` | `alpine` |
| `yourname/employee-backend:v1` | Docker Hub | `yourname/employee-backend` | `v1` |
| `075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1` | AWS ECR | `employee-backend` | `v1` |

---

## Docker Hub

**Docker Hub** is the default public registry. When you run `docker pull postgres:15`, Docker fetches it from Docker Hub automatically.

### Create a Docker Hub account

1. Go to [https://hub.docker.com](https://hub.docker.com)
2. Click **Sign up** — create a free account
3. Your username becomes part of every image name you push: `yourusername/image-name`

### Create a repository on Docker Hub

A **repository** holds all versions (tags) of one image.

**Public repository** (anyone can pull, free):
1. Log in to Docker Hub
2. Click **Create Repository**
3. Enter a name, e.g. `employee-backend`
4. Set visibility to **Public**
5. Click **Create**

**Private repository** (only you and invited collaborators can pull, free tier allows 1 private repo):
1. Same steps as above
2. Set visibility to **Private**
3. Click **Create**

To pull from a private repo on another machine, that machine must be logged in with `docker login`.

### Push an image to Docker Hub

```bash
# Step 1 — log in
docker login
# Enter your Docker Hub username and password

# Step 2 — tag your image with your Docker Hub username
docker tag employee-backend:v1 yourusername/employee-backend:v1

# Step 3 — push
docker push yourusername/employee-backend:v1
```

### Pull the image on another machine

```bash
# Public repo — no login needed
docker pull yourusername/employee-backend:v1

# Private repo — must log in first
docker login
docker pull yourusername/employee-backend:v1
```

### Verify the push worked

```bash
# Remove the local image to prove you're pulling from the registry
docker rmi yourusername/employee-backend:v1

# Pull it back down
docker pull yourusername/employee-backend:v1

# Run it
docker run -d -p 5000:5000 yourusername/employee-backend:v1
```

---

## AWS ECR (Elastic Container Registry)

**ECR** is AWS's private container registry. It integrates natively with EKS, ECS, and IAM — no separate credentials needed when running on AWS with the right IAM role.

### Why ECR over Docker Hub for AWS workloads

| | Docker Hub | AWS ECR |
|---|---|---|
| Privacy | Public by default | Private by default |
| Auth on AWS | Requires stored credentials | IAM role (no credentials needed) |
| Network | Public internet | Within AWS network (faster, no egress cost) |
| Scanning | Basic | Built-in vulnerability scanning |
| Cost | Free (with limits) | $0.10/GB storage, free data transfer within AWS |

### Create an ECR repository

**Via AWS Console:**
1. Go to **ECR** in the AWS Console
2. Click **Create repository**
3. Choose **Private**
4. Enter a name, e.g. `employee-backend`
5. Enable **Scan on push** (optional but recommended)
6. Click **Create repository**

**Via AWS CLI:**

```bash
# Create a private repository
aws ecr create-repository \
  --repository-name employee-backend \
  --region us-east-1

# Create a second one for the frontend
aws ecr create-repository \
  --repository-name employee-frontend \
  --region us-east-1

# List your repositories
aws ecr describe-repositories --region us-east-1
```

The output gives you the repository URI:
```
075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend
```

### Authenticate Docker to ECR

ECR uses temporary tokens (valid 12 hours). You must authenticate before pushing or pulling:

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 075120018043.dkr.ecr.us-east-1.amazonaws.com
# Login Succeeded
```

### Push an image to ECR

```bash
# Step 1 — build the image
docker build -t employee-backend:v1 ./backend

# Step 2 — tag it with the full ECR URI
docker tag employee-backend:v1 \
  075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1

# Step 3 — push
docker push 075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1
```

### Pull an image from ECR

```bash
# Authenticate first (if not already done)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 075120018043.dkr.ecr.us-east-1.amazonaws.com

# Pull
docker pull 075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1

# Run
docker run -d -p 5000:5000 \
  075120018043.dkr.ecr.us-east-1.amazonaws.com/employee-backend:v1
```

### List images in a repository

```bash
aws ecr list-images \
  --repository-name employee-backend \
  --region us-east-1
```

### Delete an image from ECR

```bash
aws ecr batch-delete-image \
  --repository-name employee-backend \
  --image-ids imageTag=v1 \
  --region us-east-1
```

### Delete a repository

```bash
# --force removes all images inside first
aws ecr delete-repository \
  --repository-name employee-backend \
  --force \
  --region us-east-1
```

---

## Docker Compose

Running multiple containers with individual `docker run` commands is tedious. You have to remember the right flags, the right order, the right network names. If you have three containers, that's three commands — and if you forget `--network` on one of them, nothing works.

**Docker Compose** solves this by letting you define your entire multi-container application in a single YAML file and manage the whole stack with one command.

```
docker run db + docker run backend + docker run frontend
         ↓
docker compose up
```

---

### Installing Docker Compose

Docker Compose V2 ships as a plugin built into the Docker CLI — it's the `docker compose` command (no hyphen). If you installed Docker Engine on Amazon Linux 2023 using `dnf install docker`, the plugin is included.

**Verify it's installed:**

```bash
docker compose version
# Docker Compose version v2.x.x
```

**If it's missing on Amazon Linux 2023:**

The `docker-compose-plugin` package does not exist on AL2023. Install the binary directly into the system-wide plugin directory:

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins

sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose

sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

docker compose version
```

**On Ubuntu/Debian:**

```bash
sudo apt-get install -y docker-compose-plugin
```

**On macOS / Windows:**

Docker Desktop includes Compose V2 automatically. Nothing extra to install.

> **V1 vs V2**: The old standalone binary was `docker-compose` (with a hyphen). V2 is `docker compose` (space, as a CLI plugin). V1 is deprecated. Always use V2.

---

### docker-compose.yml structure

A Compose file has four top-level keys:

```yaml
version: "3.8"          # Compose file format version

services:               # Each service = one container
  service-name:
    image: ...          # Use a pre-built image
    build: ./path       # Or build from a Dockerfile in this directory
    restart: unless-stopped
    ports:
      - "host:container"
    environment:
      KEY: value
    env_file:
      - .env            # Load env vars from a file
    volumes:
      - name:/path      # Named volume
      - ./local:/path   # Bind mount
    depends_on:
      other-service:
        condition: service_healthy   # Wait for healthcheck to pass
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - network-name

volumes:                # Declare named volumes
  volume-name:

networks:               # Declare custom networks (optional — Compose creates one by default)
  network-name:
```

**Key points:**
- Compose automatically creates a network named `<project>_default` and connects all services to it — containers reach each other by service name
- `depends_on` controls start order but does NOT wait for the app inside to be ready — use `condition: service_healthy` with a `healthcheck` for that
- `restart: unless-stopped` on every service means containers survive server reboots
- `build:` and `image:` are mutually exclusive per service — use `build` when you have a Dockerfile, `image` when pulling from a registry

---

### The two Compose files in this project

This project has two Compose files for two different teaching modules:

| File | Backend | Database | Used for |
|------|---------|----------|---------|
| `docker-compose.yml` | Node.js (`./backend-node`) | Postgres container | Docker module |
| `docker-compose.python.yml` | Python (`./backend`) | Postgres container | Kubernetes module prep |

The Python backend is what gets deployed to EKS with RDS. The Compose file lets you verify it works locally before going to Kubernetes.

---

### docker-compose.yml (Docker module — Node.js)

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: employees
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend-node
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/employees
    ports:
      - "5000:5000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend

volumes:
  postgres-data:
```

What each service does:

| Service | What it is | Key config |
|---------|-----------|------------|
| `db` | PostgreSQL 15 | Named volume keeps data across restarts. Healthcheck gates the backend start. |
| `backend` | Node.js API | Built from `./backend-node/Dockerfile`. Connects to `db` by service name. |
| `frontend` | Nginx | Built from `./frontend/Dockerfile`. Proxies `/api/` to `backend:5000`. |

---

### docker-compose.python.yml (Kubernetes module prep — Python)

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: employees
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/employees
      ENVIRONMENT: dev
    ports:
      - "5000:5000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend

volumes:
  postgres-data:
```

Identical structure to the Node.js file — only the backend `build` path changes (`./backend` instead of `./backend-node`) and `ENVIRONMENT: dev` is added for the Python app's logging config.

---

### Running the stacks

```bash
# Docker module — Node.js backend
docker compose up --build

# Kubernetes module prep — Python backend
docker compose -f docker-compose.python.yml up --build
```

Docker Compose will:
1. Build images for `backend` and `frontend` from their Dockerfiles
2. Pull `postgres:15` from Docker Hub
3. Create a shared network (`employee-app_default`)
4. Start `db` first and wait for its healthcheck to pass
5. Start `backend`, then `frontend`

Open `http://localhost:8080` — the full application is running.

---

### Environment variables and env files

Hardcoding credentials in `docker-compose.yml` is fine for local development but not for production. Use an env file to keep secrets out of the Compose file:

```bash
# .env  (never commit this file)
DATABASE_URL=postgresql://postgres:postgres@db:5432/employees
POSTGRES_PASSWORD=postgres
ENVIRONMENT=dev
```

Reference it in the Compose file:

```yaml
services:
  backend:
    build: ./backend-node
    env_file:
      - .env
```

Or reference individual variables:

```yaml
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # read from .env or shell
```

Compose automatically loads a `.env` file in the same directory as the Compose file. Variables defined there are available as `${VAR}` substitutions throughout the YAML.

```bash
# Check what variables Compose sees
docker compose config
```

---

### Health checks

A healthcheck tells Docker whether the service inside the container is actually ready — not just that the container started. Without it, `depends_on` only waits for the container process to start, not for the app to be ready to accept connections.

```yaml
db:
  image: postgres:15
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]  # command to run inside the container
    interval: 5s    # how often to run the check
    timeout: 5s     # how long to wait for a response
    retries: 5      # how many failures before marking unhealthy
    start_period: 10s  # grace period before checks start (optional)
```

The backend uses `condition: service_healthy` so it won't start until Postgres passes its healthcheck:

```yaml
backend:
  depends_on:
    db:
      condition: service_healthy
```

Check health status:

```bash
docker compose ps          # STATUS column shows "healthy" or "starting"
docker inspect employee-app-db-1 --format '{{.State.Health.Status}}'
```

---

### Core Compose commands

```bash
# Start everything (build images first)
docker compose up --build

# Start in background
docker compose up -d --build

# Use a non-default Compose file
docker compose -f docker-compose.python.yml up --build

# List running services and their status
docker compose ps

# View logs for all services
docker compose logs

# Follow logs in real time
docker compose logs -f

# Follow logs for one service
docker compose logs -f backend

# Last 50 lines from a service
docker compose logs --tail=50 backend

# Stop all services (containers removed, volumes and images kept)
docker compose down

# Stop and wipe the database volume
docker compose down -v

# Stop and remove images too
docker compose down --rmi all

# Stop without removing containers
docker compose stop

# Start previously stopped containers (no rebuild)
docker compose start

# Restart a single service
docker compose restart backend

# Rebuild a single service image
docker compose build backend

# Rebuild and restart one service without touching others
docker compose up -d --no-deps --build backend

# Pull latest base images
docker compose pull

# Print the resolved Compose config (with env var substitutions applied)
docker compose config
```

---

### Interacting with running services

```bash
# Open a shell inside a service
docker compose exec backend bash    # Node.js backend (Debian)
docker compose exec frontend sh     # frontend (Alpine)

# Connect to the database
docker compose exec db psql -U postgres -d employees

# Run a one-off command without entering the container
docker compose exec db psql -U postgres -d employees -c "SELECT * FROM employees;"

# Test backend can reach db by name
docker compose exec backend bash -c "node -e \"require('pg').Pool({connectionString:'postgresql://postgres:postgres@db:5432/employees'}).query('SELECT 1').then(()=>console.log('DB reachable'))\""
```

---

### Testing the API

```bash
# Health check
curl http://localhost:5000/api/health

# List employees
curl http://localhost:5000/api/employees

# Add an employee
curl -X POST http://localhost:5000/api/employees \
  -F "name=Jane Smith" \
  -F "email=jane@example.com" \
  -F "role=Engineer" \
  -F "department=Engineering"

# Stats
curl http://localhost:5000/api/stats
```

---

### Scaling a service

```bash
# Run 3 instances of the backend
docker compose up -d --scale backend=3

# Check all instances are running
docker compose ps
```

Note: scaling only makes sense if you have a load balancer in front. With the current setup, the frontend proxies to `backend:5000` — Docker's internal DNS will round-robin across the 3 instances automatically.

---

### Networking in Compose

Compose automatically creates a network named `<project-directory>_default` and connects every service to it. Services reach each other by their service name — no manual `docker network create` needed.

```bash
# See the network Compose created
docker network ls | grep employee

# Inspect it — see all connected containers and their IPs
docker network inspect employee-app_default

# Test connectivity between services
docker compose exec backend ping -c 3 db
docker compose exec frontend curl -s http://backend:5000/api/health
```

If you need to connect a Compose service to an external container (one started with `docker run`), add it to the Compose network:

```bash
docker network connect employee-app_default some-external-container
```

---

### Volumes in Compose

Named volumes declared at the top level of the Compose file persist data across `docker compose down` and container restarts. They are only removed with `docker compose down -v`.

```bash
# List volumes created by Compose
docker volume ls | grep employee

# Inspect the postgres volume
docker volume inspect employee-app_postgres-data

# Wipe the database and start fresh
docker compose down -v
docker compose up -d --build
```

Bind mounts are useful during development — changes to your local files are reflected inside the container immediately without a rebuild:

```yaml
backend:
  build: ./backend-node
  volumes:
    - ./backend-node:/app   # live code reload during development
```

---

## How the Build Phase Became the Release Phase

Look at what just happened:

```
Build phase (previous lecture):
  requirements.txt  ──▶  pip install  ──▶  python app.py  (runs on YOUR machine only)

Release phase (this lecture):
  requirements.txt  ──▶  Dockerfile  ──▶  docker build  ──▶  image  ──▶  runs ANYWHERE
```

The Dockerfile is the build steps automated and frozen into a reproducible image. Instead of you running `pip install` manually on your machine, Docker runs it inside a controlled environment during `docker build`.

The image is the **release artifact** — the output of the release phase. It is:
- **Immutable** — once built, it never changes
- **Versioned** — tagged with a specific version (`v1`, `be-dev-20240101`)
- **Portable** — runs the same way on any machine with Docker installed
- **Stored** — pushed to a registry (Docker Hub or ECR) so anyone can pull it

This is what gets deployed in the next phase — Kubernetes pulls the image from ECR and runs it as a container on the cluster.

---

## Docker Cheat Sheet

### Images
```bash
docker pull image:tag          # download image
docker images                  # list images
docker rmi image:tag           # remove image
docker build -t name:tag .     # build image from Dockerfile
docker tag src:tag dst:tag     # tag an image
docker push name:tag           # push to registry
```

### Containers
```bash
docker run -d -p host:cont --name name image:tag   # run container
docker ps                      # list running containers
docker ps -a                   # list all containers
docker stop name               # stop container
docker start name              # start stopped container
docker rm name                 # remove container
docker rm -f name              # force remove running container
docker logs -f name            # follow logs
docker exec -it name sh        # shell into container
```

### Networks
```bash
docker network create name             # create network
docker network ls                      # list networks
docker network inspect name            # inspect network (see connected containers + IPs)
docker network connect name container  # connect container to network
docker network disconnect name cont    # disconnect container
docker network rm name                 # remove network
docker exec c1 ping -c 3 c2            # test connectivity between containers
docker exec c1 curl http://c2:port     # test HTTP between containers
```

### Volumes
```bash
docker volume create name              # create volume
docker volume ls                       # list volumes
docker volume inspect name             # inspect volume (see host path)
docker volume rm name                  # remove volume
docker volume prune                    # remove unused volumes
docker run -v name:/path image         # mount named volume
docker run -v $(pwd)/dir:/path image   # bind mount
docker run --rm -v name:/data alpine ls /data  # inspect volume contents
```

### Restart Policy
```bash
docker run --restart unless-stopped ...        # set on run
docker update --restart unless-stopped name    # update existing container
docker inspect name --format '{{.HostConfig.RestartPolicy.Name}}'  # verify
```

### Docker Hub
```bash
docker login                                    # log in to Docker Hub
docker tag image:tag user/repo:tag              # tag for Docker Hub
docker push user/repo:tag                       # push to Docker Hub
docker pull user/repo:tag                       # pull from Docker Hub
```

### AWS ECR
```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Create repo
aws ecr create-repository --repository-name name --region us-east-1

# Tag and push
docker tag image:tag <account>.dkr.ecr.us-east-1.amazonaws.com/name:tag
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/name:tag

# List images
aws ecr list-images --repository-name name --region us-east-1
```

### Docker Compose
```bash
# Installation
docker compose version                          # verify V2 is installed
sudo dnf install -y docker-compose-plugin       # install on Amazon Linux 2023

# Start / stop
docker compose up --build                       # build and start
docker compose up -d --build                    # start in background
docker compose -f docker-compose.python.yml up --build  # use alternate file
docker compose stop                             # stop without removing
docker compose start                            # start stopped services
docker compose down                             # stop and remove containers
docker compose down -v                          # stop and remove including volumes
docker compose down --rmi all                   # stop and remove including images

# Inspect
docker compose ps                               # list services and status
docker compose logs -f                          # follow all logs
docker compose logs -f svc                      # follow one service
docker compose logs --tail=50 svc              # last 50 lines
docker compose config                           # print resolved config

# Interact
docker compose exec svc bash                    # shell into service (Debian)
docker compose exec svc sh                      # shell into service (Alpine)
docker compose exec db psql -U postgres -d employees  # connect to DB

# Rebuild / restart
docker compose build svc                        # rebuild one service
docker compose up -d --no-deps --build svc      # rebuild and restart one service
docker compose restart svc                      # restart a service
docker compose pull                             # pull latest base images

# Scale
docker compose up -d --scale svc=3             # run 3 instances
```

### Cleanup
```bash
docker system prune -a         # remove everything unused
docker container prune         # remove stopped containers
docker image prune             # remove dangling images
docker volume prune            # remove unused volumes
```

---

## What Comes Next — Kubernetes

Docker Compose is great for running the application on a single machine. But in production you need:

- **High availability** — if one container crashes, another starts automatically
- **Scaling** — run multiple copies of the backend to handle more traffic
- **Rolling updates** — deploy new versions with zero downtime
- **Load balancing** — distribute traffic across multiple containers
- **Self-healing** — automatically restart failed containers

A single Docker host cannot provide all of this reliably. This is where **Kubernetes** comes in.

```
Docker Compose (now):
  One machine  →  docker compose up  →  3 containers running

Kubernetes (next):
  Many machines (cluster)  →  kubectl apply  →  pods running across nodes
  with auto-scaling, self-healing, rolling updates, load balancing
```

The same Docker images you built and pushed to ECR in this phase are what Kubernetes pulls and runs in the next phase. The image is the bridge between Docker and Kubernetes.

Move to [Kubernetes →](../README.md#deployment-guide)
