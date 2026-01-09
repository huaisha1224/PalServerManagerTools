import requests
import json
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import webbrowser
from PIL import Image, ImageTk
import qrcode
import traceback

"""
    模块功能：
    主要用于关注B站账号之后进行软件授权，避免一切白嫖用户
    1. 获取B站登录二维码
    2. 扫码登录并获取Cookie
    3. 检查是否已关注目标用户
    4. 保存验证结果到本地缓存（避免重复验证）
    5. 读取缓存，判断是否已验证过
"""


# ===================== 配置项 =====================
def get_cache_file_path():
    """获取缓存文件的完整路径"""
    # 获取用户目录
    user_home = os.path.expanduser("~")
    # 构建缓存目录路径
    cache_dir = os.path.join(user_home, ".bili_verify")
    # 如果缓存目录不存在，则创建
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    # 返回缓存文件路径
    return os.path.join(cache_dir, "verify_cache.json")

CACHE_FILE = get_cache_file_path()  # 本地缓存文件路径
CACHE_EXPIRE_HOURS = 720  # 缓存有效期（小时），30天后重新
MAX_RETRY = 2  # API调用失败重试次数
API_INTERVAL = 1  # 两次API调用间隔（秒），避免限流
target_uid = 37443749      # 替换为您的B站UID
nickname = "怀沙2049"       # 替换为您的B站昵称

# ===================== 核心功能函数 =====================
def get_headers():
    """生成API请求头（防风控，必须配置）"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

def get_login_headers(cookie=None):
    """生成带认证信息的请求头"""
    headers = get_headers()
    if cookie:
        headers["Cookie"] = cookie
    return headers

def generate_qr_code():
    """生成B站登录二维码"""
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-fe-header"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        data = response.json()
        if data["code"] == 0:
            qrcode_key = data["data"]["qrcode_key"]
            qrcode_url = data["data"]["url"]
            return qrcode_key, qrcode_url
        else:
            return None, f"生成二维码失败: {data.get('message', '未知错误')}"
    except Exception as e:
        return None, f"生成二维码异常: {str(e)}"

def check_qr_login_status(qrcode_key):
    """检查二维码扫描状态"""
    url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}&source=main-fe-header"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        data = response.json()
        
        code = data["data"]["code"]
        message = data["data"]["message"]
        
        # code: 0-登录成功, 86038-二维码已失效, 86101-未扫码, 86090-已扫码未确认
        if code == 0:
            # 登录成功，获取cookie
            cookie_dict = requests.utils.dict_from_cookiejar(response.cookies)
            
            # 同时从返回的URL中提取cookie参数
            redirect_url = data["data"].get("url", "")
            if redirect_url:
                from urllib.parse import parse_qs, urlparse
                parsed_url = urlparse(redirect_url)
                url_params = parse_qs(parsed_url.query)
                for key, values in url_params.items():
                    if key not in cookie_dict and values:
                        cookie_dict[key] = values[0]
            
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            return (True, "登录成功", cookie_str)
        elif code == 86038:
            return (False, "二维码已失效", None)
        elif code == 86101:
            return (None, "未扫码", None)
        elif code == 86090:
            return (None, "已扫码，等待确认", None)
        else:
            return (False, f"未知状态: {message}", None)
    except Exception as e:
        error_msg = f"检查登录状态异常: {str(e)}"
        return (False, error_msg, None)

def check_follow_with_cookie(cookie, target_uid):
    """使用登录凭证检查关注状态"""
    url = f"https://api.bilibili.com/x/relation?fid={target_uid}"
    try:
        response = requests.get(url, headers=get_login_headers(cookie), timeout=10)
        data = response.json()
        
        if data["code"] != 0:
            error_msg = f"B站API返回错误：{data.get('message', '未知错误')}"
            return False, error_msg
        
        # 解析关系数据
        attribute = data["data"].get("attribute", 0)
        
        # attribute值含义:
        # 0: 未关注
        # 1: 已悄悄关注
        # 2: 已关注
        # 3: 已关注但对方未关注（单向关注）
        # 4: 已相互关注（互相关注）
        # 6: 已相互关注（备注）
        # 128: 已拉黑
        
        if attribute in [1, 2, 3, 4, 6]:
            return True, "找到关注记录"
        else:
            return False, f"未检测到关注关系（属性值：{attribute}）"
            
    except Exception as e:
        error_msg = f"检查关注状态异常: {str(e)}"
        return False, error_msg

def save_cache(user_uid):
    """保存验证结果到本地缓存（避免重复验证）"""
    cache_data = {}
    # 确保缓存目录存在
    cache_dir = os.path.dirname(CACHE_FILE)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    # 读取现有缓存
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                cache_data = json.load(f)
            except json.JSONDecodeError:
                cache_data = {}  # 缓存文件损坏则重置

    # 写入新缓存（记录验证时间+UID）
    cache_data[str(user_uid)] = {
        "verified": True,
        "verify_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 保存缓存文件
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

def load_cache(user_uid):
    """读取缓存，判断是否有效（未过期）"""
    if not os.path.exists(CACHE_FILE):
        return False
    
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try:
            cache_data = json.load(f)
        except json.JSONDecodeError:
            return False  # 缓存文件损坏
    
    user_cache = cache_data.get(str(user_uid))
    if not user_cache:
        return False
    
    # 检查缓存是否过期
    try:
        verify_time = datetime.strptime(user_cache["verify_time"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - verify_time < timedelta(hours=CACHE_EXPIRE_HOURS):
            return True
    except ValueError:
        pass  # 时间格式错误，视为过期
    
    # 过期则删除该缓存记录
    del cache_data[str(user_uid)]
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    return False

def check_cached_verification():
    """
    检查是否存在有效的缓存验证
    
    返回:
    (bool, str): (是否有效, 用户UID或None)
    """
    # 检查是否存在有效的缓存文件
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # 遍历缓存中的所有用户，检查是否有未过期的验证
            current_time = datetime.now()
            for user_uid, user_cache in cache_data.items():
                if user_cache.get("verified", False):
                    try:
                        verify_time = datetime.strptime(user_cache["verify_time"], "%Y-%m-%d %H:%M:%S")
                        if current_time - verify_time < timedelta(hours=CACHE_EXPIRE_HOURS):
                            # 找到有效的缓存
                            return True, user_uid
                    except (ValueError, KeyError):
                        continue  # 时间格式错误或缺少键，跳过此条目
        except (json.JSONDecodeError, IOError):
            pass  # 文件读取或解析错误，忽略缓存
    
    return False, None

# ===================== 界面类 =====================
class BiliVerifyApp:
    def __init__(self, root, target_uid, nickname, callback=None):
        self.root = root
        self.target_uid = target_uid
        self.nickname = nickname
        self.callback = callback  # 验证成功的回调函数
        
        self.root.title("授权验证-关注B站怀沙2049以完成授权")
        self.root.geometry("400x400")
        self.root.resizable(False, False)
        
        # 设置界面样式
        self.setup_styles()
        
        # 初始化变量
        self.qrcode_key = None
        self.qrcode_url = None
        self.cookie = None
        self.qr_after_id = None
        
        # 创建界面元素
        self.create_ui()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        # 配置标题样式
        style.configure("Title.TLabel", 
                       font=("微软雅黑", 12, "bold"),
                       foreground="#2c3e50")
        
        # 配置普通标签样式
        style.configure("Info.TLabel",
                       font=("微软雅黑", 9),
                       foreground="#34495e")
        
        # 配置状态标签样式
        style.configure("Status.TLabel",
                       font=("微软雅黑", 9),
                       foreground="#7f8c8d")
        
        # 配置成功状态样式
        style.configure("Success.TLabel",
                       font=("微软雅黑", 9),
                       foreground="#27ae60")
        
        # 配置错误状态样式
        style.configure("Error.TLabel",
                       font=("微软雅黑", 9),
                       foreground="#e74c3c")
        
        # 配置按钮样式
        style.configure("Action.TButton",
                       font=("微软雅黑", 10))
        
        # 配置主色调按钮样式
        style.configure("Accent.TButton",
                       font=("微软雅黑", 10, "bold"))
    
    def create_ui(self):
        """构建验证界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 跳转B站按钮
        link_btn = ttk.Button(
            main_frame,
            text="🔗 前往B站关注“怀沙2049”",
            command=self.open_bili_page,
            bootstyle=PRIMARY
        )
        link_btn.pack(pady=(0, 15))
        
        # 二维码显示区域
        self.qr_frame = ttk.LabelFrame(main_frame, text="扫码登录", padding=5)
        self.qr_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 二维码画布
        self.qr_canvas = tk.Canvas(self.qr_frame, width=180, height=180, bg="white")
        self.qr_canvas.pack(pady=(5, 5))
        
        # 二维码状态标签
        self.qr_status_label = ttk.Label(
            self.qr_frame,
            text="点击下方按钮生成二维码",
            bootstyle=SECONDARY
        )
        self.qr_status_label.pack(pady=(0, 5))
        
        # 按钮框架，将两个按钮放在同一行
        button_frame = ttk.Frame(self.qr_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 生成二维码按钮
        self.generate_qr_btn = ttk.Button(
            button_frame,
            text="📷 生成二维码",
            command=self.generate_qr_code_and_display,
            bootstyle=SUCCESS
        )
        self.generate_qr_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 检测关注状态按钮（初始禁用）
        self.check_follow_btn = ttk.Button(
            button_frame,
            text="🔍 检测关注状态",
            command=self.check_follow_status,
            state="disabled",
            bootstyle=INFO
        )
        self.check_follow_btn.pack(side=tk.RIGHT)
        
        # 状态提示标签
        self.status_label = ttk.Label(
            main_frame,
            text="使用B站APP扫码登录用以检测并完全授权",
            bootstyle=SECONDARY
        )
        self.status_label.pack()

    def open_bili_page(self):
        """打开B站关注页面"""
        webbrowser.open(f"https://space.bilibili.com/{self.target_uid}/follow")
    
    def verify_follow(self):
        """核心：验证用户是否关注，解锁软件"""
        # 直接使用扫码登录验证方式
        if not self.cookie:
            messagebox.showwarning("操作错误", "请先用B站APP扫码登录！")
        else:
            self.check_follow_status()
    
    def generate_qr_code_and_display(self):
        """生成二维码并显示"""
        self.qrcode_key, self.qrcode_url = generate_qr_code()  # 保存二维码URL
        if self.qrcode_key:
            self.qr_status_label.configure(text="二维码已生成，等待扫描...", bootstyle=SUCCESS)
            self.qr_canvas.delete("all")
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=6,
                border=4,
            )
            qr.add_data(self.qrcode_url)  # 使用二维码URL而不是key
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            # 调整图片尺寸以适应Canvas
            img = img.resize((160, 160))
            img = ImageTk.PhotoImage(img)
            self.qr_canvas.create_image(90, 90, image=img)  # 调整中心位置
            self.qr_canvas.image = img
            self.check_follow_btn.configure(state="normal")
            self.qr_after_id = self.root.after(1000, self.check_qr_login_status)
        else:
            self.qr_status_label.configure(text=f"生成二维码失败: {self.qrcode_url}", bootstyle=DANGER)
    
    def check_qr_login_status(self):
        """检查二维码登录状态"""
        if self.qrcode_key:
            result, msg, cookie = check_qr_login_status(self.qrcode_key)
            if result:
                self.cookie = cookie
                self.qr_status_label.configure(text="登录成功，正在验证关注状态...", bootstyle=SUCCESS)
                self.root.after_cancel(self.qr_after_id)
                self.check_follow_status()
            elif msg == "二维码已失效":
                self.qr_status_label.configure(text="二维码已失效，请重新生成", bootstyle=DANGER)
            elif msg == "未扫码":
                self.qr_status_label.configure(text="二维码已生成，等待扫描...", bootstyle=SUCCESS)
                self.qr_after_id = self.root.after(1000, self.check_qr_login_status)
            elif msg == "已扫码，等待确认":
                self.qr_status_label.configure(text="已扫码，等待确认...", bootstyle=SUCCESS)
                self.qr_after_id = self.root.after(1000, self.check_qr_login_status)
            else:
                self.qr_status_label.configure(text=f"未知状态: {msg}", bootstyle=DANGER)
    
    def check_follow_status(self):
        """检查关注状态"""
        if self.cookie:
            result, msg = check_follow_with_cookie(self.cookie, self.target_uid)
            if result:
                self.status_label.configure(text="授权验证成功！已关注目标账号", bootstyle=SUCCESS)
                messagebox.showinfo("授权验证成功", "已成功验证关注状态！")
                # 获取用户信息并保存缓存
                self.save_user_info_and_cache()
            else:
                self.status_label.configure(text=f"授权验证失败: {msg}", bootstyle=DANGER)
                messagebox.showerror("授权验证失败", msg)
        else:
            self.status_label.configure(text="请先扫码登录！", bootstyle=DANGER)
            try:
                messagebox.showwarning("操作错误", "请先用B站APP扫码登录！")
            except Exception as e:
                print(f"显示消息框时出错: {e}")
                # 即使消息框显示失败，也要确保状态标签更新
                pass

    def save_user_info_and_cache(self):
        """获取用户信息并保存到缓存"""
        try:
            # 获取用户信息
            url = "https://api.bilibili.com/x/web-interface/nav"
            response = requests.get(url, headers=get_login_headers(self.cookie), timeout=10)
            data = response.json()
            
            if data["code"] == 0:
                user_uid = data["data"]["mid"]
                print(f"获取到用户UID: {user_uid}，正在保存授权信息...")
                save_cache(user_uid)  # 保存到缓存文件
                self.run_main_app()  # 启动主应用程序
            else:
                messagebox.showerror("错误", f"获取用户信息失败: {data.get('message', '未知错误')}")
        except Exception as e:
            error_msg = f"获取用户信息异常: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def run_main_app(self):
        """启动主应用程序"""
        try:
            # 调用回调函数通知验证成功
            if self.callback:
                self.callback()
            else:
                # 如果没有提供回调函数，则显示默认消息
                messagebox.showinfo("授权验证成功", "授权验证成功")
            
            # 确保在回调执行完成后才销毁窗口
            try:
                if self.root.winfo_exists():  # 检查窗口是否存在
                    self.root.destroy()
            except tk.TclError:
                pass  # 窗口可能已被销毁
        except Exception as e:
            print(f"启动主应用程序时出错: {e}")
            traceback.print_exc()

def verify_bilibili_follow(callback=None, show_cache_message=True):
    """
    启动B站关注验证流程
    
    参数:
    target_uid: 目标B站用户UID
    nickname: 目标B站用户昵称
    callback: 验证成功后的回调函数
    show_cache_message: 是否显示缓存验证提示消息，默认为True
    
    返回:
    None
    """
    global CACHE_FILE
    
    # 确保缓存目录存在
    cache_dir = os.path.dirname(CACHE_FILE)
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
        except OSError:
            # 如果无法创建目录，使用临时目录
            import tempfile
            temp_dir = os.path.join(tempfile.gettempdir(), ".bili_verify")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            CACHE_FILE = os.path.join(temp_dir, "verify_cache.json")
    
    # 首先检查缓存
    is_valid, _ = check_cached_verification()
    if is_valid:
        # 如果缓存有效，直接调用回调函数
        print("使用缓存验证")
        print(f"目标账号: {nickname} (UID: {target_uid})")
        print("已通过缓存验证，无需重新扫码")
        
        # 根据参数决定是否显示弹窗提示
        if show_cache_message:
            # 显示弹窗提示
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            messagebox.showinfo("验证成功", f"已通过缓存验证！\n目标账号: {nickname} (UID: {target_uid})")
            root.destroy()
        
        if callback:
            callback()
        return
    
    # 缓存无效或不存在，启动验证流程
    root = ttk.Window(themename="litera")  # 使用ttkbootstrap主题
    app = BiliVerifyApp(root, target_uid, nickname, callback)
    root.mainloop()

def get_user_uid_from_cookie_file():
    """
    从cookie文件或其他途径获取当前用户的UID
    这是一个简化的实现，实际项目中可能需要更复杂的逻辑
    """
    # 在这个简单的实现中，我们返回None，表示需要重新验证
    # 在更复杂的场景中，你可以从cookie文件或者其他地方获取用户ID
    return None


# 测试程序入口点
if __name__ == "__main__":
    # 测试
    YOUR_TARGET_UID = 37443749      # 替换为您的B站UID
    YOUR_NICKNAME = "怀沙2049"       # 替换为您的B站昵称
    
    print("正在启动B站关注验证...")
    print(f"目标账号: {YOUR_NICKNAME} (UID: {YOUR_TARGET_UID})")
    
    # 步骤4: 启动验证流程
    verify_bilibili_follow(show_cache_message=False)