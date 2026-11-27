#!/usr/bin/python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Optional


@dataclass
class OptionDeliverablesList:
    symbol: str
    asset_type: str
    deliverable_units: int
    currency_type: Optional[str] = None
