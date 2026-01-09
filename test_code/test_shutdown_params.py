import sys
import os
import requests
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_shutdown_params():
    """测试关闭服务器API的不同参数格式"""
    print("=== 测试关闭服务器API的参数格式 ===")
    
    # 服务器信息
    host = "127.0.0.1"
    port = 8212
    username = "admin"
    password = "123456"
    
    url = f"http://{host}:{port}/v1/api/shutdown"
    auth = (username, password)
    headers = {"Content-Type": "application/json"}
    
    # 测试不同的参数格式
    test_params = [
        ({}, "空数据"),
        ({"seconds": 5}, "只包含seconds参数"),
        ({"time": 5}, "使用time代替seconds"),
        ({"delay": 5}, "使用delay代替seconds"),
        ({"seconds": "5"}, "seconds作为字符串"),
        ({"seconds": 5, "message": "测试消息"}, "包含seconds和message"),
        ({"message": "测试消息"}, "只包含message"),
        ({"reason": "测试原因"}, "使用reason参数"),
        ({"seconds": 5, "reason": "测试原因"}, "包含seconds和reason"),
        ({"time": 5, "message": "测试消息"}, "包含time和message"),
    ]
    
    print(f"测试URL: {url}")
    print(f"认证信息: {username}:{password}")
    print()
    
    for params, description in test_params:
        print(f"测试{description}:")
        print(f"参数: {json.dumps(params, ensure_ascii=False)}")
        
        try:
            response = requests.post(url, auth=auth, headers=headers, 
                                   data=json.dumps(params) if params else None, timeout=10)
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.text.strip():
                print(f"响应内容: {response.text}")
            else:
                print(f"响应内容: (空)")
                
            print()
            
            if response.status_code == 200:
                print("✅ 成功！这是正确的参数格式！")
                break
                
        except Exception as e:
            print(f"错误: {e}")
            print()
    
    # 测试没有Content-Type头的情况
    print("测试没有Content-Type头的情况:")
    try:
        response = requests.post(url, auth=auth, data=json.dumps({"seconds": 5}), timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()
    
    # 测试使用表单数据而不是JSON的情况
    print("测试使用表单数据而不是JSON的情况:")
    try:
        response = requests.post(url, auth=auth, data={"seconds": 5}, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()

if __name__ == "__main__":
    print("开始测试关闭服务器API的参数格式...")
    
    try:
        test_shutdown_params()
        print("=== 测试完成 ===")
        print("请查看上面的测试结果，找到正确的参数格式。")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()