# vps-strato

## Purpose

* Private, single-administrator VPS.
* The only managed host intended to be directly reachable from the public Internet.

## Network & Exposure

* Direct Internet exposure is intentionally limited to SSH on TCP port `22`.
* Web services are exposed through the Docker-managed Cloudflare Tunnel.
* Ordinary web containers must not publish ports on `0.0.0.0` or `[::]`.
* Required Nextcloud AIO loopback bindings on `127.0.0.1` are expected and are not public exposure.

## Security Baseline

* UFW denies incoming traffic by default.
* SSH authentication is key-only.
* SSH root login is disabled.
* SSH password login is disabled.
* Fail2Ban protects SSH.
* The sole administrator is intentionally trusted with sudo and Docker administration.
* Passwordless sudo is an accepted choice for this single-administrator host.

## Services & Dependencies

* Cloudflare Tunnel provides the intended ingress path for web services.
* Nextcloud AIO uses required loopback bindings on `127.0.0.1` as part of its expected architecture.

## Software & Lifecycle Notes

* The preinstalled and unused Snap/LXD environment is accepted on this host.
