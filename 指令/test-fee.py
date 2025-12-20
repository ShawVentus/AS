
from bohrium_open_sdk import OpenSDK

# 通过Bohrium平台获取的 AccessKey
access_key="4c97924ea86e4b40b9cf091dcfd20e44"

# 初始化opensdk client
client = OpenSDK(access_key=access_key)

# 获取当前用户信息
user_info = client.user.get_info()

print(user_info)