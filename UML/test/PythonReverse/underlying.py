#!/usr/bin/python
# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass
class Underlying:
    symbol: str
    description: str
    change: float
    percent_change: float
    close: float
    quote_time: int
    trade_time: int
    bid: float
    ask: float
    last: float
    mark: float
    mark_change: float
    mark_percent_change: float
    bid_size: int
    ask_size: int
    high_price: float
    low_price: float
    open_price: float
    total_volume: int
    exchange_name: str
    fifty_two_week_high: float
    fifty_two_week_low: float
    delayed: bool
