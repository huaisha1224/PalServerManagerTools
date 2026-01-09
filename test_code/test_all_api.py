import sys
import os
import requests
import json
import time

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.palrestapi import PalRestAPI

def test_all_api_functions():
    """测试所有API功能"""
    print("=== 测试所有REST API功能 ===")
    
    # 服务器信息
    host = "127.0.0.1"
    port = 8212
    username = "admin"
    password = "123456"
    
    # 创建API实例
    api = PalRestAPI(host, port, username, password)
    
    # 测试用例
    test_cases = [
        ("获取服务器信息", api.get_server_info, ()),
        ("获取玩家列表", api.get_players, ()),
        ("广播消息", api.announce_message, ("测试广播消息",)),
        ("保存世界", api.save_world, ()),
        ("停止服务器（10秒后）", api.shutdown_server, (10, "测试关闭服务器")),
    ]
    
    for test_name, func, args in test_cases:
        print(f"\n{test_name}：")
        try:
            start_time = time.time()
            flag, result = func(*args)
            end_time = time.time()
            
            print(f"   结果: {'成功' if flag else '失败'}")
            print(f"   耗时: {end_time - start_time:.2f} 秒")
            
            if flag:
                if isinstance(result, dict):
                    print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                elif isinstance(result, list):
                    print(f"   响应: 共 {len(result)} 条记录")
                    for item in result[:5]:  # 只显示前5条
                        print(f"   - {json.dumps(item, ensure_ascii=False)}")
                    if len(result) > 5:
                        print(f"   ... 还有 {len(result) - 5} 条记录")
                else:
                    print(f"   响应: {result}")
            else:
                print(f"   错误信息: {result}")
                
        except Exception as e:
            print(f"   ❌ 调用错误: {e}")
            import traceback
            traceback.print_exc()
    
    # 测试停止服务器方法的不同参数格式
    print("\n测试关闭服务器的不同参数格式：")
    try:
        # 测试不同的参数组合
        formats_to_test = [
            (5, "默认消息"),
            (1, "快速关闭"),
        ]
        
        for seconds, message in formats_to_test:
            print(f"\n   测试参数: seconds={seconds}, message={message}")
            flag, result = api.shutdown_server(seconds, message)
            print(f"   结果: {'成功' if flag else '失败'}")
            print(f"   响应: {result}")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def test_api_endpoints_directly():
    """直接测试API端点，不通过PalRestAPI类"""
    print("\n=== 直接测试API端点 ===")
    
    # 服务器信息
    host = "127.0.0.1"
    port = 8212
    username = "admin"
    password = "123456"
    
    auth = (username, password)
    base_url = f"http://{host}:{port}"
    
    # 测试的端点
    endpoints_to_test = [
        ("GET", "/v1/api/info", None, "服务器信息"),
        ("GET", "/v1/api/players", None, "玩家列表"),
        ("POST", "/v1/api/announce", {"message": "直接测试广播"}, "广播消息"),
        ("POST", "/v1/api/save", None, "保存世界"),
        ("POST", "/v1/api/shutdown", {"seconds": 10}, "关闭服务器"),
        ("POST", "/v1/api/shutdown", {"seconds": 5, "message": "测试消息"}, "关闭服务器带消息"),
    ]
    
    for method, endpoint, data, description in endpoints_to_test:
        print(f"\n{description} ({method} {endpoint}):")
        try:
            url = f"{base_url}{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            if method == "GET":
                response = requests.get(url, auth=auth, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, auth=auth, headers=headers, 
                                       data=json.dumps(data) if data else None, timeout=10)
            else:
                print(f"   ❌ 不支持的方法: {method}")
                continue
            
            print(f"   状态码: {response.status_code}")
            print(f"   响应头: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"   响应内容: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"   响应内容: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("开始测试所有REST API功能...")
    
    try:
        # 先测试API类的功能
        test_all_api_functions()
        
        # 再直接测试API端点
        test_api_endpoints_directly()
        
        print("\n=== 所有测试完成 ===")
        print("✅ 测试结束！请查看上面的测试结果。")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()