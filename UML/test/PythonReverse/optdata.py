#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from optiondeliverableslist import OptionDeliverablesList


@dataclass
class OptData:
    expiratqion_date: str
    strike_price: float
    put_call: str
    symbol: str
    description: str
    exchange_name: str
    bid: float
    ask: float
    last: float
    mark: int
    bid_size: int
    ask_size: int
    bid_ask_size: str
    last_size: int
    high_price: float
    low_price: float
    open_price: float
    close_price: float
    total_volume: int
    trade_time_in_long: int
    quote_time_in_long: int
    net_change: float
    volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    open_interest: int
    time_value: float
    theoretical_option_value: float
    theoretical_volatility: int
    expiration_date: str
    days_to_expiration: int
    expiration_type: str
    last_trading_day: int
    multiplier: int
    settlement_type: str
    deliverable_note: str
    percent_change: float
    mark_change: float
    mark_percent_change: float
    intrinsic_value: float
    extrinsic_value: float
    option_root: str
    exercise_type: str
    high52_week: float
    low52_week: float
    break_even: int
    ssid: int
    in_the_money: bool
    non_standard: bool
    mini: bool
    penny_pilot: bool
    option_deliverables_list: List[OptionDeliverablesList]
