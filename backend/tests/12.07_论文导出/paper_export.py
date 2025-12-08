import requests

url = "http://localhost:8000/api/v1/papers/export"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <YOUR_TOKEN>" # 如果开启了认证
}
payload = {
    "date_start": "2025-12-07",
    "date_end": "2025-12-07",
    "limit": 10,
    "format": "markdown" # 或 "json"
}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 200:
    print(response.text) # Markdown 内容或 JSON 字符串
else:
    print(f"Error: {response.status_code}, {response.text}")