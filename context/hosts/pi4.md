# pi4

This Raspberry Pi is LAN-only and must not be directly reachable from the Internet. SSH is
intentionally available within the LAN. A host firewall and Fail2Ban are not required by the
current LAN-only threat model.

Pi-hole provides LAN DNS. Unbound on localhost provides recursive DNS for Pi-hole; both are native
services on this host.

