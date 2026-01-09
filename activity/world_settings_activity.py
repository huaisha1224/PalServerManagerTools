#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
import shutil
import sys
import webbrowser

from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from utils import json_operation, settings_file_operation


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.module_path = os.path.split(sys.modules[__name__].__file__)[0] if sys.modules[__name__].__file__ else ""
        self.config_path = os.path.join(sys.argv[0], r"../config.json")
        self.config = json_operation.load_json(self.config_path)
        self.palserver_settings_path = None
        self.initUi()

    def initUi(self):
        # Create a simple window with just a text editor and buttons
        self.setWindowTitle("修改服务器配置文件")
        self.setFixedSize(880, 680)
        self.setWindowIcon(QIcon(os.path.join(self.module_path, r"../resource/favicon.ico")))
        self.palserver_settings_path = os.path.join(self.config["palserver_path"], r"../Pal/Saved/Config/WindowsServer/PalWorldSettings.ini")
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create a text edit widget to display the entire config file content
        self.text_edit = QTextEdit()
        main_layout.addWidget(self.text_edit)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Create save button
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.button_write_click)
        button_layout.addWidget(self.save_button)
        
        # Create default button
        self.default_button = QPushButton("恢复默认配置")
        self.default_button.clicked.connect(self.button_default_click)
        button_layout.addWidget(self.default_button)
        
        # Create online editor button
        self.online_editor_button = QPushButton("在线编辑配置")
        self.online_editor_button.clicked.connect(self.open_online_editor)
        button_layout.addWidget(self.online_editor_button)
        
        main_layout.addLayout(button_layout)
        
        # Add hint text
        hint_text = "提示：如果知道如何修改配置参数可以在上面的网站上修改好之后保存到这里\n网址：https://pal-conf.bluefissure.com/"
        hint_label = QPushButton(hint_text)
        hint_label.setFlat(True)
        hint_label.clicked.connect(self.open_online_editor)
        hint_label.setStyleSheet("text-align: left; color: gray; border: none;")
        main_layout.addWidget(hint_label)
        
        # Load the config file content
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.palserver_settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_edit.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取配置文件: {str(e)}")

    def button_write_click(self):
        try:
            content = self.text_edit.toPlainText()
            with open(self.palserver_settings_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, "成功", "服务器配置文件已修改！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存配置文件: {str(e)}")

    def button_default_click(self):
        try:
            settings_file_operation.default_setting(self.palserver_settings_path)
            self.load_settings()
            QMessageBox.information(self, "成功", "服务器配置文件已还原成默认值！")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "错误", f"找不到官方默认配置文件: {str(e)}\n请确保选择了正确的PalServer路径。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法恢复默认配置: {str(e)}")
            
    def open_online_editor(self):
        webbrowser.open("https://pal-conf.bluefissure.com/")