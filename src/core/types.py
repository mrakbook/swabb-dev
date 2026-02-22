from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ResourceRecord:
    type: str                   # 'ebs' | 'eip' | ...
    id: str
    region: str
    account: str
    name: Optional[str] = None
    created_at: Optional[str] = None
    age_days: Optional[int] = None
    reason: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    est_monthly_cost: Optional[float] = None
    delete_action: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)  # extra per-type attrs
