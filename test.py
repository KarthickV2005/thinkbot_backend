import requests

# Endpoint URL
url = "http://127.0.0.1:8000/run-pipeline"

# Example payload (replace with your real values)
payload = {
    "api_key": "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",   # your actual API key
    "file_path": r"S:\ThinkBot-Review2\backend\files\ecommerce.txt"         # path to your test idea file
}

# Send POST request
response = requests.post(url, json=payload)

# Print response
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
