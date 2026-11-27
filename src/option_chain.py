from typing import List, Optional, Any
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


@dataclass
class OptionDeliverablesList:
    symbol: str
    asset_type: str
    deliverable_units: int
    currency_type: Optional[str] = None


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
    option_deliverables_list: List[OptionDeliverablesList]
    strike_price: int
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


@dataclass
class OptInfo:
    symbol: str
    status: str
    underlying: Underlying
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
    opt_data: List[OptData]
