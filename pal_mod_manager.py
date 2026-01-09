#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
import sys
import json
import requests
import threading
import zipfile
import shutil
import tempfile
import logging
from datetime import datetime
from PyQt5.QtGui import QIcon

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, 
    QTreeWidget, QTreeWidgetItem, QHeaderView, QRadioButton, 
    QFrame, QProgressBar, QGroupBox, QTextEdit, QSplitter
)
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
# 配置日志（禁用输出）
app_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.CRITICAL + 1,  # 设置一个比CRITICAL更高的级别，完全禁用日志输出
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # 移除所有日志处理器
    ]
)
logger = logging.getLogger(__name__)

class DownloadThread(QThread):
    """下载线程"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        
    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 更新进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            self.progress_signal.emit(int(progress))
            
            self.finished_signal.emit(True, "下载成功")
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class InstallThread(QThread):
    """安装线程"""
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, app, mods):
        super().__init__()
        self.app = app
        self.mods = mods
        
    def run(self):
        success_count = 0
        failed_count = 0
        failed_mods = []
        
        total_ops = len(self.mods)
        
        for i, item in enumerate(self.mods):
            try:
                if "_uninstall" in item:
                    # 执行卸载操作
                    mod = item["mod"]
                    self.status_signal.emit(f"正在卸载 {i+1}/{total_ops} 个操作: {mod.get('DisplayName')}")
                    self.app._uninstall_single_mod(mod)
                    success_count += 1
                    logger.info(f"成功卸载MOD: {mod.get('DisplayName')}")
                else:
                    # 执行安装操作
                    mod = item
                    self.status_signal.emit(f"正在安装 {i+1}/{total_ops} 个操作: {mod.get('DisplayName')}")
                    self.app._install_single_mod(mod)
                    success_count += 1
                    logger.info(f"成功安装MOD: {mod.get('DisplayName')}")
            except Exception as e:
                failed_count += 1
                mod_display_name = item["mod"].get('DisplayName', '未知MOD') if "_uninstall" in item else item.get('DisplayName', '未知MOD')
                failed_mods.append((mod_display_name, str(e)))
                logger.error(f"{'卸载' if '_uninstall' in item else '安装'}MOD失败 {mod_display_name}: {e}")
            
            # 更新进度
            progress = ((i + 1) / total_ops) * 100
            self.progress_signal.emit(int(progress))
        
        # 完成
        if failed_count == 0:
            msg = f"成功处理 {success_count} 个操作"
            self.finished_signal.emit(True, msg)
        else:
            msg = f"操作完成，成功 {success_count} 个，失败 {failed_count} 个"
            details = "\n".join([f"{name}: {error}" for name, error in failed_mods])
            self.finished_signal.emit(False, f"{msg}\n\n失败详情：\n{details}")

class UninstallThread(QThread):
    """卸载线程"""
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, app, mods):
        super().__init__()
        self.app = app
        self.mods = mods
        
    def run(self):
        success_count = 0
        failed_count = 0
        failed_mods = []
        
        total_mods = len(self.mods)
        
        for i, mod in enumerate(self.mods):
            try:
                self.status_signal.emit(f"正在卸载 {i+1}/{total_mods} 个MOD: {mod.get('DisplayName')}")
                self.app._uninstall_single_mod(mod)
                success_count += 1
                logger.info(f"成功卸载MOD: {mod.get('DisplayName')}")
            except Exception as e:
                failed_count += 1
                failed_mods.append((mod.get('DisplayName', '未知MOD'), str(e)))
                logger.error(f"卸载MOD失败 {mod.get('DisplayName')}: {e}")
        
        # 完成
        if failed_count == 0:
            msg = f"成功卸载 {success_count} 个MOD"
            self.finished_signal.emit(True, msg)
        else:
            msg = f"卸载完成，成功 {success_count} 个，失败 {failed_count} 个"
            details = "\n".join([f"{name}: {error}" for name, error in failed_mods])
            self.finished_signal.emit(False, f"{msg}\n\n失败详情：\n{details}")

class RefreshThread(QThread):
    """刷新MOD列表线程"""
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
    def run(self):
        try:
            response = requests.get(self.app.mods_config_url, timeout=10)
            response.raise_for_status()
            
            self.app.mods_config = response.json()
            self.app.mods_list = self.app.mods_config.get("Platform", [])
            
            # 检查已安装的MOD
            self.app._check_installed_mods()
            
            logger.info(f"成功获取MOD列表，共 {len(self.app.mods_list)} 个MOD")
            self.finished_signal.emit(True, f"成功获取 {len(self.app.mods_list)} 个MOD")
            
        except Exception as e:
            logger.error(f"获取MOD列表失败: {e}")
            self.finished_signal.emit(False, f"获取MOD列表失败: {str(e)}")

class ModManagerQt(QMainWindow):
    """PyQt5版本的MOD管理器"""
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.game_path = ""
        self.mods_config = {}
        self.mods_list = []
        self.installed_mods = []
        self.selected_mods = set()
        self.is_downloading = False
        
        # 应用版本信息
        # self.version = "2025.12.19.1"
        # self.tool_name = "PalServerManager"
        
        # MOD配置URL
        self.mods_config_url = "https://hs2049.cn/tools/Palword/PalServer.json"
        
        # 自定义角色，用于在TreeWidgetItem中存储MOD信息
        self.MOD_DATA_ROLE = Qt.UserRole
        
        # 清理残留的临时文件
        self.cleanup_temp_files()
        
        # 加载UI文件
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "mod_manager.ui")
        loadUi(ui_path, self)
        
        # 设置窗口
        self.setWindowTitle("帕鲁服务MOD安装") 
        self.setFixedSize(1130, 610)
        # 设置窗口图标
        self.setWindowIcon(QIcon(os.path.join(app_dir, r"resource/favicon.ico")))
        
        # 连接信号槽
        self.setup_connections()
        
        # 初始化控件
        self.pushButton_install_ue4ss.hide()  # 初始隐藏
        self.progressBar.hide()  # 初始隐藏
        
        # 设置服务端路径相关控件为禁用状态
        self.lineEdit_path.setDisabled(True)  # 禁用服务端路径输入框
        self.pushButton_select_path.setDisabled(True)  # 禁用选择游戏路径按钮
        self.pushButton_verify_path.setDisabled(True)  # 禁用验证路径按钮
        self.textEdit_instructions.setDisabled(True)  # 禁用使用说明文本框
        
        # 自动加载游戏路径
        self.load_game_path()
        
        # 延迟200毫秒后更新UE4SS状态（确保UI已完全初始化）
        QTimer.singleShot(200, self._update_ue4ss_status)
        
        # 延迟1秒后自动获取MOD列表（确保游戏路径已加载）
        QTimer.singleShot(1000, self._auto_refresh_mods_list)
        
        # 延迟2秒后检查更新（确保应用完全初始化）
        QTimer.singleShot(2000, self._check_updates)
    
    def setup_connections(self):
        """连接信号与槽"""
        # 按钮信号连接
        self.pushButton_select_path.clicked.connect(self.select_game_path)
        self.pushButton_verify_path.clicked.connect(self.verify_game_path)
        self.pushButton_install_ue4ss.clicked.connect(self.install_ue4ss)
        self.pushButton_refresh.clicked.connect(self.refresh_mods_list)
        self.pushButton_install.clicked.connect(self.install_selected_mods)
        self.pushButton_uninstall.clicked.connect(self.uninstall_selected_mods)
        
        # 搜索和过滤信号连接
        self.lineEdit_search.textChanged.connect(self.filter_mods)
        self.radioButton_all.toggled.connect(self.filter_mods)
        self.radioButton_installed.toggled.connect(self.filter_mods)
        
        # TreeWidget信号连接
        self.treeWidget_mods.itemClicked.connect(self._on_tree_click)
        self.treeWidget_mods.itemPressed.connect(self._on_tree_click)
        self.treeWidget_mods.header().sectionClicked.connect(self._on_select_column_click)
        
        # 初始化使用说明
        instructions_content = """1. 请先在主程序中设置游戏路径
2. 安装UE4SS前置依赖，否则部分MOD可能无法使用
3. 同一分组下的MOD只能安装一个，安装新MOD时会自动卸载同分组的旧MOD
4. 安装/卸载MOD时请务必要先停止帕鲁服务器
5. 如果遇到问题，请先尝试刷新MOD列表或重启程序"""
        self.textEdit_instructions.setText(instructions_content)
    
    def select_game_path(self):
        """选择游戏路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "请选择幻兽帕鲁服务器安装目录下的PalServer.exe文件", 
            "", "可执行文件 (*.exe);;所有文件 (*)"
        )
        
        if file_path:
            # 验证选择的文件是否为PalServer.exe
            filename = os.path.basename(file_path)
            if filename.lower() == "palserver.exe":
                # 提取目录路径
                directory_path = os.path.dirname(file_path)
                self.lineEdit_path.setText(directory_path)
                self.game_path = directory_path
                self.save_game_path()
                logger.info(f"选择游戏路径: {directory_path}")
                # 更新UE4SS状态
                self._update_ue4ss_status()
            else:
                QMessageBox.critical(self, "错误", "请选择正确的PalServer.exe文件")
                logger.error(f"选择了错误的文件: {file_path}")
    
    def _check_ue4ss_installed(self):
        """检查UE4SS是否安装成功"""
        if not self.game_path:
            return False
            
        # 构建UE4SS检测路径
        ue4ss_path = os.path.join(
            os.path.abspath(self.game_path),
            "Pal", "Binaries", "Win64", "dwmapi.dll"
        )
        
        logger.info(f"检查UE4SS路径: {ue4ss_path}, 存在: {os.path.exists(ue4ss_path)}")
        return os.path.exists(ue4ss_path)
    
    def verify_game_path(self):
        """验证游戏路径"""
        path = self.lineEdit_path.text()
        if not path:
            QMessageBox.critical(self, "错误", "请先选择游戏路径")
            return
            
        # 检查路径是否有效，并验证其中是否包含PalServer.exe
        game_exe = os.path.join(path, "PalServer.exe")
        if os.path.isdir(path) and os.path.exists(game_exe):
            QMessageBox.information(self, "成功", "游戏路径验证通过")
            self.game_path = path
            self.save_game_path()
            logger.info(f"游戏路径验证通过: {path}")
            # 更新UE4SS状态
            self._update_ue4ss_status()
        else:
            QMessageBox.critical(self, "错误", "未找到PalServer.exe，请检查路径")
            logger.error(f"游戏路径验证失败: {path}")
    
    def install_ue4ss(self):
        """安装UE4SS"""
        if not self.game_path:
            QMessageBox.critical(self, "错误", "请先设置游戏路径")
            return
            
        # 确认安装
        if QMessageBox.question(self, "确认安装", "确定要安装UE4SS吗？这将解压UE4SS到游戏目录。") == QMessageBox.Yes:
            try:
                # 设置安装路径
                install_path = os.path.join(
                    os.path.abspath(self.game_path),
                    "Pal", "Binaries", "Win64"
                )
                
                # UE4SS.zip文件路径
                ue4ss_zip_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "resource", "UE4SS.zip"
                )
                
                # 检查UE4SS.zip是否存在
                if not os.path.exists(ue4ss_zip_path):
                    QMessageBox.critical(self, "错误", "未找到UE4SS.zip文件，请确保Resource目录下存在该文件")
                    logger.error(f"UE4SS.zip不存在: {ue4ss_zip_path}")
                    return
                
                # 显示进度
                self.statusBar().showMessage("正在安装UE4SS...")
                
                # 解压UE4SS.zip到安装路径
                with zipfile.ZipFile(ue4ss_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(install_path)
                
                logger.info(f"UE4SS安装成功: 解压到 {install_path}")
                QMessageBox.information(self, "成功", "UE4SS安装完成")
                
                # 更新UE4SS状态
                self._update_ue4ss_status()
                
                # 刷新MOD列表
                self._auto_refresh_mods_list()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"UE4SS安装失败: {str(e)}")
                logger.error(f"UE4SS安装失败: {e}")
            finally:
                self.statusBar().showMessage("就绪")
    
    def load_game_path(self):
        """加载保存的游戏路径"""
        try:
            # 使用与主程序相同的方式来获取配置文件路径
            config_path = os.path.join(sys.argv[0], r"../config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    if "palserver_path" in config:
                        # 检查路径是否是一个文件（完整的PalServer.exe路径）
                        if os.path.isfile(config["palserver_path"]):
                            # 提取目录路径
                            game_dir = os.path.dirname(config["palserver_path"])
                            self.lineEdit_path.setText(game_dir)
                            self.game_path = game_dir
                        else:
                            # 如果已经是目录路径，直接使用
                            self.lineEdit_path.setText(config["palserver_path"])
                            self.game_path = config["palserver_path"]
                        logger.info(f"加载游戏路径: {self.game_path}")
                        # 更新UE4SS状态
                        self._update_ue4ss_status()
        except Exception as e:
            logger.error(f"加载游戏路径失败: {e}")
    
    def _update_ue4ss_status(self):
        """更新UE4SS状态显示"""
        if not self.game_path:
            self.label_ue4ss_status.setText("UE4SS: 未检测（未设置游戏路径）")
            self.pushButton_install_ue4ss.hide()  # 隐藏安装按钮
            return
            
        if self._check_ue4ss_installed():
            self.label_ue4ss_status.setText("UE4SS: ✅ 已安装")
            logger.info("UE4SS已安装")
            self.pushButton_install_ue4ss.hide()  # 隐藏安装按钮
        else:
            self.label_ue4ss_status.setText("UE4SS: ❌ 未安装")
            logger.info("UE4SS未安装")
            self.pushButton_install_ue4ss.show()  # 显示安装按钮
    
    def _check_updates(self):
        """检查应用更新"""
        logger.info("正在检查更新...")
        # MOD管理器不使用更新检查功能
    
    def save_game_path(self):
        """保存游戏路径"""
        try:
            # 使用与主程序相同的方式来获取配置文件路径
            config_path = os.path.join(sys.argv[0], r"../config.json")
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
            
            config["palserver_path"] = self.game_path
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
                logger.info(f"保存游戏路径: {self.game_path}")
                
            # 保存游戏路径后自动获取MOD列表并更新UE4SS状态
            self._auto_refresh_mods_list()
            self._update_ue4ss_status()
        except Exception as e:
            logger.error(f"保存游戏路径失败: {e}")
    
    def _auto_refresh_mods_list(self):
        """自动获取MOD列表（启动时调用）"""
        if self.game_path:
            self.statusBar().showMessage("正在获取MOD列表...")
            # 创建刷新线程
            self.refresh_thread = RefreshThread(self)
            self.refresh_thread.finished_signal.connect(self._refresh_mods_list_finished)
            self.refresh_thread.start()
    
    def refresh_mods_list(self):
        """刷新MOD列表"""
        if not self.game_path:
            QMessageBox.critical(self, "错误", "请先设置并验证游戏路径")
            return
            
        self.statusBar().showMessage("正在获取MOD列表...")
        # 创建刷新线程
        self.refresh_thread = RefreshThread(self)
        self.refresh_thread.finished_signal.connect(self._refresh_mods_list_finished)
        self.refresh_thread.start()
    
    def _refresh_mods_list_finished(self, success, message):
        """刷新MOD列表完成后的处理"""
        if success:
            self._update_mods_tree()
            self.statusBar().showMessage(message)
        else:
            QMessageBox.critical(self, "错误", message)
            self.statusBar().showMessage("获取MOD列表失败")
    
    def _check_installed_mods(self):
        """检查已安装的MOD"""
        self.installed_mods = []
        
        if not self.game_path:
            for mod in self.mods_list:
                mod["installed"] = False
            return
            
        # 确保路径是绝对路径
        game_path_abs = os.path.abspath(self.game_path)
        
        for mod in self.mods_list:
            mod_name = mod.get("ModName", "")
            install_path = mod.get("InstallLocation", "")
            
            if mod_name and install_path:
                full_path = os.path.join(game_path_abs, install_path, mod_name)
                if os.path.exists(full_path):
                    mod["installed"] = True
                    self.installed_mods.append(mod)
                else:
                    mod["installed"] = False
            else:
                mod["installed"] = False
    
    def _update_mods_tree(self):
        """更新MOD列表树"""
        # 清空现有内容
        self.treeWidget_mods.clear()
        
        # 添加MOD
        for i, mod in enumerate(self.mods_list):
            # 检查是否匹配搜索条件
            if not self._filter_mod(mod):
                continue
                
            # 状态显示
            status = "已安装" if mod.get("installed", False) else "未安装"
            
            # 获取当前选中状态
            is_selected = mod.get("selected", False)
            select_mark = "✅" if is_selected else "⚪"
            
            # 创建树节点
            item = QTreeWidgetItem([
                select_mark,  # 选择标记
                mod.get("DisplayName", ""),
                mod.get("Description", "无描述"),
                mod.get("Author", "未知"),
                mod.get("NexusID", "/"),
                status
            ])
            
            # 设置背景色
            if i % 2 == 0:
                item.setBackground(0, Qt.lightGray)
                item.setBackground(1, Qt.lightGray)
                item.setBackground(2, Qt.lightGray)
                item.setBackground(3, Qt.lightGray)
                item.setBackground(4, Qt.lightGray)
                item.setBackground(5, Qt.lightGray)
            
            # 设置状态颜色
            if status == "已安装":
                item.setForeground(5, Qt.green)
            else:
                item.setForeground(5, Qt.red)
            
            # 将MOD信息直接存储在TreeWidgetItem中
            item.setData(0, self.MOD_DATA_ROLE, mod)
            logger.info(f"创建MOD节点: {mod.get('DisplayName', '')}, 选中状态: {is_selected}")
            
            # 添加到树中
            self.treeWidget_mods.addTopLevelItem(item)
    
    def _on_tree_click(self, item, column):
        """处理TreeWidget点击事件"""
        # 无论点击哪一列，都处理选中状态的切换
        # 获取MOD信息
        mod = item.data(0, self.MOD_DATA_ROLE)
        
        # 切换选择状态
        current_selected = mod.get("selected", False)
        new_selected = not current_selected
        mod["selected"] = new_selected
        
        # 记录调试信息
        logger.info(f"点击了MOD: {mod.get('DisplayName', '')}, 当前选中状态: {current_selected}, 新选中状态: {new_selected}")
        
        # 如果是选择状态，且MOD属于某个分组，则取消同分组内其他所有MOD的选择
        if new_selected and "Array" in mod:
            current_array = mod["Array"]
            
            # 遍历所有MOD，取消同分组内其他MOD的选择
            for tree_item in self.treeWidget_mods.findItems("", Qt.MatchContains | Qt.MatchRecursive):
                if tree_item != item:
                    other_mod = tree_item.data(0, self.MOD_DATA_ROLE)
                    if other_mod and "Array" in other_mod and other_mod["Array"] == current_array:
                        other_mod["selected"] = False
                        # 更新界面显示 - 未选中
                        tree_item.setText(0, "⚪")
        
        # 更新当前MOD的显示 - 选中显示绿色对勾，未选中显示白色圆点
        select_mark = "✅" if new_selected else "⚪"
        item.setText(0, select_mark)
    
    def _on_select_column_click(self, column):
        """处理选择列标题点击事件（全选/取消全选）"""
        if column != 0:  # 只处理选择列的点击
            return
        
        # 检查当前是否有选中的项目
        has_selected = any(mod.get("selected", False) for mod in self.mods_list)
        
        # 如果要取消全选
        if has_selected:
            for item in self.treeWidget_mods.findItems("", Qt.MatchContains | Qt.MatchRecursive):
                mod = item.data(0, self.MOD_DATA_ROLE)
                if mod:
                    mod["selected"] = False
                    # 更新界面显示 - 未选中
                    item.setText(0, "⚪")
        else:
            # 如果要全选，为每个分组选择第一个MOD
            selected_arrays = set()
            
            for item in self.treeWidget_mods.findItems("", Qt.MatchContains | Qt.MatchRecursive):
                mod = item.data(0, self.MOD_DATA_ROLE)
                
                # 检查MOD是否属于某个分组
                if mod and "Array" in mod:
                    array_id = mod["Array"]
                    
                    # 如果该分组还没有选中任何MOD，则选择当前MOD
                    if array_id not in selected_arrays:
                        mod["selected"] = True
                        # 更新界面显示 - 选中
                        item.setText(0, "✅")
                        selected_arrays.add(array_id)
                    else:
                        # 否则取消选择
                        mod["selected"] = False
                        item.setText(0, "⚪")
                elif mod:
                    # 不属于任何分组的MOD，直接选择
                    mod["selected"] = True
                    # 更新界面显示 - 选中
                    item.setText(0, "✅")
    
    def _filter_mod(self, mod):
        """过滤MOD"""
        # 搜索过滤
        search_text = self.lineEdit_search.text().lower()
        
        if search_text:
            if search_text not in mod.get("DisplayName", "").lower() and \
               search_text not in mod.get("Description", "").lower():
                return False
        
        # 显示模式过滤
        if self.radioButton_installed.isChecked():
            return mod.get("installed", False)
        
        return True
    
    def filter_mods(self):
        """过滤MOD列表"""
        self._update_mods_tree()
    
    def install_selected_mods(self):
        """安装选中的MOD"""
        if not self.game_path:
            QMessageBox.critical(self, "错误", "请先设置游戏路径")
            return
            
        # 检查UE4SS是否已安装
        if not self._check_ue4ss_installed():
            QMessageBox.critical(self, "错误", "安装MOD前，请先安装UE4SS")
            return
            
        # 更新已安装MOD列表，确保分组互斥逻辑的准确性
        self._check_installed_mods()
            
        # 获取选中的MOD - 直接根据TreeWidgetItem的文本内容判断是否选中
        selected_mods = []
        total_items = 0
        has_mod_data = 0
        
        logger.info("开始获取选中的MOD...")
        
        for item in self.treeWidget_mods.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            total_items += 1
            mod = item.data(0, self.MOD_DATA_ROLE)
            
            if mod:
                has_mod_data += 1
                display_name = mod.get("DisplayName", "未知")
                # 直接根据TreeWidgetItem的文本内容判断是否选中
                is_selected = item.text(0) == "✅"
                logger.info(f"MOD: {display_name}, 选中状态: {is_selected}")
                
                if is_selected:
                    selected_mods.append(mod)
        
        logger.info(f"总节点数: {total_items}, 有MOD数据的节点数: {has_mod_data}, 选中的MOD数: {len(selected_mods)}")
        
        if not selected_mods:
            QMessageBox.information(self, "提示", "请先选择要安装的MOD")
            return
        
        # 检测同类型MOD（Array=1）的安装情况，需要先卸载后安装
        mods_to_process = []
        for mod in selected_mods:
            # 添加当前要安装的MOD
            mods_to_process.append(mod)
            
            # 如果是Array类型（同类型只能安装一个），检查是否有已安装的同类型MOD
            if "Array" in mod:
                current_array = mod["Array"]
                
                # 查找已安装的同类型MOD
                for installed_mod in self.installed_mods:
                    if "Array" in installed_mod and installed_mod["Array"] == current_array and installed_mod != mod:
                        # 需要先卸载已安装的同类型MOD
                        mods_to_process.insert(0, {"_uninstall": True, "mod": installed_mod})
                        logger.info(f"检测到同类型MOD已安装: {installed_mod.get('DisplayName', '未知')}, 需要先卸载")
        
        # 准备显示确认提示
        install_mod_names = []
        uninstall_mod_names = []
        
        for item in mods_to_process:
            if "_uninstall" in item:
                uninstall_mod_names.append(item["mod"].get("DisplayName", "未知"))
            else:
                install_mod_names.append(item.get("DisplayName", "未知"))
        
        # 构建确认消息
        confirm_message = ""
        if uninstall_mod_names:
            confirm_message += f"需要先卸载以下同类型MOD：\n\n{chr(10).join(uninstall_mod_names)}\n\n"
        if install_mod_names:
            confirm_message += f"然后安装以下MOD：\n\n{chr(10).join(install_mod_names)}"
        
        reply = QMessageBox.question(self, "确认操作", confirm_message, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        # 开始处理（卸载和安装）
        total_ops = len(mods_to_process)
        self.statusBar().showMessage(f"正在处理 {total_ops} 个操作...")
        self.progressBar.show()
        self.progressBar.setValue(0)
        
        # 创建安装线程，传递需要处理的MOD列表（包含卸载和安装操作）
        self.install_thread = InstallThread(self, mods_to_process)
        self.install_thread.progress_signal.connect(self.progressBar.setValue)
        self.install_thread.status_signal.connect(self.statusBar().showMessage)
        self.install_thread.finished_signal.connect(self._install_mods_finished)
        self.install_thread.start()
    
    def _install_mods_finished(self, success, message):
        """安装MOD完成后的处理"""
        self.progressBar.hide()
        
        if success:
            QMessageBox.information(self, "安装完成", message)
        else:
            QMessageBox.critical(self, "安装完成", message)
        
        # 刷新列表
        self._check_installed_mods()
        self._update_mods_tree()
        self.statusBar().showMessage("安装完成")
    
    def _install_single_mod(self, mod):
        """安装单个MOD"""
        download_url = mod.get("DownloadUrl", "")
        mod_name = mod.get("ModName", "")
        install_path = mod.get("InstallLocation", "")
        
        if not all([download_url, mod_name, install_path]):
            raise ValueError("MOD信息不完整")
        
        # 确保路径是绝对路径
        game_path_abs = os.path.abspath(self.game_path)
        
        # 如果MOD属于某个分组，先卸载同分组已安装的其他MOD
        if "Array" in mod:
            current_array = mod["Array"]
            # 遍历已安装的MOD，卸载同分组的MOD
            for installed_mod in self.installed_mods[:]:  # 使用副本避免迭代中修改列表
                if "Array" in installed_mod and installed_mod["Array"] == current_array:
                    logger.info(f"卸载同分组MOD: {installed_mod.get('DisplayName')}")
                    self._uninstall_single_mod(installed_mod)
        
        # 1. 创建临时目录（使用系统临时目录）
        temp_dir = os.path.join(tempfile.gettempdir(), "pal_mod_manager")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 2. 下载并安装主MOD文件
        self._download_and_install_mod(download_url, mod_name, install_path, game_path_abs, temp_dir)
        
        # 3. 处理data数组中的子文件
        data_files = mod.get("data", [])
        for i, sub_file in enumerate(data_files):
            sub_download_url = sub_file.get("DownloadUrl", "")
            sub_mod_name = sub_file.get("ModName", "")
            sub_install_path = sub_file.get("InstallLocation", "")
            
            if sub_download_url and sub_mod_name and sub_install_path:
                logger.info(f"安装子文件 {i+1}/{len(data_files)}: {sub_mod_name}")
                self._download_and_install_mod(sub_download_url, sub_mod_name, sub_install_path, game_path_abs, temp_dir)
        
        # 4. 清理临时文件
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def _download_and_install_mod(self, download_url, mod_name, install_path, game_path_abs, temp_dir):
        """下载并安装单个MOD文件"""
        # 下载MOD文件
        zip_path = os.path.join(temp_dir, f"{mod_name}.zip")
        self._download_file(download_url, zip_path)
        
        # 解压MOD
        extract_dir = os.path.join(temp_dir, mod_name)
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 安装MOD文件
        final_install_path = os.path.join(game_path_abs, install_path)
        os.makedirs(final_install_path, exist_ok=True)
        
        # 复制解压后的文件
        for item in os.listdir(extract_dir):
            src_path = os.path.join(extract_dir, item)
            dst_path = os.path.join(final_install_path, item)
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                if os.path.exists(dst_path):
                    os.remove(dst_path)
                shutil.copy2(src_path, dst_path)
    
    def _download_file(self, url, save_path):
        """下载文件"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
        except requests.exceptions.Timeout:
            raise Exception(f"下载超时: {url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误 {e.response.status_code}: {url}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"网络连接错误: {url}")
        except IOError as e:
            raise Exception(f"文件写入错误: {save_path}, 错误: {e}")
        except Exception as e:
            raise Exception(f"下载失败: {url}, 错误: {str(e)}")
    
    def uninstall_selected_mods(self):
        """卸载选中的MOD"""
        # 获取选中的MOD - 直接根据TreeWidgetItem的文本内容判断是否选中
        selected_mods = []
        for item in self.treeWidget_mods.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            mod = item.data(0, self.MOD_DATA_ROLE)
            if mod:
                # 直接根据TreeWidgetItem的文本内容判断是否选中
                is_selected = item.text(0) == "✅"
                if is_selected:
                    selected_mods.append(mod)
        
        if not selected_mods:
            QMessageBox.information(self, "提示", "请先选择要卸载的MOD")
            return
            
        # 确认卸载 - 显示MOD名称列表
        mod_names = "\n".join([mod.get("DisplayName", "未知MOD") for mod in selected_mods])
        if QMessageBox.question(self, "确认卸载", f"确定要卸载以下 {len(selected_mods)} 个MOD吗？\n\n{mod_names}") == QMessageBox.Yes:
            self.statusBar().showMessage(f"正在卸载 {len(selected_mods)} 个MOD...")
            
            # 创建卸载线程
            self.uninstall_thread = UninstallThread(self, selected_mods)
            self.uninstall_thread.status_signal.connect(self.statusBar().showMessage)
            self.uninstall_thread.finished_signal.connect(self._uninstall_mods_finished)
            self.uninstall_thread.start()
    
    def _uninstall_mods_finished(self, success, message):
        """卸载MOD完成后的处理"""
        if success:
            QMessageBox.information(self, "卸载完成", message)
        else:
            QMessageBox.critical(self, "卸载完成", message)
        
        # 刷新列表
        self._check_installed_mods()
        self._update_mods_tree()
        self.statusBar().showMessage("卸载完成")
    
    def _uninstall_single_mod(self, mod):
        """卸载单个MOD"""
        mod_name = mod.get("ModName", "")
        install_path = mod.get("InstallLocation", "")
        
        if not all([mod_name, install_path]):
            raise ValueError("MOD信息不完整")
        
        # 确保路径是绝对路径
        game_path_abs = os.path.abspath(self.game_path)
        
        # 删除MOD文件
        full_path = os.path.join(game_path_abs, install_path, mod_name)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
        
        # 检查并删除空目录
        install_dir = os.path.join(game_path_abs, install_path)
        if os.path.exists(install_dir) and not os.listdir(install_dir):
            os.rmdir(install_dir)
    
    def cleanup_temp_files(self):
        """清理残留的临时文件"""
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "pal_mod_manager")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"清理残留临时文件: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def run(self):
        """运行应用"""
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModManagerQt()
    window.run()
    sys.exit(app.exec_())
