# Flask and MongoDB on Kubernetes

This project implements the assignment's Flask and MongoDB application for local execution and
deployment to a local Kubernetes cluster. It includes the application source, Docker image
configuration, Kubernetes resources, tests, and deployment instructions.

## Project contents

| Item | Location |
| --- | --- |
| Flask application | `app.py` |
| Python dependencies | `requirements.txt` |
| Flask unit tests | `test_app.py` |
| Docker image definition | `Dockerfile` |
| Deployment documentation | `README.md` |
| Kubernetes manifests | `k8s/` |
| Environment template | `.env.example` |

The Kubernetes directory contains:

- `secret.yaml` — MongoDB credentials
- `mongodb-pv.yaml` — persistent volume
- `mongodb-pvc.yaml` — persistent volume claim
- `mongodb-service.yaml` — internal MongoDB service
- `mongodb-statefulset.yaml` — authenticated MongoDB pod
- `flask-deployment.yaml` — two or more Flask pods
- `flask-service.yaml` — Flask access from the local machine
- `flask-hpa.yaml` — CPU-based horizontal autoscaling

## 1. Application behavior

The application exposes two required endpoints:

- `GET /` — returns `Welcome to the Flask app! The current time is: <Date and Time>`
- `POST /data` — validates and inserts a JSON object into MongoDB
- `GET /data` — returns all stored JSON objects and excludes MongoDB's `_id` field

A `health` endpoint (`GET /health`) is also included for Kubernetes liveness and readiness
probes.

Example POST body:

```json
{"sampleKey":"sampleValue"}
```

Example response:

```json
{"status":"Data inserted"}
```

## 2. Part 1: local setup

### Prerequisites

- Python 3.8 or later
- Docker Desktop
- pip
- Windows PowerShell

### Create the virtual environment

Run the following commands from a PowerShell terminal:

```powershell
cd D:\python-assignment\flask-mongodb-app
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### Why use a virtual environment?

A Python virtual environment provides an isolated package directory for this project. This:

- prevents package versions from conflicting with global or other project environments;
- makes dependency installation reproducible;
- allows the project to use an interpreter and package set separate from the system Python;
- keeps experimental changes and package upgrades from affecting unrelated applications;
- makes it easier to produce and cleanly remove a project-specific environment.

The assignment only requires Python 3.8 or later. Python 3.14 is used in this environment for
verification, while the application code is also compatible with supported Python 3 releases
with matching package wheels.

### Run MongoDB locally

Start Docker Desktop, then run:

```powershell
docker pull mongo:7
docker run -d --name mongodb -p 27017:27017 mongo:7
$env:MONGODB_URI = "mongodb://localhost:27017/"
python app.py
```

The local MongoDB container is intentionally used without authentication for the assignment's
Part 1 setup. Authentication is enabled for the Kubernetes deployment in Part 2.

The application is available at `http://localhost:5000/`.

### Test the local API

PowerShell:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:5000/"

Invoke-RestMethod -Method Post `
  -Uri "http://localhost:5000/data" `
  -ContentType "application/json" `
  -Body '{"sampleKey":"sampleValue"}'

Invoke-RestMethod -Method Get -Uri "http://localhost:5000/data"
```

curl:

```bash
curl http://localhost:5000/
curl -X POST -H "Content-Type: application/json" \
  -d '{"sampleKey":"sampleValue"}' \
  http://localhost:5000/data
curl http://localhost:5000/data
```

### Run unit tests

```powershell
python -m unittest -v
```

The test suite exercises the root endpoint, POST and GET data behavior, invalid input, and the
health endpoint. MongoDB access is replaced with an in-memory fake collection in the unit tests,
so these tests do not require a running database.

## 3. Docker image

The Dockerfile uses the Python 3.14 slim image, installs `requirements.txt`, copies the
application, exposes port 5000, and starts it using Gunicorn rather than Flask's development
server.

Build the image:

```powershell
cd D:\python-assignment\flask-mongodb-app
docker build -t flask-mongodb-app:latest .
```

Verify it locally:

```powershell
docker images flask-mongodb-app
docker run --rm -p 5000:5000 flask-mongodb-app:latest
```

### Push to a container registry

Choose a registry and set shell variables. Docker Hub is used as an example:

```powershell
$REGISTRY = "docker.io"
$USERNAME = "<your-dockerhub-username>"
$IMAGE = "flask-mongodb-app"
$TAG = "latest"
$FULL_IMAGE = "$REGISTRY/$USERNAME/$IMAGE:$TAG"

docker login $REGISTRY
docker tag flask-mongodb-app:latest $FULL_IMAGE
docker push $FULL_IMAGE
```

For a registry other than Docker Hub, replace `$REGISTRY` with its registry hostname. If the
registry is private, replace `flask-mongodb-app:latest` in `k8s/flask-deployment.yaml` with
`$FULL_IMAGE` and configure a Kubernetes image pull secret.

Example private-registry pull secret:

```powershell
kubectl create secret docker-registry registry-creds `
  --docker-server=<registry-host> `
  --docker-username=<username> `
  --docker-password=<password> `
  --docker-email=<email>
```

Then add `imagePullSecrets` under the pod spec:

```yaml
spec:
  imagePullSecrets:
    - name: registry-creds
```

For this local test, the image is loaded directly into Minikube with `minikube image load`, so no
external registry is required.

## 4. Kubernetes setup on Windows with Minikube

Install Docker Desktop and Minikube, then open a new PowerShell terminal.

```powershell
winget install -e --id Kubernetes.minikube
minikube start --driver=docker
minikube addons enable metrics-server
```

Verify that the cluster is available:

```powershell
kubectl get nodes
kubectl get pods -A
```

### Configure credentials

Change the placeholder values in `k8s/secret.yaml` before deployment:

```yaml
stringData:
  mongo-root-username: flaskuser
  mongo-root-password: <strong-unique-password>
```

Do not use an example password for a shared or public environment. A Kubernetes Secret
base64-encodes data in Kubernetes API storage conventions but does not itself encrypt it. For a
production cluster, enable encryption at rest and use an external secret manager.

### Load and deploy the application

Build the image locally and load it into the Minikube container runtime:

```powershell
docker build -t flask-mongodb-app:latest .
minikube image load flask-mongodb-app:latest
```

Apply resources in dependency order:

```powershell
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/mongodb-pv.yaml
kubectl apply -f k8s/mongodb-pvc.yaml
kubectl apply -f k8s/mongodb-service.yaml
kubectl apply -f k8s/mongodb-statefulset.yaml
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/flask-hpa.yaml
```

Or apply the complete directory:

```powershell
kubectl apply -f k8s/
```

Check the rollout:

```powershell
kubectl get pods -o wide
kubectl rollout status deployment/flask-app
kubectl rollout status statefulset/mongodb
kubectl get svc,pvc,hpa
```

The deployment should show two ready Flask pods and one ready MongoDB pod.

### Access the Flask service

```powershell
minikube service flask-app --url
```

Open the returned URL. If its variable is assigned in PowerShell, test it with:

```powershell
$FLASK_URL = (minikube service flask-app --url)
Invoke-RestMethod "$FLASK_URL/"
Invoke-RestMethod -Method Post -Uri "$FLASK_URL/data" `
  -ContentType "application/json" `
  -Body '{"sampleKey":"sampleValue"}'
Invoke-RestMethod "$FLASK_URL/data"
```

The NodePort service is used for local access. It exposes Flask port 5000 internally at service
port 80 and assigns a node port locally.

## 5. MongoDB authentication

MongoDB authentication is enabled with the following mechanisms:

- `MONGO_INITDB_ROOT_USERNAME` initializes the MongoDB root username.
- `MONGO_INITDB_ROOT_PASSWORD` initializes the corresponding password.
- The StatefulSet runs MongoDB with `--auth`.
- Credentials are obtained from `mongodb-auth` Secret key references rather than hard-coded
  directly in container arguments.
- Flask receives `MONGODB_URI` through environment variables:

```text
mongodb://<username>:<password>@mongodb:27017/flask_db?authSource=admin
```

The MongoDB service is type `ClusterIP`, so it is accessible only inside the cluster. It is not
exposed through NodePort or LoadBalancer.

Authentication can be checked with a temporary MongoDB pod:

```powershell
kubectl run mongo-probe --rm -i --restart=Never --image=mongo:7 --command -- `
  mongosh "mongodb://flaskuser:<password>@mongodb:27017/flask_db?authSource=admin" `
  --quiet --eval "db.runCommand({ping:1})"
```

A successful response is `{ ok: 1 }`. Password characters that have URI-reserved meaning should
be percent-encoded in a connection string in a real deployment.

## 6. Deployment and StatefulSet design

### Flask Deployment

The `flask-deployment.yaml` manifest starts with two replicas. Kubernetes creates independent
Flask pods behind the Flask service. Gunicorn and Kubernetes both provide process-level scaling:
Gunicorn handles concurrency inside each pod, while the Deployment and HPA add or remove pods.

Readiness and liveness HTTP probes call `/health`, allowing Kubernetes to stop traffic to an
unready pod and restart an unhealthy pod.

### MongoDB StatefulSet

MongoDB uses a StatefulSet instead of a Deployment because it is stateful database software.
The StatefulSet provides a stable pod identity and is paired with persistent storage.
This assignment uses one MongoDB replica because Minikube is a single-node local environment.
A MongoDB replica set would be required for database high availability and automatic primary
failover in a production deployment.

## 7. Kubernetes services

### Flask service

`flask-service.yaml` creates a `NodePort` service:

- service port: 80
- target port: 5000
- selector: `app: flask-app`

NodePort was chosen so a local Minikube cluster can expose Flask without additional cloud
load-balancer or Ingress infrastructure. In a public cloud cluster, a LoadBalancer or Ingress
with TLS would be more suitable.

### MongoDB service

`mongodb-service.yaml` creates a `ClusterIP` service named `mongodb`:

- service port: 27017
- target port: 27017
- selector: `app: mongodb`

ClusterIP was chosen because MongoDB should be reachable by the application but never exposed
directly to the local or public network.

## 8. Persistent storage

`mongodb-pv.yaml` defines a 1 GiB PersistentVolume:

- access mode: `ReadWriteOnce`
- storage class: `manual`
- host path: `/data/mongodb`
- reclaim policy: `Retain`

`mongodb-pvc.yaml` requests the same capacity from the manually configured storage class.
The StatefulSet mounts the claim at `/data/db`, which is MongoDB's data directory.

Retain was chosen so deleting a PVC or pod does not automatically delete stored database data.
The explicit hostPath configuration is suitable for local Minikube. A cloud cluster would
normally use a provisioned storage class backed by managed block storage.

To verify persistence, POST data, delete `mongodb-0`, wait for replacement, and GET `/data`
again. The data should remain available if the PVC remains bound.

## 9. DNS resolution

Kubernetes DNS assigns names to Services in the cluster. The MongoDB Service is named `mongodb`,
so another pod can use the short name `mongodb` in the same namespace.

The Flask pod sets:

```text
MONGODB_URI=mongodb://<credentials>@mongodb:27017/flask_db?authSource=admin
```

Resolution follows this path:

1. Flask asks cluster DNS for `mongodb`.
2. Kubernetes DNS resolves `mongodb` to the MongoDB Service ClusterIP.
3. The Service routes port 27017 to the MongoDB pod selected by `app: mongodb`.
4. MongoDB authenticates the supplied credentials.

The fully qualified service name is:

```text
mongodb.<namespace>.svc.cluster.local
```

This format is useful across namespaces or when explicit names are preferred. Pod IPs are not used
because they may change after rescheduling or restart.

## 10. Resource requests and limits

The Flask and MongoDB pods use the following values:

| Setting | Flask | MongoDB |
| --- | --- | --- |
| CPU request | `200m` (0.2 CPU) | `200m` (0.2 CPU) |
| Memory request | `250Mi` | `250Mi` |
| CPU limit | `500m` (0.5 CPU) | `500m` (0.5 CPU) |
| Memory limit | `500Mi` | `500Mi` |

### Requests

Requests are the resources Kubernetes reserves for scheduling:

- 200 millicores is 0.2 of a CPU core.
- 250Mi is 250 mebibytes of memory.
- An application should normally have enough scheduled resources for baseline operation.

### Limits

Limits are upper bounds:

- 500 millicores is 0.5 of a CPU core.
- 500Mi is 500 mebibytes of memory.
- CPU exceeding the limit is throttled.
- Memory exceeding the limit can lead to container termination or an out-of-memory event.

Requests and limits prevent a pod from consuming an uncontrolled share of cluster resources and
help the scheduler place pods reliably. The limits are sample values for this assignment and may
need tuning based on real MongoDB working-set size and Flask traffic.

## 11. Horizontal Pod Autoscaling

`k8s/flask-hpa.yaml` configures:

- target Deployment: `flask-app`
- minimum replicas: 2
- maximum replicas: 5
- metric: average CPU utilization
- target: 70%

The metrics-server addon supplies CPU measurements. The HPA calculates whether the current
average utilization is above or below 70% and adjusts the Deployment's replica count.

## 12. Testing scenarios

### Unit testing

The unit test suite was run with:

```powershell
python -m unittest -v
```

Result:

```text
Ran 4 tests
OK
```

Covered scenarios:

- root endpoint returns HTTP 200 and the welcome text;
- POST inserts a JSON object and returns HTTP 201;
- GET returns the inserted object;
- non-JSON POST input returns HTTP 400;
- health endpoint returns HTTP 200.

### Database interaction testing

The live Minikube cluster was tested using both an authenticated MongoDB probe and the Flask API.

Authenticated MongoDB test:

```powershell
kubectl run mongo-probe --rm -i --restart=Never --image=mongo:7 --command -- `
  mongosh "mongodb://flaskuser:<password>@mongodb:27017/flask_db?authSource=admin" `
  --quiet --eval "db.runCommand({ping:1})"
```

Result:

```text
{ ok: 1 }
```

A Flask pod was then used to POST and GET a JSON object. The POST response was:

```text
{"status":"Data inserted"}
```

The subsequent GET response was:

```text
[{"assignment":"verified"}]
```

This verified that:

- the Flask pods resolved `mongodb`;
- MongoDB authentication succeeded;
- Flask inserted data;
- Flask retrieved the stored document.

### Autoscaling test

The metrics-server addon was enabled, and the HPA reported 2 replicas and an initial CPU
utilization of approximately 2%.

A temporary busybox pod was then started inside the cluster with an infinite loop requesting
the Flask root endpoint:

```powershell
kubectl run high-traffic --restart=Never --image=busybox:1.36 -- `
  /bin/sh -c "while true; do wget -q -O- http://flask-app/ >/dev/null; done"

Start-Sleep -Seconds 90
kubectl get hpa flask-app
kubectl get deployment flask-app
```

Observed result after approximately 90 seconds:

```text
TARGETS        MINPODS  MAXPODS  REPLICAS
cpu: 25%/70%   2        5        2
```

The initial 90-second observation remained at 2 replicas. Metrics-server reporting stabilized
after the test continued briefly, and a follow-up cluster observation showed the HPA at
`cpu: 46%/70%` with 3 replicas:

```text
TARGETS        MINPODS  MAXPODS  REPLICAS
cpu: 46%/70%   2        5        3
```

The traffic reached roughly 46% average CPU utilization, below the 70% target, before
continuing briefly enough for a metrics/reporting interval to produce 3 replicas. This
demonstrates observed HPA operation, but the 70% threshold was not sustained enough to create
replicas 4 or 5. After the traffic pod was deleted, the HPA would continue cooling down and
scale toward the 2-replica minimum if sustained utilization dropped.

Stop the test pod:

```powershell
kubectl delete pod high-traffic --wait=true
```

### Stronger scale-up test

For a load test intended to exceed 70%, use a pod that repeatedly performs CPU work or use a
load-testing tool such as `hey` or `wrk`. Monitor the HPA continuously:

```powershell
kubectl get hpa flask-app --watch
kubectl get deployment flask-app --watch
```

Run the load in one terminal and leave the watch commands in separate terminals. Before declaring
the test successful, verify:

- CPU utilization exceeds 70%;
- the replica count increases toward 5;
- all new pods become ready;
- application requests continue to succeed;
- after load stops, the HPA scale-down returns toward 2 replicas.

### Issues encountered

During setup, the following issues were diagnosed and resolved:

- Docker Desktop was stopped; it was started and the Docker engine was verified.
- Minikube was installed but initially not on the current PowerShell path; the full executable
  path was used.
- An early MongoDB readiness probe used an authenticated `mongosh ping` command with a 1-second
  timeout. It was replaced by a TCP socket check for port 27017.
- The initial pod created from the old probe specification was deleted so the recreated pod used
  the updated StatefulSet template.
- Kubernetes PVC storage binding was observed while the pod was starting; it resolved once the
  PV/PVC became bound.
- Metrics CPU data initially arrived after the metrics-server addon was enabled; it settled to
  2% during normal operation.
- The first curl-based in-cluster POST command had shell quoting issues. API interaction was
  verified successfully from inside a Flask pod with a Python JSON request.

## 13. Design choices and alternatives

### Flask

Gunicorn was chosen instead of Flask's built-in development server because Gunicorn is designed
for multi-process production-style serving. Flask's development server is simpler for local
debugging but is not suitable for the container workload model.

### MongoDB

MongoDB was chosen because it is required by the assignment and stores JSON-like documents
without a fixed SQL schema. A single MongoDB StatefulSet is appropriate for a local exercise.
A cloud database or managed MongoDB replica set was not chosen because it would require external
accounts and would not demonstrate Kubernetes volume and pod concepts.

### StatefulSet

A StatefulSet was chosen over a Deployment for MongoDB to preserve pod identity and pair cleanly
with persistent storage. For this one-node cluster, StatefulSet replication was left at 1.

### Service types

ClusterIP was chosen for MongoDB to keep database traffic internal. NodePort was chosen for Flask
because it provides straightforward local access in Minikube. In a cloud deployment, LoadBalancer
or Ingress is a better public exposure mechanism.

### Storage

An explicit PV and PVC were used to demonstrate Kubernetes persistent storage. The Minikube
hostPath PV is not suitable for multi-node or production storage, but it is directly testable
with the local cluster. Dynamic provisioning could be preferable in a cloud environment.

### Credentials

A Kubernetes Secret was used instead of embedding credentials in source code or arguments. This
keeps credentials out of the application image and provides references to pod environment
variables. External secret management is preferable for production.

### Scaling

The HPA was chosen because the assignment requires CPU-based scaling. It maintains two replicas
for baseline availability and scales to five. Kubernetes Deployment rolling updates and
readiness probes preserve access during pod replacement.

## 14. Resource and application verification

Useful verification commands:

```powershell
kubectl get pods,deploy,statefulset,svc,pvc,hpa
kubectl describe hpa flask-app
kubectl describe pvc mongodb-pvc
kubectl logs -l app=flask-app --tail=100
kubectl logs mongodb-0 --tail=100
```

To confirm a pod has the expected resource configuration:

```powershell
kubectl get pod -l app=flask-app -o yaml
kubectl get pod mongodb-0 -o yaml
```

## 15. Cleanup

Stop and remove Kubernetes resources:

```powershell
kubectl delete -f k8s/flask-hpa.yaml
kubectl delete -f k8s/flask-service.yaml
kubectl delete -f k8s/flask-deployment.yaml
kubectl delete -f k8s/mongodb-statefulset.yaml
kubectl delete -f k8s/mongodb-service.yaml
kubectl delete -f k8s/mongodb-pvc.yaml
kubectl delete -f k8s/mongodb-pv.yaml
kubectl delete -f k8s/secret.yaml
```

Stop Minikube and Docker resources:

```powershell
minikube stop
docker rm -f mongodb
docker rmi flask-mongodb-app:latest
```
