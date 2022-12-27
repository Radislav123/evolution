import requests


simulation = True

if simulation:
    method = "simulate"
    path = "simulator"
    params = {
        "ticks": 500,
        "width": 120,
        "height": 20,
        "draw": 1,
        "tps": 0
    }
else:
    method = "play"
    path = "player"
    params = {
        "world_db_id": 237,
        "tps": 50
    }

response = requests.request(method, f"http://127.0.0.1:8000/{path}/", params = params)
print(f"{response.status_code}: {response.text}")