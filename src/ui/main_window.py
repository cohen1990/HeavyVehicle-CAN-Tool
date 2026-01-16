#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - 支持多硬件版本
"""
import threading
import os
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QStatusBar,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QApplication, QDialog, QFileDialog,
    QSplitter, QComboBox, QSpinBox, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

# 导入多硬件管理器
from src.hardware.multi_can_manager import multi_can_manager, DeviceConfig
from src.ui.multi_connect_dialog import MultiConnectDialog
from src.ui.advanced_signal_dialog import AdvancedSignalDialog
from src.ui.import_dbc_dialog import ImportDBCDialog
from src.dbc.dbc_manager import dbc_manager
from src.config.signal_config import signal_config

class MainWindow(QMainWindow):
    """主窗口类 - 支持多硬件"""
    
    # 自定义信号
    can_message_received = pyqtSignal(object)
    device_status_changed = pyqtSignal(str, bool)  # device_id, connected
    
    def __init__(self):
        super().__init__()
        self.connected_devices = {}  # device_id -> device_info
        self.current_signals = {}
        self.message_count = 0
        self._processing_click = False
        
        # 记录状态
        self.recording = False
        self.recording_file = None
        self.recording_start_time = None
        
        # 定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(1000)  # 每秒更新一次
        
        self.dbc_manager = None
        self.init_ui()
        self.setup_connections()
        self.test_mode = None
        # 注册回调
        multi_can_manager.register_callback(self.handle_can_message)
        
    def init_ui(self):
        """初始化界面 - 多硬件版本"""
        # 设置窗口属性
        self.setWindowTitle("重型车CAN监控工具 v2.0 - 多硬件支持")
        self.setGeometry(100, 100, 1400, 900)  # 更大的窗口
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 1. 顶部控制栏
        control_group = QGroupBox("🚀 控制中心")
        control_layout = QVBoxLayout()
        
        # 第一行：硬件控制
        hardware_row = QHBoxLayout()
        
        self.btn_multi_connect = QPushButton("🔌 多硬件连接")
        self.btn_multi_connect.setFixedWidth(120)
        hardware_row.addWidget(self.btn_multi_connect)
        
        self.btn_disconnect_all = QPushButton("🔌 断开所有")
        self.btn_disconnect_all.setFixedWidth(120)
        self.btn_disconnect_all.setEnabled(False)
        hardware_row.addWidget(self.btn_disconnect_all)
        
        hardware_row.addStretch()
        
        self.lbl_device_count = QLabel("设备: 0/0")
        hardware_row.addWidget(self.lbl_device_count)
        
        self.lbl_message_rate = QLabel("消息率: 0/s")
        hardware_row.addWidget(self.lbl_message_rate)
        
        control_layout.addLayout(hardware_row)
        
        # 第二行：数据控制
        data_row = QHBoxLayout()
        
        self.btn_import_dbc = QPushButton("📁 导入DBC")
        self.btn_import_dbc.setFixedWidth(100)
        self.btn_import_dbc.setEnabled(False)
        data_row.addWidget(self.btn_import_dbc)
        
        self.btn_signal_config = QPushButton("⚙️ 信号配置")
        self.btn_signal_config.setFixedWidth(100)
        self.btn_signal_config.setEnabled(False)
        data_row.addWidget(self.btn_signal_config)
        
        self.btn_import_config = QPushButton("📥 导入配置")
        self.btn_import_config.setFixedWidth(100)
        self.btn_import_config.setEnabled(False)
        data_row.addWidget(self.btn_import_config)
        
        data_row.addStretch()
        
        self.btn_start = QPushButton("▶️ 开始监控")
        self.btn_start.setFixedWidth(120)
        self.btn_start.setEnabled(False)
        data_row.addWidget(self.btn_start)
        
        self.btn_record = QPushButton("⏺️ 开始记录")
        self.btn_record.setFixedWidth(120)
        self.btn_record.setEnabled(False)
        data_row.addWidget(self.btn_record)
        
        control_layout.addLayout(data_row)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 2. 设备状态区域
        device_group = QGroupBox("📡 设备状态")
        device_layout = QHBoxLayout()
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(6)
        self.device_table.setHorizontalHeaderLabels([
            "设备名称", "类型", "端口", "状态", "消息数", "错误数"
        ])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setMaximumHeight(150)
        
        device_layout.addWidget(self.device_table)
        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)
        
        # 3. 主显示区域 - 分割窗口
        main_splitter = QSplitter(Qt.Vertical)
        
        # 上半部分：信号监控
        signals_group = QGroupBox("📊 信号监控")
        signals_layout = QVBoxLayout()
        
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(6)
        self.signal_table.setHorizontalHeaderLabels([
            "信号名称", "值", "单位", "设备", "时间", "状态"
        ])
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        signals_layout.addWidget(self.signal_table)
        signals_group.setLayout(signals_layout)
        
        # 下半部分：原始报文
        message_group = QGroupBox("📨 原始报文")
        message_layout = QVBoxLayout()
        
        # 报文过滤选项
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("过滤:"))
        
        self.cb_show_all = QCheckBox("显示所有设备")
        self.cb_show_all.setChecked(True)
        filter_layout.addWidget(self.cb_show_all)
        
        self.combo_device_filter = QComboBox()
        self.combo_device_filter.addItem("所有设备")
        self.combo_device_filter.setMaximumWidth(150)
        filter_layout.addWidget(self.combo_device_filter)
        
        self.btn_clear_messages = QPushButton("清空报文")
        self.btn_clear_messages.clicked.connect(self.clear_message_table)
        filter_layout.addWidget(self.btn_clear_messages)
        
        filter_layout.addStretch()
        message_layout.addLayout(filter_layout)
        
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(7)
        self.message_table.setHorizontalHeaderLabels([
            "时间", "设备", "端口", "ID", "数据", "长度", "类型"
        ])
        self.message_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.message_table.setMaximumHeight(300)
        
        message_layout.addWidget(self.message_table)
        message_group.setLayout(message_layout)
        
        main_splitter.addWidget(signals_group)
        main_splitter.addWidget(message_group)
        main_splitter.setSizes([500, 300])
        
        main_layout.addWidget(main_splitter, 1)
        
        # 4. 底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态栏标签
        self.lbl_main_status = QLabel("🚀 就绪 - 请连接硬件")
        self.status_bar.addWidget(self.lbl_main_status)
        
        self.lbl_recording = QLabel("⏺️ 记录: 未开始")
        self.status_bar.addWidget(self.lbl_recording)
        
        self.lbl_memory = QLabel("💾 内存: --")
        self.status_bar.addWidget(self.lbl_memory)
        
        self.lbl_time = QLabel("🕐 " + datetime.now().strftime("%H:%M:%S"))
        self.status_bar.addWidget(self.lbl_time)
        
        # 更新时间显示
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
    def setup_connections(self):
        """设置信号槽连接"""
        self.btn_multi_connect.clicked.connect(self.on_multi_connect_clicked)
        self.btn_disconnect_all.clicked.connect(self.on_disconnect_all_clicked)
        self.btn_import_dbc.clicked.connect(self.on_import_dbc_clicked)
        self.btn_signal_config.clicked.connect(self.on_signal_config_clicked)
        self.btn_import_config.clicked.connect(self.on_import_config_clicked)
        self.btn_start.clicked.connect(self.on_start_clicked)
        self.btn_record.clicked.connect(self.on_record_clicked)
        
        # 连接自定义信号
        self.can_message_received.connect(self.on_can_message_received)
        self.device_status_changed.connect(self.on_device_status_changed)
        
    def on_connect_clicked(self):
        """连接硬件按钮点击"""
        dialog = ConnectDialog(self)
        
        # 连接对话框的信号
        def on_dialog_connected(port, device_type, baudrate):
            # 连接成功，更新界面状态
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_import_dbc.setEnabled(True)
            self.btn_import_config.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.btn_config.setEnabled(True)
            
            # 更新连接状态显示
            self.lbl_connection.setText(f"已连接 ({device_type})")
            self.lbl_connection.setStyleSheet("color: green; font-weight: bold;")
            self.lbl_baudrate.setText(f"波特率: {baudrate}")
            
            self.status_bar.showMessage(f"硬件连接成功 - 端口: {port}")
            
            # 注册消息回调
            can_manager.register_callback(self.handle_can_message)
            print(f"回调已注册，数量: {len(can_manager.callbacks)}")
            
            # 如果是虚拟设备，创建测试模式对象（但不启动）
            if device_type == "virtual":
                try:
                    from src.hardware.test_mode import TestMode
                    self.test_mode = TestMode(self.handle_can_message)
                    print("测试模式对象已创建（未启动）")
                except ImportError as e:
                    print(f"无法导入测试模式: {e}")
                    # 如果没有测试模式，使用虚拟CAN
                    can_manager.connect(DeviceType.VIRTUAL, port, baudrate)
        
        dialog.connected.connect(on_dialog_connected)
        
        # 显示对话框（非阻塞）
        dialog.exec_()
    
    def on_disconnect_clicked(self):
        """断开连接按钮点击"""
        # 停止监控（如果正在监控）
        if self.btn_start.text() == "停止监控":
            self.stop_all_tasks()
        
        # 停止测试模式
        if self.test_mode:
            if self.test_mode.running:
                self.test_mode.stop()
        
        # 断开所有设备
        for port in can_manager.get_connected_devices():
            can_manager.disconnect(port)
        
        # 更新界面状态
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_record.setEnabled(False)
        self.btn_import_dbc.setEnabled(False)
        self.btn_import_config.setEnabled(False)
        self.btn_config.setEnabled(False)
        
        # 重置按钮状态
        self.btn_start.setText("开始监控")
        self.btn_record.setText("开始记录")
        
        self.lbl_connection.setText("未连接")
        self.lbl_connection.setStyleSheet("color: red; font-weight: bold;")
        self.lbl_baudrate.setText("波特率: --")
        self.lbl_message_count.setText("接收消息: 0")
        self.status_bar.showMessage("硬件已断开")
        
        # 取消消息回调
        can_manager.unregister_callback(self.handle_can_message)
        
        # 清空表格
        self.message_count = 0
        self.message_table.setRowCount(0)
        
        # 重置信号值
        self.reset_signal_display()
    def on_multi_connect_clicked(self):
        """多硬件连接按钮点击"""
        try:
            from src.ui.enhanced_connect_dialog import EnhancedConnectDialog
            
            dialog = EnhancedConnectDialog(self)
            
            # ✅ 修复：正确连接信号
            dialog.devices_connected.connect(self.on_devices_connected)
            
            # 显示对话框
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                print("硬件连接配置完成")
            else:
                print("硬件连接已取消")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开硬件连接对话框失败: {e}")
            import traceback
            traceback.print_exc()
    def on_devices_connected(self, device_list):
        """设备连接完成后的处理"""
        if device_list:
            # 更新设备显示
            self.update_device_display(device_list)
            
            connected_count = len(device_list)
            if connected_count > 0:
                self.btn_import_dbc.setEnabled(True)
                self.btn_disconnect_all.setEnabled(True)
                self.btn_start.setEnabled(True)
                
                self.lbl_main_status.setText(f"✅ 已连接 {connected_count} 个设备")
                self.status_bar.showMessage(f"设备连接成功: {connected_count} 个设备就绪", 3000)
                
                # 自动开始监控
                if self.btn_start.text() == "▶️ 开始监控":
                    self.start_monitoring()
        else:
            self.lbl_main_status.setText("⚠️ 无设备连接")
            QMessageBox.warning(self, "警告", "没有设备成功连接，请检查连接设置")
    

    def update_device_display(self, device_list):
        """更新设备显示"""
        # 这里可以根据需要更新设备显示
        pass

    def on_disconnect_all_clicked(self):
        """断开所有设备"""
        if self.btn_start.text() == "⏸️ 停止监控":
            self.stop_monitoring()
        
        multi_can_manager.disconnect_all_devices()
        self.update_device_table()
        
        self.btn_import_dbc.setEnabled(False)
        self.btn_signal_config.setEnabled(False)
        self.btn_import_config.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_record.setEnabled(False)
        self.btn_disconnect_all.setEnabled(False)
        
        self.lbl_main_status.setText("🔌 所有设备已断开")
        self.status_bar.showMessage("所有CAN设备已断开", 3000)
        
        # 清空表格
        self.message_count = 0
        self.message_table.setRowCount(0)
        self.clear_signal_display()
    def start_monitoring(self):
        """开始监控"""
        if not multi_can_manager.get_connected_devices():
            QMessageBox.warning(self, "警告", "没有已连接的设备")
            return
        
        # 更新按钮状态
        self.btn_start.setText("⏸️ 停止监控")
        self.btn_record.setEnabled(True)
        self.lbl_main_status.setText("📡 监控中...")
        
        # 开始接收数据
        multi_can_manager.start_receiving()
        
        # 重置计数器
        multi_can_manager.clear_statistics()
        self.message_count = 0
        self.message_table.setRowCount(0)
        
        self.status_bar.showMessage("开始监控所有设备", 3000)

    def stop_monitoring(self):
        """停止监控"""
        # 更新按钮状态
        self.btn_start.setText("▶️ 开始监控")
        self.btn_record.setEnabled(False)
        self.lbl_main_status.setText("⏹️ 监控已停止")
        
        # 停止接收
        multi_can_manager.stop_receiving()
        
        # 停止记录（如果正在记录）
        if self.recording:
            self.stop_recording()
        
        self.status_bar.showMessage("监控已停止", 3000)

    def on_start_clicked(self):
        """开始/停止监控按钮点击"""
        if self._processing_click:
            return
        
        self._processing_click = True
        try:
            current_text = self.btn_start.text()
            
            if current_text == "▶️ 开始监控":
                self.start_monitoring()
            elif current_text == "⏸️ 停止监控":
                self.stop_monitoring()
                
        finally:
            self._processing_click = False
    
    def stop_all_tasks(self):
        """停止所有任务"""
        print("[stop_all_tasks] 开始停止所有任务")
        
        def stop_tasks():
            # 1. 停止CAN管理器
            print("  停止CAN管理器...")
            try:
                can_manager.stop_receiving()
                print("  ✓ CAN管理器已停止")
            except Exception as e:
                print(f"  ✗ 停止CAN管理器失败: {e}")
            
            # 2. 停止测试模式
            print("  停止测试模式...")
            if hasattr(self, 'test_mode') and self.test_mode:
                try:
                    if self.test_mode.running:
                        self.test_mode.stop()
                        print(f"  ✓ 测试模式已停止 (running={self.test_mode.running})")
                    else:
                        print(f"  ✓ 测试模式未运行 (running={self.test_mode.running})")
                except Exception as e:
                    print(f"  ✗ 停止测试模式失败: {e}")
            else:
                print("  ✓ 测试模式对象不存在")
            
            print("[stop_all_tasks] 所有任务已停止")
        
        # 在后台线程中执行停止操作
        stop_thread = threading.Thread(target=stop_tasks, daemon=True)
        stop_thread.start()
    def update_status_display(self):
        """更新状态显示"""
        try:
            # 更新设备计数
            total_devices = len(multi_can_manager.devices)
            connected_devices = len(multi_can_manager.get_connected_devices())
            self.lbl_device_count.setText(f"设备: {connected_devices}/{total_devices}")
            
            # 更新消息率
            stats = multi_can_manager.get_statistics()
            message_rate = int(stats['message_rate'])
            self.lbl_message_rate.setText(f"消息率: {message_rate}/s")
            
            # 更新内存使用
            import psutil
            memory = psutil.Process().memory_info().rss / 1024 / 1024
            self.lbl_memory.setText(f"💾 内存: {memory:.1f} MB")
            
            # 更新队列状态
            queue_size = stats['queue_size']
            if queue_size > 8000:
                self.status_bar.showMessage(f"警告: 消息队列较满 ({queue_size})", 1000)
                
        except Exception as e:
            print(f"更新状态显示失败: {e}")

    def update_clock(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.lbl_time.setText(f"🕐 {current_time}")
    def handle_can_message(self, can_msg):
        """处理CAN消息（在多CAN管理器的线程中调用）"""
        # 检查是否在监控状态
        if self.btn_start.text() == "▶️ 开始监控":
            return
        
        # 发送到主线程处理
        self.can_message_received.emit(can_msg)

    def on_can_message_received(self, can_msg):
        """在主线程中处理CAN消息"""
        self.message_count += 1
        
        # 更新原始报文表格
        self.add_message_to_table(can_msg)
        
        # 如果DBC已加载，解析信号
        if dbc_manager.messages:
            self.update_signal_values(can_msg)
        
        # 如果正在记录，写入文件
        if self.recording and self.recording_file:
            self.record_message(can_msg)

    def add_message_to_table(self, can_msg):
        """添加报文到表格"""
        # 检查是否显示所有设备
        if not self.cb_show_all.isChecked():
            current_device = self.combo_device_filter.currentText()
            if current_device != "所有设备" and can_msg.device_name != current_device:
                return
        
        row = self.message_table.rowCount()
        self.message_table.insertRow(0)  # 插入到第一行
        
        # 只保留最近200条报文
        if row >= 200:
            self.message_table.removeRow(200)
        
        # 时间戳
        timestamp = datetime.fromtimestamp(can_msg.timestamp).strftime('%H:%M:%S.%f')[:-3]
        
        # 填充数据
        self.message_table.setItem(0, 0, QTableWidgetItem(timestamp))
        self.message_table.setItem(0, 1, QTableWidgetItem(can_msg.device_name))
        self.message_table.setItem(0, 2, QTableWidgetItem(can_msg.port))
        self.message_table.setItem(0, 3, QTableWidgetItem(f"0x{can_msg.can_id:08X}"))
        self.message_table.setItem(0, 4, QTableWidgetItem(can_msg.data.hex(' ').upper()))
        self.message_table.setItem(0, 5, QTableWidgetItem(str(can_msg.dlc)))
        self.message_table.setItem(0, 6, QTableWidgetItem("扩展" if can_msg.is_extended else "标准"))
    def update_device_table(self):
        """更新设备状态表格"""
        self.device_table.setRowCount(0)
        
        devices_info = multi_can_manager.get_all_device_info()
        
        for i, device_info in enumerate(devices_info):
            self.device_table.insertRow(i)
            
            # 设备名称
            name_item = QTableWidgetItem(device_info['name'])
            self.device_table.setItem(i, 0, name_item)
            
            # 设备类型
            type_item = QTableWidgetItem(device_info['type'])
            self.device_table.setItem(i, 1, type_item)
            
            # 端口
            port_item = QTableWidgetItem(device_info['port'])
            self.device_table.setItem(i, 2, port_item)
            
            # 状态
            status_text = "✅ 已连接" if device_info['connected'] else "❌ 未连接"
            status_item = QTableWidgetItem(status_text)
            if device_info['connected']:
                status_item.setForeground(QColor(0, 128, 0))  # 绿色
            else:
                status_item.setForeground(QColor(255, 0, 0))  # 红色
            self.device_table.setItem(i, 3, status_item)
            
            # 消息数
            count_item = QTableWidgetItem(str(device_info['message_count']))
            self.device_table.setItem(i, 4, count_item)
            
            # 错误数
            error_item = QTableWidgetItem(str(device_info['error_count']))
            if device_info['error_count'] > 0:
                error_item.setForeground(QColor(255, 0, 0))  # 红色
            self.device_table.setItem(i, 5, error_item)

    def update_device_filter_combo(self):
        """更新设备过滤下拉框"""
        self.combo_device_filter.clear()
        self.combo_device_filter.addItem("所有设备")
        
        devices_info = multi_can_manager.get_all_device_info()
        for device_info in devices_info:
            if device_info['connected']:
                self.combo_device_filter.addItem(device_info['name'])

    def on_device_status_changed(self, device_id, connected):
        """设备状态变化"""
        self.update_device_table()
        self.update_device_filter_combo()
        
        device_info = multi_can_manager.get_device_info(device_id)
        if device_info:
            status = "连接" if connected else "断开"
            self.status_bar.showMessage(f"设备 {device_info['name']} {status}", 2000)
    def update_signal_values(self, can_msg):
        """使用DBC解析的数据更新信号值"""
        if not dbc_manager.messages:
            return  # DBC未加载
        
        # 解码消息
        decoded = dbc_manager.decode_message(can_msg.can_id, can_msg.data)
        
        if not decoded:
            return  # 无法解码或DBC中没有该消息
        
        # 更新信号配置中的值
        for signal_name, value in decoded.items():
            signal_config.update_signal_value(
                can_msg.can_id,
                signal_name,
                value,
                can_msg.timestamp
            )
        
        # 更新表格显示
        self.update_signal_table_with_values(decoded, can_msg)

    def update_signal_table_with_values(self, decoded_signals, can_msg):
        """使用解码后的信号值更新表格"""
        current_time = time.strftime("%H:%M:%S")
        
        # 查找需要更新的信号
        for i, selected_signal in enumerate(signal_config.selected_signals):
            if (selected_signal.message_ref.can_id == can_msg.can_id and 
                selected_signal.signal_ref.name in decoded_signals):
                
                value = decoded_signals[selected_signal.signal_ref.name]
                
                # 更新表格
                if i < self.signal_table.rowCount():
                    self.signal_table.setItem(i, 1, QTableWidgetItem(f"{value:.3f}"))
                    self.signal_table.setItem(i, 3, QTableWidgetItem(current_time))
                    
                    # 可选：根据值范围设置颜色
                    self.update_cell_color(i, 1, value, selected_signal.signal_ref)

    def update_cell_color(self, row, col, value, signal_ref):
        """根据值范围更新单元格颜色"""
        if signal_ref.min is not None and value < signal_ref.min:
            color = QColor(255, 200, 200)  # 浅红色，低于最小值
        elif signal_ref.max is not None and value > signal_ref.max:
            color = QColor(255, 200, 200)  # 浅红色，高于最大值
        else:
            color = QColor(selected_signal.color)  # 使用配置的颜色
        
        item = self.signal_table.item(row, col)
        if item:
            item.setForeground(color)    
    def reset_signal_display(self):
        """重置信号显示"""
        for i in range(10):
            self.signal_table.setItem(i, 1, QTableWidgetItem("--"))
            self.signal_table.setItem(i, 3, QTableWidgetItem("--"))
    
    def freeze_signal_display(self):
        """冻结信号显示（停止时调用）"""
        current_time = time.strftime("%H:%M:%S")
        
        for i in range(10):
            try:
                current_item = self.signal_table.item(i, 1)
                if current_item:
                    current_value = current_item.text()
                    if current_value not in ["--", "已停止", "就绪"]:
                        self.signal_table.setItem(i, 3, QTableWidgetItem(f"已停止 ({current_time})"))
            except:
                pass
    
    def on_import_dbc_clicked(self):
        """导入DBC按钮点击"""
        dialog = ImportDBCDialog(self)
        
        def on_dbc_imported():
            """DBC导入完成后的处理"""
            messages = dbc_manager.get_all_messages()
            signals = dbc_manager.get_all_signals()
            
            # 更新状态栏
            self.status_bar.showMessage(
                f"DBC导入完成: {len(messages)} 个消息, {len(signals)} 个信号"
            )
            
            # 更新按钮状态
            if messages:
                self.btn_signal_config.setEnabled(True)
                
            # 显示提示
            QMessageBox.information(
                self, 
                "导入完成", 
                f"成功导入 {len(messages)} 个消息, {len(signals)} 个信号\n"
                "现在可以配置要监控的信号了。"
            )
        
        dialog.dbc_imported.connect(on_dbc_imported)
        dialog.exec_()
        
    def on_import_config_clicked(self):
        """导入配置按钮点击"""
        try:
            from src.utils.config_manager import ConfigManager
            
            filepath, _ = QFileDialog.getOpenFileName(
                self, "导入信号配置", "", 
                "配置文件 (*.json *.yaml);;所有文件 (*.*)"
            )
            
            if not filepath:
                return
            
            success, message = ConfigManager.import_signal_config(filepath)
            
            if success:
                # 更新界面
                self.update_signal_table_from_config()
                
                status = signal_config.get_signal_status()
                self.status_bar.showMessage(f"配置导入成功: {status['total_selected']} 个信号")
                
                QMessageBox.information(self, "成功", f"配置导入成功\n\n{message}")
                
                # 启用相关按钮
                if status['total_selected'] > 0:
                    self.btn_record.setEnabled(True)
            else:
                QMessageBox.warning(self, "警告", f"配置导入失败\n\n{message}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入配置失败: {e}")

    def on_export_config_clicked(self):
        """导出配置按钮点击"""
        try:
            from src.utils.config_manager import ConfigManager
            
            if not signal_config.selected_signals:
                QMessageBox.warning(self, "警告", "没有要导出的信号配置")
                return
            
            default_filename = f"can_signal_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出信号配置", default_filename,
                "JSON文件 (*.json);;YAML文件 (*.yaml);;所有文件 (*.*)"
            )
            
            if not filepath:
                return
            
            success = ConfigManager.export_signal_config(filepath)
            
            if success:
                QMessageBox.information(self, "成功", f"配置已导出到:\n{filepath}")
            else:
                QMessageBox.warning(self, "警告", "配置导出失败")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出配置失败: {e}")


    def on_signal_config_clicked(self):
        """信号配置按钮点击事件"""
        try:
            # 确保dbc_manager存在
            if not hasattr(self, 'dbc_manager'):
                self.dbc_manager = None
            
            # 创建对话框
            dialog = AdvancedSignalDialog(self, self.dbc_manager)
            
            # 设置对话框样式
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTableWidget {
                    background-color: white;
                    border: 1px solid #cccccc;
                    gridline-color: #e0e0e0;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #4a9cff;
                    color: white;
                }
                QPushButton {
                    background-color: #5c6bc0;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3f51b5;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
                QLineEdit {
                    padding: 6px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QLabel {
                    font-weight: bold;
                }
            """)
            
            # 显示对话框
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                signal_configs = dialog.signal_configs
                
                # 过滤有效配置
                valid_configs = []
                for config in signal_configs:
                    if config.get('name', '').strip():
                        valid_configs.append(config)
                
                if valid_configs:
                    # 如果还没有save_signal_configs方法，添加一个简单的
                    if not hasattr(self, 'save_signal_configs'):
                        import json
                        import os
                        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
                        if not os.path.exists(config_dir):
                            os.makedirs(config_dir)
                        
                        config_file = os.path.join(config_dir, "signal_configs.json")
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(valid_configs, f, ensure_ascii=False, indent=2)
                        
                        print(f"信号配置已保存到: {config_file}")
                    
                    QMessageBox.information(self, "成功", 
                        f"已成功配置 {len(valid_configs)} 个信号")
            
        except Exception as e:
            print(f"打开信号配置对话框时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", 
                f"打开信号配置对话框时出错:\n{str(e)}")
            
    def on_signals_updated():
        """信号更新完成后的处理"""
        # 更新信号表格显示
        self.update_signal_table_from_config()
        
        # 更新状态栏
        status = signal_config.get_signal_status()
        self.status_bar.showMessage(
            f"信号配置完成: {status['total_selected']} 个信号", 3000
        )
        
        # 启用记录按钮
        if status['total_selected'] > 0:
            self.btn_record.setEnabled(True)
        
        QMessageBox.information(
            self,
            "配置完成",
            f"已成功配置 {status['total_selected']} 个信号\n\n"
            f"提示: 现在可以开始监控和记录数据"
        )
    def save_configs_to_dbc_manager(self, configs):
        """将配置保存到dbc_manager"""
        if self.dbc_manager is None:
            return
        
        try:
            # 在dbc_manager中创建自定义信号配置属性
            if not hasattr(self.dbc_manager, 'signal_configs'):
                self.dbc_manager.signal_configs = []
            
            # 更新配置
            self.dbc_manager.signal_configs = configs
            
            print(f"已将 {len(configs)} 个配置保存到dbc_manager")
            
            # 可以选择保存到文件
            if hasattr(self.dbc_manager, 'save_signal_configs'):
                self.dbc_manager.save_signal_configs(configs)
            
        except Exception as e:
            print(f"保存配置到dbc_manager失败: {e}")            
    
    def on_config_clicked(self):
        """配置按钮点击 - 增强版"""
        try:
            # 检查是否已加载DBC
            messages = dbc_manager.get_all_messages()
            if not messages:
                QMessageBox.warning(
                    self, 
                    "警告", 
                    "请先导入DBC文件\n\n"
                    "操作步骤:\n"
                    "1. 点击'连接硬件'连接设备\n"
                    "2. 点击'导入DBC'加载J1939数据库\n"
                    "3. 再点击'信号配置'选择监控信号"
                )
                return
            
            from src.ui.signal_select_dialog import SignalSelectDialog
            
            dialog = SignalSelectDialog(self)
            
            def on_signals_selected():
                """信号选择完成后的处理"""
                try:
                    # 更新信号表格显示
                    self.update_signal_table_from_config()
                    
                    # 更新状态栏
                    status = signal_config.get_signal_status()
                    self.status_bar.showMessage(
                        f"已选择 {status['total_selected']} 个信号进行监控"
                    )
                    
                    # 启用记录按钮
                    if status['total_selected'] > 0:
                        self.btn_record.setEnabled(True)
                    
                    QMessageBox.information(
                        self,
                        "配置完成",
                        f"已成功配置 {status['total_selected']} 个信号\n\n"
                        f"提示: 现在可以点击'开始监控'查看实时数据"
                    )
                except Exception as e:
                    print(f"信号选择后处理失败: {e}")
                    QMessageBox.warning(self, "警告", f"配置处理失败: {e}")
            
            dialog.signals_selected.connect(on_signals_selected)
            
            # 显示对话框（模态）
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                print(f"信号配置完成，选择了 {len(signal_config.selected_signals)} 个信号")
            else:
                print("信号配置已取消")
                
        except Exception as e:
            print(f"打开信号配置对话框失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"打开配置对话框失败: {e}")
    def update_signal_table_from_config(self):
        """根据配置更新信号表格"""
        # 清空表格
        self.signal_table.setRowCount(0)
        
        # 添加选中的信号
        for i, selected_signal in enumerate(signal_config.selected_signals):
            self.signal_table.insertRow(i)
            
            self.signal_table.setItem(i, 0, QTableWidgetItem(selected_signal.display_name))
            self.signal_table.setItem(i, 1, QTableWidgetItem("--"))
            self.signal_table.setItem(i, 2, QTableWidgetItem(selected_signal.signal_ref.unit))
            self.signal_table.setItem(i, 3, QTableWidgetItem("--"))
            
            # 设置颜色（可选）
            color = QColor(selected_signal.color)
            for col in range(4):
                item = self.signal_table.item(i, col)
                if item:
                    item.setForeground(color)        
    def on_record_clicked(self):
        """记录按钮点击"""
        if self.btn_record.text() == "开始记录":
            self.btn_record.setText("停止记录")
            self.status_bar.showMessage("记录中...")
        else:
            self.btn_record.setText("开始记录")
            self.status_bar.showMessage("监控中...")
    def clear_message_table(self):
        """清空报文表格"""
        self.message_table.setRowCount(0)
        self.message_count = 0
        self.status_bar.showMessage("报文表格已清空", 2000)

    def clear_signal_display(self):
        """清空信号显示"""
        self.signal_table.setRowCount(0)
        
        # 如果没有选择的信号，显示默认行
        if len(signal_config.selected_signals) == 0:
            for i in range(10):
                self.signal_table.insertRow(i)
                self.signal_table.setItem(i, 0, QTableWidgetItem(f"信号{i+1}"))
                self.signal_table.setItem(i, 1, QTableWidgetItem("--"))
                self.signal_table.setItem(i, 2, QTableWidgetItem(""))
                self.signal_table.setItem(i, 3, QTableWidgetItem("--"))
                self.signal_table.setItem(i, 4, QTableWidgetItem("--"))
                self.signal_table.setItem(i, 5, QTableWidgetItem("--"))

    def update_signal_table_from_config(self):
        """根据配置更新信号表格"""
        try:
            # 清空表格
            self.signal_table.setRowCount(0)
            
            # 添加选中的信号
            for i, selected_signal in enumerate(signal_config.selected_signals):
                self.signal_table.insertRow(i)
                
                self.signal_table.setItem(i, 0, QTableWidgetItem(selected_signal.display_name))
                self.signal_table.setItem(i, 1, QTableWidgetItem("--"))
                
                unit = selected_signal.signal_ref.unit if hasattr(selected_signal.signal_ref, 'unit') else ""
                self.signal_table.setItem(i, 2, QTableWidgetItem(unit))
                
                # 默认设备显示为"所有"
                self.signal_table.setItem(i, 3, QTableWidgetItem("所有"))
                self.signal_table.setItem(i, 4, QTableWidgetItem("--"))
                self.signal_table.setItem(i, 5, QTableWidgetItem("正常"))
                
                # 设置颜色
                try:
                    color = QColor(selected_signal.color)
                    for col in range(6):
                        item = self.signal_table.item(i, col)
                        if item:
                            item.setForeground(color)
                except:
                    pass
            
            # 如果没有选择的信号，显示默认行
            if len(signal_config.selected_signals) == 0:
                for i in range(10):
                    self.signal_table.insertRow(i)
                    self.signal_table.setItem(i, 0, QTableWidgetItem(f"信号{i+1}"))
                    self.signal_table.setItem(i, 1, QTableWidgetItem("--"))
                    self.signal_table.setItem(i, 2, QTableWidgetItem(""))
                    self.signal_table.setItem(i, 3, QTableWidgetItem("--"))
                    self.signal_table.setItem(i, 4, QTableWidgetItem("--"))
                    self.signal_table.setItem(i, 5, QTableWidgetItem("--"))
            
        except Exception as e:
            print(f"更新信号表格失败: {e}")

    def update_signal_values(self, can_msg):
        """使用DBC解析的数据更新信号值"""
        try:
            # 检查是否有DBC数据
            if not hasattr(dbc_manager, 'messages') or not dbc_manager.messages:
                return  # DBC未加载
                
            # 解码消息
            decoded = dbc_manager.decode_message(can_msg.can_id, can_msg.data)
            
            if not decoded:
                return  # 无法解码或DBC中没有该消息
            
            # 更新信号配置中的值
            for signal_name, value in decoded.items():
                signal_config.update_signal_value(
                    can_msg.can_id,
                    signal_name,
                    value,
                    can_msg.timestamp
                )
            
            # 更新表格显示
            self.update_signal_table_with_values(decoded, can_msg)
            
        except Exception as e:
            print(f"更新信号值失败: {e}")

    def update_signal_table_with_values(self, decoded_signals, can_msg):
        """使用解码后的信号值更新表格"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # 查找需要更新的信号
            for i, selected_signal in enumerate(signal_config.selected_signals):
                try:
                    if (selected_signal.message_ref.can_id == can_msg.can_id and 
                        selected_signal.signal_ref.name in decoded_signals):
                        
                        value = decoded_signals[selected_signal.signal_ref.name]
                        
                        # 更新表格
                        if i < self.signal_table.rowCount():
                            self.signal_table.setItem(i, 1, QTableWidgetItem(f"{value:.3f}"))
                            self.signal_table.setItem(i, 3, QTableWidgetItem(can_msg.device_name))
                            self.signal_table.setItem(i, 4, QTableWidgetItem(current_time))
                            
                            # 根据值范围更新状态
                            status = self.check_signal_status(value, selected_signal.signal_ref)
                            self.signal_table.setItem(i, 5, QTableWidgetItem(status))
                            
                            # 设置状态颜色
                            if status == "正常":
                                color = QColor(0, 128, 0)  # 绿色
                            elif status == "警告":
                                color = QColor(255, 165, 0)  # 橙色
                            else:
                                color = QColor(255, 0, 0)  # 红色
                            
                            status_item = self.signal_table.item(i, 5)
                            if status_item:
                                status_item.setForeground(color)
                except:
                    continue  # 跳过错误
                    
        except Exception as e:
            print(f"更新信号表格值失败: {e}")

    def check_signal_status(self, value, signal_ref):
        """检查信号状态"""
        try:
            # 检查是否有最小最大值
            has_min = hasattr(signal_ref, 'min') and signal_ref.min is not None
            has_max = hasattr(signal_ref, 'max') and signal_ref.max is not None
            
            if has_min and value < signal_ref.min:
                return "过低"
            elif has_max and value > signal_ref.max:
                return "过高"
            else:
                return "正常"
                
        except:
            return "正常"

    def record_message(self, can_msg):
        """记录消息到文件"""
        try:
            if not self.recording_file:
                return
            
            timestamp = datetime.fromtimestamp(can_msg.timestamp).isoformat()
            
            # 如果是CSV文件
            if self.recording_file.endswith('.csv'):
                import csv
                
                # 解码信号
                decoded = {}
                if dbc_manager.messages:
                    decoded = dbc_manager.decode_message(can_msg.can_id, can_msg.data)
                
                # 写入CSV行
                writer = csv.writer(self.recording_file_obj)
                
                if decoded:
                    # 写入解码后的信号
                    for signal_name, value in decoded.items():
                        row = [
                            timestamp,
                            can_msg.device_name,
                            can_msg.port,
                            f"0x{can_msg.can_id:08X}",
                            signal_name,
                            value,
                            can_msg.data.hex()
                        ]
                        writer.writerow(row)
                else:
                    # 写入原始报文
                    row = [
                        timestamp,
                        can_msg.device_name,
                        can_msg.port,
                        f"0x{can_msg.can_id:08X}",
                        "RAW",
                        "",
                        can_msg.data.hex()
                    ]
                    writer.writerow(row)
                    
        except Exception as e:
            print(f"记录消息失败: {e}")

    def start_recording(self):
        """开始记录"""
        try:
            # 选择保存文件
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存记录文件", "", 
                "CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if not filename:
                return False
            
            # 添加时间戳到文件名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            if not filename.endswith('.csv'):
                filename = f"{filename}_{timestamp}.csv"
            
            self.recording_file = filename
            self.recording_file_obj = open(filename, 'w', newline='', encoding='utf-8')
            self.recording_start_time = time.time()
            
            # 写入CSV表头
            import csv
            writer = csv.writer(self.recording_file_obj)
            writer.writerow([
                '时间戳', '设备名称', '端口', 'CAN ID', '信号名称', 
                '信号值', '原始数据', '扩展帧', 'DLC'
            ])
            
            # 更新界面
            self.btn_record.setText("⏹️ 停止记录")
            self.recording = True
            self.lbl_recording.setText(f"⏺️ 记录中: {os.path.basename(filename)}")
            
            self.status_bar.showMessage(f"开始记录到: {filename}", 3000)
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始记录失败: {e}")
            return False

    def stop_recording(self):
        """停止记录"""
        try:
            if self.recording_file_obj:
                self.recording_file_obj.close()
            
            # 更新界面
            self.btn_record.setText("⏺️ 开始记录")
            self.recording = False
            
            record_time = time.time() - self.recording_start_time
            self.lbl_recording.setText(f"⏺️ 记录: 已停止 ({record_time:.1f}秒)")
            
            self.status_bar.showMessage(f"记录已停止，文件保存到: {self.recording_file}", 3000)
            
            # 重置记录状态
            self.recording_file = None
            self.recording_file_obj = None
            self.recording_start_time = None
            
        except Exception as e:
            print(f"停止记录失败: {e}")

    def on_record_clicked(self):
        """记录按钮点击"""
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()
    def cleanup(self):
        """清理资源"""
        try:
            # 停止监控
            if hasattr(self, 'btn_start') and hasattr(self.btn_start, 'text'):
                if self.btn_start.text() == "⏸️ 停止监控":
                    self.stop_monitoring()
            
            # 停止记录
            if hasattr(self, 'recording') and self.recording:
                try:
                    self.stop_recording()
                except:
                    pass
            
            # 停止多CAN管理器
            try:
                from src.hardware.multi_can_manager import multi_can_manager
                multi_can_manager.cleanup()
            except:
                pass
            
            # 清理现有的can_manager
            try:
                from src.hardware.can_manager import can_manager
                can_manager.cleanup()
            except:
                pass
            
            # 清理测试模式（如果有）
            if hasattr(self, 'test_mode') and self.test_mode is not None:
                try:
                    if hasattr(self.test_mode, 'running') and self.test_mode.running:
                        self.test_mode.stop()
                except:
                    pass
            
            print("资源清理完成")
            
        except Exception as e:
            print(f"清理资源时出错: {e}")
        
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 清理资源
        self.cleanup()
        
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出程序吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()