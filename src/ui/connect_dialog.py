#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件连接对话框 - 修复版
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QGroupBox, QGridLayout,
    QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from src.hardware.can_manager import DeviceType, can_manager

class ConnectDialog(QDialog):
    """硬件连接对话框"""
    
    connected = pyqtSignal(str, str, int)  # port, device_type, baudrate
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("连接硬件")
        self.setMinimumWidth(400)
        self.setModal(True)  # 设置为模态对话框
        self.init_ui()
        self.refresh_devices()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 设备类型选择
        device_group = QGroupBox("设备选择")
        device_layout = QGridLayout()
        
        device_layout.addWidget(QLabel("设备类型:"), 0, 0)
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItem("虚拟设备", DeviceType.VIRTUAL)  # 虚拟设备放在前面
        self.device_type_combo.addItem("NI USB-8502", DeviceType.NI_8502)
        self.device_type_combo.addItem("Kvaser", DeviceType.Kvaser)
        self.device_type_combo.currentIndexChanged.connect(self.on_device_type_changed)
        device_layout.addWidget(self.device_type_combo, 0, 1)
        
        device_layout.addWidget(QLabel("端口:"), 1, 0)
        self.port_combo = QComboBox()
        self.port_combo.currentIndexChanged.connect(self.on_port_changed)
        device_layout.addWidget(self.port_combo, 1, 1)
        
        device_layout.addWidget(QLabel("波特率:"), 2, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems([
            "10000", "20000", "50000", "100000", 
            "125000", "250000", "500000", "800000", "1000000"
        ])
        self.baudrate_combo.setCurrentText("500000")
        device_layout.addWidget(self.baudrate_combo, 2, 1)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_devices)
        device_layout.addWidget(refresh_btn, 1, 2)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.connect_btn.setDefault(True)
        self.connect_btn.setEnabled(False)  # 初始禁用
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def on_device_type_changed(self, index):
        """设备类型改变"""
        self.refresh_devices()
        
    def on_port_changed(self, index):
        """端口选择改变"""
        # 当选择了有效端口时启用连接按钮
        current_data = self.port_combo.currentData()
        self.connect_btn.setEnabled(current_data is not None and current_data != "")
        
    def refresh_devices(self):
        """刷新设备列表"""
        device_type = self.device_type_combo.currentData()
        
        # 清空端口列表
        self.port_combo.clear()
        
        # 获取可用设备
        available_devices = can_manager.list_available_devices()
        
        if device_type in available_devices:
            ports = available_devices[device_type]
            if ports:
                for port in ports:
                    self.port_combo.addItem(str(port), port)
                # 默认选择第一个端口
                self.port_combo.setCurrentIndex(0)
                self.connect_btn.setEnabled(True)
            else:
                self.port_combo.addItem("未检测到设备", "")
                self.connect_btn.setEnabled(False)
        else:
            self.port_combo.addItem("设备类型不可用", "")
            self.connect_btn.setEnabled(False)
    
    def on_connect_clicked(self):
        """连接按钮点击"""
        device_type = self.device_type_combo.currentData()
        port = self.port_combo.currentData()
        baudrate = int(self.baudrate_combo.currentText())
        
        if not port:
            QMessageBox.warning(self, "警告", "请选择有效的端口")
            return
        
        # 尝试连接
        if can_manager.connect(device_type, port, baudrate):
            self.connected.emit(port, device_type.value, baudrate)
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "连接失败，请检查设备和驱动")