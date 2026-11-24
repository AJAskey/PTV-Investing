"""Convert a Schwab options chain JSON file into a formatted Excel workbook."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

from options_bs_calculator import calculate_option_price

import logging

SCENARIO_SPECS: list[tuple[int, float]] = [
    (30, 0.15),
    (90, 0.30),
    (180, 0.50),
]

COLUMNS: list[tuple[str, str, str]] = [
    ("Expiration", "expiration_date", "@"),
    ("DTE", "daysToExpiration", "#,##0"),
    ("Type", "putCall", "@"),
    ("Strike", "strikePrice", "$#,##0.00"),
    ("Contract Symbol", "symbol", "@"),
    ("Bid", "bid", "$#,##0.00"),
    ("Ask", "ask", "$#,##0.00"),
    ("Last", "last", "$#,##0.00"),
    ("Mark", "mark", "$#,##0.00"),
    ("Bid/Ask Size", "bidAskSize", "@"),
    ("Volume", "totalVolume", "#,##0"),
    ("Open Interest", "openInterest", "#,##0"),
    ("IV (%)", "volatility", "0.000"),
    ("Delta", "delta", "0.000"),
    ("Gamma", "gamma", "0.000"),
    ("Theta", "theta", "0.000"),
    ("Vega", "vega", "0.000"),
    ("Rho", "rho", "0.000"),
    ("ITM", "inTheMoney", "@"),
    ("Intrinsic", "intrinsicValue", "$#,##0.00"),
    ("Extrinsic", "extrinsicValue", "$#,##0.00"),
    ("Break Even", "breakEven", "$#,##0.00"),
    ("Net Change", "netChange", "+$#,##0.00;-$#,##0.00;$0.00"),
    ("Change (%)", "percentChange", "0.00"),
    ("High", "highPrice", "$#,##0.00"),
    ("Low", "lowPrice", "$#,##0.00"),
    ("52W High", "high52Week", "$#,##0.00"),
    ("52W Low", "low52Week", "$#,##0.00"),
    ("Exp Type", "expirationType", "@"),
]


def _flatten_exp_map(exp_map: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for exp_key, strikes in exp_map.items():
        exp_date = exp_key.split(":", 1)[0]
        for contracts in strikes.values():
            for contract in contracts:
                rows.append(
                    {
                        **contract,
                        "expiration_date": exp_date,
                        "symbol": str(contract.get("symbol", "")).strip(),
                    }
                )
    return rows


def extract_contracts(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return sorted (calls, puts) contract lists from a Schwab options chain payload."""
    calls = _flatten_exp_map(payload.get("callExpDateMap", {}))
    puts = _flatten_exp_map(payload.get("putExpDateMap", {}))
    sort_key = lambda c: (
        c.get("expiration_date", ""),
        float(c.get("strikePrice") or 0.0),
        c.get("putCall", ""),
    )
    calls.sort(key=sort_key)
    puts.sort(key=sort_key)
    return calls, puts


def _write_summary_sheet(
    ws: Worksheet,
    payload: dict[str, Any],
    calls: list[dict[str, Any]],
    puts: list[dict[str, Any]],
) -> None:
    underlying = payload.get("underlying") or {}
    rows = [
        ("Symbol", payload.get("symbol", underlying.get("symbol", ""))),
        ("Description", underlying.get("description", "")),
        ("Exchange", underlying.get("exchangeName", "")),
        ("Underlying Price", payload.get("underlyingPrice", underlying.get("last"))),
        ("Bid / Ask", f"{underlying.get('bid')} / {underlying.get('ask')}"),
        ("Net Change", underlying.get("change")),
        ("Percent Change (%)", underlying.get("percentChange")),
        (
            "Day Low / High",
            f"{underlying.get('lowPrice')} - {underlying.get('highPrice')}",
        ),
        (
            "52W Low / High",
            f"{underlying.get('fiftyTwoWeekLow')} - {underlying.get('fiftyTwoWeekHigh')}",
        ),
        ("Total Volume", underlying.get("totalVolume")),
        ("Interest Rate (%)", payload.get("interestRate")),
        ("Dividend Yield (%)", payload.get("dividendYield")),
        ("Chain Volatility", payload.get("volatility")),
        ("Total Contracts", len(calls) + len(puts)),
        ("Call Contracts", len(calls)),
        ("Put Contracts", len(puts)),
        ("Status", payload.get("status", "")),
        ("Date", date.today()),
    ]

    ws.append(["Field", "Value"])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            start_color="1F4E78", end_color="1F4E78", fill_type="solid"
        )

    for label, value in rows:
        ws.append([label, value])

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(horizontal="left")

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 36


def _write_options_table(
    ws: Worksheet,
    table_name: str,
    contracts: list[dict[str, Any]],
    min_open_interest: int = 100,
) -> None:
    headers = [col[0] for col in COLUMNS]
    ws.append(headers)

    eligible = [
        c for c in contracts if (c.get("openInterest") or 0) > min_open_interest
    ]
    for contract in eligible:
        row_values: list[Any] = []
        for _, key, _ in COLUMNS:
            val = contract.get(key)
            if key == "inTheMoney" and isinstance(val, bool):
                val = "YES" if val else "NO"
            row_values.append(val)
        ws.append(row_values)

    last_col = get_column_letter(len(COLUMNS))
    last_row = max(2, len(eligible) + 1)
    table = Table(displayName=table_name, ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(table)
    ws.freeze_panes = "H2"

    for col_idx, (header, _, num_fmt) in enumerate(COLUMNS, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header)
        for row_idx in range(2, len(eligible) + 2):
            cell = ws.cell(row=row_idx, column=col_idx)
            if num_fmt != "@":
                cell.number_format = num_fmt
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, 28)


def _write_scenarios_sheet(
    ws: Worksheet,
    table_name: str,
    contracts: list[dict[str, Any]],
    payload: dict[str, Any],
    option_type: str,
    min_dte: int = 30,
    min_open_interest: int = 100,
    logger: Any = None,
    high_profit_file: Any = None,
) -> None:
    """Write a Black-Scholes scenario projection sheet for contracts with DTE >= min_dte and openInterest > min_open_interest."""
    ws.sheet_properties.tabColor = "FFFF00"

    logger.info(
        f"aja  Writing scenarios sheet for {option_type} contracts with DTE >= {min_dte} and openInterest > {min_open_interest}"
    )

    opt = option_type.lower()
    sign = "+" if opt == "call" else "-"
    underlying = payload.get("underlying") or {}
    ul_price = float(payload.get("underlyingPrice") or underlying.get("last") or 0.0)
    r = float(payload.get("interestRate") or 0.0) / 100.0
    q = float(payload.get("dividendYield") or 0.0) / 100.0
    iv = float(payload.get("volatility") or 0.0) 
    open_date = date.today()
    
    logger.info(
        f"aja  Underlying price: {ul_price}, interest rate: {r:.4%}, dividend yield: {q:.4%}, volatility: {iv:.2f}%"
    )

    headers: list[tuple[str, str]] = [
        ("Open Date", "yyyy-mm-dd"),
        ("Expiration", "yyyy-mm-dd"),
        ("DTE", "#,##0"),
        ("Type", "@"),
        ("Break Even", "$#,##0.00"),
        ("UL Price", "$#,##0.00"),
        ("Strike", "$#,##0.00"),
        ("Mark (Buy Price)", "$#,##0.00"),
        ("IV (%)", "0.000"),
    ]
    for days_out, _ in SCENARIO_SPECS:
        headers.append((f"Sell Date {days_out}D", "yyyy-mm-dd"))
    for days_out, _ in SCENARIO_SPECS:
        headers.append((f"Sell DTE {days_out}D", "#,##0"))
    for days_out, move in SCENARIO_SPECS:
        headers.append((f"Sell UL {sign}{int(move * 100)}% {days_out}D", "$#,##0.00"))
    for days_out, move in SCENARIO_SPECS:
        headers.append(
            (f"Sell Price {sign}{int(move * 100)}% {days_out}D", "$#,##0.00")
        )
    for days_out, move in SCENARIO_SPECS:
        headers.append(
            (
                f"Profit {sign}{int(move * 100)}% {days_out}D",
                "+$#,##0.00;-$#,##0.00;$0.00",
            )
        )

    headers.append(("Chg 15p", "+0.00%;-0.00%;0.00%"))
    headers.append(("Chg 30p", "+0.00%;-0.00%;0.00%"))
    headers.append(("Chg 50p", "+0.00%;-0.00%;0.00%"))

    ws.append([h[0] for h in headers])

    eligible = [
        c
        for c in contracts
        if (c.get("daysToExpiration") or 0) >= min_dte
        and (c.get("openInterest") or 0) > min_open_interest
        and (iv < 100.0)
    ]
    logger.info(
        f"aja 263 Found {len(eligible)} eligible {option_type} contracts with DTE >= {min_dte} and openInterest > {min_open_interest} and IV: {iv}")
    

    for contract in eligible:
        exp_date = date.fromisoformat(contract["expiration_date"])
        dte = contract.get("daysToExpiration")
        break_even_val = contract.get("breakEven")
        break_even = float(break_even_val) if break_even_val is not None else None
        strike = float(contract.get("strikePrice") or 0.0)
        mark_val = (
            contract.get("mark")
            if contract.get("mark") is not None
            else contract.get("last")
        )
        mark = float(mark_val) if mark_val is not None else None
        iv_pct = contract.get("volatility")

        sell_dates: list[date] = []
        sell_dtes: list[int | None] = []
        sell_uls: list[float] = []
        sell_prices: list[float | None] = []
        profits: list[float | None] = []
        profit_pcts: list[float | None] = []

        for days_out, move in SCENARIO_SPECS:
            sell_date = open_date + timedelta(days=days_out)
            sell_dte = (exp_date - sell_date).days
            mult = (1.0 + move) if opt == "call" else (1.0 - move)
            target_ul = ul_price * mult

            sell_dates.append(sell_date)
            sell_uls.append(target_ul)

            if (
                sell_dte > 0
                and ul_price > 0
                and strike > 0
                and iv_pct is not None
                and float(iv_pct) >= 0
            ):
                ivm = iv_pct / 100.0
                """ Assume longer-dated options are going in the direction desired, 
                   and IV is increasing as time goes on. 
                """
                if sell_dte > 60:
                    ivm = ivm * 1.25
                elif sell_dte > 100:
                    ivm = ivm * 1.5

                proj_price = calculate_option_price(
                    S=target_ul,
                    K=strike,
                    DTE=sell_dte,
                    r=r,
                    iv=ivm,
                    option_type=opt,
                    q=q,
                    logger=logger,
                )
                profit = (proj_price - mark) if mark is not None else None
                profit_pct = (
                    (profit / mark)
                    if (profit is not None and mark is not None and mark > 0)
                    else None
                )
                sell_dtes.append(sell_dte)
                sell_prices.append(proj_price)
                profits.append(profit)
                profit_pcts.append(profit_pct)

                if profit_pct is not None and profit_pct > 1.5:
                    if logger:
                        logger.info(
                            f"High profit percentage for {contract.get('symbol')} : {exp_date} : {strike} : {profit_pct:.2%}"
                        )
                    if high_profit_file:
                        high_profit_file.write(
                            f"{contract.get('symbol')} : {exp_date} : {strike} : {profit_pct:.2%}\n"
                        )

            else:
                sell_dtes.append(None)
                sell_prices.append(None)
                profits.append(None)
                profit_pcts.append(None)

        ws.append(
            [
                open_date,
                exp_date,
                dte,
                contract.get("putCall", opt.upper()),
                break_even,
                ul_price,
                strike,
                mark,
                float(iv_pct) if iv_pct is not None else None,
                *sell_dates,
                *sell_dtes,
                *sell_uls,
                *sell_prices,
                *profits,
                *profit_pcts,
            ]
        )

    last_col = get_column_letter(len(headers))
    last_row = max(2, len(eligible) + 1)
    table = Table(displayName=table_name, ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(table)
    ws.freeze_panes = "H2"

    for col_idx, (header, num_fmt) in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header)
        for row_idx in range(2, len(eligible) + 2):
            cell = ws.cell(row=row_idx, column=col_idx)
            if num_fmt != "@":
                cell.number_format = num_fmt
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, 24)


def convert_options_json_to_excel(
    input_path: str | Path,
    output_path: str | Path,
    logger: logging.Logger | None = None,
    high_profit_file: TextIO | None = None,
) -> tuple[int, int]:
    """Read a Schwab options chain JSON file and write a formatted Excel workbook."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    calls, puts = extract_contracts(payload)
    all_contracts = sorted(
        calls + puts,
        key=lambda c: (
            c.get("expiration_date", ""),
            float(c.get("strikePrice") or 0.0),
            c.get("putCall", ""),
        ),
    )

    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = "Summary"
    _write_summary_sheet(summary_ws, payload, calls, puts)

    all_ws = wb.create_sheet("All Options")
    _write_options_table(all_ws, "AllOptionsTable", all_contracts)

    calls_ws = wb.create_sheet("Calls")
    _write_options_table(calls_ws, "CallsTable", calls)

    puts_ws = wb.create_sheet("Puts")
    _write_options_table(puts_ws, "PutsTable", puts)

    call_scenarios_ws = wb.create_sheet("Call Scenarios")
    _write_scenarios_sheet(
        call_scenarios_ws,
        "CallScenariosTable",
        calls,
        payload,
        "call",
        logger=logger,
        high_profit_file=high_profit_file,
    )

    put_scenarios_ws = wb.create_sheet("Put Scenarios")
    _write_scenarios_sheet(
        put_scenarios_ws,
        "PutScenariosTable",
        puts,
        payload,
        "put",
        logger=logger,
        high_profit_file=high_profit_file,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return len(calls), len(puts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Schwab options chain JSON file to an Excel workbook."
    )
    parser.add_argument(
        "input_json",
        nargs="?",
        default="data/nvda_options_chain.json",
        help="Path to the Schwab options chain JSON file (default: data/nvda_options_chain.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .xlsx path (default: same name as input with .xlsx extension)",
    )
    args = parser.parse_args()

    in_path = Path(args.input_json)
    if not in_path.exists():
        raise FileNotFoundError(f"Input JSON file not found: {in_path}")

    out_path = Path(args.output) if args.output else in_path.with_suffix(".xlsx")
    call_count, put_count = convert_options_json_to_excel(in_path, out_path)
    print(
        f"Created {out_path} ({call_count} calls, {put_count} puts, {call_count + put_count} total contracts)."
    )


if __name__ == "__main__":
    main()
