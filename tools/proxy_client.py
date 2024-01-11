import sys
import requests
from datetime import datetime
import time

base_url = 'http://localhost:27872'

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        print(f"Function '{func.__name__}' executed in {duration_ms:.2f} ms")
        return result
    return wrapper

def do_proxy_request(thepath, thebody={}):
    url = f"{base_url}/proxy"
    headers = {'Content-Type': 'application/json'}

    # Get the current time in ISO 8601 format
    current_time = datetime.now().isoformat()

    # Example of hardcoded request data with the current time
    data = {
        "created_at": current_time,
        "method": "GET",
        "path": thepath,
        "body": thebody,
    }

    response = requests.post(url, json=data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

@timeit
def request_healthcheck():
    do_proxy_request('/api/healthcheck')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python proxy_cilent.py healthcheck")
        sys.exit(1)

    request_name = sys.argv[1]

    if request_name == 'healthcheck':
        request_healthcheck()
