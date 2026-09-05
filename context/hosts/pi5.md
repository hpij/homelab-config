# pi5

## Purpose

* Provides storage and supporting services for the home network.
* Hosts services used for file storage, monitoring, and Transmission peer traffic.

## Network & Exposure

* Services are intended primarily for the home network.
* The router intentionally forwards UDP port `51414` to the non-VPN Transmission service for peer traffic.
* The intentional UDP `51414` forwarding alone is not configuration drift.

## Security Baseline

* A host firewall is not required by the current home-network threat model.
* Fail2Ban is not required by the current home-network threat model.

## Services & Dependencies

* Samba provides LAN file storage.
* InfluxDB supports monitoring workloads.
* Pironman5 supports host and case monitoring.

## Storage & Mounts

The following storage mounts are expected:

* `/mnt/USBSSD_Crucial_2TB`
* `/mnt/USBSSD_Kingston_500GB`
* `/mnt/NVME_ADATA_1TB`

* Confirm required mounts before performing storage-dependent operations.
