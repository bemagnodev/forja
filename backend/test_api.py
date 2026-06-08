import requests
import json

r = requests.post("http://127.0.0.1:8000/api/token", json={"username":"ryanbloureiro", "password":"password"})
print(r.status_code)
