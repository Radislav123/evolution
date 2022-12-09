import requests


simulation = False

if simulation:
    method = "simulate"
    path = "simulator"
    params = {
        "ticks": 100,
        "width": 1000,
        "height": 1000,
        "draw": 1,
        "tps": 3
    }
else:
    method = "play"
    path = "player"
    params = {
        "world_db_id": 4,
        "tps": 1
    }

response = requests.request(method, f"http://127.0.0.1:8000/{path}/", params = params)
print(f"{response.status_code}: {response.text}")
