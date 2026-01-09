import os
import sys

# 获取配置文件路径
palserver_path = r"H:/SteamLibrary/steamapps/common/PalServer/PalServer.exe"
palserver_settings_path = os.path.abspath(os.path.join(palserver_path, r"../Pal/Saved/Config/WindowsServer/PalWorldSettings.ini"))

print(f"配置文件路径: {palserver_settings_path}")

if os.path.exists(palserver_settings_path):
    print("\n配置文件内容:")
    # 读取文件内容
    try:
        with open(palserver_settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(content)
    except UnicodeDecodeError:
        with open(palserver_settings_path, 'r', encoding='ansi') as f:
            content = f.read()
        print(content)
    
    print("\n解析结果:")
    # 尝试解析配置文件
    try:
        from utils import settings_file_operation
        option_settings = settings_file_operation.load_setting(palserver_settings_path)
        for key, value in option_settings.items():
            print(f"  {key}: {value}")
        
        if "ServerName" in option_settings:
            print(f"\n找到了ServerName: {option_settings['ServerName']}")
        else:
            print("\n没有找到ServerName键")
        
        if "ServerDescription" in option_settings:
            print(f"找到了ServerDescription: {option_settings['ServerDescription']}")
        else:
            print("没有找到ServerDescription键")
    except Exception as e:
        print(f"解析出错: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("配置文件不存在!")
