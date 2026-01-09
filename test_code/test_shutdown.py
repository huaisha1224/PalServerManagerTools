import sys
import os
import requests
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.palrestapi import PalRestAPI

def test_shutdown_server():
    """测试关闭服务器方法"""
    print("=== 测试关闭服务器方法 ===")
    
    # 服务器信息
    host = "127.0.0.1"
    port = 8212
    username = "admin"
    password = "123456"
    
    # 直接使用requests测试不同的参数格式
    print("\n1. 使用requests直接测试shutdown API：")
    url = f"http://{host}:{port}/v1/api/shutdown"
    auth = (username, password)
    headers = {"Content-Type": "application/json"}
    
    # 测试不同的参数格式
    test_cases = [
        # 当前使用的格式
        ({"seconds": 1, "message": "Server shutting down"}, "格式1: {seconds, message}"),
        # 可能的其他格式
        ({"time": 1, "reason": "Server shutting down"}, "格式2: {time, reason}"),
        ({"delay": 1, "text": "Server shutting down"}, "格式3: {delay, text}"),
        # 只提供必要参数
        ({"seconds": 1}, "格式4: {seconds}"),
        ({}, "格式5: 空数据"),
    ]
    
    for data, description in test_cases:
        print(f"\n   测试{description}：")
        try:
            response = requests.post(url, auth=auth, headers=headers, 
                                   data=json.dumps(data), timeout=10)
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            if response.status_code == 200:
                print(f"   ✅ 成功！")
                break
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    # 测试PalRestAPI类的shutdown_server方法
    print("\n2. 测试PalRestAPI.shutdown_server方法：")
    try:
        api = PalRestAPI(host, port, username, password)
        flag, result = api.shutdown_server(1, "Server shutting down")
        print(f"   结果: {'成功' if flag else '失败'}")
        print(f"   响应: {result}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("开始测试关闭服务器功能...")
    
    try:
        test_shutdown_server()
        print("\n=== 测试完成 ===")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()