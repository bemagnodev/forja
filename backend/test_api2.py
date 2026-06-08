import requests

urls = ["http://127.0.0.1:8000/api/users/me", "http://127.0.0.1:8000/api/users/me/"]
for u in urls:
    print(f"Testing {u}")
    r = requests.get(u)
    print(r.status_code)
    try:
        print(r.json())
    except:
        print(r.text[:100])
