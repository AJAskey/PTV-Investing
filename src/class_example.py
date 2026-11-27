import json
from typing import Any, Dict, List
from option_chain import OptInfo, Underlying, OptData, OptionDeliverablesList


def parse_underlying(data: Dict[str, Any]) -> Underlying:
    return Underlying(
        symbol=data["symbol"],
        description=data["description"],
        change=data["change"],
        percent_change=data["percentChange"],
        close=data["close"],
        quote_time=data["quoteTime"],
        trade_time=data["tradeTime"],
        bid=data["bid"],
        ask=data["ask"],
        last=data["last"],
        mark=data["mark"],
        mark_change=data["markChange"],
        mark_percent_change=data["markPercentChange"],
        bid_size=data["bidSize"],
        ask_size=data["askSize"],
        high_price=data["highPrice"],
        low_price=data["lowPrice"],
        open_price=data["openPrice"],
        total_volume=data["totalVolume"],
        exchange_name=data["exchangeName"],
        fifty_two_week_high=data["fiftyTwoWeekHigh"],
        fifty_two_week_low=data["fiftyTwoWeekLow"],
        delayed=data["delayed"],
    )


def parse_deliverable(data: Dict[str, Any]) -> OptionDeliverablesList:
    return OptionDeliverablesList(
        symbol=data["symbol"],
        asset_type=data["assetType"],
        deliverable_units=data["deliverableUnits"],
        currency_type=data.get("currencyType"),
    )


def parse_opt_data(exp_key: str, data: Dict[str, Any]) -> OptData:
    deliverables = [
        parse_deliverable(d) for d in data.get("optionDeliverablesList", [])
    ]
    return OptData(
        expiratqion_date=exp_key,  # map key e.g. "2026-12-18:24"
        put_call=data["putCall"],
        symbol=data["symbol"],
        description=data["description"],
        exchange_name=data["exchangeName"],
        bid=data["bid"],
        ask=data["ask"],
        last=data["last"],
        mark=data["mark"],
        bid_size=data["bidSize"],
        ask_size=data["askSize"],
        bid_ask_size=data["bidAskSize"],
        last_size=data["lastSize"],
        high_price=data["highPrice"],
        low_price=data["lowPrice"],
        open_price=data["openPrice"],
        close_price=data["closePrice"],
        total_volume=data["totalVolume"],
        trade_time_in_long=data["tradeTimeInLong"],
        quote_time_in_long=data["quoteTimeInLong"],
        net_change=data["netChange"],
        volatility=data["volatility"],
        delta=data["delta"],
        gamma=data["gamma"],
        theta=data["theta"],
        vega=data["vega"],
        rho=data["rho"],
        open_interest=data["openInterest"],
        time_value=data["timeValue"],
        theoretical_option_value=data["theoreticalOptionValue"],
        theoretical_volatility=data["theoreticalVolatility"],
        option_deliverables_list=deliverables,
        strike_price=data["strikePrice"],
        expiration_date=data["expirationDate"],
        days_to_expiration=data["daysToExpiration"],
        expiration_type=data["expirationType"],
        last_trading_day=data["lastTradingDay"],
        multiplier=data["multiplier"],
        settlement_type=data["settlementType"],
        deliverable_note=data["deliverableNote"],
        percent_change=data["percentChange"],
        mark_change=data["markChange"],
        mark_percent_change=data["markPercentChange"],
        intrinsic_value=data["intrinsicValue"],
        extrinsic_value=data["extrinsicValue"],
        option_root=data["optionRoot"],
        exercise_type=data["exerciseType"],
        high52_week=data["high52Week"],
        low52_week=data["low52Week"],
        break_even=data["breakEven"],
        ssid=data["ssid"],
        in_the_money=data["inTheMoney"],
        non_standard=data["nonStandard"],
        mini=data["mini"],
        penny_pilot=data["pennyPilot"],
    )


def load_option_chain(json_data: Dict[str, Any]) -> OptInfo:
    opt_data_list: List[OptData] = []

    # Flatten both callExpDateMap and putExpDateMap into opt_data
    for map_name in ("callExpDateMap", "putExpDateMap"):
        exp_map = json_data.get(map_name, {})
        for exp_key, strikes_map in exp_map.items():
            for _strike_str, contracts in strikes_map.items():
                for contract in contracts:
                    opt_data_list.append(parse_opt_data(exp_key, contract))

    return OptInfo(
        symbol=json_data["symbol"],
        status=json_data["status"],
        underlying=parse_underlying(json_data["underlying"]),
        strategy=json_data["strategy"],
        interval=json_data["interval"],
        is_delayed=json_data["isDelayed"],
        is_index=json_data["isIndex"],
        interest_rate=json_data["interestRate"],
        underlying_price=json_data["underlyingPrice"],
        volatility=json_data["volatility"],
        days_to_expiration=json_data["daysToExpiration"],
        dividend_yield=json_data["dividendYield"],
        number_of_contracts=json_data["numberOfContracts"],
        asset_main_type=json_data["assetMainType"],
        asset_sub_type=json_data["assetSubType"],
        is_chain_truncated=json_data["isChainTruncated"],
        eth_option_eligible=json_data["ethOptionEligible"],
        has_binary_options=json_data["hasBinaryOptions"],
        opt_data=opt_data_list,
    )


if __name__ == "__main__":
    with open("data/mu_options_chain.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    chain = load_option_chain(raw)
    print(f"{chain.symbol}: loaded {len(chain.opt_data)} contracts")
    print("First contract:", chain.opt_data[0].symbol, chain.opt_data[0].strike_price)