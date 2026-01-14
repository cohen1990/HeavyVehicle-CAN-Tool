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
    QToolButton, QMenu, QAction, QGridLayout,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon
from functools import partial
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
        self.load_connected_devices()
    def load_connected_devices(self):
        """加载已连接的设备"""
        try:
            from src.hardware.multi_can_manager import multi_can_manager
            
            devices_info = multi_can_manager.get_all_device_info()
            
            for device_info in devices_info:
                if device_info['connected']:
                    # 检查是否已存在
                    exists = False
                    for existing in self.connected_devices:
                        if existing.get('port') == device_info.get('port'):
                            exists = True
                            # 更新连接状态
                            existing['connected'] = True
                            break
                    
                    if not exists:
                        # 添加到表格
                        device_data = {
                            'name': device_info['name'],
                            'type': device_info['type'],
                            'port': device_info['port'],
                            'baudrate': device_info.get('baudrate', 500000),
                            'connected': True
                        }
                        
                        self.add_device_to_connected(device_data)
                        
                        # 更新最后添加的行的状态
                        row = len(self.connected_devices) - 1
                        if row >= 0:
                            # 更新状态显示
                            status_item = QTableWidgetItem("✅ 已连接")
                            status_item.setForeground(QColor(0, 128, 0))
                            self.table_connected.setItem(row, 4, status_item)
            
            self.update_device_stats()
            
        except Exception as e:
            print(f"加载已连接设备失败: {e}")
    def add_existing_device_to_table(self, device_info):
        """添加已存在的设备到表格"""
        # 检查是否已存在
        for existing in self.connected_devices:
            if existing.get('device_id') == device_info.get('id'):
                return  # 已存在
        
        # 创建设备信息
        device_data = {
            'name': device_info['name'],
            'type': device_info['type'],
            'port': device_info['port'],
            'baudrate': device_info['baudrate'],
            'connected': True,
            'device_id': device_info['id']
        }
        
        # 添加到表格
        self.add_device_to_table_row(device_data)
        
        # 存储到列表
        self.connected_devices.append(device_data)
        self.update_device_count()
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
    def create_button_handler(self, row, handler_type):
        """创建按钮处理器工厂函数"""
        if handler_type == 'connect':
            def handler():
                self.connect_single_device(row)
            return handler
        elif handler_type == 'disconnect':
            def handler():
                self.disconnect_single_device(row)
            return handler
        elif handler_type == 'remove':
            def handler():
                self.remove_device(row)
            return handler
        return None
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
        panel = QGroupBox("📡 已配置设备")
        layout = QVBoxLayout()
        
        # 已连接设备表格
        self.table_connected = QTableWidget()
        self.table_connected.setColumnCount(6)  # ✅ 从7列改为6列
        self.table_connected.setHorizontalHeaderLabels([
            "设备名称", "类型", "接口", "波特率", "状态", "操作"
        ])
        self.table_connected.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_connected.setColumnWidth(5, 80)  # 操作列宽度
        
        layout.addWidget(self.table_connected)
        
        # 设备操作按钮（简化）
        button_layout = QHBoxLayout()
        
        self.btn_remove_selected = QPushButton("移除选中")
        self.btn_remove_selected.clicked.connect(self.remove_selected_devices)
        button_layout.addWidget(self.btn_remove_selected)
        
        self.btn_clear_all = QPushButton("清空所有")
        self.btn_clear_all.clicked.connect(self.clear_all_devices)
        button_layout.addWidget(self.btn_clear_all)
        
        button_layout.addStretch()
        
        # ✅ 添加设备统计
        self.lbl_device_stats = QLabel("设备: 0 个 (待连接)")
        button_layout.addWidget(self.lbl_device_stats)
        
        layout.addLayout(button_layout)
        
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
            # 检查是否已存在
            for i in range(self.table_connected.rowCount()):
                existing_port = self.table_connected.item(i, 2).text()
                if existing_port == device_info['port']:
                    QMessageBox.warning(self, "警告", f"接口 {device_info['port']} 已存在")
                    return
            
            # 添加新行
            row = self.table_connected.rowCount()
            self.table_connected.insertRow(row)
            
            # ✅ 设备名称
            name_item = QTableWidgetItem(device_info['name'])
            self.table_connected.setItem(row, 0, name_item)
            
            # ✅ 设备类型
            type_map = {
                'virtual': '虚拟设备',
                'ni_8502': 'NI USB-8502',
                'kvaser': 'Kvaser'
            }
            type_item = QTableWidgetItem(type_map.get(device_info['type'], device_info['type']))
            self.table_connected.setItem(row, 1, type_item)
            
            # ✅ 接口
            port_item = QTableWidgetItem(device_info['port'])
            self.table_connected.setItem(row, 2, port_item)
            
            # ✅ 波特率（带下拉框）
            baudrate_combo = QComboBox()
            baudrate_combo.addItems(["10000", "20000", "50000", "100000", 
                                   "125000", "250000", "500000", "800000", "1000000"])
            baudrate = device_info.get('baudrate', 500000)
            baudrate_combo.setCurrentText(str(baudrate))
            baudrate_combo.currentTextChanged.connect(
                lambda text, r=row: self.update_device_baudrate(r, int(text))
            )
            self.table_connected.setCellWidget(row, 3, baudrate_combo)
            
            # ✅ 状态（初始显示"待连接"）
            status_item = QTableWidgetItem("待连接")
            status_item.setForeground(QColor(160, 160, 160))  # 灰色
            self.table_connected.setItem(row, 4, status_item)
            
            # ✅ 操作：只保留移除按钮
            btn_remove = QPushButton("移除")
            # 使用functools.partial避免lambda问题
            from functools import partial
            btn_remove.clicked.connect(partial(self.remove_device, row))
            
            remove_widget = QWidget()
            remove_layout = QHBoxLayout()
            remove_layout.setContentsMargins(2, 2, 2, 2)
            remove_layout.addWidget(btn_remove)
            remove_widget.setLayout(remove_layout)
            
            self.table_connected.setCellWidget(row, 5, remove_widget)
            
            # 存储完整信息
            device_info['row'] = row
            device_info['connected'] = False
            device_info['message_count'] = 0
            
            self.connected_devices.append(device_info)
            self.update_device_count()
            self.update_device_stats()  # 更新统计
            
            self.lbl_status.setText(f"已添加设备: {device_info['name']}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加设备失败: {e}")
            import traceback
            traceback.print_exc()
    def update_device_stats(self):
        """更新设备统计信息"""
        total_devices = len(self.connected_devices)
        connected_devices = sum(1 for dev in self.connected_devices if dev.get('connected', False))
        
        if connected_devices > 0:
            stats_text = f"设备: {total_devices} 个 ({connected_devices} 个已连接)"
        else:
            stats_text = f"设备: {total_devices} 个 (待连接)"
        
        self.lbl_device_stats.setText(stats_text)
    def create_remove_handler(row_num):
        def handler():
            self.remove_device(row_num)
        return handler
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
        
        if device_info.get('connected', False):
            return
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
            
            # ✅ 修复：确保连接成功
            from src.hardware.can_manager import can_manager
            success = can_manager.connect(device_type, device_info['port'], baudrate)
            
            if success:
                # 更新状态
                status_item = QTableWidgetItem("✅ 已连接")
                status_item.setForeground(QColor(0, 128, 0))
                self.table_connected.setItem(row, 4, status_item)
                device_info['connected'] = True
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
                
                # ✅ 重要：更新多CAN管理器
                # ✅ 修复：避免重复添加到multi_can_manager
                from src.hardware.multi_can_manager import multi_can_manager
                device_id = f"{device_info['type']}_{device_info['port']}"
                
                if device_id not in multi_can_manager.devices:
                    multi_can_manager.add_device(
                        device_type=device_info['type'],
                        port=device_info['port'],
                        baudrate=baudrate,
                        name=device_info['name']
                    )
                
                # 确保设备在multi_can_manager中连接
                multi_can_manager.connect_device(device_id)
                
                self.lbl_status.setText(f"设备连接成功: {device_info['name']}")
                    
            else:
                QMessageBox.warning(self, "警告", f"连接失败: {device_info['name']}")
                # 保持未连接状态
                device_info['connected'] = False
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接设备失败: {e}")
            import traceback
            traceback.print_exc()
    def disconnect_single_device(self, row):
        """断开单个设备"""
        print(f"DEBUG: 断开设备，行号: {row}")
        
        if row >= len(self.connected_devices):
            print(f"DEBUG: 行号无效")
            return
        
        device_info = self.connected_devices[row]
        device_name = device_info.get('name', '未知设备')
        
        try:
            # 1. 断开can_manager连接
            from src.hardware.can_manager import can_manager
            can_manager.disconnect(device_info['port'])
            
            # 2. 断开multi_can_manager连接
            from src.hardware.multi_can_manager import multi_can_manager
            device_id = f"{device_info['type']}_{device_info['port']}"
            multi_can_manager.disconnect_device(device_id)
            
            # 3. 更新表格状态
            status_item = QTableWidgetItem("未连接")
            status_item.setForeground(QColor(255, 0, 0))
            self.table_connected.setItem(row, 4, status_item)
            
            # 4. 更新按钮文本
            button_widget = self.table_connected.cellWidget(row, 6)
            if button_widget:
                layout = button_widget.layout()
                if layout and layout.itemAt(0):
                    btn = layout.itemAt(0).widget()
                    if btn:
                        btn.setText("连接")
                        # 重新连接信号
                        btn.clicked.disconnect()
                        btn.clicked.connect(partial(self.connect_single_device, row))
            
            # 5. 更新设备状态
            device_info['connected'] = False
            
            self.lbl_status.setText(f"设备已断开: {device_name}")
            print(f"DEBUG: 设备 {device_name} 断开成功")
            
        except Exception as e:
            print(f"DEBUG: 断开设备失败: {e}")
            import traceback
            traceback.print_exc()
    
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
        """移除设备 - 修复行索引问题"""
        print(f"\n=== 移除设备开始 ===")
        print(f"传入行号: {row}")
        print(f"表格当前行数: {self.table_connected.rowCount()}")
        print(f"设备列表长度: {len(self.connected_devices)}")
        
        # ✅ 修复：验证行号有效性
        if row < 0 or row >= len(self.connected_devices):
            print(f"错误: 行号 {row} 无效")
            return
        
        if row >= self.table_connected.rowCount():
            print(f"错误: 行号 {row} 超出表格范围")
            return
        
        try:
            # 获取要移除的设备
            device_to_remove = self.connected_devices[row]
            print(f"要移除的设备: {device_to_remove.get('name')}")
            
            # 如果已连接，先断开
            if device_to_remove.get('connected', False):
                print("设备已连接，先断开...")
                self.disconnect_single_device(row)
            
            # 从表格移除
            print(f"从表格移除第 {row} 行")
            self.table_connected.removeRow(row)
            
            # 从列表移除
            print(f"从设备列表移除索引 {row}")
            removed = self.connected_devices.pop(row)
            print(f"已移除设备: {removed.get('name')}")
            
            # ✅ 关键修复：重新绑定剩余行的按钮
            self._rebind_all_buttons()
            
            # 更新设备计数
            self.update_device_count()
            
            print(f"剩余设备数: {len(self.connected_devices)}")
            print("=== 移除设备完成 ===\n")
            
        except Exception as e:
            print(f"移除设备时出错: {e}")
            import traceback
            traceback.print_exc()

    def _rebind_all_buttons(self):
        """重新绑定所有行的按钮"""
        print("重新绑定所有按钮...")
        
        for row in range(self.table_connected.rowCount()):
            if row < len(self.connected_devices):
                # 更新行号
                self.connected_devices[row]['row'] = row
                
                # 重新绑定按钮
                button_widget = self.table_connected.cellWidget(row, 6)
                if button_widget:
                    layout = button_widget.layout()
                    if layout:
                        # 清空所有连接
                        for i in range(layout.count()):
                            widget = layout.itemAt(i).widget()
                            if widget:
                                try:
                                    widget.clicked.disconnect()
                                except:
                                    pass
                        
                        # 重新连接按钮
                        if layout.itemAt(0):
                            btn1 = layout.itemAt(0).widget()
                            if btn1:
                                if self.connected_devices[row].get('connected', False):
                                    btn1.setText("断开")
                                    btn1.clicked.connect(lambda checked, r=row: self.disconnect_single_device(r))
                                else:
                                    btn1.setText("连接")
                                    btn1.clicked.connect(lambda checked, r=row: self.connect_single_device(r))
                        
                        if layout.itemAt(1):
                            btn2 = layout.itemAt(1).widget()
                            if btn2:
                                btn2.setText("移除")
                                btn2.clicked.connect(lambda checked, r=row: self.remove_device(r))
    
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

    def remove_selected_devices(self):
        """移除选中的设备"""
        # 获取选中的行
        selected_rows = set()
        for item in self.table_connected.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要移除的设备")
            return
        
        # 从后往前移除
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.connected_devices):
                self.remove_device(row)

    def clear_all_devices(self):
        """清空所有设备"""
        if not self.connected_devices:
            return
        
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            f"确定要清空所有 {len(self.connected_devices)} 个设备吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 断开所有已连接的设备
            for device_info in self.connected_devices:
                if device_info.get('connected', False):
                    try:
                        from src.hardware.can_manager import can_manager
                        can_manager.disconnect(device_info['port'])
                    except:
                        pass
            
            # 清空表格
            self.table_connected.setRowCount(0)
            
            # 清空设备列表
            self.connected_devices.clear()
            
            # 更新统计
            self.update_device_count()
            self.update_device_stats()
            
            self.lbl_status.setText("所有设备已清空")
    
    def accept(self):
        """完成按钮点击 - 连接所有设备（简化版）"""
        print("DEBUG: 完成按钮点击，开始连接所有设备")
        
        if not self.connected_devices:
            print("DEBUG: 没有设备，直接关闭")
            super().accept()
            return
        
        print(f"DEBUG: 找到 {len(self.connected_devices)} 个设备")
        
        # 禁用按钮，防止重复点击
        self.btn_ok.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        
        # 显示连接状态
        self.lbl_status.setText("正在连接设备...")
        QApplication.processEvents()  # 更新界面
        
        connected_count = 0
        failed_count = 0
        connected_device_list = []
        
        try:
            from src.hardware.can_manager import DeviceType, can_manager
            from src.hardware.multi_can_manager import multi_can_manager
            
            for i, device_info in enumerate(self.connected_devices):
                device_name = device_info['name']
                
                # 更新状态
                self.lbl_status.setText(f"正在连接: {device_name} ({i+1}/{len(self.connected_devices)})")
                QApplication.processEvents()  # 更新界面
                
                try:
                    # 如果已经连接，跳过
                    if device_info.get('connected', False):
                        print(f"DEBUG: 设备 {device_name} 已连接，跳过")
                        connected_count += 1
                        continue
                    
                    # 映射设备类型
                    type_map = {
                        'virtual': DeviceType.VIRTUAL,
                        'ni_8502': DeviceType.NI_8502,
                        'kvaser': DeviceType.Kvaser
                    }
                    
                    device_type = type_map.get(device_info['type'])
                    if not device_type:
                        print(f"DEBUG: 不支持的类型: {device_info['type']}")
                        failed_count += 1
                        continue
                    
                    # 连接设备
                    baudrate = device_info.get('baudrate', 500000)
                    success = can_manager.connect(device_type, device_info['port'], baudrate)
                    
                    if success:
                        # 更新表格状态
                        row = device_info['row']
                        status_item = QTableWidgetItem("✅ 已连接")
                        status_item.setForeground(QColor(0, 128, 0))  # 绿色
                        self.table_connected.setItem(row, 4, status_item)
                        
                        # 添加到multi_can_manager
                        device_id = f"{device_info['type']}_{device_info['port']}"
                        if device_id not in multi_can_manager.devices:
                            multi_can_manager.add_device(
                                device_type=device_info['type'],
                                port=device_info['port'],
                                baudrate=baudrate,
                                name=device_info['name']
                            )
                        
                        # 连接设备
                        multi_can_manager.connect_device(device_id)
                        
                        # 更新设备状态
                        device_info['connected'] = True
                        
                        connected_count += 1
                        connected_device_list.append({
                            'name': device_info['name'],
                            'type': device_info['type'],
                            'port': device_info['port'],
                            'baudrate': baudrate,
                            'connected': True,
                            'device_id': device_id
                        })
                        
                        print(f"DEBUG: 设备 {device_name} 连接成功")
                    else:
                        print(f"DEBUG: 设备 {device_name} 连接失败")
                        failed_count += 1
                        # 更新表格状态为失败
                        row = device_info['row']
                        status_item = QTableWidgetItem("❌ 连接失败")
                        status_item.setForeground(QColor(255, 0, 0))  # 红色
                        self.table_connected.setItem(row, 4, status_item)
                        
                except Exception as e:
                    print(f"DEBUG: 连接设备 {device_name} 时出错: {e}")
                    failed_count += 1
                    import traceback
                    traceback.print_exc()
            
            print(f"DEBUG: 连接完成: {connected_count} 成功, {failed_count} 失败")
            
            # 更新统计
            self.update_device_stats()
            
            # 重新启用按钮
            self.btn_ok.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            
            if connected_count > 0:
                # 发射信号
                self.devices_connected.emit(connected_device_list)
                
                # 显示成功消息
                result_msg = f"连接完成: {connected_count} 成功"
                if failed_count > 0:
                    result_msg += f", {failed_count} 失败"
                
                self.lbl_status.setText(result_msg)
                
                # 延迟关闭，让用户看到结果
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, lambda: QDialog.accept(self))
            else:
                # 所有设备连接失败
                self.lbl_status.setText("所有设备连接失败")
                
                reply = QMessageBox.warning(
                    self,
                    "连接失败",
                    f"所有设备连接失败\n\n"
                    f"成功: {connected_count}, 失败: {failed_count}\n\n"
                    "是否仍然关闭对话框？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    super().accept()
        
        except Exception as e:
            print(f"DEBUG: 连接过程中出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 重新启用按钮
            self.btn_ok.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            
            QMessageBox.critical(self, "错误", f"连接设备时发生错误: {e}")

    def closeEvent(self, event):
        """关闭对话框时清理资源"""
        try:
            # 断开所有连接
            for device_info in self.connected_devices:
                if device_info.get('connected', False):
                    try:
                        from src.hardware.can_manager import can_manager
                        can_manager.disconnect(device_info['port'])
                    except:
                        pass
        except:
            pass
        
        super().closeEvent(event)