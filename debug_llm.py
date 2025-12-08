import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("ACCESS_KEY")
base_url = "https://openapi.dp.tech/openapi/v1"

print(f"API Key: {api_key[:5]}...")
print(f"Base URL: {base_url}")

client = OpenAI(
    api_key="",
    base_url=base_url,
)

try:
    print("Sending request...")
    completion = client.chat.completions.create(
        model="qwen3-max",
        messages=[
            {"role": "user", "content": "Hello, say hi in json format."}
        ],
        temperature=1,
        response_format={"type": "json_object"}
    )
    
    print(f"Type of completion: {type(completion)}")
    print(f"Completion: {completion}")
    
    if hasattr(completion, 'choices'):
        print("Has choices attribute.")
        print(completion.choices[0].message.content)
    else:
        print("No choices attribute.")

except Exception as e:
    print(f"Error: {e}")
