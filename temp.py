import requests


simulation = True

if simulation:
    method = "simulate"
    path = "simulator"
    params = {
        "ticks": 120,
        "width": 1000,
        "height": 1000,
        "draw": 1,
        "tps": 15
    }
else:
    method = "play"
    path = "player"
    params = {
        "world_db_id": 4,
        "tps": 15
    }

response = requests.request(method, f"http://127.0.0.1:8000/{path}/", params = params)
print(f"{response.status_code}: {response.text}")
