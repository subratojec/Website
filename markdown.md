# Building a Kubernetes Homelab from Scratch on Fedora

> **Build it. Break it. Understand it.**

Managed Kubernetes hides the underlying complexity. To truly understand the infrastructure—what happens when DNS breaks, networking fails, or nodes refuse to join—I built a two-node cluster from scratch on a Fedora laptop. No Minikube, no kind, just raw VMs.

---

## Architecture & Stack

**Goal:** Start with a laptop. End with a real two-node Kubernetes cluster.

```text
                     Fedora Laptop (16GB RAM)
                              │
                         KVM / libvirt
                              │
                    192.168.150.0/24 (Calico CNI)
                         ┌────┴────┐
                k8s-master         k8s-worker
                (4GB, 2vCPU)       (4GB, 2vCPU)
                .150.75            .150.22
```

**Stack:** Fedora Cloud Base, KVM/libvirt, containerd, kubeadm, Calico CNI, Kubernetes v1.31.14.

---

## The Build Process (And What Broke)

### 1. Creating the VMs
Installed KVM on Fedora and provisioned two VMs (`k8s-master` and `k8s-worker`) using cloud-init.
```bash
sudo dnf install @virtualization
```

### 2. Networking & DNS Conflicts
**Problem:** The libvirt network failed to start because AdGuard Home was hogging port `53` on the host. 
**Solution:** Disabled libvirt's built-in DNS (kept DHCP), and configured the VMs to use the host's DNS via `systemd-resolved` overrides in `/etc/systemd/resolved.conf.d/`.

### 3. The Internet Routing Trap
**Problem:** VMs could resolve names, but couldn't reach the internet. DNS != Connectivity. 
**Solution:** The libvirt `firewalld` zone lacked forwarding and NAT. 
```bash
sudo firewall-cmd --zone=libvirt --add-forward --permanent
sudo firewall-cmd --zone=libvirt --add-masquerade --permanent
sudo firewall-cmd --reload
```
*> Note: A Docker installation on the host had misaligned `iptables-nft` rules with libvirt's native nftables, requiring a backend alignment.*

### 4. Ghost Interfaces on the Bridge
**Problem:** After cycling the network, VMs were "running" but `ip link show master virbr0` showed no attached VM interfaces.
**Solution:** Restarted the VMs to reattach their `vnet` interfaces to `virbr0`. Running state doesn't guarantee network attachment.

### 5. Preparing the Nodes
Loaded essential modules and enabled IP forwarding on both VMs.
```bash
sudo modprobe overlay
sudo modprobe br_netfilter
```
```text
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1
net.ipv4.ip_forward=1
```
Configured `containerd` with `SystemdCgroup = true`.

### 6. The Fedora `zram` Surprise
**Problem:** `kubelet` crashed with `running with swap on is not supported`. `swapon --show` revealed Fedora was using `/dev/zram0` as swap, despite traditional swap being disabled.
**Solution:** Disabled `zram-generator`.
```bash
sudo touch /etc/systemd/zram-generator.conf
sudo systemctl daemon-reload
sudo swapoff /dev/zram0
sudo zramctl --reset /dev/zram0
sudo systemctl restart kubelet
```

### 7. Initializing the Control Plane
```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=192.168.150.75
```
Configured `kubectl` to point to the new cluster:
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### 8. Joining the Worker
**Problem:** `kubeadm join` failed due to missing dependencies (`conntrack`, `ethtool`, `tc`).
**Solution:** Installed the missing packages and re-ran the join command.
```bash
sudo dnf install -y conntrack-tools ethtool iproute-tc
```

### 9. Fixing `NotReady` Nodes
**Problem:** Both nodes successfully joined but remained `NotReady`. CoreDNS was stuck in `Pending`.
**Reason:** Kubernetes requires a Container Network Interface (CNI) to function.
**Solution:** Installed Calico.
```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.1/manifests/calico.yaml
```
Once Calico deployed, CoreDNS transitioned to `Running` and the nodes flipped to `Ready`. Labeled the worker for clarity:
```bash
kubectl label node k8s-worker node-role.kubernetes.io/worker=
```

---

## Final Status

```bash
kubectl get nodes
```
```text
NAME         STATUS   ROLES
k8s-master   Ready    control-plane
k8s-worker   Ready    worker
```

### The Takeaway
The debugging path taught me exactly how the Kubernetes layers interact:
`VM → Linux → DNS → Firewall/NAT → Bridge → Runtime → Kubelet → kubeadm → Control Plane → Worker → CNI → Ready Cluster`.

You don't build a homelab because it's easier than the cloud. **You build it because it's yours to break.**
