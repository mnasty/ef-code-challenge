# EvenFinancial Code Challenge Submission
## Please see the below guide for an interactive demo on the installation and deployment of the model serving framework to Kubernetes

### Prerequisites:
```brew install minikube```

#### Docker Desktop: https://www.docker.com/products/docker-desktop/

#### Apache Spark (3.3.0 / 2.11): https://spark.apache.org/downloads.html

### Once all prerequisites are installed:

#### Clone this repo into the directory of your choice: 
```git clone https://github.com/mnasty/ef-code-challenge.git```

#### Configure docker desktop memory constraints to ensure at least 8GB of memory is avaliable to docker:

![alt text](https://github.com/mnasty/ef-code-challenge/blob/master/res/screenshots/screen1.png?raw=true)

![alt text](https://github.com/mnasty/ef-code-challenge/blob/master/res/screenshots/screen2.png?raw=true)

#### Start local kubernetes environment (min 2 cpus, 8GB memory):
```minikube start --driver=docker --memory 8192 --cpus 4```

---

### Database Deployment (Postgres):

#### Apply yaml defined K8 components to support DB:
```kubectl apply -f res/k8/postgres-cm.yaml``` \
```kubectl apply -f res/k8/postgres-pv.yaml``` \
```kubectl apply -f res/k8/postgres-svc.yaml``` \
```kubectl apply -f res/k8/postgres-sec.yaml```

#### Submit deployment, spin up DB:
```kubectl apply -f res/k8/postgres-dep.yaml```

#### Ensure any local postgres services are not running:
```brew services stop postgresql```

#### List pod names:
```kubectl get all```
```
...:code-challenge Mick$ kubectl get all
NAME                            READY   STATUS    RESTARTS   AGE
pod/(*pod name*->)postgres-76c84dc8d8-465gn   1/1     Running   0          8d

NAME                 TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
service/kubernetes   ClusterIP   10.96.0.1        <none>        443/TCP          8d
service/postgres     NodePort    10.110.230.221   <none>        5432:32763/TCP   8d

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/postgres   1/1     1            1           8d

NAME                                  DESIRED   CURRENT   READY   AGE
replicaset.apps/postgres-76c84dc8d8   1         1         1       8d
```

#### Forward postgres port outside K8 virtual network using pod name:
```kubectl port-forward <pod_name> 5432:5432```

#### Execute LoadData.py to load data into DB (in a new terminal window):
```source model-venv/bin/activate``` \
```python3 LoadData.py```

---

### API Deployment (Flask):

#### Configure jdbc uri: 
```kubectl get all```

Locate and copy service IP:
```
...:code-challenge Mick$ kubectl get all
NAME                            READY   STATUS    RESTARTS   AGE
pod/postgres-76c84dc8d8-465gn   1/1     Running   0          8d

NAME                 TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
service/kubernetes   ClusterIP   10.96.0.1        <none>        443/TCP          8d
service/postgres     NodePort    (*db vn ip*->)10.110.230.221   <none>        5432:32763/TCP   8d

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/postgres   1/1     1            1           8d

NAME                                  DESIRED   CURRENT   READY   AGE
replicaset.apps/postgres-76c84dc8d8   1         1         1       8d
```
Reconstruct URI for k8 virtual network:
```postgresql://postgres:password@<paste_here>:5432/postgres```
```
API:95 -> engine = create_engine('postgresql://postgres:password@<paste_here>:5432/postgres')
API:111 -> engine = create_engine('postgresql://postgres:password@<paste_here>:5432/postgres')
```

#### Set/ensure docker env for local API image deployment:
```eval $(minikube docker-env)```

#### Go into API folder:
```cd api/```

#### Build docker image, **ensure you're running from <project_root>/api:** 
```docker build . -t click-api-env:latest```

#### Move back to project root: 
```cd ..```

#### Setup API service: 
```kubectl apply -f res/k8/api-svc.yaml```

#### Deploy API: 
```kubectl apply -f res/k8/api-dep.yaml```

#### Expose service to access locally (use seperate terminal window): 
```minikube service click-service```

---

### Model Deployment (Spark):

#### Go to spark home (root dir of unzipped spark download):
```cd $SPARK_HOME``` or
```cd spark-3.3.0-bin-hadoop3/```

#### Set/ensure docker env for local API image deployment:
```eval $(minikube docker-env)```

#### Build docker image for spark & pyspark:
```bin/docker-image-tool.sh -m -t 3.3.0 -p ./kubernetes/dockerfiles/spark/bindings/python/Dockerfile build```

#### Go back to project root (wherever you cloned this repo)
```cd .../```

#### Configure jdbc uri (repeating procedure above):
```
Main:26 -> db_uri=postgresql://postgres:password@10.110.230.221:5432/postgres
```

#### Update cluster ports:
```kubectl cluster-info```

Locate and copy port:
```
...:code-challenge Mick$ kubectl cluster-info
Kubernetes control plane is running at https://127.0.0.1:(*port*->)52306
CoreDNS is running at https://127.0.0.1:52306/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

```nano run-model.sh```

Apply new port:
```
run-model.sh:4 -> --master k8s://https://127.0.0.1:xxxxx \
```

#### Set/ensure docker env for local API image deployment:
```eval $(minikube docker-env)```

#### Build custom image for env, **ensure you're running from project root**:
```docker build . -t click-model-env:latest```

#### Deploy zookeeper:
```kubectl apply -f res/k8/zookeeper-svc.yaml``` \
```kubectl apply -f res/k8/zookeeper-dep.yaml```

#### Deploy kafka:
```kubectl apply -f res/k8/kafka-svc.yaml``` \
```kubectl apply -f res/k8/kafka-dep.yaml```

#### Apply spark config:
```kubectl apply -f res/k8/spark-roles.yaml```

#### Ensure all deployed resources have spun up successfully:
```kubectl get all``` 

***STATUS = Running***

Access kafka pod, repeating procedure "List pod names:" above (equivalent to ssh): \
```kubectl exec -it kafka-deployment-6b7b57cbd9-sd27c -- /bin/bash```

#### Create topics:
```
kafka-topics --create --bootstrap-server localhost:29092 --replication-factor 1 --partitions 1 --topic requests
```
```
kafka-topics --create --bootstrap-server localhost:29092 --replication-factor 1 --partitions 1 --topic responses
```
```exit```

#### Submit streaming job:
```
chmod +x run-model.sh
./run-model.sh
```

---

### Monitor and View All Deployments:
```minikube dashboard```

---

### Test Deployments:

Download Postman: https://www.postman.com/downloads/

Load 'Click API.postman_collection.json' to test each API endpoint. 

![alt text](https://github.com/mnasty/ef-code-challenge/blob/master/res/screenshots/screen3.png?raw=true)

Ensure that the port on each request matches the click service port when exposed via minikube:
```
...:~ Mick$ minikube service click-service
|-----------|---------------|-------------|---------------------------|
| NAMESPACE |     NAME      | TARGET PORT |            URL            |
|-----------|---------------|-------------|---------------------------|
| default   | click-service | api/8080    | http://192.168.49.2:31074 |
|-----------|---------------|-------------|---------------------------|
🏃  Starting tunnel for service click-service.
|-----------|---------------|-------------|------------------------|
| NAMESPACE |     NAME      | TARGET PORT |          URL           |
|-----------|---------------|-------------|------------------------|
| default   | click-service |             | http://127.0.0.1:(*port*->)60946 |
|-----------|---------------|-------------|------------------------|
🎉  Opening service default/click-service in default browser...
❗  Because you are using a Docker driver on darwin, the terminal needs to be open to run it.
```

![alt text](https://github.com/mnasty/ef-code-challenge/blob/master/res/screenshots/screen4.png?raw=true)

To delete cluster and all deployments when finished: \
```minikube delete```
---

### Sample requests and responses:

####/predictions - POST
req:
```
{
	"lender_id": "1103",
	"loan_purpose": "debt_consolidation",
	"credit":"poor",
	"annual_income": "24000.0",
	"apr":"199.0"
}
```

res:
```
{
  "rawPrediction": {
    "type": 1,
    "values": [
      1.939631552899531,
      -1.939631552899531
    ]
  },
  "probability": {
    "type": 1,
    "values": [
      0.9797523898258298,
      0.020247610174170174
    ]
  },
  "prediction": 0
}
```

###/assignment - POST
req:
```
{
	"version": "0.5_0.0"
}
```

res:
```
{
  "version": {
    "0": "0.5_0.0",
    "set": "True"
  }
}
```

###/current_model - GET
```
{
  "version": {
    "0": "none set"
  }
}
```

```
{
  "version": {
    "0": "0.5_0.0"
  }
}
```
