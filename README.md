# Kubernetes Prometheus Operator Template
Add Prometheus monitoring to a Kubernetes project with the [prometheus-operator](https://github.com/coreos/prometheus-operator).
The prometheus-operator is a set of Kubernetes resources, namely [pods](https://kubernetes.io/docs/concepts/workloads/pods/pod/)
and [custom resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) that
enable a local (on cluster) Prometheus server to monitor resources internal to the cluster that are not exposed to
the world.  While this can be done with default Prometheus, using the operator is the easiest way to integrate
Prometheus with Kubernetes.

All of this information and configuration is available in the prometheus operator repository.  The purpose of this
repository is to boil the configuration and setup down to only the essential parts necessary to monitor a single application
in a particular namespace.

TL;DR: run the generation script, and apply the files.

Most of the initial setup came from the
[getting started guide](https://github.com/coreos/prometheus-operator/blob/master/Documentation/user-guides/getting-started.md)
reference that for updates or if things break here.

### Getting Started
Create the prometheus operator and service account to start.
```bash
kubectl create -f prometheus_operator.yml
kubectl create -f prometheus_service_account.yml
```

Now either create the [example application](#example-application) to test or configure your [custom application](#custom-application).

### Example Application
Resource files for an example application are in the example_app directory.  Once started this application will publish
a metrics endpoint that Prometheus can scrape.  Create all of the resources in the example_app directory and view the
running pods.
```bash
kubectl get pods --namespace default
```
If the prometheus resources (server, operator, servicemonitor, etc) are created after the application it could take
several minutes for targets to register on the Prometheus server.

After [exposing prometheus](#exposing-prometheus) the example app endpoints can been seen in the Prometheus server.

Delete one of the pods of the example application and watch Prometheus drop the old target and register the new one
on the prometheus targets page.

### Custom Application
To apply prometheus to your custom application either manually modify the templates in the custom app directory
or run the generation script and apply the files.  Applying the files will setup Prometheus but will not expose the
service, because this could differ depending on your environment.  Expose the service and check the targets page to
verify your pods are being scraped.  This setup will need to be done for each namespace.

### Exposing Prometheus
The method for exposing the Kubernetes Prometheus application will depend on the Kubernetes implementation.

If using the internal THDKS implementation expose a
[NodePort](https://kubernetes.io/docs/tutorials/kubernetes-basics/expose/expose-intro/#overview-of-kubernetes-services)
and navigate to `any_kubernetes_non_master_node:30900`.  Get the cluster nodes with `kubectl get nodes`.
```bash
kubectl create -f example_app/prometheus_svc_node_port.yml
```

On GKE a load balancer will be a better fit.
```bash
kubectl create -f example_app/prometheus_svc_load_balancer.yml
```
It will take a minute for GKE to create an external IP so just `watch kubectl get svc` and wait until
the EXTERNAL-IP is populated, then navigate to `EXTERNAL-IP:9090`.

The examples here are for the example application. Include the service type flag with the generation script
to create an accompanying exposure service file for your custom app.

### Upgrade
Upgrade the prometheus operator by updating the image tag for the deployment resource in prometheus_operator.yml.
Relevant tags can be found in the [image hosting repository](https://quay.io/repository/coreos/prometheus-operator?tag=latest&tab=tags).

### Script Dependencies
Use pipenv to satisfy dependencies for the project.
```bash
pip3 install pipenv
pipenv sync
$(pipenv --py) $SCRIPT
```

### Testing
```
cd k8s_prometheus_operator
export PYTHONPATH=$(dirname $(pwd))
$(pipenv --py) -m unittest tests.py
```

### Short Comings
This setup has not been tested with multiple applications on differing ports or on different namespaces.
Results are not guaranteed.  If you test/implement this case update the documentation here.

