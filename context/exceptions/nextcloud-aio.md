# Nextcloud AIO exception

The official Nextcloud All-in-One deployment on `vps-strato` is intentionally not managed by
`homelab-docker`. Its mastercontainer manages the sibling AIO containers through the Docker socket;
those siblings must not be managed or updated independently.

The `nextcloud-aio-mastercontainer` and `nextcloud-aio-nextcloud` containers start as root by
upstream design, so root inside either container alone is not a security finding. The
`nextcloud-aio-watchtower` update helper may normally be in `Exited (0)` state. Nextcloud is
exposed through the host's Cloudflare Tunnel and reverse-proxy architecture.

Security logging is intended to preserve the real client address when proxy forwarding is
resolved correctly. A private Docker address in Nextcloud's `remoteAddr` is an internal network
hop, not necessarily the originating Internet client; the origin cannot be attributed from that
record alone.

Relevant deviations include unexpected Docker socket mounts, unexpected privileges or
capabilities, public exposure of the AIO management interface, or configuration materially outside
the supported AIO architecture.

