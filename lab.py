import requests


print(requests.post('http://localhost:8082/', json={'image': '...'}))