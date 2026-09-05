# pi5

This Raspberry Pi serves the home network. Samba provides LAN file storage, while InfluxDB and
Pironman5 support host and case monitoring. A host firewall and Fail2Ban are not required by the
current home-network threat model.

The required storage mounts are:

- `/mnt/USBSSD_Crucial_2TB`
- `/mnt/USBSSD_Kingston_500GB`
- `/mnt/NVME_ADATA_1TB`

Confirm required mounts before storage-dependent operations.

Services are intended for the home network. The router intentionally forwards UDP port 51414 to
the non-VPN Transmission service for peer traffic; that forwarding alone is not drift.

