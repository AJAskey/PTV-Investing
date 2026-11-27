#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from optdata import OptData
    from underlying import Underlying


@dataclass
class OptInfo:
    symbol: str
    status: str
    strategy: str
    interval: int
    is_delayed: bool
    is_index: bool
    interest_rate: float
    underlying_price: float
    volatility: int
    days_to_expiration: int
    dividend_yield: float
    number_of_contracts: int
    asset_main_type: str
    asset_sub_type: str
    is_chain_truncated: bool
    eth_option_eligible: bool
    has_binary_options: bool
    underlying: Underlying
    opt_data: List[OptData]
