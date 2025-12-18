import requests
import random

def get_google_images(query, api_key, cse_id):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'cx': cse_id,
        'key': api_key,
        'searchType': 'image',
        'num': 10,
        'safe': 'active'
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return [item['link'] for item in data.get('items', [])]
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []
      
