import requests
import json  

def fetch_codeforces_data(handle):
    api_url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=5"
    
    response = requests.get(api_url)
    json_data = response.json()
    
     
    print(json.dumps(json_data, indent=4, sort_keys=True))

if __name__ == "__main__":
    user_handle = "bemagno"
    fetch_codeforces_data(user_handle)