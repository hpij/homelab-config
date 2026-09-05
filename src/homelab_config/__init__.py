"""Read-only access to canonical homelab configuration."""

from .inventory import load_inventory, select_hosts
from .models import Inventory

__all__ = ["Inventory", "load_inventory", "select_hosts"]
__version__ = "0.1.0"
