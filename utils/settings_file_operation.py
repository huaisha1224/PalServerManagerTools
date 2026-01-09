import os
import shutil


def load_setting(file_path):
    """
    Load settings from PalWorldSettings.ini file.
    This function attempts to parse the configuration file regardless of its format,
    extracting key-value pairs from the OptionSettings section.
    """
    try:
        # Try UTF-8 encoding first
        with open(file_path, 'r', encoding="utf-8") as file:
            file_data = file.read()
    except UnicodeDecodeError:
        # Fall back to ANSI if UTF-8 fails
        with open(file_path, 'r', encoding='ansi') as file:
            file_data = file.read()
    

    
    # 辅助函数：找到匹配的右括号位置
    def find_matching_parenthesis(text, start_index):
        """找到匹配的右括号的位置"""
        count = 1
        for i in range(start_index + 1, len(text)):
            if text[i] == "(":
                count += 1
            elif text[i] == ")":
                count -= 1
                if count == 0:
                    return i
        return -1  # 没有找到匹配的括号

    # Extract the OptionSettings part regardless of file structure
    try:
        start_index = file_data.index("(")
        end_index = find_matching_parenthesis(file_data, start_index)
        if end_index != -1:
            config_data = file_data[start_index + 1:end_index]
        else:
            # 如果没有找到匹配的右括号，尝试其他方法
            if "OptionSettings=" in file_data:
                # Extract everything after OptionSettings=
                option_line = file_data.split("OptionSettings=")[1].strip()
                if option_line.startswith("(") and option_line.endswith(")"):
                    config_data = option_line[1:-1]
                else:
                    # If it's not wrapped in parentheses, return it as-is
                    config_data = option_line
            else:
                # If we still can't find it, return empty dict
                return {}
    except ValueError:
        # If we can't find parentheses, try to find the OptionSettings line
        if "OptionSettings=" in file_data:
            # Extract everything after OptionSettings=
            option_line = file_data.split("OptionSettings=")[1].strip()
            if option_line.startswith("(") and option_line.endswith(")"):
                config_data = option_line[1:-1]
            else:
                # If it's not wrapped in parentheses, return it as-is
                config_data = option_line
        else:
            # If we still can't find it, return empty dict
            return {}
    
    # Parse key-value pairs
    settings = {}
    if config_data:
        try:
            # 导入正则表达式模块
            import re
            
            # 首先直接提取ServerName，确保它被正确读取
            server_name_pattern = r'ServerName\s*=\s*"([^"]+)"'
            server_name_match = re.search(server_name_pattern, config_data)
            if server_name_match:
                settings["ServerName"] = server_name_match.group(1)
            else:
                # 尝试更宽松的匹配方式
                server_name_match = re.search(r'ServerName\s*=\s*([^,]+)', config_data)
                if server_name_match:
                    value = server_name_match.group(1).strip()
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    settings["ServerName"] = value
            
            # 直接提取ServerDescription，确保它被正确读取
            server_desc_pattern = r'ServerDescription\s*=\s*"([^"]+)"'
            server_desc_match = re.search(server_desc_pattern, config_data)
            if server_desc_match:
                settings["ServerDescription"] = server_desc_match.group(1)
            else:
                # 尝试更宽松的匹配方式
                server_desc_match = re.search(r'ServerDescription\s*=\s*([^,]+)', config_data)
                if server_desc_match:
                    value = server_desc_match.group(1).strip()
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    settings["ServerDescription"] = value
            
            # 然后使用正则表达式提取所有其他键值对
            pattern = r'(\w+)\s*=\s*((?:"[^"]*"|\([^)]*\)|[^,\n]+)?)'
            matches = re.findall(pattern, config_data)
            
            # 处理每个匹配
            for match in matches:
                key = match[0].strip()
                value = match[1].strip()
                
                # 处理引号
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # 只有当键不是ServerName或ServerDescription时才添加，避免覆盖上面直接提取的值
                if key not in ["ServerName", "ServerDescription"]:
                    settings[key] = value
            
        except Exception as e:
            # 如果解析失败，输出错误信息
            import traceback
            traceback.print_exc()
            # 返回已经解析的内容
            pass
    
    return settings


def save_setting(file_path, setting):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write("[/Script/Pal.PalGameWorldSettings]\nOptionSettings=" + "(" + setting + ")\n")


def default_setting(file_path):
    """
    Create a default setting file.
    Always uses the official default configuration file from the game directory.
    """
    # The file_path is something like:
    # H:/SteamLibrary/steamapps/common/PalServer/Pal/Saved/Config/WindowsServer/PalWorldSettings.ini
    # We need to go up 5 directories to reach the PalServer.exe directory:
    # H:/SteamLibrary/steamapps/common/PalServer/
    
    # Go up 5 directory levels to reach PalServer.exe directory
    palserver_exe_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(file_path)))))
    
    # Construct the path to DefaultPalWorldSettings.ini
    default_config_path = os.path.join(palserver_exe_dir, "DefaultPalWorldSettings.ini")
    
    # Always use the official default configuration file if it exists
    if os.path.exists(default_config_path):
        # Copy the official default configuration
        shutil.copy(default_config_path, file_path)
    else:
        # Raise an exception if the official default configuration file doesn't exist
        raise FileNotFoundError(f"Official default configuration file not found at {default_config_path}")