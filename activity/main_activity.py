import os
import sys
import subprocess
import shutil
import time
from datetime import datetime, timedelta

from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QTextCharFormat, QColor, QTextCursor, QDesktopServices
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTableWidgetItem, QMenu, QAction, QInputDialog, QStatusBar
import psutil
import pyperclip

from . import world_settings_activity
from utils import json_operation, random_password, settings_file_operation, bili_authorization
from utils.pal_restapi import PalRestAPI  # Import the new REST API client
import setting

# Import MOD manager
from pal_mod_manager import ModManagerQt


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.module_path = os.path.split(sys.modules[__name__].__file__)[0]
        self.config_path = os.path.join(sys.argv[0], r"../config.json")
        self.config = json_operation.load_json(self.config_path)
        self.rest_api_connect_flag = False
        self.pal_rest_api = None
        self.server_run_flag = False
        self.server_run_time = datetime.now()
        self.last_auto_backup_time = datetime.now()
        self.player_list = []
        self.palserver_settings_path = None
        self.option_settings_dict = {}
        self.initUi()

    def initUi(self):
        loadUi(os.path.join(self.module_path, r"../ui/main.ui"), self)
        if setting.publicity_ad:
            self.setWindowTitle("帕鲁服务器管理工具                 By 怀沙2049" +  " - " + setting.publicity_ad)
        else:
            self.setWindowTitle("帕鲁服务器管理工具                 By 怀沙2049" )
        self.setFixedSize(1450, 730)
        self.setWindowIcon(QIcon(os.path.join(self.module_path, r"../resource/favicon.ico")))
        self.table_widget_player_list.setColumnWidth(0, 80)
        self.table_widget_player_list.setColumnWidth(1, 100)
        self.table_widget_player_list.setColumnWidth(2, 130)

        if setting.status_bar_show_flag:
            status_bar = QStatusBar()
            self.setStatusBar(status_bar)
            status_bar.showMessage(setting.status_bar_message)

        # 不设置默认值，直接显示空
        self.text_edit_server_name.setText("")
        self.text_edit_server_description.setText("")
        
        # 添加调试信息，检查config中是否有palserver_path
        if "palserver_path" in self.config:
            self.text_browser_api_server_notice("client_message", f"检测到游戏服务安装路径: {self.config['palserver_path']}")
        else:
            self.text_browser_api_server_notice("client_message", "请先设置好游戏路径")
        
        self.check_palserver_path()

        if "game_port" in self.config:
            self.line_edit_game_port.setText(str(self.config["game_port"]))
        if "game_publicport" in self.config:
            self.line_edit_game_publicport.setText(str(self.config["game_publicport"]))
        if "game_player_limit" in self.config:
            self.line_edit_game_player_limit.setText(str(self.config["game_player_limit"]))

        # Update API settings from config, but prioritize RESTAPIPort from PalWorldSettings.ini if available
        if "api_addr" in self.config:
            self.line_edit_api_addr.setText(self.config["api_addr"])
        
        # Check if we have the actual RESTAPIPort from the server settings
        if hasattr(self, 'option_settings_dict') and "RESTAPIPort" in self.option_settings_dict:
            # Use the actual RESTAPIPort from PalWorldSettings.ini
            actual_api_port = int(self.option_settings_dict["RESTAPIPort"])
            self.line_edit_api_port.setText(str(actual_api_port))
            # Update the config to use this port
            self.config["api_port"] = actual_api_port
            self.save_config_json()
        elif "api_port" in self.config:
            # Fall back to the saved config port if RESTAPIPort isn't available
            self.line_edit_api_port.setText(str(self.config["api_port"]))
            
        if "api_password" in self.config:
            self.line_edit_api_password.setText(self.config["api_password"])

        if "crash_detection_flag" in self.config:
            self.check_box_crash_detection.setChecked(self.config["crash_detection_flag"])
            if self.config["crash_detection_flag"]:
                self.check_box_crash_detection_click(True)
        if "auto_restart_time_limit" in self.config:
            self.line_edit_auto_restart_time_limit.setText(str(self.config["auto_restart_time_limit"]))
        if "auto_restart_flag" in self.config:
            self.check_box_auto_restart.setChecked(self.config["auto_restart_flag"])
            if self.config["auto_restart_flag"]:
                self.check_box_auto_restart_click(True)
        if "auto_restart_player_limit" in self.config:
            self.line_edit_auto_restart_player_limit.setText(str(self.config["auto_restart_player_limit"]))
        if "auto_restart_player_flag" in self.config:
            self.check_box_auto_restart_player.setChecked(self.config["auto_restart_player_flag"])
            if self.config["auto_restart_player_flag"]:
                self.check_box_auto_restart_player_click(True)

        if "auto_backup_time_limit" in self.config:
            self.line_edit_auto_backup_time_limit.setText(str(self.config["auto_backup_time_limit"]))
        if "backup_dir_path" in self.config:
            if os.path.isdir(self.config["backup_dir_path"]):
                self.line_edit_backup_path.setText(self.config["backup_dir_path"])
                self.check_box_auto_backup.setEnabled(True)
                self.line_edit_auto_backup_time_limit.setEnabled(True)
                if "auto_backup_flag" in self.config:
                    self.check_box_auto_backup.setChecked(self.config["auto_backup_flag"])
                    if self.config["auto_backup_flag"]:
                        self.check_box_auto_backup_click(True)
            else:
                self.config.pop("backup_dir_path")
                self.save_config_json()

        if "launch_options_info" in self.config:
            self.line_edit_launch_options.setText(self.config["launch_options_info"])
        if "launch_options_flag" in self.config:
            self.check_box_launch_options.setChecked(self.config["launch_options_flag"])
            self.line_edit_launch_options.setEnabled(not self.config["launch_options_flag"])

        self.timed_detection_timer_1000 = QTimer(self)
        self.timed_detection_timer_1000.timeout.connect(self.timed_detection_1000)
        self.timed_detection_timer_1000.start(1000)
        self.timed_detection_timer_5000 = QTimer(self)
        self.timed_detection_timer_5000.timeout.connect(self.timed_detection_5000)
        self.timed_detection_timer_5000.start(5000)
        self.player_list_timer = QTimer(self)
        self.player_list_timer.timeout.connect(self.timed_detection_timer_60000)
        self.player_list_timer.start(60000)
        
        # 创建菜单栏并添加关于菜单项
        self.create_menu_bar()

    def timed_detection_1000(self):
        if self.server_run_flag:
            if "palserver_pid" in self.config:
                if psutil.pid_exists(self.config["palserver_pid"]) is False:
                    self.server_run_flag = False
                    if self.config["crash_detection_flag"]:
                        self.text_browser_api_server_notice("client_error", "检测到服务端崩溃，开始重启 ！")
                        self.button_game_start_click()
        else:
            if "palserver_pid" in self.config:
                if psutil.pid_exists(self.config["palserver_pid"]):
                    self.server_run_flag = True

        if self.server_run_flag:
            self.label_server_status.setText("正在运行")
            self.label_server_status.setStyleSheet("color:green")
        else:
            self.label_server_status.setText("已停止")
            self.label_server_status.setStyleSheet("color:red")
        self.button_game_start.setEnabled(not self.server_run_flag)
        self.button_game_stop.setEnabled(self.server_run_flag)
        self.button_game_restart.setEnabled(self.server_run_flag)
        self.button_game_kill.setEnabled(self.server_run_flag)
        # 服务器名称和描述设置为只读，总是从配置文件读取
        self.text_edit_server_name.setEnabled(False)
        self.text_edit_server_description.setEnabled(False)
        self.button_edit_server_name.setEnabled(False)

        self.line_edit_command.setEnabled(self.rest_api_connect_flag)
        self.button_send_command.setEnabled(self.rest_api_connect_flag)
        self.button_countdown_stop.setEnabled(self.rest_api_connect_flag)
        self.button_broadcast.setEnabled(self.rest_api_connect_flag)

        if self.config["auto_restart_flag"] and self.server_run_flag:
            if self.server_run_time + timedelta(seconds=self.config["auto_restart_time_limit"]) < datetime.now():
                if self.config["auto_restart_player_flag"]:
                    if len(self.player_list) <= self.config["auto_restart_player_limit"]:
                        self.text_browser_api_server_notice("client_message", "检测到符合服务器自动重启条件，开始重启！")
                        self.button_game_restart_click()
                else:
                    self.text_browser_api_server_notice("client_message", "检测到符合服务器自动重启条件，开始重启！")
                    self.button_game_restart_click()

        if self.config["auto_backup_flag"]:
            if self.last_auto_backup_time + timedelta(seconds=self.config["auto_backup_time_limit"]) < datetime.now():
                self.text_browser_api_server_notice("client_message", "检测到符合服务器自动备份标准，开始备份！")
                old_dir_path = os.path.join(self.config["palserver_path"], r"../Pal/Saved/")
                new_dir_path = os.path.join(self.config["backup_dir_path"], datetime.now().strftime("%Y%m%d %H-%M-%S"))
                shutil.copytree(old_dir_path, new_dir_path)
                self.text_browser_api_server_notice("client_success", "存档自动备份完成！备份路径：" + str(os.path.abspath(new_dir_path)))
                self.last_auto_backup_time = datetime.now()

    def timed_detection_5000(self):
        try:
            self.label_cpu_info.setText(str(psutil.cpu_percent(interval=0)) + " %")
            self.label_mem_info.setText(str(round(psutil.virtual_memory().used / (1024 * 1024), 2)) + " MB / " + str(round(psutil.virtual_memory().total / (1024 * 1024), 2)) + " MB")
            if self.server_run_flag:
                mem_info = 0
                psu_proc = psutil.Process(self.config["palserver_pid"])
                pcs = psu_proc.children(recursive=True)
                for proc in pcs:
                    mem_info += proc.memory_full_info().rss
                self.label_mem_info_2.setText(str(round(mem_info / (1024 * 1024), 2)) + " MB")
            else:
                self.label_mem_info_2.setText("0 MB")
        except:
            return

        if "palserver_path" in self.config:
            total, used, free = shutil.disk_usage(self.config["palserver_path"])
            self.label_disk_info.setText(str(round(used / (1024 * 1024 * 1024), 2)) + " GB / " + str(round(total / (1024 * 1024 * 1024), 2)) + " GB")
        else:
            self.label_disk_info.setText("未设置")

        if "backup_dir_path" in self.config:
            total, used, free = shutil.disk_usage(self.config["backup_dir_path"])
            self.label_disk_info_2.setText(str(round(used / (1024 * 1024 * 1024), 2)) + " GB / " + str(round(total / (1024 * 1024 * 1024), 2)) + " GB")
        else:
            self.label_disk_info_2.setText("未设置")

    def timed_detection_timer_60000(self):
        if self.rest_api_connect_flag is False:
            self.label_online_player.setText("未连接REST API")
            return

        self.table_widget_player_list.clearContents()
        self.table_widget_player_list.setRowCount(0)

        self.player_list_menu = QMenu(self)
        kick_action = QAction('踢出该玩家', self)
        kick_action.triggered.connect(self.kick_player)
        ban_action = QAction('封禁该玩家', self)
        ban_action.triggered.connect(self.ban_player)
        copy_uid_action = QAction('复制玩家UID', self)
        copy_uid_action.triggered.connect(self.copy_uid)
        copy_steamid_action = QAction('复制玩家StramID', self)
        copy_steamid_action.triggered.connect(self.copy_steamid)
        self.player_list_menu.addAction(kick_action)
        self.player_list_menu.addAction(ban_action)
        self.player_list_menu.addAction(copy_uid_action)
        self.player_list_menu.addAction(copy_steamid_action)
        self.table_widget_player_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget_player_list.customContextMenuRequested.connect(self.show_player_list_menu)

        flag, api_result = self.pal_rest_api.get_players()
        if flag is False:
            self.rest_api_connect_flag = False
            self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
            return
        player_list = api_result["players"] if "players" in api_result else []
        player_id = 0
        self.player_list = []
        for player in player_list:
            if player == "":
                continue
            # player_info = player.split(",")  # Old RCON format
            # if len(player_info) < 3:
            #     continue
            self.player_list.append(player)
            self.table_widget_player_list.insertRow(player_id)
            item = QTableWidgetItem(player["name"] if "name" in player else "")
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.table_widget_player_list.setItem(player_id, 0, item)
            item = QTableWidgetItem(str(player["level"]) if "level" in player else "")
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.table_widget_player_list.setItem(player_id, 1, item)
            item = QTableWidgetItem(player["userId"] if "userId" in player else "")
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.table_widget_player_list.setItem(player_id, 2, item)
            player_id += 1

        self.label_online_player.setText(str(player_id) + "/" + str(self.config["game_player_limit"]))

    def kick_player(self):
        selected_items = self.table_widget_player_list.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            player_user_id = self.player_list[selected_row].get("userId", "")
            if player_user_id:
                command = "踢出玩家: " + player_user_id
                self.text_browser_api_server_notice("client_command", command)
                flag, api_result = self.pal_rest_api.kick_player(player_user_id)
                if flag:
                    self.text_browser_api_server_notice("server_success", "玩家踢出成功")
                else:
                    self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
        self.timed_detection_timer_60000()

    def ban_player(self):
        selected_items = self.table_widget_player_list.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            player_user_id = self.player_list[selected_row].get("userId", "")
            if player_user_id:
                command = "封禁玩家: " + player_user_id
                self.text_browser_api_server_notice("client_command", command)
                flag, api_result = self.pal_rest_api.ban_player(player_user_id)
                if flag:
                    self.text_browser_api_server_notice("server_success", "玩家封禁成功")
                else:
                    self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
        self.timed_detection_timer_60000()

    def copy_uid(self):
        selected_items = self.table_widget_player_list.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            player_uid = self.player_list[selected_row].get("userId", "")
            pyperclip.copy(player_uid)

    def copy_steamid(self):
        selected_items = self.table_widget_player_list.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            # 尝试获取SteamID，可能的字段名包括steamId、SteamID等
            player_steamid = self.player_list[selected_row].get("steamId", "")
            if not player_steamid:
                player_steamid = self.player_list[selected_row].get("SteamID", "")
            pyperclip.copy(player_steamid)

    def text_browser_api_server_notice(self, message_type, message):
        cursor = self.text_browser_api_server.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_browser_api_server.setTextCursor(cursor)
        black_format = QTextCharFormat()
        black_format.setForeground(QColor("black"))
        red_format = QTextCharFormat()
        red_format.setForeground(QColor("red"))
        green_format = QTextCharFormat()
        green_format.setForeground(QColor("green"))
        blue_format = QTextCharFormat()
        blue_format.setForeground(QColor("blue"))
        grey_format = QTextCharFormat()
        grey_format.setForeground(QColor(190, 190, 190))
        sky_blue_format = QTextCharFormat()
        sky_blue_format.setForeground(QColor(135, 206, 235))
        dark_violet_format = QTextCharFormat()
        dark_violet_format.setForeground(QColor(148, 0, 211))
        olive_drab_format = QTextCharFormat()
        olive_drab_format.setForeground(QColor(105, 139, 34))
        self.text_browser_api_server.setCurrentCharFormat(dark_violet_format)
        self.text_browser_api_server.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if message_type == "client_success":
            self.text_browser_api_server.setCurrentCharFormat(sky_blue_format)
            self.text_browser_api_server.insertPlainText("  CLIENT: ")
            self.text_browser_api_server.setCurrentCharFormat(green_format)
            self.text_browser_api_server.insertPlainText("[SUCCESS] ")
        if message_type == "client_message":
            self.text_browser_api_server.setCurrentCharFormat(sky_blue_format)
            self.text_browser_api_server.insertPlainText("  CLIENT: ")
            self.text_browser_api_server.setCurrentCharFormat(olive_drab_format)
            self.text_browser_api_server.insertPlainText("[MESSAGE] ")
        if message_type == "client_error":
            self.text_browser_api_server.setCurrentCharFormat(sky_blue_format)
            self.text_browser_api_server.insertPlainText("  CLIENT: ")
            self.text_browser_api_server.setCurrentCharFormat(red_format)
            self.text_browser_api_server.insertPlainText("  [ERROR] ")
        if message_type == "client_command":
            self.text_browser_api_server.setCurrentCharFormat(sky_blue_format)
            self.text_browser_api_server.insertPlainText("  CLIENT: ")
            self.text_browser_api_server.setCurrentCharFormat(blue_format)
            self.text_browser_api_server.insertPlainText("[COMMAND] ")
        if message_type == "server_success":
            self.text_browser_api_server.setCurrentCharFormat(grey_format)
            self.text_browser_api_server.insertPlainText("  SERVER: ")
            self.text_browser_api_server.setCurrentCharFormat(green_format)
            self.text_browser_api_server.insertPlainText("[SUCCESS] ")
        self.text_browser_api_server.setCurrentCharFormat(black_format)
        self.text_browser_api_server.insertPlainText(message)
        self.text_browser_api_server.ensureCursorVisible()

    def save_config_json(self):
        json_operation.save_json(self.config_path, self.config)

    def check_palserver_path(self):
        if "palserver_path" not in self.config:
            return False

        if os.path.isfile(self.config["palserver_path"]) is False:
            self.line_edit_palserver_path.setText("")
            self.config.pop("palserver_path")
            self.save_config_json()
            self.text_browser_api_server_notice("client_error", "检测到 PalServer.exe 文件不存在，请重新选择！")
            return False

        self.palserver_settings_path = os.path.abspath(os.path.join(self.config["palserver_path"], r"../Pal/Saved/Config/WindowsServer/PalWorldSettings.ini"))
        if os.path.isfile(self.palserver_settings_path) is False:
            self.line_edit_palserver_path.setText("")
            self.config.pop("palserver_path")
            self.save_config_json()
            self.text_browser_api_server_notice("client_error", "服务端路径下的 /Pal/Saved/Config/WindowsServer/PalWorldSettings.ini 配置文件不存在，请启动一次PalServer.exe，或检查服务端完整性！")
            return False

        self.line_edit_palserver_path.setText(self.config["palserver_path"])
        if os.stat(self.palserver_settings_path).st_size < 10:
            self.text_browser_api_server_notice("client_success", "检测到 服务端路径下的 /Pal/Saved/Config/WindowsServer/PalWorldSettings.ini 配置文件大小不正确，正在重新初始化。")
            settings_file_operation.default_setting(self.palserver_settings_path)

        self.save_config_json()
        self.button_open_settings_dir.setEnabled(True)
        # 启用获取REST API连接信息按钮
        self.button_get_api_config.setEnabled(True)

        try:
            self.option_settings_dict = settings_file_operation.load_setting(self.palserver_settings_path)
        except Exception as e:
            self.text_browser_api_server_notice("client_error", f"配置文件解析出错: {str(e)}，使用空配置继续")
            self.option_settings_dict = {}

        # 获取ServerName和ServerDescription，没有默认值
        server_name = self.option_settings_dict.get("ServerName", "")
        server_description = self.option_settings_dict.get("ServerDescription", "")
        
        self.text_edit_server_name.setText(server_name)
        self.text_edit_server_description.setText(server_description)

    def button_select_file_click(self):
        """选择PalServer.exe文件按钮点击事件"""
        # 定义授权成功后的回调函数
        def authorize_success():
            """授权成功后执行的操作"""
            qfile_dialog = QFileDialog.getOpenFileName(self, "选择文件", "/", "PalServer (PalServer.exe)")
            self.config["palserver_path"] = qfile_dialog[0]
            self.save_config_json()
            self.text_browser_api_server_notice("client_success", "已获取PalServer.exe路径：" + qfile_dialog[0])
            self.check_palserver_path()
        
        # 调用B站授权验证
        bili_authorization.verify_bilibili_follow(callback=authorize_success, show_cache_message=False)

    def button_open_settings_dir_click(self):
        os.system("explorer /select,\"" + str(os.path.abspath(self.palserver_settings_path)) + "\"")
        self.text_browser_api_server_notice("client_success", "已打开 配置文件夹 目录，请修改REST API相关字段")

    def button_get_api_config_click(self):
        # Reload settings from file to ensure we're using the latest configuration
        try:
            self.option_settings_dict = settings_file_operation.load_setting(self.palserver_settings_path)
        except Exception as e:
            self.text_browser_api_server_notice("client_error", f"重新加载配置文件出错: {str(e)}")
            return
        
        # For REST API, we primarily check RESTAPIEnabled, not RCONEnabled
        # RCON is an older protocol and REST API is the preferred method
        # So we no longer require RCONEnabled to be True for REST API functionality
        
        # 检查 REST API 是否已启用
        if 'RESTAPIEnabled' not in self.option_settings_dict:
            self.text_browser_api_server_notice("client_error", "配置文件中 RESTAPIEnabled 未配置，请修改为 True 或使用自动配置！")
            QMessageBox.critical(self, "错误", "配置文件中 RESTAPIEnabled 未配置，请修改为 True 或使用自动配置！")
            return
        
        if self.option_settings_dict.get('RESTAPIEnabled') != "True":
            self.text_browser_api_server_notice("client_error", "配置文件中 RESTAPIEnabled 未启用，请修改为 True 或使用自动配置！")
            QMessageBox.critical(self, "错误", "配置文件中 RESTAPIEnabled 未启用，请修改为 True 或使用自动配置！")
            return
        
        # 检查 AdminPassword 是否已配置
        if 'AdminPassword' not in self.option_settings_dict:
            self.text_browser_api_server_notice("client_error", "配置文件中 AdminPassword 未配置，请设置密码或使用自动配置！")
            QMessageBox.critical(self, "错误", "配置文件中 AdminPassword 未配置，请设置密码或使用自动配置！")
            return
        
        admin_password = self.option_settings_dict.get('AdminPassword', '').replace('"', '')
        if not admin_password:
            self.text_browser_api_server_notice("client_error", "配置文件中 AdminPassword 为空，请设置密码或使用自动配置！")
            QMessageBox.critical(self, "错误", "配置文件中 AdminPassword 为空，请设置密码或使用自动配置！")
            return
        
        self.config["api_addr"] = "127.0.0.1"
        
        # Use RESTAPIPort if available, otherwise fall back to RCONPort for backward compatibility
        if "RESTAPIPort" in self.option_settings_dict:
            self.config["api_port"] = int(self.option_settings_dict["RESTAPIPort"])
        else:
            self.config["api_port"] = int(self.option_settings_dict["RCONPort"])
            
        self.config["api_password"] = self.option_settings_dict["AdminPassword"].replace("\"", "")
        self.save_config_json()
        self.line_edit_api_addr.setText("127.0.0.1")
        
        # Update the UI with the correct port
        if "RESTAPIPort" in self.option_settings_dict:
            self.line_edit_api_port.setText(str(self.option_settings_dict["RESTAPIPort"]))
        else:
            self.line_edit_api_port.setText(str(self.option_settings_dict["RCONPort"]))
            
        self.line_edit_api_password.setText(self.option_settings_dict["AdminPassword"].replace("\"", ""))
        self.text_browser_api_server_notice("client_success", "已获取配置文件中的 REST API 连接信息")

    def button_automatic_api_click(self):
        # Enable both RCON and REST API
        self.option_settings_dict['RCONEnabled'] = True
        self.option_settings_dict['RCONPort'] = 25575
        
        # Enable REST API if supported
        self.option_settings_dict['RESTAPIEnabled'] = True
        
        # Use existing RESTAPIPort if it's already set in the file, otherwise use default 8211
        if "RESTAPIPort" not in self.option_settings_dict:
            self.option_settings_dict['RESTAPIPort'] = 8211
            
        admin_password = random_password.random_string()
        self.option_settings_dict['AdminPassword'] = "\"" + admin_password + "\""
        new_option_settings = ','.join(f"{key}={value}" for key, value in self.option_settings_dict.items())
        settings_file_operation.save_setting(self.palserver_settings_path, new_option_settings)
        self.config["api_addr"] = "127.0.0.1"
        
        # Use the actual RESTAPIPort value from the settings
        self.config["api_port"] = int(self.option_settings_dict['RESTAPIPort'])
        self.config["api_password"] = admin_password
        self.save_config_json()
        self.line_edit_api_addr.setText(self.config["api_addr"])
        self.line_edit_api_port.setText(str(self.config["api_port"]))
        self.line_edit_api_password.setText(self.config["api_password"])
        self.text_browser_api_server_notice("client_success", "已自动配置 REST API 连接信息，已生成随机密码：" + admin_password)

    def line_edit_api_textchange(self):
        api_addr = self.line_edit_api_addr.text()
        api_port = self.line_edit_api_port.text()
        api_password = self.line_edit_api_password.text()
        self.button_test_connect.setEnabled(api_addr != "" and api_port != "")

    def button_test_connect_click(self):
        api_addr = self.line_edit_api_addr.text()
        api_port = self.line_edit_api_port.text()
        api_password = self.line_edit_api_password.text()
        if api_port.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "REST API 端口只能为数字，请重新输入！")
            return
        if int(api_port) < 1000 or int(api_port) > 65534:
            self.text_browser_api_server_notice("client_error", "REST API 端口需在1000~65534范围，请重新输入！")
            return

        # 尝试使用用户提供的密码进行认证
        self.pal_rest_api = PalRestAPI(api_addr, int(api_port), "admin", api_password)
        flag, api_result = self.pal_rest_api.get_server_info()
        
        # 如果认证失败，尝试常见的默认密码
        if flag is False and "Unauthorized" in api_result:
            self.text_browser_api_server_notice("client_message", "尝试使用默认密码...")
            # 尝试常见默认密码
            default_passwords = ['123456', 'admin', 'password']
            for pwd in default_passwords:
                # 跳过用户已经尝试过的密码
                if pwd == api_password:
                    continue
                    
                self.pal_rest_api = PalRestAPI(api_addr, int(api_port), "admin", pwd)
                flag, api_result = self.pal_rest_api.get_server_info()
                if flag is True:
                    # 使用成功的默认密码更新配置
                    api_password = pwd
                    self.line_edit_api_password.setText(pwd)
                    self.text_browser_api_server_notice("client_message", f"使用默认密码 {pwd} 认证成功！")
                    break
        
        if flag is False:
            self.rest_api_connect_flag = False
            self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
            return
        
        # Extract server version from the response
        server_version = api_result["version"] if "version" in api_result else "Unknown"
        self.label_server_version.setText(server_version)
        self.config["api_addr"] = api_addr
        self.config["api_port"] = int(api_port)
        self.config["api_password"] = api_password
        self.save_config_json()
        self.rest_api_connect_flag = True
        self.text_browser_api_server_notice("client_success", "REST API 服务器连接成功")

    def check_box_launch_options_click(self, flag):
        self.line_edit_launch_options.setEnabled(not flag)

    def button_game_start_click(self):
        if "palserver_path" not in self.config:
            self.text_browser_api_server_notice("client_error", "请先选择PalServer.exe服务端文件！")
            return

        game_port = self.line_edit_game_port.text()
        game_publicport = self.line_edit_game_publicport.text()
        game_player_limit = self.line_edit_game_player_limit.text()
        if game_port.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "游戏 连接端口只能为数字，请重新输入！")
            return
        if int(game_port) < 1000 or int(game_port) > 65534:
            self.text_browser_api_server_notice("client_error", "游戏 连接端口需在1000~65534范围，请重新输入！")
            return
        if game_publicport.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "游戏 查询端口只能为数字，请重新输入！")
            return
        if int(game_publicport) < 1000 or int(game_publicport) > 65534:
            self.text_browser_api_server_notice("client_error", "游戏 查询端口需在1000~65534范围，请重新输入！")
            return
        if game_player_limit.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "游戏 人数上限只能为数字，请重新输入！")
            return
        if int(game_player_limit) < 2 or int(game_player_limit) > 128:
            self.text_browser_api_server_notice("client_error", "游戏 人数上限需在2~128范围，请重新输入！")
            return

        self.config["launch_options_flag"] = self.check_box_launch_options.isChecked()
        self.config["launch_options_info"] = self.line_edit_launch_options.text()
        command = self.config["palserver_path"] + " -port=" + game_port + " -players=" + game_player_limit + " -publicip 0.0.0.0 -publicport " + game_publicport
        if self.config["launch_options_flag"]:
            command += " " + self.config["launch_options_info"]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        self.config["game_port"] = int(game_port)
        self.config["game_publicport"] = int(game_publicport)
        self.config["game_player_limit"] = int(game_player_limit)
        self.config["palserver_pid"] = process.pid
        self.save_config_json()
        self.text_browser_api_server_notice("client_success", "PalServer 服务器已启动，获取到进程PID：" + str(process.pid))
        self.server_run_flag = True
        self.server_run_time = datetime.now()

    def button_game_stop_click(self):
        if self.rest_api_connect_flag is False:
            self.text_browser_api_server_notice("client_error", "请先连接REST API ！")
            return
        command = "停止 游戏服务器"
        self.text_browser_api_server_notice("client_command", command)
        flag, api_result = self.pal_rest_api.shutdown_server(1, "服务器将在1秒后停止!!!")
        if flag is False:
            self.rest_api_connect_flag = False
            self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
            return
        self.text_browser_api_server_notice("server_success", "服务器关闭命令发送成功")
        self.server_run_flag = False

    def button_game_restart_click(self):
        if self.rest_api_connect_flag is False:
            self.text_browser_api_server_notice("client_error", "请先连接 REST API ！")
            return
        self.server_run_flag = False
        self.stop_countdown = 11
        self.stop_timer = QTimer(self)
        self.stop_timer.timeout.connect(self.broadcast_restart)
        self.stop_timer.start(1000)

    def broadcast_restart(self):
        self.stop_countdown -= 1
        if self.stop_countdown > 0:
            command = "广播 服务器将在 " + str(int(self.stop_countdown)) + " 秒后重启!!!"
            self.text_browser_api_server_notice("client_command", command)
            flag, api_result = self.pal_rest_api.announce_message("服务器将在 " + str(int(self.stop_countdown)) + " 秒后重启!!!")
            if flag is False:
                self.rest_api_connect_flag = False
                self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
                return
            self.text_browser_api_server_notice("server_success", "消息广播成功")
        elif self.stop_countdown == 0:
            command = "停止游戏服务器"
            self.text_browser_api_server_notice("client_command", command)
            flag, api_result = self.pal_rest_api.shutdown_server(1, "服务器将在0秒后重启!!!")
            if flag is False:
                self.rest_api_connect_flag = False
                self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
                return
            self.server_run_flag = False
            self.text_browser_api_server_notice("server_success", "服务器关闭命令发送成功")
        elif self.stop_countdown == -10:
            self.button_game_start_click()
        elif self.stop_countdown == -20:
            self.stop_timer.stop()
            self.button_test_connect_click()

    def button_game_kill_click(self):
        self.server_run_flag = False
        psu_proc = psutil.Process(self.config["palserver_pid"])
        pcs = psu_proc.children(recursive=True)
        for proc in pcs:
            os.kill(proc.pid, 9)
        self.text_browser_api_server_notice("client_success", "已强制停止服务端")

    def button_send_command_click(self):
        command = self.line_edit_command.text()
        if command == "":
            return
        self.text_browser_api_server_notice("client_command", command.replace("\n", ""))
        # For now, we'll map some common RCON commands to REST API equivalents
        if command.lower().startswith("broadcast "):
            message = command[10:]  # Extract message after "broadcast "
            flag, api_result = self.pal_rest_api.announce_message(message)
        elif command.lower().startswith("kickplayer "):
            user_id = command[11:]  # Extract user ID after "kickplayer "
            flag, api_result = self.pal_rest_api.kick_player(user_id)
        elif command.lower().startswith("banplayer "):
            user_id = command[10:]  # Extract user ID after "banplayer "
            flag, api_result = self.pal_rest_api.ban_player(user_id)
        elif command.lower() == "shutdown":
            flag, api_result = self.pal_rest_api.shutdown_server(1, "服务器将在1秒后关闭!!!")
        else:
            # For unrecognized commands, show a message indicating REST API should be used
            self.text_browser_api_server_notice("client_error", "命令不支持通过REST API执行。请使用特定的UI按钮或检查REST API文档。")
            return
            
        if flag is False:
            self.rest_api_connect_flag = False
            self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
            return
        self.text_browser_api_server_notice("server_success", "命令执行成功")
        self.line_edit_command.setText("")

    def show_player_list_menu(self, position):
        self.player_list_menu.exec_(self.table_widget_player_list.mapToGlobal(position))

    def button_countdown_stop_click(self):
        if self.rest_api_connect_flag is False:
            self.text_browser_api_server_notice("client_error", "请先连接 REST API ！")
            return
        value, flag = QInputDialog.getInt(self, "倒计时关服并广播", "设置多少时间后关服(秒)：", 60, 10, 999, 2)
        if flag:
            self.stop_countdown = value + 1
            self.stop_timer = QTimer(self)
            self.stop_timer.timeout.connect(self.broadcast_stop)
            self.stop_timer.start(1000)

    def broadcast_stop(self):
        self.stop_countdown -= 1
        if self.stop_countdown > 0:
            command = "广播 服务器将在 " + str(int(self.stop_countdown)) + " 秒后关闭!!!"
            self.text_browser_api_server_notice("client_command", command)
            flag, api_result = self.pal_rest_api.announce_message("服务器将在 " + str(int(self.stop_countdown)) + " 秒后关闭!!!")
            if flag is False:
                self.rest_api_connect_flag = False
                self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
                return
            self.text_browser_api_server_notice("server_success", "消息广播成功")
        elif self.stop_countdown == 0:
            self.button_game_stop_click()
            self.stop_timer.stop()

    def button_broadcast_click(self):
        value, flag = QInputDialog.getText(self, "广播", "请输入需要全服广播的内容：")
        if flag:
            command = "Broadcast " + value
            self.text_browser_api_server_notice("client_command", command)
            flag, api_result = self.pal_rest_api.announce_message(value)
            if flag is False:
                self.rest_api_connect_flag = False
                self.text_browser_api_server_notice("client_error", api_result.replace("\n", ""))
                return
            self.text_browser_api_server_notice("server_success", "消息广播成功")

    def check_box_crash_detection_click(self, flag):
        self.config["crash_detection_flag"] = flag
        self.save_config_json()

    def check_box_auto_restart_click(self, flag):
        self.config["auto_restart_flag"] = flag
        self.line_edit_auto_restart_time_limit.setEnabled(not flag)
        if flag:
            self.config["auto_restart_time_limit"] = int(self.line_edit_auto_restart_time_limit.text())
        self.save_config_json()

    def line_edit_auto_restart_time_limit_textchange(self):
        auto_restart_time_limit = self.line_edit_auto_restart_time_limit.text()
        if auto_restart_time_limit.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "重启时间 只能为数字，请重新输入！")
            return
        if int(auto_restart_time_limit) < 600 or int(auto_restart_time_limit) > 86400:
            self.text_browser_api_server_notice("client_error", "重启时间 需在600~86400范围，请重新输入！")
            return
        self.config["auto_restart_time_limit"] = int(auto_restart_time_limit)
        self.save_config_json()

    def create_menu_bar(self):
        """创建菜单栏并添加菜单项"""
        # 创建菜单栏
        menu_bar = self.menuBar()
        
        # 直接将MOD管理作为菜单项添加到菜单栏（不是子菜单）
        mod_action = QAction("MOD管理", self)
        mod_action.triggered.connect(self.open_mod_manager)
        menu_bar.addAction(mod_action)
        
        # 创建使用帮助菜单项
        help_action = QAction("使用帮助", self)
        help_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.bilibili.com/video/BV1z6vzBwEgc/")))
        menu_bar.addAction(help_action)
        
        # 直接将关于作为菜单项添加到菜单栏（不是子菜单）
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.about_clicked)
        menu_bar.addAction(about_action)

    def about_clicked(self):
        """关于菜单项点击事件"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        
        # 创建关于对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("关于 帕鲁服务器管理工具")
        dialog.setFixedSize(500, 400)
        
        # 创建主布局
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(40, 30, 40, 30)  # 设置外边距
        layout.setSpacing(20)  # 设置控件间距
        
        # 添加标题
        title_label = QLabel("帕鲁服务器管理工具V1.0   By 怀沙2049")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 添加说明文本
        info_text = "本工具使用Hualuoo的开源项目palworld-helper修改而来，重新使用Rest-api代替RCON用以管理服务器，并新增了MOD管理功能·"
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignJustify)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(info_label)
        
        # 添加功能列表标题
        features_title = QLabel("功能特性：")
        features_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(features_title)
        
        # 添加功能列表
        features = [
            "- 服务器配置管理",
            "- REST API连接与控制",
            "- 玩家管理",
            "- 自动存档备份",
            "- 游戏服务管理",
            "- 服务器资源监控",
            "- 服务器MOD安装"
        ]
        
        # 创建功能列表布局
        features_layout = QVBoxLayout()
        features_layout.setSpacing(5)
        
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setAlignment(Qt.AlignLeft)
            feature_label.setStyleSheet("font-size: 13px;")
            features_layout.addWidget(feature_label)
        
        layout.addLayout(features_layout)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(20)
        
        # 添加使用帮助按钮
        help_button = QPushButton("使用帮助")
        help_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.bilibili.com/video/BV1z6vzBwEgc/")))
        help_button.setFixedWidth(100)
        button_layout.addWidget(help_button)

        # 添加更新说明按钮
        update_button = QPushButton("更新说明")
        update_button.clicked.connect(self.show_update_notes)
        update_button.setFixedWidth(100)
        button_layout.addWidget(update_button)

        # 添加加入群聊按钮
        AddQun_button = QPushButton("加入群聊")
        AddQun_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://qm.qq.com/q/yRy3O2oQ6s")))
        AddQun_button.setFixedWidth(100)
        button_layout.addWidget(AddQun_button)
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        close_button.setFixedWidth(100)
        button_layout.addWidget(close_button)
        
        # 添加按钮布局到主布局
        layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec_()
    
    def open_mod_manager(self):
        """打开MOD管理器窗口"""
        try:
            self.mod_manager_window = ModManagerQt()
            self.mod_manager_window.show()
        except Exception as e:
            self.text_browser_api_server_notice("client_error", f"打开MOD管理器失败: {str(e)}")

    def show_update_notes(self):
        """显示更新说明"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
        
        announcement_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resource", "announcement.txt")
        content = ""
        try:
            if os.path.exists(announcement_path):
                with open(announcement_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "更新说明文件不存在"
        except Exception as e:
            content = f"读取更新说明失败: {str(e)}"
        
        dialog = QDialog(self)
        dialog.setWindowTitle("更新说明")
        dialog.setFixedSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-size: 14px;")
        layout.addWidget(text_edit)
        
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        close_button.setFixedWidth(100)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()

    def check_box_auto_restart_player_click(self, flag):
        self.config["auto_restart_player_flag"] = flag
        self.line_edit_auto_restart_player_limit.setEnabled(not flag)
        if flag:
            self.config["auto_restart_player_limit"] = int(self.line_edit_auto_restart_player_limit.text())
        self.save_config_json()

    def line_edit_auto_restart_player_limit_textchange(self):
        auto_restart_player_limit = self.line_edit_auto_restart_player_limit.text()
        if auto_restart_player_limit.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "重启人数限制 只能为数字，请重新输入！")
            return
        if int(auto_restart_player_limit) < 0 or int(auto_restart_player_limit) > 128:
            self.text_browser_api_server_notice("client_error", "重启人数限制 需在0~128范围，请重新输入！")
            return

    def check_box_auto_backup_click(self, flag):
        self.config["auto_backup_flag"] = flag
        self.line_edit_auto_backup_time_limit.setEnabled(not flag)
        if flag:
            self.config["auto_backup_time_limit"] = int(self.line_edit_auto_backup_time_limit.text())
        self.save_config_json()

    def line_edit_auto_backup_time_limit_textchange(self):
        auto_backup_time_limit = self.line_edit_auto_backup_time_limit.text()
        if auto_backup_time_limit.isdigit() is False:
            self.text_browser_api_server_notice("client_error", "备份时间间隔 只能为数字，请重新输入！")
            return
        if int(auto_backup_time_limit) < 600 or int(auto_backup_time_limit) > 86400:
            self.text_browser_api_server_notice("client_error", "备份时间间隔 需在600~86400范围，请重新输入！")
            return

    def button_select_backup_dir_click(self):
        qfile_dialog = QFileDialog.getExistingDirectory(self, "选择文件夹", None)
        if os.path.isdir(qfile_dialog):
            self.line_edit_backup_path.setText(qfile_dialog)
            self.config["backup_dir_path"] = qfile_dialog
            self.save_config_json()
            self.check_box_auto_backup.setEnabled(True)
            self.line_edit_auto_backup_time_limit.setEnabled(True)

    def button_edit_settings_click(self):
        if "palserver_path" in self.config is False:
            QMessageBox.critical(self, "错误", "请先配置 PalServer.exe 路径，再修改配置文件！")
            return
        if self.palserver_settings_path is None:
            QMessageBox.critical(self, "错误", "请先配置 PalServer.exe 路径，再修改配置文件！")
            return
        if os.path.isfile(self.palserver_settings_path) is False:
            QMessageBox.critical(self, "错误", "服务端路径下的 /Pal/Saved/Config/WindowsServer/PalWorldSettings.ini 配置文件不存在，请启动一次PalServer.exe，或检查服务端完整性！")
            return

        self.world_settings_window = world_settings_activity.Window()
        self.world_settings_window.show()

    def button_edit_server_name_click(self):
        self.option_settings_dict["ServerName"] = "\"" + self.text_edit_server_name.toPlainText().replace("\n", "") + "\""
        self.option_settings_dict["ServerDescription"] = "\"" + self.text_edit_server_description.toPlainText().replace("\n", "") + "\""
        new_option_settings = ','.join(f"{key}={value}" for key, value in self.option_settings_dict.items())
        settings_file_operation.save_setting(self.palserver_settings_path, new_option_settings)
        self.text_browser_api_server_notice("client_success", "服务器名称或服务器描述已修改成功，现可启动服务器查看。")
