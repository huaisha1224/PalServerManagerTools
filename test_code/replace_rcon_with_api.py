#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
替换代码中的RCON相关文本为API
"""

import os
import re

def replace_rcon_with_api():
    file_path = "activity/main_activity.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换所有RCON相关的文本
    new_content = re.sub(r'self.text_browser_rcon_server_notice', r'self.text_browser_api_server_notice', content)
    
    # 写入修改后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"已完成文件 {file_path} 的替换")

if __name__ == "__main__":
    replace_rcon_with_api()