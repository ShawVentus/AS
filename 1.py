import os
from openai import OpenAI

# 把 base_url 指向根域（非 /chat/completions），OpenAI SDK 会自己拼接路径
BASE_URL = "https://openapi.dp.tech/openapi/v1" 
API_KEY  = os.getenv("ACCESS_KEY") or "4c97924ea86e4b40b9cf091dcfd20e44"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat_non_stream(messages, model="qwen3-max"):
    """非流式对话：一次性返回完整结果"""
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False,
    )
    print(resp)
    # print(resp.choices[0].message.content)

# def chat_stream(messages, model="qwen3-max"):
#     """流式对话：逐块返回"""
#     stream = client.chat.completions.create(
#         model=model,
#         messages=messages,
#         stream=True,
#     )
#     for chunk in stream:
#         if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
#             print(chunk.choices[0].delta.content, end="", flush=True)
#     print()  # 换行

if __name__ == "__main__":
    msgs = [{"role": "user", "content": "你是什么模型?"}]
    print("=== 非流式 ===")
    chat_non_stream(msgs, "qwen-plus")
    # print("\n=== 流式 ===")
    # chat_stream(msgs, "qwen-plus")