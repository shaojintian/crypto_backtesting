import ccxt
import json
from datetime import datetime

def test_binance_connection():
    try:
        # Load API credentials
        with open('user_data/config.json') as f:
            config = json.load(f)
        
        # Initialize Binance Futures client
        exchange = ccxt.binanceusdm({
            'apiKey': config['exchange']['key'],
            'secret': config['exchange']['secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        # Test API Connection
        print("Testing API Connection...")
        balance = exchange.fetch_balance()
        print(f"Connection successful! USDT Balance: {balance['USDT']['free']}")
        
        # Test Futures Access
        print("\nTesting Futures Access...")
        positions = exchange.fetch_positions()
        print("Futures access OK!")
        
        # Test Margin Mode
        print("\nTesting Margin Mode Setting...")
        symbol = "BTC/USDT:USDT"
        exchange.set_margin_mode('isolated', symbol=symbol)
        print("Margin mode setting OK!")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_binance_connection()