#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = "Huaisha2049"
import requests
import webbrowser
from packaging import version
from PyQt5.QtWidgets import QMessageBox

def check_updates(tool_name, local_version):
    """
    检查汉化工具的新版本并提示更新
    
    本函数执行以下操作：
    1. 向版本服务器发送GET请求获取版本信息
    2. 解析服务器返回的JSON数据
    3. 比较服务器版本与本地版本号
    4. 若发现新版本则弹出提示框并打开浏览器下载
    5. 处理网络请求和版本比较过程中的异常情况

    参数:
        tool_name (str): 工具名称
        local_version (str): 当前本地版本号
        
    返回值:
        无
        
    异常:
        当网络请求失败或数据解析出错时，弹出错误提示框
    """
    try:
        # 发送网络请求获取版本信息
        url = f'https://api.hs2049.cn/tools/{tool_name}'
        response = requests.get(url, timeout=10)
        data = response.json()

        # 解析服务器版本信息
        server_version = data.get("Version")
        # 使用packaging库进行版本号比对
        if version.parse(local_version) < version.parse(server_version):
            # 发现新版本时执行提示流程
            QMessageBox.information(None, "发现新版本", "检测到新版本，点击确定后将自动打开下载链接")
            webbrowser.open(data.get("DownloadUrl"))
    except Exception as e:
        # 异常处理：显示错误详情
        QMessageBox.critical(None, "更新检查失败", f"无法检查更新：{e}")