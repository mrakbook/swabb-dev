from __future__ import annotations

from typing import Dict

from .scanners.ebs import EbsScanner
from .scanners.eip import EipScanner

SCANNERS: Dict[str, object] = {
    "ebs": EbsScanner(),
    "eip": EipScanner(),
}

def list_supported() -> list[str]:
    return sorted(SCANNERS.keys())

def get(name: str):
    return SCANNERS[name]
