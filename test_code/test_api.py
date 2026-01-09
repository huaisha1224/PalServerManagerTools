import requests

url = "http://127.0.0.1:8212/v1/api/info"

payload={}
headers = {
  'Authorization': 'Basic dXNlcm5hbWU6MTIzNDU2'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)