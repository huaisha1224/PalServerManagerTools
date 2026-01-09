#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
import os

from activity import main_activity
from utils import json_operation
from utils import update_checker

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore, QtGui

if __name__ == '__main__':
    config_path = os.path.join(sys.argv[0], r"../config.json")
    if os.path.isfile(config_path) is False:
        default_config = {
            "game_port": 8211,  # 游戏端口
            "game_publicport": 25575,  # 游戏查询端口
            "game_player_limit": 32,  # 游戏玩家数上限
            "api_addr": "127.0.0.1",  # API 服务器地址
            "api_port": 8212,  # REST API 服务器端口
            "api_password": "",  # 管理员密码
            "crash_detection_flag": False,  # 是否开启崩溃检测
            "auto_restart_flag": False,  # 是否开启自动重启
            "auto_restart_time_limit": 7200,  # 自动重启时间间隔(秒)
            "auto_restart_player_flag": False,  # 自动重启是否判断玩家数
            "auto_restart_player_limit": 0,  # 仅在玩家数小于该值时自动重启
            "launch_options_flag": False,  # 是否开启自定义启动项
            "launch_options_info": "",  # 自定义启动项信息
            "auto_backup_flag": False,  # 是否开启自动备份
            "auto_backup_time_limit": 3600  # 自动备份时间间隔(秒)
        }
        json_operation.save_json(config_path, default_config)

    # 适应高DPI设备
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    # 适应Windows缩放
    QtGui.QGuiApplication.setAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    # 实例化，传参
    app = QApplication(sys.argv)
    
    # 创建对象
    main_window = main_activity.Window()
    # 创建窗口
    main_window.show()
    
    # 使用QTimer延迟执行版本检查，确保主窗口完全显示
    from PyQt5.QtCore import QTimer
    
    def delayed_version_check():
        """延迟执行版本检查的函数"""
        local_version = "2025.12.29.1"  # 当前程序版本号
        tool_name = "PalServerManager"    # 每一个版本的api接口信息
        update_checker.check_updates(tool_name, local_version)
    
    # 设置500毫秒延迟，让主窗口有足够时间渲染
    QTimer.singleShot(500, delayed_version_check)
    
    # 进入程序的主循环，并通过exit函数确保主循环安全结束(该释放资源的一定要释放)
    sys.exit(app.exec_())
