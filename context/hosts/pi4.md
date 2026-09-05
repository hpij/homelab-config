# pi4

## Purpose

* Provides LAN DNS for the home network.
* Pi-hole and Unbound form the host's DNS stack.

## Network & Exposure

* Intended for LAN-only operation.
* Direct Internet reachability is not expected.
* SSH access within the LAN is intentional.

## Security Baseline

* A host firewall is not required by the current LAN-only threat model.
* Fail2Ban is not required by the current LAN-only threat model.

## Services & Dependencies

* Pi-hole provides DNS service to the LAN.
* Unbound runs locally as the recursive DNS resolver used by Pi-hole.