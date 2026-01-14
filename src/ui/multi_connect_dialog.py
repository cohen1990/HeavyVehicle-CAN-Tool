#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多硬件连接对话框 - 最小化版本
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QComboBox, QLineEdit,
                             QSpinBox, QCheckBox, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

class MultiConnectDialog(QDialog):
    """多硬件连接对话框"""
    
    devices_connected = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("连接硬件")
        self.setMinimumSize(400, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 设备配置
        group = QGroupBox("设备设置")
        form = QFormLayout()
        
        self.cb_type = QComboBox()
        self.cb_type.addItems(["虚拟设备", "NI USB-8502", "Kvaser"])
        form.addRow("设备类型:", self.cb_type)
        
        self.cb_port = QComboBox()
        self.cb_port.addItems(["virtual0", "virtual1", "Dev1/CNI0"])
        form.addRow("端口:", self.cb_port)
        
        self.cb_baudrate = QComboBox()
        self.cb_baudrate.addItems(["500000", "250000", "125000"])
        form.addRow("波特率:", self.cb_baudrate)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        # 按钮
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        btn_ok = QPushButton("连接")
        btn_ok.clicked.connect(self.on_connect)
        buttons.addWidget(btn_ok)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        
        layout.addLayout(buttons)
        self.setLayout(layout)
    
    def on_connect(self):
        """连接设备"""
        device_info = {
            'type': self.cb_type.currentText(),
            'port': self.cb_port.currentText(),
            'baudrate': self.cb_baudrate.currentText()
        }
        self.devices_connected.emit([device_info])
        self.accept()

