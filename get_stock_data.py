import time
from schwab_client import SchwabAPIError, SchwabClient, download_ticker_data

import gen_logging

logger = gen_logging.setup_logging(logger_name="Get_STOCK_DATA")
logger.info("test")


with open("data/stocks.txt", "r") as file:
  tickers = file.read().splitlines()


client = SchwabClient()

for ticker in tickers:
    try:
        download_ticker_data(
            ticker,
            client=client,
            include_options=True,  # set False if you only need quote + 250d history for TA-Lib,
            logger=logger
        )
    except SchwabAPIError as exc:
        print(f"Skipping {ticker}: {exc}")
    time.sleep(0.5)