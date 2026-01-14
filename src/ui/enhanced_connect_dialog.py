#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版硬件连接对话框
显示可用硬件列表和已连接硬件管理
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QComboBox, QSpinBox,
    QCheckBox, QLineEdit, QSplitter, QWidget,
    QFormLayout, QListWidget, QListWidgetItem,
    QToolButton, QMenu, QAction, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon

from src.hardware.can_manager import can_manager, DeviceType
from src.hardware.multi_can_manager import multi_can_manager

class EnhancedConnectDialog(QDialog):
    """增强版硬件连接对话框"""
    
    devices_connected = pyqtSignal(list)  # 设备连接完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("硬件连接管理")
        self.setMinimumSize(900, 600)
        self.connected_devices = []
        self.available_interfaces = {}
        self.init_ui()
        self.scan_available_devices()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🔧 CAN硬件连接管理")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 主区域 - 分割窗口
        splitter = QSplitter(Qt.Horizontal)
        
        # 左面板：可用硬件
        left_panel = self.create_available_devices_panel()
        splitter.addWidget(left_panel)
        
        # 右面板：已连接硬件
        right_panel = self.create_connected_devices_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 500])
        layout.addWidget(splitter)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("就绪")
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        
        self.lbl_device_count = QLabel("已连接: 0 个设备")
        status_layout.addWidget(self.lbl_device_count)
        
        layout.addLayout(status_layout)
        
        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_refresh = QPushButton("🔄 刷新设备")
        self.btn_refresh.clicked.connect(self.scan_available_devices)
        button_layout.addWidget(self.btn_refresh)
        
        self.btn_connect_selected = QPushButton("🔌 连接选中")
        self.btn_connect_selected.clicked.connect(self.connect_selected_devices)
        button_layout.addWidget(self.btn_connect_selected)
        
        self.btn_disconnect_all = QPushButton("🔌 断开所有")
        self.btn_disconnect_all.clicked.connect(self.disconnect_all_devices)
        button_layout.addWidget(self.btn_disconnect_all)
        
        self.btn_ok = QPushButton("✅ 完成")
        self.btn_ok.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("❌ 取消")
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_available_devices_panel(self):
        """创建可用硬件面板"""
        panel = QGroupBox("📋 可用硬件接口")
        layout = QVBoxLayout()
        
        # 设备类型筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        
        self.cb_filter_type = QComboBox()
        self.cb_filter_type.addItems(["所有类型", "虚拟设备", "NI设备", "Kvaser设备"])
        self.cb_filter_type.currentTextChanged.connect(self.filter_available_devices)
        filter_layout.addWidget(self.cb_filter_type)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 可用设备列表
        self.list_available = QListWidget()
        self.list_available.setSelectionMode(QListWidget.MultiSelection)
        self.list_available.itemDoubleClicked.connect(self.on_device_double_clicked)
        
        layout.addWidget(self.list_available)
        
        # 快速连接区域
        quick_connect_group = QGroupBox("⚡ 快速连接")
        quick_layout = QGridLayout()
        
        quick_layout.addWidget(QLabel("接口:"), 0, 0)
        self.cb_quick_port = QComboBox()
        quick_layout.addWidget(self.cb_quick_port, 0, 1)
        
        quick_layout.addWidget(QLabel("波特率:"), 1, 0)
        self.cb_quick_baudrate = QComboBox()
        self.cb_quick_baudrate.addItems(["10000", "20000", "50000", "100000", 
                                        "125000", "250000", "500000", "800000", "1000000"])
        self.cb_quick_baudrate.setCurrentText("500000")
        quick_layout.addWidget(self.cb_quick_baudrate, 1, 1)
        
        quick_layout.addWidget(QLabel("设备名:"), 2, 0)
        self.edit_quick_name = QLineEdit()
        self.edit_quick_name.setPlaceholderText("可选的设备别名")
        quick_layout.addWidget(self.edit_quick_name, 2, 1)
        
        self.btn_quick_connect = QPushButton("➕ 添加设备")
        self.btn_quick_connect.clicked.connect(self.quick_add_device)
        quick_layout.addWidget(self.btn_quick_connect, 3, 0, 1, 2)
        
        quick_connect_group.setLayout(quick_layout)
        layout.addWidget(quick_connect_group)
        
        panel.setLayout(layout)
        return panel
    
    def create_connected_devices_panel(self):
        """创建已连接硬件面板"""
        panel = QGroupBox("📡 已连接设备")
        layout = QVBoxLayout()
        
        # 已连接设备表格
        self.table_connected = QTableWidget()
        self.table_connected.setColumnCount(7)
        self.table_connected.setHorizontalHeaderLabels([
            "设备名称", "类型", "接口", "波特率", "状态", "消息数", "操作"
        ])
        self.table_connected.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_connected.setColumnWidth(6, 100)  # 操作列宽度
        
        layout.addWidget(self.table_connected)
        
        # 设备操作按钮
        button_layout = QHBoxLayout()
        
        self.btn_edit = QPushButton("✏️ 编辑配置")
        self.btn_edit.clicked.connect(self.edit_selected_device)
        button_layout.addWidget(self.btn_edit)
        
        self.btn_reconnect = QPushButton("🔄 重新连接")
        self.btn_reconnect.clicked.connect(self.reconnect_selected_device)
        button_layout.addWidget(self.btn_reconnect)
        
        self.btn_disconnect = QPushButton("❌ 断开选中")
        self.btn_disconnect.clicked.connect(self.disconnect_selected_devices)
        button_layout.addWidget(self.btn_disconnect)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 批量配置
        batch_group = QGroupBox("🎯 批量配置")
        batch_layout = QHBoxLayout()
        
        batch_layout.addWidget(QLabel("设置所有设备波特率为:"))
        self.cb_batch_baudrate = QComboBox()
        self.cb_batch_baudrate.addItems(["500000", "250000", "125000", "1000000"])
        batch_layout.addWidget(self.cb_batch_baudrate)
        
        self.btn_apply_batch = QPushButton("应用")
        self.btn_apply_batch.clicked.connect(self.apply_batch_settings)
        batch_layout.addWidget(self.btn_apply_batch)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        panel.setLayout(layout)
        return panel
    
    def scan_available_devices(self):
        """扫描可用设备"""
        self.list_available.clear()
        self.available_interfaces = {}
        
        self.lbl_status.setText("正在扫描设备...")
        
        try:
            # 获取可用设备列表
            available = can_manager.list_available_devices()
            
            device_count = 0
            
            # 虚拟设备
            for port in available.get(DeviceType.VIRTUAL, []):
                device_id = f"virtual_{port}"
                item = QListWidgetItem(f"💻 虚拟设备: {port}")
                item.setData(Qt.UserRole, {
                    'type': 'virtual',
                    'port': port,
                    'name': f"虚拟设备 {port}"
                })
                self.list_available.addItem(item)
                self.available_interfaces[device_id] = 'virtual'
                device_count += 1
            
            # NI设备
            for port in available.get(DeviceType.NI_8502, []):
                device_id = f"ni_{port}"
                item = QListWidgetItem(f"🔧 NI USB-8502: {port}")
                item.setData(Qt.UserRole, {
                    'type': 'ni_8502',
                    'port': port,
                    'name': f"NI设备 {port}"
                })
                self.list_available.addItem(item)
                self.available_interfaces[device_id] = 'ni_8502'
                device_count += 1
            
            # Kvaser设备
            for port in available.get(DeviceType.Kvaser, []):
                device_id = f"kvaser_{port}"
                item = QListWidgetItem(f"🔌 Kvaser: 通道{port}")
                item.setData(Qt.UserRole, {
                    'type': 'kvaser',
                    'port': port,
                    'name': f"Kvaser 通道{port}"
                })
                self.list_available.addItem(item)
                self.available_interfaces[device_id] = 'kvaser'
                device_count += 1
            
            # 更新快速连接下拉框
            self.cb_quick_port.clear()
            for i in range(self.list_available.count()):
                item = self.list_available.item(i)
                device_info = item.data(Qt.UserRole)
                display_text = f"{device_info['name']} ({device_info['port']})"
                self.cb_quick_port.addItem(display_text, device_info)
            
            self.lbl_status.setText(f"找到 {device_count} 个可用接口")
            
        except Exception as e:
            self.lbl_status.setText(f"扫描设备失败: {e}")
            print(f"扫描设备失败: {e}")
    
    def filter_available_devices(self, filter_type):
        """过滤可用设备"""
        for i in range(self.list_available.count()):
            item = self.list_available.item(i)
            device_info = item.data(Qt.UserRole)
            
            if filter_type == "所有类型":
                item.setHidden(False)
            elif filter_type == "虚拟设备" and device_info['type'] == 'virtual':
                item.setHidden(False)
            elif filter_type == "NI设备" and device_info['type'] == 'ni_8502':
                item.setHidden(False)
            elif filter_type == "Kvaser设备" and device_info['type'] == 'kvaser':
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def on_device_double_clicked(self, item):
        """双击设备快速添加"""
        device_info = item.data(Qt.UserRole)
        self.add_device_to_connected(device_info)
    
    def quick_add_device(self):
        """快速添加设备"""
        if self.cb_quick_port.currentIndex() < 0:
            QMessageBox.warning(self, "警告", "请选择要连接的接口")
            return
        
        device_info = self.cb_quick_port.currentData()
        device_info['baudrate'] = int(self.cb_quick_baudrate.currentText())
        
        custom_name = self.edit_quick_name.text().strip()
        if custom_name:
            device_info['name'] = custom_name
        
        self.add_device_to_connected(device_info)
    
    def add_device_to_connected(self, device_info):
        """添加设备到已连接列表"""
        try:
            # 检查是否已连接
            for i in range(self.table_connected.rowCount()):
                existing_port = self.table_connected.item(i, 2).text()
                if existing_port == device_info['port']:
                    QMessageBox.warning(self, "警告", f"接口 {device_info['port']} 已连接")
                    return
            
            # 添加新行
            row = self.table_connected.rowCount()
            self.table_connected.insertRow(row)
            
            # 设备名称
            name_item = QTableWidgetItem(device_info['name'])
            self.table_connected.setItem(row, 0, name_item)
            
            # 设备类型
            type_map = {
                'virtual': '虚拟设备',
                'ni_8502': 'NI USB-8502',
                'kvaser': 'Kvaser'
            }
            type_item = QTableWidgetItem(type_map.get(device_info['type'], device_info['type']))
            self.table_connected.setItem(row, 1, type_item)
            
            # 接口
            port_item = QTableWidgetItem(device_info['port'])
            self.table_connected.setItem(row, 2, port_item)
            
            # 波特率（带下拉框）
            baudrate_combo = QComboBox()
            baudrate_combo.addItems(["10000", "20000", "50000", "100000", 
                                   "125000", "250000", "500000", "800000", "1000000"])
            baudrate = device_info.get('baudrate', 500000)
            baudrate_combo.setCurrentText(str(baudrate))
            baudrate_combo.currentTextChanged.connect(
                lambda text, r=row: self.update_device_baudrate(r, int(text))
            )
            self.table_connected.setCellWidget(row, 3, baudrate_combo)
            
            # 状态
            status_item = QTableWidgetItem("未连接")
            status_item.setForeground(QColor(255, 0, 0))  # 红色
            self.table_connected.setItem(row, 4, status_item)
            
            # 消息数
            count_item = QTableWidgetItem("0")
            self.table_connected.setItem(row, 5, count_item)
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_connect = QPushButton("连接")
            btn_connect.clicked.connect(lambda checked, r=row: self.connect_single_device(r))
            button_layout.addWidget(btn_connect)
            
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(lambda checked, r=row: self.remove_device(r))
            button_layout.addWidget(btn_remove)
            
            button_widget.setLayout(button_layout)
            self.table_connected.setCellWidget(row, 6, button_widget)
            
            # 存储完整信息
            device_info['row'] = row
            device_info['connected'] = False
            device_info['message_count'] = 0
            
            self.connected_devices.append(device_info)
            self.update_device_count()
            
            self.lbl_status.setText(f"已添加设备: {device_info['name']}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加设备失败: {e}")
    
    def update_device_baudrate(self, row, baudrate):
        """更新设备波特率"""
        if 0 <= row < len(self.connected_devices):
            self.connected_devices[row]['baudrate'] = baudrate
            
            # 如果设备已连接，重新连接
            if self.connected_devices[row]['connected']:
                self.reconnect_device(row)
    
    def connect_single_device(self, row):
        """连接单个设备"""
        if row >= len(self.connected_devices):
            return
        
        device_info = self.connected_devices[row]
        
        try:
            # 映射设备类型
            type_map = {
                'virtual': DeviceType.VIRTUAL,
                'ni_8502': DeviceType.NI_8502,
                'kvaser': DeviceType.Kvaser
            }
            
            device_type = type_map.get(device_info['type'])
            if not device_type:
                QMessageBox.warning(self, "警告", f"不支持的类型: {device_info['type']}")
                return
            
            # 连接设备
            baudrate = device_info.get('baudrate', 500000)
            success = can_manager.connect(device_type, device_info['port'], baudrate)
            
            if success:
                # 更新状态
                status_item = QTableWidgetItem("已连接")
                status_item.setForeground(QColor(0, 128, 0))  # 绿色
                self.table_connected.setItem(row, 4, status_item)
                
                # 更新按钮
                button_widget = self.table_connected.cellWidget(row, 6)
                if button_widget:
                    layout = button_widget.layout()
                    if layout and layout.itemAt(0):
                        btn = layout.itemAt(0).widget()
                        if btn:
                            btn.setText("断开")
                            btn.clicked.disconnect()
                            btn.clicked.connect(lambda checked, r=row: self.disconnect_single_device(r))
                
                device_info['connected'] = True
                self.lbl_status.setText(f"设备连接成功: {device_info['name']}")
            else:
                QMessageBox.warning(self, "警告", f"连接失败: {device_info['name']}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接设备失败: {e}")
    
    def disconnect_single_device(self, row):
        """断开单个设备"""
        if row >= len(self.connected_devices):
            return
        
        device_info = self.connected_devices[row]
        
        try:
            # 断开设备
            can_manager.disconnect(device_info['port'])
            
            # 更新状态
            status_item = QTableWidgetItem("未连接")
            status_item.setForeground(QColor(255, 0, 0))  # 红色
            self.table_connected.setItem(row, 4, status_item)
            
            # 更新按钮
            button_widget = self.table_connected.cellWidget(row, 6)
            if button_widget:
                layout = button_widget.layout()
                if layout and layout.itemAt(0):
                    btn = layout.itemAt(0).widget()
                    if btn:
                        btn.setText("连接")
                        btn.clicked.disconnect()
                        btn.clicked.connect(lambda checked, r=row: self.connect_single_device(r))
            
            device_info['connected'] = False
            self.lbl_status.setText(f"设备已断开: {device_info['name']}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"断开设备失败: {e}")
    
    def connect_selected_devices(self):
        """连接所有选中的设备"""
        selected_items = self.list_available.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要连接的设备")
            return
        
        for item in selected_items:
            device_info = item.data(Qt.UserRole)
            self.add_device_to_connected(device_info)
        
        self.lbl_status.setText(f"已添加 {len(selected_items)} 个设备")
    
    def disconnect_selected_devices(self):
        """断开选中的设备"""
        selected_rows = set()
        for item in self.table_connected.selectedItems():
            selected_rows.add(item.row())
        
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.connected_devices) and self.connected_devices[row]['connected']:
                self.disconnect_single_device(row)
    
    def disconnect_all_devices(self):
        """断开所有设备"""
        for row in range(len(self.connected_devices)):
            if self.connected_devices[row]['connected']:
                self.disconnect_single_device(row)
        
        self.lbl_status.setText("所有设备已断开")
    
    def reconnect_selected_device(self):
        """重新连接选中的设备"""
        selected_rows = set()
        for item in self.table_connected.selectedItems():
            selected_rows.add(item.row())
        
        for row in selected_rows:
            if row < len(self.connected_devices):
                if self.connected_devices[row]['connected']:
                    self.disconnect_single_device(row)
                self.connect_single_device(row)
    
    def reconnect_device(self, row):
        """重新连接设备"""
        if row < len(self.connected_devices) and self.connected_devices[row]['connected']:
            self.disconnect_single_device(row)
            self.connect_single_device(row)
    
    def edit_selected_device(self):
        """编辑选中的设备配置"""
        selected_rows = set()
        for item in self.table_connected.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要编辑的设备")
            return
        
        row = next(iter(selected_rows))  # 取第一个选中的行
        if row >= len(self.connected_devices):
            return
        
        device_info = self.connected_devices[row]
        
        # 创建编辑对话框
        from PyQt5.QtWidgets import QInputDialog
        
        new_name, ok = QInputDialog.getText(
            self, "编辑设备名称", 
            "输入新的设备名称:", 
            text=device_info['name']
        )
        
        if ok and new_name.strip():
            device_info['name'] = new_name.strip()
            self.table_connected.item(row, 0).setText(new_name.strip())
            self.lbl_status.setText(f"设备名称已更新: {new_name}")
    
    def remove_device(self, row):
        """移除设备"""
        if row >= len(self.connected_devices):
            return
        
        device_info = self.connected_devices[row]
        
        # 如果已连接，先断开
        if device_info['connected']:
            self.disconnect_single_device(row)
        
        # 从表格中移除
        self.table_connected.removeRow(row)
        
        # 从列表中移除
        self.connected_devices.pop(row)
        
        # 更新后续行的row索引
        for i in range(row, len(self.connected_devices)):
            self.connected_devices[i]['row'] = i
        
        self.update_device_count()
        self.lbl_status.setText(f"设备已移除: {device_info['name']}")
    
    def apply_batch_settings(self):
        """应用批量设置"""
        baudrate = int(self.cb_batch_baudrate.currentText())
        
        for row in range(self.table_connected.rowCount()):
            combo = self.table_connected.cellWidget(row, 3)
            if combo:
                combo.setCurrentText(str(baudrate))
            
            if row < len(self.connected_devices):
                self.connected_devices[row]['baudrate'] = baudrate
        
        self.lbl_status.setText(f"所有设备波特率已设置为: {baudrate}")
    
    def update_device_count(self):
        """更新设备计数"""
        connected_count = sum(1 for d in self.connected_devices if d['connected'])
        total_count = len(self.connected_devices)
        self.lbl_device_count.setText(f"已连接: {connected_count}/{total_count} 个设备")
    
    def accept(self):
        """确定按钮点击"""
        # 收集所有已连接的设备信息
        connected_devices = []
        for device_info in self.connected_devices:
            if device_info['connected']:
                connected_devices.append({
                    'name': device_info['name'],
                    'type': device_info['type'],
                    'port': device_info['port'],
                    'baudrate': device_info.get('baudrate', 500000),
                    'connected': True
                })
        
        if connected_devices:
            self.devices_connected.emit(connected_devices)
        
        super().accept()