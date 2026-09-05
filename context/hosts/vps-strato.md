# vps-strato

This private, single-administrator VPS is the only managed host intended to be directly reachable
from the public Internet.

UFW denies incoming traffic by default. Only SSH on TCP port 22 may be directly Internet-reachable;
SSH is key-only, root and password login are disabled, and Fail2Ban protects SSH. Web services are
exposed through the Docker-managed Cloudflare Tunnel. Web containers must not publish ports on
`0.0.0.0` or `[::]`; required Nextcloud AIO loopback bindings on `127.0.0.1` are expected.

The sole administrator is intentionally trusted with sudo and Docker administration. Passwordless
sudo is an accepted choice for this single-admin host. Preinstalled LXD from the Snap ecosystem is
accepted; unused LXD is not drift. This accepted capability is distinct from the mechanisms that
the central updater currently manages.

