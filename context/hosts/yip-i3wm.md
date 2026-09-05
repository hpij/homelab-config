# yip-i3wm

This personal desktop is the local homelab controller. It is LAN-only and is not intended to
accept direct Internet traffic. An SSH server, host firewall, and Fail2Ban are not required by the
current threat model.

Samba provides LAN file sharing, Ollama provides an LLM API to the LAN, and Sendspin provides
Music Assistant audio output. libvirt/KVM is used for occasional local virtual machines.

Expected storage mounts are `TMP`, `VMs`, `DATA16`, and `DATA8`. Confirm required mounts before
storage-dependent operations.

An application should exist in only one of APT, Snap, or Flatpak. Duplicate installations across
those package managers are configuration drift.

