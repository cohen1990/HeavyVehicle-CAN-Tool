#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号选择对话框 - 增强版
"""

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QGroupBox, QMessageBox,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMenu, QAction, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon

from src.dbc.dbc_manager import dbc_manager
from src.config.signal_config import signal_config

class SignalSelectDialog(QDialog):
    """信号选择对话框 - 增强版"""
    
    signals_selected = pyqtSignal()  # 信号选择完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择监控信号")
        self.setMinimumSize(1000, 700)  # 增大窗口尺寸
        self.selected_signals = []
        self.init_ui()
        self.load_dbc_signals()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 1. 标题和工具栏
        toolbar_layout = QHBoxLayout()
        
        title_label = QLabel("选择要监控的信号")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch()
        
        # 搜索框
        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setMaximumWidth(200)
        self.search_edit.setPlaceholderText("输入信号名或消息名...")
        self.search_edit.textChanged.connect(self.filter_signals)
        toolbar_layout.addWidget(self.search_edit)
        
        # 展开/折叠按钮
        self.btn_expand = QPushButton("展开全部")
        self.btn_expand.clicked.connect(self.expand_all)
        toolbar_layout.addWidget(self.btn_expand)
        
        self.btn_collapse = QPushButton("折叠全部")
        self.btn_collapse.clicked.connect(self.collapse_all)
        toolbar_layout.addWidget(self.btn_collapse)
        
        layout.addLayout(toolbar_layout)
        
        # 2. 主区域 - 分割窗口
        splitter = QSplitter(Qt.Horizontal)
        
        # 左面板：信号树（占60%）
        left_widget = QGroupBox("可用信号 (双击或拖拽添加)")
        left_layout = QVBoxLayout()
        
        self.signal_tree = QTreeWidget()
        self.signal_tree.setHeaderLabels(["消息/信号", "ID", "单位", "范围", "类型"])
        self.signal_tree.setColumnWidth(0, 250)
        self.signal_tree.setColumnWidth(1, 100)
        self.signal_tree.setColumnWidth(2, 80)
        self.signal_tree.setColumnWidth(3, 120)
        self.signal_tree.setColumnWidth(4, 80)
        
        # 启用拖拽
        self.signal_tree.setDragEnabled(True)
        self.signal_tree.setDragDropMode(QTreeWidget.DragOnly)
        
        self.signal_tree.itemDoubleClicked.connect(self.on_signal_double_clicked)
        self.signal_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.signal_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        left_layout.addWidget(self.signal_tree)
        
        # 左面板按钮
        left_btn_layout = QHBoxLayout()
        
        self.btn_select_all = QPushButton("全选当前")
        self.btn_select_all.clicked.connect(self.select_current_message)
        left_btn_layout.addWidget(self.btn_select_all)
        
        left_btn_layout.addStretch()
        
        self.btn_add_selected = QPushButton("添加选中 →")
        self.btn_add_selected.clicked.connect(self.add_selected)
        left_btn_layout.addWidget(self.btn_add_selected)
        
        left_layout.addLayout(left_btn_layout)
        left_widget.setLayout(left_layout)
        
        # 右面板：已选信号（占40%）
        right_widget = QGroupBox("已选信号 (最多20个)")
        right_layout = QVBoxLayout()
        
        # 已选信号表格
        self.selected_table = QTableWidget()
        self.selected_table.setColumnCount(6)
        self.selected_table.setHorizontalHeaderLabels([
            "显示名称", "消息", "信号", "单位", "颜色", "操作"
        ])
        self.selected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.selected_table.horizontalHeader().setStretchLastSection(True)
        self.selected_table.setColumnWidth(0, 150)
        self.selected_table.setColumnWidth(1, 100)
        self.selected_table.setColumnWidth(2, 100)
        self.selected_table.setColumnWidth(3, 60)
        self.selected_table.setColumnWidth(4, 60)
        
        right_layout.addWidget(self.selected_table)
        
        # 右面板按钮
        right_btn_layout = QHBoxLayout()
        
        self.btn_save_config = QPushButton("保存配置")
        self.btn_save_config.clicked.connect(self.save_configuration)
        right_btn_layout.addWidget(self.btn_save_config)
        
        self.btn_load_config = QPushButton("加载配置")
        self.btn_load_config.clicked.connect(self.load_configuration)
        right_btn_layout.addWidget(self.btn_load_config)
        
        right_btn_layout.addStretch()
        
        self.btn_remove_selected = QPushButton("移除选中")
        self.btn_remove_selected.clicked.connect(self.remove_selected)
        right_btn_layout.addWidget(self.btn_remove_selected)
        
        self.btn_clear_all = QPushButton("清空所有")
        self.btn_clear_all.clicked.connect(self.clear_selected)
        right_btn_layout.addWidget(self.btn_clear_all)
        
        right_layout.addLayout(right_btn_layout)
        right_widget.setLayout(right_layout)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])  # 6:4的比例
        
        layout.addWidget(splitter)
        
        # 3. 底部：统计和控制
        bottom_layout = QHBoxLayout()
        
        # 统计信息
        self.lbl_total_signals = QLabel("总信号数: 0")
        bottom_layout.addWidget(self.lbl_total_signals)
        
        self.lbl_filtered_signals = QLabel("筛选后: 0")
        bottom_layout.addWidget(self.lbl_filtered_signals)
        
        self.lbl_selected_count = QLabel("已选信号: 0/20")
        self.lbl_selected_count.setStyleSheet("color: blue; font-weight: bold;")
        bottom_layout.addWidget(self.lbl_selected_count)
        
        bottom_layout.addStretch()
        
        # 自动颜色选项
        self.cb_auto_color = QCheckBox("自动分配颜色")
        self.cb_auto_color.setChecked(True)
        bottom_layout.addWidget(self.cb_auto_color)
        
        layout.addLayout(bottom_layout)
        
        # 4. 按钮区域
        btn_layout = QHBoxLayout()
        
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setDefault(True)
        btn_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 初始化状态
        self.update_stats()
    
    def load_dbc_signals(self):
        """加载DBC信号到树形控件 - 按字母排序"""
        self.signal_tree.clear()
        
        messages = dbc_manager.get_all_messages()
        if not messages:
            QMessageBox.warning(self, "警告", "请先导入DBC文件")
            return
        
        # 按消息名称字母排序
        sorted_messages = sorted(messages, key=lambda msg: msg.name.upper())
        
        total_signals = 0
        
        # 按消息分组
        for message in sorted_messages:
            parent = QTreeWidgetItem(self.signal_tree)
            parent.setText(0, message.name)
            parent.setText(1, f"0x{message.can_id:X}")
            parent.setText(4, "消息")
            parent.setData(0, Qt.UserRole, message)  # 存储消息对象
            
            # 按信号名称字母排序
            sorted_signals = sorted(message.signals, key=lambda sig: sig.name.upper())
            
            # 添加信号
            for signal in sorted_signals:
                child = QTreeWidgetItem(parent)
                child.setText(0, signal.name)
                child.setText(2, signal.unit if signal.unit else "")
                
                # 显示范围
                range_text = ""
                if signal.min is not None and signal.max is not None:
                    range_text = f"{signal.min:.2f}-{signal.max:.2f}"
                elif signal.min is not None:
                    range_text = f"≥{signal.min:.2f}"
                elif signal.max is not None:
                    range_text = f"≤{signal.max:.2f}"
                child.setText(3, range_text)
                child.setText(4, "信号")
                
                child.setData(0, Qt.UserRole, (message, signal))  # 存储消息和信号对象
                total_signals += 1
            
            # 默认展开前10个消息（否则太多）
            if len(sorted_messages) <= 20:
                parent.setExpanded(True)
            else:
                # 只展开包含搜索词或重要的消息
                important_prefixes = ['ENG', 'EEC', 'CCVS', 'VEP', 'EBC']
                msg_name = message.name.upper()
                if any(msg_name.startswith(prefix) for prefix in important_prefixes):
                    parent.setExpanded(True)
        
        # 更新统计
        self.lbl_total_signals.setText(f"总信号数: {total_signals}")
        self.lbl_filtered_signals.setText(f"筛选后: {total_signals}")
    
    def expand_all(self):
        """展开所有消息"""
        for i in range(self.signal_tree.topLevelItemCount()):
            item = self.signal_tree.topLevelItem(i)
            item.setExpanded(True)
    
    def collapse_all(self):
        """折叠所有消息"""
        for i in range(self.signal_tree.topLevelItemCount()):
            item = self.signal_tree.topLevelItem(i)
            item.setExpanded(False)
    
    def filter_signals(self, text):
        """过滤信号 - 完整修复版"""
        try:
            text = text.lower()
            
            visible_count = 0
            root = self.signal_tree.invisibleRootItem()
            
            if not root:
                return
            
            # 遍历所有顶级项目（消息）
            for i in range(root.childCount()):
                message_item = root.child(i)
                if not message_item:
                    continue
                    
                message_name = message_item.text(0).lower() if message_item.text(0) else ""
                message_has_visible_child = False
                
                # 遍历所有子项目（信号）
                for j in range(message_item.childCount()):
                    signal_item = message_item.child(j)
                    if not signal_item:
                        continue
                        
                    signal_name = signal_item.text(0).lower() if signal_item.text(0) else ""
                    
                    # 检查是否匹配
                    if text in signal_name or text in message_name:
                        signal_item.setHidden(False)
                        message_has_visible_child = True
                        visible_count += 1
                    else:
                        signal_item.setHidden(True)
                
                # 设置消息项的可见性
                if text in message_name or message_has_visible_child:
                    message_item.setHidden(False)
                    if message_has_visible_child:
                        message_item.setExpanded(True)
                    visible_count += 1
                else:
                    message_item.setHidden(True)
            
            self.lbl_filtered_signals.setText(f"筛选后: {visible_count}")
            
        except Exception as e:
            print(f"过滤信号时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def select_current_message(self):
        """选择当前消息的所有信号"""
        current_item = self.signal_tree.currentItem()
        if not current_item:
            return
        
        # 如果是消息节点，选择其所有子信号
        if current_item.childCount() > 0:
            for i in range(current_item.childCount()):
                child = current_item.child(i)
                self.add_signal_item(child)
        # 如果是信号节点，选择它
        elif current_item.parent():
            self.add_signal_item(current_item)
    
    def show_tree_context_menu(self, position):
        """显示树形控件的右键菜单"""
        item = self.signal_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        if item.childCount() > 0:  # 消息节点
            add_message_action = QAction("添加此消息所有信号", self)
            add_message_action.triggered.connect(self.select_current_message)
            menu.addAction(add_message_action)
        else:  # 信号节点
            add_signal_action = QAction("添加此信号", self)
            add_signal_action.triggered.connect(lambda: self.add_signal_item(item))
            menu.addAction(add_signal_action)
        
        menu.exec_(self.signal_tree.viewport().mapToGlobal(position))
    
    def on_signal_double_clicked(self, item, column):
        """双击信号添加到已选列表"""
        if item.childCount() == 0:  # 只处理信号节点
            self.add_signal_item(item)
    
    def add_selected(self):
        """添加选中的信号"""
        items = self.signal_tree.selectedItems()
        for item in items:
            if item.childCount() == 0:  # 只处理信号节点
                self.add_signal_item(item)
    
    def add_signal_item(self, tree_item):
        """从树节点添加信号到表格"""
        if len(self.selected_signals) >= 20:
            QMessageBox.warning(self, "警告", "最多只能选择20个信号")
            return
        
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return
        
        message, signal = data
        
        # 检查是否已存在
        for selected in self.selected_signals:
            if (selected['message'].name == message.name and 
                selected['signal'].name == signal.name):
                return  # 已存在，跳过
        
        # 添加到表格
        row = self.selected_table.rowCount()
        self.selected_table.insertRow(row)
        
        # 生成显示名称
        display_name = f"{message.name}.{signal.name}"
        
        # 添加数据
        self.selected_table.setItem(row, 0, QTableWidgetItem(display_name))
        self.selected_table.setItem(row, 1, QTableWidgetItem(message.name))
        self.selected_table.setItem(row, 2, QTableWidgetItem(signal.name))
        self.selected_table.setItem(row, 3, QTableWidgetItem(signal.unit if signal.unit else ""))
        
        # 颜色显示
        color_index = len(self.selected_signals) % len(signal_config.color_pool)
        color = signal_config.color_pool[color_index]
        color_item = QTableWidgetItem()
        color_item.setBackground(QColor(color))
        self.selected_table.setItem(row, 4, color_item)
        
        # 添加移除按钮
        remove_btn = QPushButton("移除")
        remove_btn.clicked.connect(lambda: self.remove_row(row))
        self.selected_table.setCellWidget(row, 5, remove_btn)
        
        # 存储数据
        self.selected_signals.append({
            'message': message,
            'signal': signal,
            'display_name': display_name,
            'color': color
        })
        
        # 更新统计
        self.update_stats()
    
    def remove_row(self, row):
        """移除指定行"""
        if 0 <= row < len(self.selected_signals):
            self.selected_signals.pop(row)
            self.selected_table.removeRow(row)
            
            # 重新设置行号（因为按钮的lambda需要正确的行号）
            for i in range(self.selected_table.rowCount()):
                btn = self.selected_table.cellWidget(i, 5)
                if btn:
                    btn.clicked.disconnect()
                    btn.clicked.connect(lambda checked, r=i: self.remove_row(r))
            
            self.update_stats()
    
    def remove_selected(self):
        """移除选中的行"""
        selected_rows = set()
        for item in self.selected_table.selectedItems():
            selected_rows.add(item.row())
        
        # 从后往前移除，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            self.remove_row(row)
    
    def clear_selected(self):
        """清空所有已选信号"""
        self.selected_signals.clear()
        self.selected_table.setRowCount(0)
        self.update_stats()
    
    def save_configuration(self):
        """保存配置到文件"""
        if not self.selected_signals:
            QMessageBox.warning(self, "警告", "没有要保存的信号配置")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存信号配置", "", 
            "JSON文件 (*.json);;YAML文件 (*.yaml);;所有文件 (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # 构建配置数据
            config_data = {
                'version': '1.0',
                'signals': [],
                'settings': {
                    'auto_color': self.cb_auto_color.isChecked()
                }
            }
            
            for item in self.selected_signals:
                config_data['signals'].append({
                    'message_name': item['message'].name,
                    'message_id': item['message'].can_id,
                    'signal_name': item['signal'].name,
                    'display_name': item['display_name'],
                    'color': item['color']
                })
            
            # 保存到文件
            if filepath.endswith('.json'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif filepath.endswith('.yaml'):
                import yaml
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            else:
                # 默认用JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "成功", f"配置已保存到:\n{filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败:\n{e}")
    
    def load_configuration(self):
        """从文件加载配置"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载信号配置", "", 
            "配置文件 (*.json *.yaml);;所有文件 (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # 读取文件
            if filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif filepath.endswith('.yaml'):
                import yaml
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                QMessageBox.warning(self, "警告", "不支持的文件格式")
                return
            
            # 验证数据格式
            if 'signals' not in config_data:
                QMessageBox.warning(self, "警告", "无效的配置文件格式")
                return
            
            # 清空当前选择
            self.clear_selected()
            
            # 加载信号
            loaded_count = 0
            failed_count = 0
            
            for sig_data in config_data['signals']:
                try:
                    # 查找消息和信号
                    message = dbc_manager.get_message_by_name(sig_data['message_name'])
                    if not message:
                        # 尝试用ID查找
                        message = dbc_manager.get_message(sig_data.get('message_id', 0))
                    
                    if not message:
                        failed_count += 1
                        continue
                    
                    signal = message.get_signal(sig_data['signal_name'])
                    if not signal:
                        failed_count += 1
                        continue
                    
                    # 添加到表格
                    row = self.selected_table.rowCount()
                    self.selected_table.insertRow(row)
                    
                    display_name = sig_data.get('display_name', f"{message.name}.{signal.name}")
                    color = sig_data.get('color', signal_config.color_pool[loaded_count % len(signal_config.color_pool)])
                    
                    self.selected_table.setItem(row, 0, QTableWidgetItem(display_name))
                    self.selected_table.setItem(row, 1, QTableWidgetItem(message.name))
                    self.selected_table.setItem(row, 2, QTableWidgetItem(signal.name))
                    self.selected_table.setItem(row, 3, QTableWidgetItem(signal.unit if signal.unit else ""))
                    
                    color_item = QTableWidgetItem()
                    color_item.setBackground(QColor(color))
                    self.selected_table.setItem(row, 4, color_item)
                    
                    remove_btn = QPushButton("移除")
                    remove_btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
                    self.selected_table.setCellWidget(row, 5, remove_btn)
                    
                    self.selected_signals.append({
                        'message': message,
                        'signal': signal,
                        'display_name': display_name,
                        'color': color
                    })
                    
                    loaded_count += 1
                    
                    if loaded_count >= 20:
                        break  # 达到上限
                        
                except Exception as e:
                    failed_count += 1
                    continue
            
            # 更新设置
            if 'settings' in config_data:
                self.cb_auto_color.setChecked(config_data['settings'].get('auto_color', True))
            
            self.update_stats()
            
            msg = f"加载完成:\n成功: {loaded_count} 个信号"
            if failed_count > 0:
                msg += f"\n失败: {failed_count} 个信号（可能DBC不匹配）"
            
            QMessageBox.information(self, "完成", msg)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败:\n{e}")
    
    def update_stats(self):
        """更新统计信息"""
        selected_count = len(self.selected_signals)
        self.lbl_selected_count.setText(f"已选信号: {selected_count}/20")
        
        # 启用/禁用确定按钮
        self.btn_ok.setEnabled(selected_count > 0)
    
    def accept(self):
        """确定按钮点击"""
        if not self.selected_signals:
            QMessageBox.warning(self, "警告", "请至少选择一个信号")
            return
        
        # 添加到信号配置
        signal_config.clear_signals()
        
        success_count = 0
        for item in self.selected_signals:
            success = signal_config.add_signal(
                item['signal'],
                item['message'],
                item['display_name']
            )
            if success:
                # 设置颜色
                for selected_signal in signal_config.selected_signals:
                    if (selected_signal.display_name == item['display_name']):
                        selected_signal.color = item['color']
                success_count += 1
        
        # 发出信号
        self.signals_selected.emit()
        
        QMessageBox.information(
            self, "成功", 
            f"已成功配置 {success_count} 个信号"
        )
        
        super().accept()