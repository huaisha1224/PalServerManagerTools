import requests
import json
from typing import Dict, Any, Optional, Tuple


class PalRestAPI:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, username: str = "admin", password: str = ""):
        """
        初始化帕鲁服务器REST API客户端。
        
        参数:
            host: 服务器主机地址
            port: 服务器端口
            username: 基本认证用户名
            password: 基本认证密码
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.auth = (username, password) if username else None

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Tuple[bool, Any]:
        """
        向REST API发送HTTP请求。
        
        参数:
            method: HTTP方法 (GET, POST, 等)
            endpoint: API端点
            data: 请求附带的数据
            
        返回:
            (success, response_data) 元组
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, auth=self.auth, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, auth=self.auth, headers=headers, 
                                       data=json.dumps(data) if data else None, timeout=10)
            else:
                return False, f"不支持的HTTP方法: {method}"
            
            # 检查请求是否成功
            if response.status_code == 200:
                try:
                    if response.text.strip():
                        return True, response.json()
                    else:
                        # 处理空响应
                        return True, {"status": "success", "message": "操作执行成功"}
                except json.JSONDecodeError:
                    # 如果不是JSON响应，返回文本内容
                    if response.text.strip():
                        return True, response.text
                    else:
                        return True, {"status": "success", "message": "操作执行成功"}
            elif response.status_code == 401:
                return False, "未授权: 请检查用户名和密码"
            elif response.status_code == 400:
                # 尝试获取详细的错误信息
                if response.text.strip():
                    return False, f"请求错误: {response.text}"
                else:
                    return False, "请求错误: 无效的请求数据"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            return False, "连接错误: 无法连接到服务器"
        except requests.exceptions.Timeout:
            return False, "超时错误: 请求超时"
        except Exception as e:
            return False, f"未知错误: {str(e)}"

    def get_server_info(self) -> Tuple[bool, Any]:
        """
        获取服务器信息。
        
        返回:
            包含版本、服务器名称、描述和世界GUID的服务器信息
        """
        return self._make_request("GET", "/v1/api/info")

    def get_players(self) -> Tuple[bool, Any]:
        """
        获取服务器上的玩家列表。
        
        返回:
            包含玩家详细信息的列表
        """
        return self._make_request("GET", "/v1/api/players")

    def announce_message(self, message: str) -> Tuple[bool, Any]:
        """
        向所有玩家广播消息。
        
        参数:
            message: 要广播的消息
            
        返回:
            成功状态和响应
        """
        data = {"message": message}
        return self._make_request("POST", "/v1/api/announce", data)

    def kick_player(self, user_id: str) -> Tuple[bool, Any]:
        """
        将玩家踢出服务器。
        
        参数:
            user_id: 要踢出的玩家的用户ID
            
        返回:
            成功状态和响应
        """
        data = {"userId": user_id}
        return self._make_request("POST", "/v1/api/kick", data)

    def ban_player(self, user_id: str) -> Tuple[bool, Any]:
        """
        禁止玩家进入服务器。
        
        参数:
            user_id: 要禁止的玩家的用户ID
            
        返回:
            成功状态和响应
        """
        data = {"userId": user_id}
        return self._make_request("POST", "/v1/api/ban", data)

    def unban_player(self, user_id: str) -> Tuple[bool, Any]:
        """
        解除玩家的禁止。
        
        参数:
            user_id: 要解除禁止的玩家的用户ID
            
        返回:
            成功状态和响应
        """
        data = {"userId": user_id}
        return self._make_request("POST", "/v1/api/unban", data)

    def save_world(self) -> Tuple[bool, Any]:
        """
        保存世界状态。
        
        返回:
            成功状态和响应
        """
        return self._make_request("POST", "/v1/api/save")

    def shutdown_server(self, waittime: int = 1, message: str = "服务器将在1秒后关闭") -> Tuple[bool, Any]:
        """
        优雅地关闭服务器。
        
        参数:
            waittime: 关闭前的等待时间(必须 <= 1秒)
            message: 关闭前广播的消息
            
        返回:
            成功状态和响应
        """
        # 确保waittime不超过1秒，根据API要求
        if waittime > 1:
            waittime = 1
            
        # 使用正确的参数名waittime
        data = {"waittime": waittime}
        return self._make_request("POST", "/v1/api/shutdown", data)

    def stop_server(self) -> Tuple[bool, Any]:
        """
        强制停止服务器。
        
        返回:
            成功状态和响应
        """
        return self._make_request("POST", "/v1/api/stop")