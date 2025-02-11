import os
import requests
import socket

def check_proxy_settings():
    print("=== Proxy Settings ===")
    
    # Check environment variables
    proxy_vars = {
        'http_proxy': os.environ.get('http_proxy'),
        'https_proxy': os.environ.get('https_proxy'),
        'HTTP_PROXY': os.environ.get('HTTP_PROXY'),
        'HTTPS_PROXY': os.environ.get('HTTPS_PROXY')
    }
    
    print("\nEnvironment Variables:")
    for var, value in proxy_vars.items():
        print(f"{var}: {value}")
    
    # Check requests library proxy
    print("\nRequests Library Settings:")
    print(f"Current Proxies: {requests.utils.get_environ_proxies('https://api.binance.com')}")
    
    # Try to get current IP
    try:
        print("\nCurrent IP:")
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        print(f"Public IP: {response.json()['ip']}")
    except Exception as e:
        print(f"Error getting IP: {e}")

if __name__ == "__main__":
    check_proxy_settings()