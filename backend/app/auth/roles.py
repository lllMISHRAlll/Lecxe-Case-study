from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    PROCUREMENT_MANAGER = "procurement_manager"
    BUSINESS_OWNER = "business_owner"
    WAREHOUSE_MANAGER = "warehouse_manager"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()
