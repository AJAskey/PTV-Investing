import time, os
from schwab_client import SchwabAPIError, SchwabClient, download_ticker_data
import options_to_excel
import gen_logging

logger = gen_logging.setup_logging(logger_name="Get_STOCK_DATA")
logger.info("test")

with open("Input/stocks.txt", "r") as file:
    tickers = file.read().splitlines()

client = SchwabClient()

os.remove("HP_file.txt")

with open("HP_file.txt", "a+") as high_profit_file:
    high_profit_file.write("Hello, world!")

    for ticker in tickers:

        ticker_lc = ticker.lower()
        in_path = f"data/{ticker_lc}_options_chain.json"
        out_path = f"data/{ticker_lc}_options_chain.xlsx"
        logger.info(f"Converting {in_path} to {out_path}...")
        call_count, put_count = options_to_excel.convert_options_json_to_excel(
            ticker_lc, in_path, out_path, logger, high_profit_file
        )
        logger.info(
            f"Created {out_path} ({call_count} calls, {put_count} puts, {call_count + put_count} total contracts)."
        )
