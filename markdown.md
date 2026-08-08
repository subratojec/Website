# Building a Kubernetes Homelab from Scratch on Fedora

> **Build it. Break it. Understand it.**

Kubernetes is easy to use when someone else has already built the infrastructure for you.

Create a cluster, connect `kubectl`, deploy an application, and you're ready.

But I wanted to understand what happens underneath.

So I decided to build my own **Kubernetes homelab from scratch** — locally, on my Fedora laptop, without using a managed Kubernetes service, Minikube, or kind.

The goal was simple:

> **Start with a laptop. End with a real two-node Kubernetes cluster.**

And, more importantly, understand every layer along the way.

---

## 🏗️ The Goal

The target architecture was intentionally simple:

```text
                         Fedora Laptop
                      16 GB RAM / 144 GB
                              │
                         KVM / libvirt
                              │
                    192.168.150.0/24
                         │          │
                         │          │
                ┌────────▼───┐  ┌───▼─────────┐
                │ k8s-master │  │ k8s-worker  │
                │            │  │             │
                │ 4 GB RAM   │  │ 4 GB RAM    │
                │ 2 vCPU     │  │ 2 vCPU      │
                │ .150.75    │  │ .150.22     │
                └─────┬──────┘  └──────┬──────┘
                      │                │
                      └───────┬────────┘
                              │
                           Calico
                              │
                       Pod Networking
```

### The stack

- Fedora Linux
- KVM/libvirt
- Fedora Cloud Base
- containerd
- kubeadm
- kubelet
- kubectl
- Calico CNI
- Kubernetes `v1.31.14`

The final cluster would contain:

- **1 control-plane node**
- **1 worker node**
- **4 GB RAM + 2 vCPU per VM**

---

## 💡 Why Build It Yourself?

There is a difference between **using Kubernetes** and **understanding Kubernetes**.

When Kubernetes is provided as a managed service, many important layers disappear behind an API.

I wanted to see those layers myself.

```text
Laptop
   ↓
Linux
   ↓
Virtualization
   ↓
Virtual Network
   ↓
Virtual Machines
   ↓
Container Runtime
   ↓
Kubernetes
   ↓
CNI
   ↓
Ready Nodes
```

This also meant that when something broke, I couldn't simply recreate the cluster and move on.

I had to find out **why** it broke.

And there were quite a few surprises.

---

# 1. Creating the Virtual Machines

I started by installing KVM/libvirt on Fedora:

```bash
sudo dnf install @virtualization
```

I used a Fedora Cloud Base image and created two virtual machines.

### `k8s-master`

```text
RAM: 4 GB
CPU: 2 vCPU
IP: 192.168.150.75
```

### `k8s-worker`

```text
RAM: 4 GB
CPU: 2 vCPU
IP: 192.168.150.22
```

I used **cloud-init** to configure the VMs with the `singh` user and SSH access.

At this point, I didn't have Kubernetes yet.

I just had two Linux machines.

And then networking decided to become the first challenge.

---

# 2. The First Problem: DNS

The libvirt network initially refused to start properly.

After checking what was using DNS port `53`, I found the problem:

```bash
ss -tulnp | grep :53
```

**AdGuard Home** was already listening on port `53` on my Fedora host.

Libvirt's DNS service was trying to use the same port.

So effectively:

```text
AdGuard Home ───────► Port 53
                         ▲
                         │
libvirt dnsmasq ────────┘
```

Two services wanted the same port.

### The fix

I disabled DNS functionality inside the libvirt network while keeping DHCP.

That allowed the virtual network to start.

---

# 3. Fixing DNS Inside the VMs

Disabling libvirt DNS created another problem.

The VMs could no longer resolve domain names.

I initially looked at:

```text
/etc/resolv.conf
```

But modern Fedora uses **systemd-resolved**, so manually editing that file isn't a reliable long-term solution.

Instead, I configured DNS through:

```text
/etc/systemd/resolved.conf.d/
```

The VMs were configured to use the host-side DNS service.

After restarting `systemd-resolved`, DNS resolution started working.

But there was still a problem.

The VMs could resolve names, but they couldn't properly reach the Internet.

---

# 4. DNS Works, But Internet Doesn't

This was where the debugging became more interesting.

The desired network path was:

```text
Kubernetes VM
     │
     ▼
  virbr0
     │
     ▼
 Fedora Host
     │
     ▼
 Forwarding + NAT
     │
     ▼
 Internet
```

The libvirt `firewalld` zone did not have the forwarding and masquerading configuration required by this setup.

I enabled both:

```bash
sudo firewall-cmd --zone=libvirt --add-forward --permanent
sudo firewall-cmd --zone=libvirt --add-masquerade --permanent
sudo firewall-cmd --reload
```

This was an important reminder:

> **DNS and Internet connectivity are two different problems.**

A VM can resolve a hostname correctly and still be unable to reach the Internet.

---

# 5. nftables vs iptables

Then I found another layer.

The Fedora host had Docker-related `iptables-nft` rules while libvirt was using native nftables rules.

The NAT rules existed.

But packets weren't behaving the way I expected.

This was one of those situations where looking at a configuration file wasn't enough.

I had to look at the actual networking path.

Eventually, I aligned the firewall backend configuration and restarted the affected infrastructure.

That led to another interesting problem.

---

# 6. The Bridge Lost Its VMs

After cycling the libvirt network, the VMs were still showing as running.

But the bridge had no attached VM interfaces.

I checked:

```bash
ip link show master virbr0
```

Nothing useful was attached.

The important lesson:

> **A VM being "running" does not necessarily mean its network interface is correctly connected.**

The virtual NICs had detached from the bridge.

Restarting the VMs reattached their `vnet` interfaces to `virbr0`.

After that, the network was finally stable.

---

# 7. Preparing the Kubernetes Nodes

Now I could finally start preparing the actual Kubernetes nodes.

Both nodes needed the required kernel modules and networking configuration.

```bash
sudo modprobe overlay
sudo modprobe br_netfilter
```

I also configured:

```text
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1
net.ipv4.ip_forward=1
```

These settings are important for Kubernetes networking.

I also installed and configured **containerd** as the container runtime.

The important containerd configuration was:

```text
SystemdCgroup = true
```

Both nodes were configured consistently.

---

# 8. Fedora's zram Surprise

This was probably my favorite debugging moment.

Kubelet refused to start.

The error was:

```text
running with swap on is not supported
```

But I had already disabled swap.

So I checked:

```bash
swapon --show
```

And found:

```text
NAME       TYPE       SIZE  USED  PRIO
/dev/zram0 partition  3.8G  0B    100
```

Fedora was using **zram as swap**.

So even though traditional swap was disabled, Kubernetes still saw swap enabled.

The source was:

```text
zram-generator
```

The Fedora configuration contained:

```text
[zram0]
zram-size = min(ram, 8192)
```

I created an empty configuration override:

```bash
sudo touch /etc/systemd/zram-generator.conf
```

Then:

```bash
sudo systemctl daemon-reload
sudo swapoff /dev/zram0
sudo zramctl --reset /dev/zram0
```

Finally:

```bash
swapon --show
```

returned nothing.

I restarted kubelet:

```bash
sudo systemctl restart kubelet
```

And this time:

```text
Active: active (running)
```

The lesson:

> **Always check what is actually using a resource, not what you think is using it.**

---

# 9. Initializing the Kubernetes Control Plane

With the infrastructure ready, I initialized the master.

```bash
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --apiserver-advertise-address=192.168.150.75
```

The first attempt wasn't clean.

`kubeadm` reported that several Kubernetes ports were already in use and that Kubernetes manifests and etcd data already existed.

For example:

```text
Port-6443 is in use
Port-10259 is in use
Port-10257 is in use
```

and:

```text
/etc/kubernetes/manifests/kube-apiserver.yaml already exists
```

This meant the node already contained Kubernetes state.

Since this was a lab environment, I reset the node:

```bash
sudo kubeadm reset -f
```

Then I verified that the old manifests and etcd data were gone.

After that, `kubeadm init` completed successfully.

---

# 10. Configuring kubectl

After initialization, `kubectl` needed the Kubernetes configuration.

I copied the admin kubeconfig:

```bash
mkdir -p $HOME/.kube

sudo cp -i /etc/kubernetes/admin.conf \
  $HOME/.kube/config

sudo chown $(id -u):$(id -g) \
  $HOME/.kube/config
```

Before this, `kubectl` was trying to connect to:

```text
localhost:8080
```

which resulted in:

```text
connection refused
```

After configuring kubeconfig, `kubectl` correctly connected to:

```text
https://192.168.150.75:6443
```

---

# 11. Joining the Worker

Next came the worker.

I used the `kubeadm join` command generated by the control plane:

```bash
sudo kubeadm join 192.168.150.75:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

The first attempt failed because I didn't run it as root.

After using `sudo`, kubeadm found another missing dependency:

```text
[ERROR FileExisting-conntrack]:
conntrack not found in system path
```

There were also warnings for `ethtool` and `tc`.

I installed the required tools:

```bash
sudo dnf install -y conntrack-tools ethtool iproute-tc
```

Then I ran the join command again.

This time the worker successfully joined the cluster.

---

# 12. Both Nodes Were NotReady

At this point:

```bash
kubectl get nodes
```

showed:

```text
k8s-master   NotReady
k8s-worker   NotReady
```

This was another important Kubernetes lesson.

The control plane was running.

The worker had joined.

But the cluster wasn't actually ready.

I checked the pods:

```bash
kubectl get pods -A -o wide
```

The control-plane components were running.

But CoreDNS was:

```text
Pending
```

Why?

Because there was no **CNI** yet.

---

# 13. Installing Calico

Kubernetes needed a pod network.

I installed **Calico** as the CNI:

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.1/manifests/calico.yaml
```

After a few minutes:

```bash
kubectl get pods -A
```

showed the Calico components running.

Then CoreDNS moved from:

```text
Pending
```

to:

```text
Running
```

And finally:

```bash
kubectl get nodes
```

gave me:

```text
NAME         STATUS   ROLES
k8s-master   Ready    control-plane
k8s-worker   Ready    <none>
```

The Kubernetes cluster was working.

---

# 14. Giving the Worker an Explicit Role

The worker was already functioning as a worker.

Kubernetes doesn't require the word `worker` to appear in the `ROLES` column.

But for clarity, I added the label:

```bash
kubectl label node k8s-worker \
  node-role.kubernetes.io/worker=
```

Now the cluster looks much clearer:

```text
NAME         STATUS   ROLES
k8s-master   Ready    control-plane
k8s-worker   Ready    worker
```

---

# 🏁 The Final Homelab

The final architecture looks like this:

```text
                         Fedora Laptop
                      16 GB RAM / 144 GB
                              │
                         KVM / libvirt
                              │
                    192.168.150.0/24
                         │          │
                         │          │
                ┌────────▼───┐  ┌───▼─────────┐
                │ k8s-master │  │ k8s-worker  │
                │            │  │             │
                │ 4 GB RAM   │  │ 4 GB RAM    │
                │ 2 vCPU     │  │ 2 vCPU      │
                │ .150.75    │  │ .150.22     │
                └─────┬──────┘  └──────┬──────┘
                      │                │
                      └───────┬────────┘
                              │
                           Calico
                              │
                       Pod Networking
```

And the final verification:

```bash
kubectl get nodes
```

```text
NAME         STATUS   ROLES
k8s-master   Ready    control-plane
k8s-worker   Ready    worker
```

Two nodes.

One control plane.

One worker.

Calico networking.

Both nodes Ready.

And everything running locally.

---

# 🧠 What I Learned

The biggest lesson wasn't a Kubernetes command.

It was learning how many layers sit underneath a Kubernetes cluster.

When kubelet failed, the problem was actually **Fedora's zram**.

When the VMs couldn't access the Internet, the problem wasn't Kubernetes — it was **forwarding and NAT**.

When libvirt networking broke, the problem involved **DNS, firewall configuration and virtual bridges**.

When Kubernetes nodes remained `NotReady`, the problem was the **missing CNI**.

The debugging path looked like this:

```text
VM
 ↓
Linux
 ↓
DNS
 ↓
Firewall
 ↓
NAT
 ↓
Bridge
 ↓
Container Runtime
 ↓
Kubelet
 ↓
kubeadm
 ↓
Control Plane
 ↓
Worker
 ↓
CNI
 ↓
Ready Cluster
```

And that is exactly why I wanted to build this homelab.

Not just to say:

> **"I know Kubernetes."**

But to understand **what makes Kubernetes actually work.**

---

# 🚀 Final Thoughts

I started with a Fedora laptop and two virtual machines.

There was no Kubernetes cluster.

No control plane.

No worker.

No pod network.

Just Linux, virtualization and a lot of troubleshooting.

By the end, I had a working two-node Kubernetes cluster running completely locally.

```text
BUILD
  ↓
BREAK
  ↓
DEBUG
  ↓
UNDERSTAND
  ↓
BUILD BETTER
```

That's the real purpose of a homelab.

> **You don't build it because it's easier than the cloud.**
>
> **You build it because it's yours to break.**

And every time you fix it, you understand a little more about what's happening underneath.

---

**Current status:** Kubernetes foundation complete.

**Cluster:** `k8s-master` + `k8s-worker`

**Runtime:** containerd

**CNI:** Calico

**Kubernetes:** v1.31.14

**Environment:** Local Fedora + KVM/libvirt

**Next step:** Build something on top of it.
