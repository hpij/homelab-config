# yip-i3wm

## Purpose

* Personal desktop and local homelab controller.
* Provides several LAN-facing services in addition to its desktop role.
* Runs occasional local virtual machines through libvirt/KVM.

## Network & Exposure

* Intended for LAN-only operation.
* Direct Internet traffic to the host is not expected.
* An SSH server is not required by the current operating model.

## Security Baseline

* A host firewall is not required by the current threat model.
* Fail2Ban is not required by the current threat model.

## Services & Dependencies

* Samba provides LAN file sharing.
* Ollama provides an LLM API to the LAN.
* Sendspin provides Music Assistant audio output.
* libvirt/KVM provides local virtual-machine capability.

## Storage & Mounts

The following storage mounts are expected:

* `TMP`
* `VMs`
* `DATA16`
* `DATA8`

* Confirm required mounts before performing storage-dependent operations.

## Software & Lifecycle Notes

* Software may intentionally come from different sources such as APT, Snap, Flatpak, AppImage, source builds, Git checkouts.
* Duplicate installations of the same application across those package managers are configuration drift.

