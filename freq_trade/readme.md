docker compose down

docker compose up -d

docker compose run --rm freqtrade-trade backtesting --config user_data/config_backtest.json --strategy MeanReversionStrategy --timeframe 20250110-20250201 -i 3m 


docker compose run --rm freqtrade-trade download-data  --timerange 20241101-20241201 --timeframe 3m --prepend