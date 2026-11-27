import time, os
from schwab_client import SchwabAPIError, SchwabClient, download_ticker_data
import options_to_excel
import gen_logging, common

logger = gen_logging.setup_logging(logger_name="Get_STOCK_DATA")

with open(f"{common.ptv_path}/Input/stocks-small.txt", "r") as file:
    tickers = [line.strip() for line in file if line.strip()]

client = SchwabClient()

with open(f"{common.subdata_path}/analysis/HP_file.txt", "a+") as high_profit_file:
    high_profit_file.write("PTV-Investing.net \n")
    high_profit_file.write("High-performance option contracts (HP) \n")
    high_profit_file.write(
        "Stocks with ADX > 30 and DI- > DI+, will show only puts.\nStocks with ADX > 30 and DI- < DI+, will show only calls.\n"
    )
    high_profit_file.write("Only profits greater than 200% are shown. \n")

    for ticker in tickers:
        try:
            download_ticker_data(
                ticker,
                client=client,
                include_options=True,  # set False if you only need quote + 250d history for TA-Lib,
                logger=logger,
            )
        except SchwabAPIError as exc:
            print(f"Skipping {ticker}: {exc}")
            continue
        time.sleep(0.5)
        ticker_lc = ticker.lower()
        in_path = f"{common.stockdata_path}/{ticker_lc}_options_chain.json"
        out_path = f"{common.subdata_path}/analysis/{ticker_lc}_options_chain.xlsx"
        logger.info(f"Converting {in_path} to {out_path}...")
        
        call_count, put_count = options_to_excel.convert_options_json_to_excel(
            ticker, in_path, out_path, logger, high_profit_file
        )
        logger.info(
            f"Created {out_path} ({call_count} calls, {put_count} puts, {call_count + put_count} total contracts)."
        )
