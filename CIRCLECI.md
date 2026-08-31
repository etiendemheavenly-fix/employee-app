# CircleCI — CI/CD with CircleCI

---

## Where We Are in the SDLC

```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌─────────┐   ┌──────────────┐   ┌─────────┐
│  PLAN  │──▶│  CODE  │──▶│ BUILD  │──▶│  TEST  │──▶│ RELEASE │──▶│    DEPLOY    │──▶│ MONITOR │
│        │   │        │   │        │   │        │   │ (Docker)│   │  (CI/CD)     │   │ Grafana │
└────────┘   └────────┘   └────────┘   └────────┘   └─────────┘   └──────────────┘   └─────────┘
                                                                            ↑
                                                                      You are here
```

This project has three CI/CD pipelines that all do the same thing — test, build, push to ECR, deploy — but in different tools:

| Tool | Config file | Where it runs |
|------|-------------|---------------|
| GitHub Actions | `.github/workflows/` | GitHub's servers |
| Jenkins | `Jenkinsfile` | Your own Jenkins server |
| CircleCI | `.circleci/config.yml` | CircleCI's servers |

This guide covers **CircleCI**. See `CICD.md` for GitHub Actions.

---

## What is CircleCI?

CircleCI is a cloud-based CI/CD platform. Like GitHub Actions, it runs your pipeline automatically when you push code — no server to manage. You define the pipeline in a YAML file, connect your GitHub repo, and CircleCI handles the rest.

### CircleCI vs GitHub Actions

| | GitHub Actions | CircleCI |
|---|---|---|
| Config location | `.github/workflows/*.yml` | `.circleci/config.yml` |
| Trigger | Built into GitHub | Connects to GitHub via OAuth |
| Free tier | 2,000 minutes/month | 6,000 credits/month |
| Reusable steps | Actions (marketplace) | Orbs (CircleCI registry) |
| Parallelism | Matrix builds | Parallel jobs + test splitting |
| Setup | Zero — already in GitHub | Requires CircleCI account + project setup |

Both tools are widely used in industry. The concepts are identical — jobs, steps, triggers, secrets. The syntax is different.

---

## Key Concepts

| Concept | What it is |
|---------|-----------|
| **Pipeline** | The full automated process triggered by a push |
| **Workflow** | Defines which jobs run and in what order |
| **Job** | A group of steps that run on the same machine (executor) |
| **Step** | A single task — run a command or use an orb command |
| **Executor** | The environment a job runs in — Docker image, machine, etc. |
| **Orb** | A reusable package of jobs, commands, and executors (like GitHub Actions actions) |
| **Context** | A named set of environment variables shared across projects in your org |
| **Workspace** | Shared storage that passes files between jobs in the same workflow |
| **`persist_to_workspace`** | Save files from one job to the workspace |
| **`attach_workspace`** | Load files saved by a previous job |

---

## CircleCI Config Structure

All CircleCI config lives in a single file:

```
.circleci/
└── config.yml
```

The file has five top-level sections:

```yaml
version: 2.1          # always 2.1

orbs:                 # import reusable packages
  aws-cli: circleci/aws-cli@4.1
  python: circleci/python@2.1

commands:             # reusable step sequences (like functions)
  my-command:
    steps:
      - run: echo "reusable"

jobs:                 # define what each job does
  my-job:
    docker:
      - image: cimg/base:current
    steps:
      - checkout
      - run: echo "hello"

workflows:            # define which jobs run and when
  my-workflow:
    jobs:
      - my-job:
          context: my-context   # inject variables from a context
```

---

## Setting Up CircleCI

### Step 1 — Create a CircleCI account

1. Go to [https://circleci.com](https://circleci.com)
2. Click **Sign Up** → **Sign up with GitHub**
3. Authorise CircleCI to access your GitHub account

### Step 2 — Connect your project

1. In the CircleCI dashboard, click **Projects**
2. Find `employee-app` in the list
3. Click **Set Up Project**
4. Choose **Fastest** (use the existing `.circleci/config.yml` in the repo)
5. Click **Set Up Project**

CircleCI will immediately trigger a pipeline on the current branch.

### Step 3 — Create a Context

All credentials for this pipeline are stored in a CircleCI **Context** named `employee-app`. A context is a named set of environment variables that can be shared across all projects in your organisation — no per-project setup needed.

```
CircleCI → Organisation Settings → Contexts → Create Context
Name: employee-app
```

Add the following variables to the context:

| Variable | Value | Purpose |
|----------|-------|---------|
| `AWS_ACCESS_KEY_ID` | Your IAM access key | Authenticate to AWS |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key | Authenticate to AWS |
| `AWS_REGION` | `us-east-1` | AWS region |
| `ECR_REGISTRY` | `075120018043.dkr.ecr.us-east-1.amazonaws.com` | ECR registry URL |
| `EC2_HOST` | EC2 public IP | SSH deploy target |
| `EC2_USER` | `ec2-user` | SSH username |
| `SSH_FINGERPRINT` | SSH key fingerprint (added in Step 4) | Identify which SSH key to inject |

> **Never** put these values directly in `config.yml` — that file is committed to the repo.

### Step 4 — Add the SSH key to CircleCI

See the [SSH Setup section](#setting-up-ssh-for-ec2-deployment) below. Once added, copy the fingerprint and add it to the context as `SSH_FINGERPRINT`.

### Step 5 — Create an IAM user for CircleCI

```
AWS Console → IAM → Users → Create user
Name: circleci-ci
Attach policies:
  - AmazonEC2ContainerRegistryPowerUser
```

Create access keys and add them to the context as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

---

## Branching Strategy

```
feature/* / fix/* / chore/*  ──▶  test only (no build, no deploy)
develop                       ──▶  test → build → push to ECR → deploy to DEV EC2
main                          ──▶  test → build → push to ECR → deploy to PROD EC2
```

Controlled in the `workflows` section using `filters`:

```yaml
workflows:
  build-and-deploy:
    jobs:
      - test:
          context: employee-app       # runs on ALL branches

      - build-and-push:
          context: employee-app
          requires: [test]
          filters:
            branches:
              only: [develop, main]   # only on these two branches

      - deploy:
          context: employee-app
          requires: [build-and-push]
          filters:
            branches:
              only: [develop, main]
```

| Branch | Jobs that run |
|--------|--------------|
| `feature/anything` | `test` only |
| `fix/anything` | `test` only |
| `develop` | `test` → `build-and-push` → `deploy` (dev EC2) |
| `main` | `test` → `build-and-push` → `deploy` (prod EC2) |

---

## The Config File — `.circleci/config.yml`

```yaml
version: 2.1

orbs:
  aws-cli: circleci/aws-cli@4.1
  python: circleci/python@2.1

# ── Reusable commands ──────────────────────────────────────────────────────────
commands:
  ecr-login:
    steps:
      - run:
          name: Authenticate Docker to ECR
          command: |
            aws ecr get-login-password --region $AWS_REGION | \
              docker login --username AWS --password-stdin $ECR_REGISTRY

# ── Jobs ───────────────────────────────────────────────────────────────────────
jobs:

  # ── Job 1: Test ───────────────────────────────────────────────────────────────
  test:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - python/install-packages:
          pkg-manager: pip
          pip-dependency-file: backend/requirements.txt
      - run:
          name: Run pytest
          command: |
            cd backend
            DATABASE_URL=sqlite:///test.db \
            AWS_REGION=us-east-1 \
            pytest -v

  # ── Job 2: Build & Push ───────────────────────────────────────────────────────
  build-and-push:
    docker:
      - image: cimg/base:current
    steps:
      - checkout
      - setup_remote_docker:
          docker_layer_caching: true
      - aws-cli/setup:
          aws_access_key_id: AWS_ACCESS_KEY_ID
          aws_secret_access_key: AWS_SECRET_ACCESS_KEY
          region: AWS_REGION
      - ecr-login
      - run:
          name: Set image tags
          command: |
            TIMESTAMP=$(date +'%Y%m%d-%H%M%S')
            if [ "$CIRCLE_BRANCH" = "main" ]; then
              echo "export BACKEND_TAG=be-prod-${TIMESTAMP}" >> $BASH_ENV
              echo "export FRONTEND_TAG=fe-prod-${TIMESTAMP}" >> $BASH_ENV
            else
              echo "export BACKEND_TAG=be-dev-${TIMESTAMP}" >> $BASH_ENV
              echo "export FRONTEND_TAG=fe-dev-${TIMESTAMP}" >> $BASH_ENV
            fi
      - run:
          name: Build and push backend
          command: |
            docker build -t $ECR_REGISTRY/employee-backend:$BACKEND_TAG backend/
            docker push $ECR_REGISTRY/employee-backend:$BACKEND_TAG
      - run:
          name: Build and push frontend
          command: |
            docker build -t $ECR_REGISTRY/employee-frontend:$FRONTEND_TAG frontend/
            docker push $ECR_REGISTRY/employee-frontend:$FRONTEND_TAG
      - run:
          name: Save tags for deploy job
          command: |
            echo $BACKEND_TAG > /tmp/backend_tag
            echo $FRONTEND_TAG > /tmp/frontend_tag
      - persist_to_workspace:
          root: /tmp
          paths:
            - backend_tag
            - frontend_tag

  # ── Job 3: Deploy to EC2 ──────────────────────────────────────────────────────
  deploy:
    docker:
      - image: cimg/base:current
    steps:
      - attach_workspace:
          at: /tmp
      - run:
          name: Load tags
          command: |
            echo "export BACKEND_TAG=$(cat /tmp/backend_tag)" >> $BASH_ENV
            echo "export FRONTEND_TAG=$(cat /tmp/frontend_tag)" >> $BASH_ENV
      - add_ssh_keys:
          fingerprints:
            - "$SSH_FINGERPRINT"
      - run:
          name: Deploy to EC2
          command: |
            ssh -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST \
              BACKEND_TAG=$BACKEND_TAG \
              FRONTEND_TAG=$FRONTEND_TAG \
              ECR_REGISTRY=$ECR_REGISTRY \
              AWS_REGION=$AWS_REGION \
              'bash -s' << 'EOF'
                aws ecr get-login-password --region $AWS_REGION | \
                  docker login --username AWS --password-stdin $ECR_REGISTRY

                docker network inspect employee-network >/dev/null 2>&1 || \
                  docker network create employee-network

                if ! docker ps --format '{{.Names}}' | grep -q '^db$'; then
                  docker rm -f db || true
                  docker run -d --name db --restart unless-stopped \
                    --network employee-network \
                    -e POSTGRES_USER=postgres \
                    -e POSTGRES_PASSWORD=postgres \
                    -e POSTGRES_DB=employees \
                    -v postgres-data:/var/lib/postgresql/data \
                    postgres:15
                  until docker exec db pg_isready -U postgres; do sleep 2; done
                fi

                docker pull $ECR_REGISTRY/employee-backend:$BACKEND_TAG
                docker pull $ECR_REGISTRY/employee-frontend:$FRONTEND_TAG

                docker rm -f backend frontend || true

                docker run -d --name backend --restart unless-stopped \
                  --network employee-network \
                  -p 5000:5000 \
                  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/employees \
                  $ECR_REGISTRY/employee-backend:$BACKEND_TAG

                docker run -d --name frontend --restart unless-stopped \
                  --network employee-network \
                  -p 8080:80 \
                  $ECR_REGISTRY/employee-frontend:$FRONTEND_TAG

                docker image prune -f
            EOF

# ── Workflows ──────────────────────────────────────────────────────────────────
workflows:
  build-and-deploy:
    jobs:
      - test:
          context: employee-app

      - build-and-push:
          context: employee-app
          requires:
            - test
          filters:
            branches:
              only:
                - develop
                - main

      - deploy:
          context: employee-app
          requires:
            - build-and-push
          filters:
            branches:
              only:
                - develop
                - main
```

---

## Config Walkthrough

### `version: 2.1`

Always `2.1`. This enables orbs, commands, and other modern features.

---

### Orbs

```yaml
orbs:
  aws-cli: circleci/aws-cli@4.1
  python: circleci/python@2.1
```

Orbs are reusable packages published to the CircleCI registry — equivalent to GitHub Actions' `uses:` actions.

| Orb | What it provides |
|-----|-----------------|
| `circleci/aws-cli` | `aws-cli/setup` — installs and configures the AWS CLI using context variables |
| `circleci/python` | `python/install-packages` — installs pip dependencies with caching |

---

### Commands

```yaml
commands:
  ecr-login:
    steps:
      - run:
          name: Authenticate Docker to ECR
          command: |
            aws ecr get-login-password --region $AWS_REGION | \
              docker login --username AWS --password-stdin $ECR_REGISTRY
```

A `command` is a reusable sequence of steps — like a function. Define it once, call it in any job.

---

### Job 1 — `test`

- Runs on **every branch** — no filter
- `cimg/python:3.11` — CircleCI's convenience image with Python 3.11 pre-installed
- `checkout` — built-in step that clones the repo
- `python/install-packages` — installs deps with pip caching
- `DATABASE_URL=sqlite:///test.db` — uses SQLite so no real database is needed in CI

---

### Job 2 — `build-and-push`

Key points:

- `setup_remote_docker` — CircleCI jobs run inside Docker containers. To run Docker commands inside a job, you need a separate remote Docker environment. `docker_layer_caching: true` caches image layers between runs to speed up builds.
- `$CIRCLE_BRANCH` — built-in CircleCI variable with the current branch name. Used to tag images differently for `develop` (`be-dev-*`) vs `main` (`be-prod-*`).
- `$BASH_ENV` — CircleCI's way of persisting environment variables between steps. Writing `export VAR=value >> $BASH_ENV` makes `VAR` available in all subsequent steps.
- `persist_to_workspace` — saves the tag files so the `deploy` job can read them.

---

### Job 3 — `deploy`

- `attach_workspace` — loads the tag files saved by `build-and-push`
- `add_ssh_keys` — injects the SSH private key stored in CircleCI into the job using the fingerprint from the context
- Variables are passed explicitly to the remote shell via `ssh ... VAR=value 'bash -s'` so they are available inside the heredoc on the EC2 instance
- The deploy script: authenticates with ECR, creates the network if missing, starts postgres if not running, pulls new images, replaces old containers, prunes old images

---

### Workflow

```yaml
workflows:
  build-and-deploy:
    jobs:
      - test:
          context: employee-app       # every branch

      - build-and-push:
          context: employee-app
          requires: [test]            # only after test passes
          filters:
            branches:
              only: [develop, main]

      - deploy:
          context: employee-app
          requires: [build-and-push]
          filters:
            branches:
              only: [develop, main]
```

`context: employee-app` on every job injects all variables from the context. The `requires` field creates a dependency chain — a job won't start until all required jobs pass. Combined with `filters`, this gives full control over what runs where.

---

## Setting Up SSH for EC2 Deployment

### Step 1 — Generate an SSH key pair

```bash
ssh-keygen -t rsa -b 4096 -f circleci-deploy-key -N ""
# Creates: circleci-deploy-key (private) and circleci-deploy-key.pub (public)
```

### Step 2 — Add the public key to EC2

```bash
# On your EC2 instance
cat circleci-deploy-key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 3 — Add the private key to CircleCI

```
CircleCI → Projects → employee-app → Project Settings
→ SSH Keys → Additional SSH Keys → Add SSH Key
→ Hostname: <your EC2 IP>
→ Private Key: paste the full contents of circleci-deploy-key
→ Add SSH Key
```

CircleCI shows you the **fingerprint** of the key after saving. Copy it.

### Step 4 — Add the fingerprint to the context

```
CircleCI → Organisation Settings → Contexts → employee-app
→ Add Environment Variable
→ SSH_FINGERPRINT = <fingerprint from Step 3>
```

---

## Built-in CircleCI Variables

CircleCI injects these automatically — no setup needed:

| Variable | Value |
|----------|-------|
| `$CIRCLE_BRANCH` | Current branch name (`develop`, `main`, `feature/x`) |
| `$CIRCLE_SHA1` | Full git commit SHA |
| `$CIRCLE_BUILD_NUM` | Pipeline build number |
| `$CIRCLE_PROJECT_REPONAME` | Repository name |
| `$CIRCLE_USERNAME` | GitHub username that triggered the build |
| `$BASH_ENV` | Path to file used to persist env vars between steps |

---

## Pipeline Flow — End to End

```
Developer pushes to feature/add-search
        │
        ▼
CircleCI triggers pipeline
  └── test (context: employee-app)
        ├── FAIL → red ✗, developer notified, pipeline stops
        └── PASS → green ✓
              └── build-and-push? NO — feature branch filtered out
              └── deploy? NO — feature branch filtered out

Developer merges to develop
        │
        ▼
CircleCI triggers pipeline
  └── test → PASS
        └── build-and-push (develop passes filter)
              ├── docker build backend → be-dev-20240101-120000
              ├── docker push to ECR
              ├── docker build frontend → fe-dev-20240101-120000
              ├── docker push to ECR
              └── persist tags to workspace
        └── deploy (develop passes filter)
              ├── attach workspace (load tags)
              ├── inject SSH key via fingerprint
              ├── SSH into DEV EC2
              ├── docker pull new images from ECR
              ├── docker rm old containers
              └── docker run new containers

Team merges develop to main
        │
        ▼
CircleCI triggers pipeline
  └── test → PASS
        └── build-and-push (main passes filter)
              ├── docker build backend → be-prod-20240101-130000
              ├── docker push to ECR
              └── persist tags to workspace
        └── deploy (main passes filter)
              ├── SSH into PROD EC2
              └── docker run new containers
```

---

## Switching Between Branches

```bash
# Feature branch — only test runs
git checkout -b feature/my-change
git push origin feature/my-change

# Trigger dev deploy
git checkout develop
git merge feature/my-change
git push origin develop

# Trigger prod deploy
git checkout main
git merge develop
git push origin main
```

---

## Viewing Pipeline Results

```
CircleCI dashboard → Pipelines
```

Every pipeline run shows which branch triggered it, which jobs ran, duration, and full logs per step. Click any failed step to see the exact error.

To re-run a failed pipeline:
```
CircleCI → Pipelines → select the run → Rerun → Rerun from failed
```

---

## Summary

| Concept | CircleCI | GitHub Actions equivalent |
|---------|----------|-----------------------------|
| Config file | `.circleci/config.yml` | `.github/workflows/*.yml` |
| Reusable package | Orb | Action (`uses:`) |
| Reusable steps | `commands:` | Composite action |
| Pass data between jobs | `persist_to_workspace` / `attach_workspace` | `outputs` + `needs` |
| Credentials | Context | Repository / org secrets |
| Branch filter | `filters.branches.only` | `on.push.branches` |
| Job dependency | `requires` | `needs` |
| Current branch | `$CIRCLE_BRANCH` | `${{ github.ref_name }}` |
| Docker in job | `setup_remote_docker` | Available by default |

---

## What Comes Next — Kubernetes

The same Docker images pushed to ECR by this pipeline are what Kubernetes pulls when deploying to EKS. In the Kubernetes phase, the deploy stage changes from SSH + `docker run` to `helm upgrade` — the test and build stages stay exactly the same.

```
Now (EC2):
  test → build → push to ECR → SSH → docker run on EC2

Next (EKS):
  test → build → push to ECR → helm upgrade → pods on EKS
```
