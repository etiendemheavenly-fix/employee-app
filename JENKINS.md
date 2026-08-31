# Jenkins CI/CD

## What is Jenkins?

Jenkins is an open-source automation server that builds, tests, and deploys your application automatically. Every time you push code to GitHub, Jenkins picks it up and runs your pipeline — or tells you it broke before it ever reaches production.

It is self-hosted — you run it on your own EC2 instance. Full control, no per-minute billing, no vendor lock-in.

The pipeline for this app does:

```
Clone → Test (pytest) → Build Docker images → Push to DockerHub → SSH Deploy to EC2
```

### Pipeline Stages

| Stage | What it does |
|-------|--------------|
| Test | `pip install -r requirements.txt` + `pytest` against SQLite |
| Build & Push | `docker build` backend + frontend, push to DockerHub |
| Deploy | SSH into app EC2, `docker pull`, remove old containers, `docker run` |

### DockerHub Repositories

| Image | DockerHub repo |
|-------|----------------|
| Backend | `chafah/employee-backend` |
| Frontend | `chafah/employee-frontend` |

### Jenkins Job Types Covered

| Job Type | How it's configured | Best for |
|----------|--------------------|---------|
| Freestyle | Jenkins UI only | Simple tasks, demos, intro to Jenkins |
| Pipeline | `Jenkinsfile` in repo | Single-branch CI/CD |
| Multibranch Pipeline | `Jenkinsfile` per branch | Full team workflow, PR builds |
| Multi-configuration | Jenkins UI (axes) | Matrix testing across environments |
| Folder | N/A | Organising jobs, scoping credentials |
| Organization Folder | `Jenkinsfile` per repo | Org-wide CI/CD, auto-discover repos |

---

## Part 1 — Launch the Jenkins EC2 Instance

| Setting | Value |
|---------|-------|
| AMI | Amazon Linux 2023 |
| Instance type | `t3.medium` (2 vCPU, 4 GB RAM) |
| Storage | 20 GB gp3 |
| Security group | 22 (SSH), 8080 (Jenkins UI) |

---

## Part 2 — Install Jenkins

SSH into the instance and run:

```bash
# Java 21 — required by Jenkins (LTS requires Java 21 or 25)
sudo dnf install -y java-21-amazon-corretto-headless

# Add the Jenkins repo
sudo wget -O /etc/yum.repos.d/jenkins.repo \
    https://pkg.jenkins.io/redhat-stable/jenkins.repo

sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# Install and start
sudo dnf install -y jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins

# Verify
sudo systemctl status jenkins
```

---

## Part 3 — Install Docker and Python on the Jenkins Server

Jenkins needs Docker to build images and Python/pip to run the backend tests.

```bash
# Docker
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker

# Allow Jenkins to run Docker without sudo
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

# Python + pip (for pytest)
sudo dnf install -y python3 python3-pip
```

---

## Part 4 — Access Jenkins

Open your browser:

```
http://<JENKINS_EC2_PUBLIC_IP>:8080
```

### Unlock Jenkins

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Paste the password into the browser.

### Setup Wizard

1. Click **Install suggested plugins** and wait
2. Create your admin user (username, password, email)
3. Set Jenkins URL to `http://<JENKINS_EC2_PUBLIC_IP>:8080`
4. Click **Save and Finish → Start using Jenkins**

---

## Part 5 — Install Plugins

Go to **Manage Jenkins → Plugins → Available plugins** and install:

### Core / Pipeline

| Plugin | Why |
|--------|-----|
| **Pipeline** | Runs `Jenkinsfile` pipelines (usually pre-installed) |
| **Pipeline: Stage View** | Shows stages as a visual table in classic UI |
| **Git** | Clones your GitHub repo |
| **GitHub Integration** | Webhook trigger from GitHub |
| **SSH Agent** | SSH into the deploy EC2 using a private key |
| **Docker Pipeline** | Docker commands inside pipelines |
| **Credentials Binding** | `withCredentials` block in pipelines |

### Blue Ocean

| Plugin | Why |
|--------|-----|
| **Blue Ocean** | Modern pipeline UI — installs all Blue Ocean plugins in one go |

After installing Blue Ocean, access it at:
```
http://<JENKINS_EC2_PUBLIC_IP>:8080/blue
```
Blue Ocean shows each pipeline run as a visual stage-by-stage flow with colour-coded pass/fail and live log streaming per stage.

### Useful Extras

| Plugin | Why |
|--------|-----|
| **Timestamper** | Adds timestamps to every console log line |
| **AnsiColor** | Renders colour in console output |
| **Build Timeout** | Kills a hung build after N minutes |
| **Workspace Cleanup** | Wipes the workspace before each build |
| **Email Extension** | Send rich HTML email notifications on failure |
| **Slack Notification** | Post build results to a Slack channel |

Search each one, tick it, click **Install**. Restart Jenkins when prompted.

---

## Part 6 — Add Credentials

Go to **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**

### 1. DockerHub

| Field | Value |
|-------|-------|
| Kind | Username with password |
| Username | your DockerHub username |
| Password | your DockerHub access token |
| ID | `dockerhub-credentials` |

> Generate a token at: DockerHub → Account Settings → Personal access tokens → New token

### 2. EC2 SSH Key

| Field | Value |
|-------|-------|
| Kind | Secret file |
| File | upload your `.pem` file |
| ID | `ec2-ssh-key` |
| Description | EC2 deploy server SSH key |

### 3. EC2 Host (deploy server IP)

| Field | Value |
|-------|-------|
| Kind | Secret text |
| Secret | your deploy EC2 public IP |
| ID | `ec2-host` |

### 4. Database URL

| Field | Value |
|-------|-------|
| Kind | Secret text |
| Secret | `postgresql://postgres:postgres@db:5432/employees` |
| ID | `database-url` |

---

## Part 7 — Prepare the Deploy EC2 Instance

The EC2 instance that runs the app needs Docker installed.

```bash
# On the deploy EC2
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
newgrp docker
```

Make sure the Jenkins server can SSH into this instance using the key you added in Part 6.

---

## Part 8 — Update the Jenkinsfile

Open `Jenkinsfile` in the repo and replace the placeholder with your actual DockerHub username:

```groovy
DOCKERHUB_BACKEND  = 'chafah/employee-backend'
DOCKERHUB_FRONTEND = 'chafah/employee-frontend'
```

---

## Part 9 — Jenkins Job Types

When you click **New Item** in Jenkins, you see all available job types. Here is every type, what it does, and when to use it.

---

### 1. Freestyle Project

The original Jenkins job type. Everything is configured through the Jenkins UI — no script file, no Groovy, no Jenkinsfile. You fill in forms: where is the code, what commands to run, when to trigger, what to do after. Jenkins translates your form inputs into a build.

This is the best starting point for teaching Jenkins because students see every concept (SCM, build steps, triggers, post-build actions) as a visible UI field before they ever write a Jenkinsfile.

---

#### Step 1 — Create the job

1. On the Jenkins dashboard click **New Item**
2. Enter name: `employee-app-freestyle`
3. Select **Freestyle project**
4. Click **OK**

---

#### Step 2 — Connect to GitHub (Source Code Management)

This tells Jenkins where to clone the code from.

1. Scroll to **Source Code Management**
2. Select **Git**
3. Fill in:

| Field | Value |
|-------|-------|
| Repository URL | `https://github.com/LandmakTechnology/employee-app.git` |
| Credentials | None (public repo) |
| Branch Specifier | `*/main` |

Jenkins will clone the repo into a workspace directory on the Jenkins server before running any build step.

---

#### Step 3 — Set a Build Trigger

This controls when the job runs automatically.

1. Scroll to **Build Triggers**
2. Tick **Poll SCM**
3. Set schedule: `H/5 * * * *` (check GitHub every 5 minutes for new commits)

> Poll SCM is good for teaching. For production use the GitHub webhook instead (covered in Part 10).

---

#### Step 4 — Add Build Steps

Build steps are the actual commands Jenkins runs. We will add three steps to mirror the full pipeline: test, build Docker image, run the container.

**Step 4a — Test the backend**

1. Scroll to **Build Steps** → click **Add build step** → **Execute shell**
2. Paste:

```bash
echo "=== Installing dependencies ==="
pip3 install -r backend/requirements.txt

echo "=== Running tests ==="
cd backend
DATABASE_URL=sqlite:///test.db python3 -m pytest -v
```

This installs the Python packages from `backend/requirements.txt` and runs pytest using SQLite so no real database is needed.

**Step 4b — Build the Docker image**

> **Prerequisite:** The Jenkins user must be in the `docker` group. If you have not done this yet, run on the Jenkins EC2:
> ```bash
> sudo usermod -aG docker jenkins
> sudo systemctl restart jenkins
> ```

1. Click **Add build step** → **Execute shell** again
2. Paste:

```bash
echo "=== Building Docker image ==="
docker build -t employee-backend:freestyle-${BUILD_NUMBER} backend/
docker build -t employee-frontend:freestyle-${BUILD_NUMBER} frontend/

echo "=== Images built ==="
docker images | grep employee
```

`${BUILD_NUMBER}` is a built-in Jenkins variable — it increments with every build (1, 2, 3…). This tags each image uniquely so you can tell builds apart.

**Step 4c — Push to DockerHub**

To push to DockerHub from a Freestyle job you use the **Credentials Binding** plugin to inject the DockerHub secret into the shell environment.

1. Scroll up to **Build Environment** → tick **Use secret text(s) or file(s)**
2. Click **Add** → **Username and password (separated)**

| Field | Value |
|-------|-------|
| Username Variable | `DOCKER_USER` |
| Password Variable | `DOCKER_PASS` |
| Credentials | select `dockerhub-credentials` |

3. Back in **Build Steps** → **Add build step** → **Execute shell**:

```bash
echo "=== Logging in to DockerHub ==="
echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

echo "=== Pushing images ==="
docker push chafah/employee-backend:freestyle-${BUILD_NUMBER}
docker push chafah/employee-frontend:freestyle-${BUILD_NUMBER}

docker logout
```

> The credentials are injected as environment variables at runtime. They never appear in the console log.

**Step 4d — Deploy to EC2**

This step SSHs into the deploy EC2, pulls the new images from DockerHub, removes the old containers, and starts fresh ones.

First, add two more bindings in **Build Environment → Use secret text(s) or file(s)**:

| Binding type | Variable | Credential ID |
|---|---|---|
| Secret text | `EC2_HOST` | `ec2-host` |
| Secret text | `DATABASE_URL` | `database-url` |

For the SSH key, add one more binding:
- Click **Add** → **Secret file**

| Field | Value |
|-------|-------|
| Variable | `SSH_KEY` |
| Credentials | select `ec2-ssh-key` |

Then click **Add build step** → **Execute shell**:

```bash
echo "=== Deploying to EC2 ==="

chmod 400 $SSH_KEY

ssh -o StrictHostKeyChecking=no -i $SSH_KEY ec2-user@$EC2_HOST "
    docker pull chafah/employee-backend:freestyle-${BUILD_NUMBER}
    docker pull chafah/employee-frontend:freestyle-${BUILD_NUMBER}

    docker network create employee-network 2>/dev/null || true

    if ! docker ps --format '{{.Names}}' | grep -q '^db$'; then
        docker run -d --name db --restart unless-stopped \
          --network employee-network \
          -e POSTGRES_USER=postgres \
          -e POSTGRES_PASSWORD=postgres \
          -e POSTGRES_DB=employees \
          -p 5432:5432 \
          postgres:15
        until docker exec db pg_isready -U postgres; do sleep 2; done
    else
        echo 'Postgres already running, skipping'
    fi

    docker rm -f backend frontend 2>/dev/null || true

    docker run -d --name backend --restart unless-stopped \
      --network employee-network \
      -p 5000:5000 \
      -e DATABASE_URL=$DATABASE_URL \
      chafah/employee-backend:freestyle-${BUILD_NUMBER}

    docker run -d --name frontend --restart unless-stopped \
      --network employee-network \
      -p 80:80 \
      chafah/employee-frontend:freestyle-${BUILD_NUMBER}

    echo 'Deploy complete'
"
```

What each line does:
- `docker pull` — fetches the exact build image from DockerHub onto the deploy EC2
- `docker network create ... || true` — creates the network if it does not exist, ignores error if it does
- Postgres block — only starts the `db` container if it is not already running, then waits until it is ready to accept connections before continuing
- `docker rm -f` — stops and removes the old backend and frontend containers only (Postgres is left running)
- `docker run` — starts the new containers on the same network with the same ports
- `DATABASE_URL` is passed in as an environment variable so the backend knows how to reach Postgres

> **Prerequisite:** The deploy EC2 must have Docker installed and the Jenkins EC2's SSH public key must be in `~/.ssh/authorized_keys` on the deploy EC2. See Part 7.

---

#### Step 5 — Add Post-build Actions

Post-build actions run after all build steps finish — whether the build passed or failed.

1. Scroll to **Post-build Actions** → **Add post-build action** → **Archive the artifacts**
   - Files to archive: `backend/test-results/*.xml` *(if pytest is configured to output XML)*
2. **Add post-build action** → **Publish JUnit test result report**
   - Test report XMLs: `backend/test-results/*.xml`

This makes test results visible directly on the build page as a pass/fail graph over time.

---

#### Step 6 — Save and run

1. Click **Save**
2. Click **Build Now** on the left sidebar
3. Click the build number that appears under **Build History** (e.g. `#1`)
4. Click **Console Output** to watch every command run live

You will see Jenkins:
- Clone the repo from GitHub
- Run pip install and pytest
- Build the Docker images
- Push to DockerHub
- SSH into the deploy EC2, pull the images, replace the containers

Access the app at `http://<DEPLOY_EC2_PUBLIC_IP>`

---

#### Key concepts this job teaches

| Concept | Where you see it |
|---------|------------------|
| Workspace | Jenkins clones the repo to `/var/lib/jenkins/workspace/employee-app-freestyle` |
| Build number | `${BUILD_NUMBER}` increments each run — visible in image tags and on the deploy EC2 |
| Environment variables | `DOCKER_USER`, `DOCKER_PASS`, `EC2_HOST`, `DATABASE_URL`, `SSH_KEY` injected via Credentials Binding |
| Build triggers | Poll SCM checks GitHub every 5 minutes |
| Post-build actions | Test results archived and graphed per build |
| Console output | Every shell command and its stdout/stderr printed live |

---

#### Freestyle vs Pipeline — the key difference

With Freestyle, the job configuration lives only in Jenkins. If you delete the job, the configuration is gone. With a Pipeline job, the `Jenkinsfile` lives in the Git repo — it is versioned, reviewed, and survives a Jenkins reinstall. That is why teams move from Freestyle to Pipeline once they outgrow simple builds.

---

### 2. Pipeline

A single pipeline driven by a `Jenkinsfile` stored in your repo (Pipeline script from SCM) or written directly in the Jenkins UI (Pipeline script). The `Jenkinsfile` uses Groovy-based DSL and defines stages that Jenkins executes in order.

This is the job type used by the `employee-app` pipeline.

**Create it:**

1. **New Item** → name: `employee-app` → **Pipeline** → **OK**
2. Scroll to **Pipeline** section:

| Field | Value |
|-------|-------|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/LandmakTechnology/employee-app.git` |
| Branch | `*/main` |
| Script Path | `Jenkinsfile` |

3. Click **Save** → **Build Now**

**What it teaches:** Pipeline as code — the `Jenkinsfile` lives in the repo, versioned with the application.

---

### 3. Multibranch Pipeline

Automatically scans your repo and creates a separate pipeline for every branch and pull request that contains a `Jenkinsfile`. When a branch is deleted, its pipeline is removed automatically.

This is the most production-like setup — `main` runs the full deploy, `develop` runs tests, feature branches run tests on every push.

**Create it:**

1. **New Item** → name: `employee-app-multibranch` → **Multibranch Pipeline** → **OK**
2. **Branch Sources** → **Add source** → **Git**
   - Project Repository: `https://github.com/LandmakTechnology/employee-app.git`
3. **Build Configuration** → Script Path: `Jenkinsfile`
4. **Scan Multibranch Pipeline Triggers** → tick **Periodically if not otherwise run** → `1 minute`
5. Click **Save** — Jenkins immediately scans and creates a pipeline per branch

**What it teaches:** Branch-based CI/CD — each branch has its own build history, PRs get their own pipeline, branch cleanup is automatic.

---

### 4. Multi-configuration Project (Matrix)

Runs the same build job across multiple combinations of parameters — called axes. For example, test against Python 3.9, 3.10, and 3.11 simultaneously, or test on Linux and Windows at the same time. Each combination runs as a separate sub-build and results are shown in a matrix grid.

Requires the **Matrix Project** plugin (search and install from **Manage Jenkins → Plugins**).

**Create it:**

1. **New Item** → name: `employee-app-matrix` → **Multi-configuration project** → **OK**
2. **Source Code Management** → Git → same repo URL and branch
3. **Configuration Matrix** → **Add axis** → **User-defined Axis**
   - Name: `PYTHON_VERSION`
   - Values: `3.9 3.10 3.11`
4. **Build Steps** → **Execute shell**:

```bash
pip install -r backend/requirements.txt
cd backend
DATABASE_URL=sqlite:///test.db pytest -v
```

5. Click **Save** → **Build Now** — Jenkins runs one build per axis value in parallel

**What it teaches:** Matrix testing — validate your app works across multiple environments or configurations in a single job.

---

### 5. Folder

Not a build job — a container for organising other jobs. Folders can be nested. Each folder has its own credentials scope, so secrets defined in a folder are only available to jobs inside it.

Requires the **Folders** plugin (usually pre-installed with suggested plugins).

**Create it:**

1. **New Item** → name: `employee-app-jobs` → **Folder** → **OK**
2. Add a display name and description → **Save**
3. Click into the folder → **New Item** to create jobs inside it

**What it teaches:** Job organisation — group related pipelines together, scope credentials per team or project.

---

### 6. Organization Folder

Scans an entire GitHub organisation (or Bitbucket/GitLab) and automatically creates a Multibranch Pipeline for every repo that contains a `Jenkinsfile`. New repos are discovered automatically on the next scan.

Requires the **GitHub Branch Source** plugin.

**Create it:**

1. **New Item** → name: `LandmakTechnology` → **Organization Folder** → **OK**
2. **Repository Sources** → **Add** → **GitHub**
   - Credentials: add a GitHub personal access token
   - Owner: `LandmakTechnology`
3. **Scan Organization Triggers** → tick **Periodically** → `1 hour`
4. Click **Save** — Jenkins scans the org and creates pipelines for every repo with a `Jenkinsfile`

**What it teaches:** Organisation-wide CI/CD — one Jenkins item manages every repo in a GitHub org automatically.

---

### Comparison

| Job Type | Config location | Multi-branch | Best for |
|----------|----------------|--------------|----------|
| Freestyle | Jenkins UI | No | Simple tasks, demos, Jenkins intro |
| Pipeline | `Jenkinsfile` in repo | No (one branch) | Single-branch CI/CD |
| Multibranch Pipeline | `Jenkinsfile` per branch | Yes | Full team workflow, PR builds |
| Multi-configuration | Jenkins UI | No | Matrix testing across environments |
| Folder | N/A | N/A | Organising jobs, scoping credentials |
| Organization Folder | `Jenkinsfile` per repo | Yes (all repos) | Org-wide CI/CD, auto-discover repos |

---

### Run any job

Click **Build Now** on any job. Click the build number → **Console Output** to watch it live.
Or open Blue Ocean at `http://<JENKINS_EC2_PUBLIC_IP>:8080/blue` for the visual stage view.

---

## Part 10 — Auto-trigger on Push (Webhook)

### On Jenkins

1. Pipeline → **Configure**
2. Under **Build Triggers** → tick **GitHub hook trigger for GITScm polling**
3. Save

### On GitHub

1. Repo → **Settings → Webhooks → Add webhook**
2. Payload URL: `http://<JENKINS_EC2_PUBLIC_IP>:8080/github-webhook/`
3. Content type: `application/json`
4. Trigger: **Just the push event**
5. Click **Add webhook**

Every push to `main` now triggers the pipeline automatically.

---

## Pipeline Flow

```
git push to main
       │
       ▼
┌──────────┐    ┌─────────────────────┐    ┌──────────────────────────┐
│   Test   │───▶│   Build & Push      │───▶│        Deploy            │
│          │    │                     │    │                          │
│ pip      │    │ docker build        │    │ SSH into EC2             │
│ install  │    │ backend/ → DockerHub│    │ docker pull              │
│ pytest   │    │ frontend/→ DockerHub│    │ docker run backend :5000 │
│          │    │                     │    │ docker run frontend :80  │
└──────────┘    └─────────────────────┘    └──────────────────────────┘
```

Access the app at `http://<DEPLOY_EC2_PUBLIC_IP>`

---

## Troubleshooting

**`docker: permission denied`**
```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

**`pip: command not found`**

Amazon Linux 2023 ships `pip3`, not `pip`. Use `pip3` and `python3 -m pytest` in all build steps:
```bash
pip3 install -r backend/requirements.txt
python3 -m pytest -v
```

**`Host key verification failed`**
The `-o StrictHostKeyChecking=no` flag in the Jenkinsfile handles this automatically.

**`Cannot connect to Docker daemon`**
```bash
sudo systemctl start docker
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

**`invalid reference format`** (DockerHub push fails)
Make sure `DOCKERHUB_BACKEND` and `DOCKERHUB_FRONTEND` use lowercase only — DockerHub repo names must be lowercase.

**`Warning: Identity file not accessible`** (SSH key error)
Use **Secret file** kind for the EC2 SSH key credential, not SSH Username with private key. Add `chmod 400 $SSH_KEY` as the first line of the deploy shell step.

**`ERR_SSL_PROTOCOL_ERROR` in browser**
The app does not have SSL. Use `http://` not `https://`:
```
http://<DEPLOY_EC2_PUBLIC_IP>
```
