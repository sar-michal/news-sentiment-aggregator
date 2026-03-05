import requests

def fetch_gdelt_news():
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": "sourceLang:english",
        "mode": "artlist",
        "format": "json",
        "maxrecords": "50",
        "sort": "datedesc"
    }
    response = requests.get(url=endpoint, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(data, file=open("articles.json", "w"))
        print("saved")
    else: print(f"failed: {response.status_code}" )
fetch_gdelt_news()