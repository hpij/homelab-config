"""Small immutable models for declared homelab configuration."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SelectionError


@dataclass(frozen=True)
class Access:
    access_type: str
    host: str | None = None


@dataclass(frozen=True)
class Operator:
    user: str
    sudo: str


@dataclass(frozen=True)
class Availability:
    mode: str


@dataclass(frozen=True)
class PackageManager:
    capability_id: str


@dataclass(frozen=True)
class RuntimeCapability:
    capability_id: str
    managed_workloads_owner: str | None = None


@dataclass(frozen=True)
class Component:
    capability_id: str


@dataclass(frozen=True)
class Software:
    package_managers: tuple[PackageManager, ...]
    runtimes: tuple[RuntimeCapability, ...]
    components: tuple[Component, ...]


@dataclass(frozen=True)
class HomelabUpdateManagement:
    mechanisms: tuple[str, ...]


@dataclass(frozen=True)
class Management:
    homelab_update: HomelabUpdateManagement | None = None


@dataclass(frozen=True)
class HostContext:
    include: tuple[str, ...] = ()


@dataclass(frozen=True)
class Host:
    host_id: str
    access: Access
    operator: Operator
    availability: Availability | None
    software: Software
    management: Management | None
    context: HostContext

    @property
    def ssh_target(self) -> str | None:
        if self.access.access_type != "ssh" or self.access.host is None:
            return None
        return f"{self.operator.user}@{self.access.host}"


@dataclass(frozen=True)
class Appliance:
    appliance_id: str
    kind: str
    name: str
    access: Access
    user: str

    @property
    def ssh_target(self) -> str | None:
        if self.access.access_type != "ssh" or self.access.host is None:
            return None
        return f"{self.user}@{self.access.host}"


@dataclass(frozen=True)
class Inventory:
    """Canonical membership and loaded records, all in declared index order."""

    hosts: tuple[Host, ...]
    appliances: tuple[Appliance, ...]
    config_root: str

    @property
    def host_ids(self) -> tuple[str, ...]:
        return tuple(host.host_id for host in self.hosts)

    @property
    def appliance_ids(self) -> tuple[str, ...]:
        return tuple(appliance.appliance_id for appliance in self.appliances)

    def host(self, host_id: str) -> Host:
        for host in self.hosts:
            if host.host_id == host_id:
                return host
        raise SelectionError(f"unknown canonical host ID: {host_id}")

    def appliance(self, appliance_id: str) -> Appliance:
        for appliance in self.appliances:
            if appliance.appliance_id == appliance_id:
                return appliance
        raise SelectionError(f"unknown canonical appliance ID: {appliance_id}")
