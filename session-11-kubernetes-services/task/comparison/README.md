# Session 11 — Task 2: Kubernetes Object Comparison

- **Name:** Raj Prakash
- **Enrollment No:** 24BCS10328

Back to the [session 11 task index](../README.md). Where a claim below has evidence, it links to
real output: from [session 10](../../../session10-k8s-core-objects/task/README.md), where I
applied each of these objects and watched them behave, and from
[Task 1](../README.md) of this session.

---

## 1. Deployment vs ReplicaSet

| | ReplicaSet | Deployment |
|---|---|---|
| **Purpose** | keep exactly N copies of one pod template running | manage an application's *versions* over time |
| **Pod management** | creates/deletes pods directly to match `replicas` | never touches pods — creates and scales **ReplicaSets** |
| **Scaling** | `kubectl scale rs ...` works | `kubectl scale deploy ...` — the Deployment passes the number to its current ReplicaSet |
| **Rolling updates** | none — changing the template does **not** replace running pods | yes: a new ReplicaSet scales up while the old one scales down (`maxSurge` / `maxUnavailable`) |
| **Rollback** | none | `kubectl rollout undo` — scales an old ReplicaSet back up |
| **Use directly?** | almost never | yes, for every stateless app |

**The relationship** is ownership: `Deployment → ReplicaSet → Pod`. It is not a mental model — it
is a field you can print. In session 10:

```text
$ kubectl get rs -l app=myapp -o jsonpath='{...ownerReferences...}'
myapp-55d8f46968  ownerRef -> Deployment/myapp
```

The suffix `55d8f46968` is a hash of the pod template. Change the image and the hash changes, so
you get a **second** ReplicaSet. During the session 10 rollout both existed at once, and
afterwards the old one stayed at `DESIRED 0` — which is the entire rollback mechanism:

```text
myapp-55d8f46968   0   0   0   2m31s     ← old template, kept at zero
myapp-756b955d54   3   3   3   2m15s     ← new template
```

A ReplicaSet on its own cannot do this. If you edit a bare ReplicaSet's image, existing pods keep
the old image until something deletes them — the ReplicaSet only counts pods matching its
selector; it does not compare their spec with its template.

---

## 2. Deployment vs DaemonSet vs StatefulSet

| | Deployment | DaemonSet | StatefulSet |
|---|---|---|---|
| **Use case** | stateless apps: APIs, web front ends, workers | one agent per node: log shippers, metrics exporters, CNI, kube-proxy | stateful, clustered apps: databases, Kafka, ZooKeeper, Elasticsearch |
| **Pod creation** | all at once, random names (`web-app-89d947d67-wj4x8`) | one per (tolerated) node, created when a node joins | **in order**, `name-0`, `name-1`, …; each waits for the previous to be Ready |
| **Scaling** | `replicas: N` | **no `replicas` field** — the node count decides | `replicas: N`; up adds the next ordinal, down removes the **highest** first |
| **Networking** | one ClusterIP Service in front, pods interchangeable | usually `hostNetwork`/`hostPort`, or reached per node | a **headless** Service; each pod gets a stable DNS name `name-N.svc` |
| **Storage** | none, or one shared volume | usually `hostPath` (node logs, `/proc`) | `volumeClaimTemplates`: **one PVC per pod**, reattached to the same ordinal, kept on scale-down |
| **Update** | rolling, any order | rolling, node by node | rolling in **reverse ordinal** order |
| **Examples** | nginx, a Flask API, the session 16 calculator | node-exporter, Fluent Bit, Calico, kube-proxy | MySQL, PostgreSQL, Redis cluster, Kafka |

Behaviour I actually saw, rather than read about:

- **DaemonSet "every node" means every node it tolerates.** In session 10 a 3-node cluster gave
  `DESIRED 2` because the control plane has a `NoSchedule` taint; adding a toleration made it 3.
- **StatefulSet identity survives pod deletion.** Session 10: `mysql-0` deleted and recreated with
  a new UID and IP, but the same name and the same PVC with the row I had written. Task 1 of this
  session showed the same for DNS — `web-stateful-1` came back with a new IP and its
  `web-stateful-1.web-service-headless` record followed it.
- **StatefulSet PVCs outlive scale-down.** Scaling MySQL 3 → 1 → 3 kept the PVC ages running —
  the volumes waited for their pods to come back.

Rule of thumb: if any pod could be replaced by any other pod, use a Deployment. If each node needs
one, use a DaemonSet. If pods are *not* interchangeable — they have a role, data or a peer
relationship — use a StatefulSet.

---

## 3. ReplicaSet vs Service

They answer different questions and need each other.

| | ReplicaSet | Service |
|---|---|---|
| **Responsibility** | *how many* pods exist | *how to reach* them |
| **Works on** | the pod lifecycle — creates replacements | the network — a stable IP + DNS name |
| **Selects pods by** | label selector | label selector (independently) |
| **Knows about the other?** | no | no |

**Why a Service is required:** a ReplicaSet keeps the *count* right by creating **new** pods —
different names, different IPs. Session 10 showed a deleted pod `10.244.1.4` replaced by one at a
new address in under a second. Any client holding a pod IP would now be talking to nothing. The
Service gives clients one address that never changes, while the pods behind it come and go.

**How traffic reaches pods** (Task 1, ClusterIP section):

```text
client pod ── DNS: web-service-clusterip ─► CoreDNS ─► 10.96.14.117 (ClusterIP)
     │
     └─ connect 10.96.14.117:8080 ─► node iptables (written by kube-proxy)
                                      └─ DNAT to one of the EndpointSlice IPs, port 80
                                           10.244.1.16 | 10.244.2.15 | 10.244.2.14
```

1. The Service's selector is evaluated by the **EndpointSlice controller**, not at request time.
   It keeps the list of ready pod IPs current.
2. **kube-proxy** on every node turns that list into iptables rules for the ClusterIP.
3. **CoreDNS** maps the Service name to the ClusterIP.
4. A connection to the ClusterIP is rewritten (DNAT) on the client's node to one pod IP —
   chosen per connection.

The two objects never reference each other — the label is the only link. That is also how they
break: a typo in either selector gives a ReplicaSet with healthy pods and a Service with **no
endpoints**, which Task 1 showed fails instantly with `Connection refused`.
