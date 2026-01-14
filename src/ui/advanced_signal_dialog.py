#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版信号配置对话框
"""

import os
import json
import yaml
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QGroupBox, QMessageBox,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMenu, QAction, QCheckBox, QSpinBox,
    QTabWidget, QWidget, QFormLayout, QDoubleSpinBox,
    QColorDialog, QComboBox, QTextEdit, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon

from src.dbc.dbc_manager import dbc_manager
from src.config.signal_config import signal_config

class AdvancedSignalDialog(QDialog):
    """增强版信号配置对话框"""
    
    signals_updated = pyqtSignal()  # 信号更新完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("信号配置管理")
        self.setMinimumSize(1200, 800)
        self.selected_signals = []
        self.signal_limit = 20  # 默认信号数量限制
        
        # 加载当前配置
        self.load_current_config()
        self.init_ui()
        self.load_dbc_signals()
    
    def load_current_config(self):
        """加载当前配置"""
        self.selected_signals.clear()
        for sig in signal_config.selected_signals:
            self.selected_signals.append({
                'message': sig.message_ref,
                'signal': sig.signal_ref,
                'display_name': sig.display_name,
                'color': sig.color,
                'recording_enabled': sig.recording_enabled,
                'custom_min': None,
                'custom_max': None,
                'custom_scale': None,
                'custom_offset': None
            })
    
    def init_ui(self):
        """初始化增强界面"""
        layout = QVBoxLayout()
        
        # 1. 工具栏
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)
        
        # 2. 主区域 - 标签页
        self.tab_widget = QTabWidget()
        
        # 标签1: 信号选择
        self.tab_selection = self.create_selection_tab()
        self.tab_widget.addTab(self.tab_selection, "📡 信号选择")
        
        # 标签2: 信号编辑
        self.tab_editing = self.create_editing_tab()
        self.tab_widget.addTab(self.tab_editing, "✏️ 信号编辑")
        
        # 标签3: 配置管理
        self.tab_config = self.create_config_tab()
        self.tab_widget.addTab(self.tab_config, "⚙️ 配置管理")
        
        layout.addWidget(self.tab_widget)
        
        # 3. 状态栏
        status_bar = self.create_status_bar()
        layout.addLayout(status_bar)
        
        # 4. 按钮栏
        button_bar = self.create_button_bar()
        layout.addLayout(button_bar)
        
        self.setLayout(layout)
        self.update_stats()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 标题
        title = QLabel("📊 高级信号配置")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        toolbar.addWidget(title)
        
        toolbar.addStretch()
        
        # 信号数量限制
        toolbar.addWidget(QLabel("信号限制:"))
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 100)
        self.spin_limit.setValue(self.signal_limit)
        self.spin_limit.valueChanged.connect(self.on_limit_changed)
        self.spin_limit.setMaximumWidth(80)
        toolbar.addWidget(self.spin_limit)
        
        # 快速操作
        btn_clear = QPushButton("🗑️ 清空")
        btn_clear.clicked.connect(self.clear_selected)
        btn_clear.setMaximumWidth(80)
        toolbar.addWidget(btn_clear)
        
        return toolbar
    
    def create_selection_tab(self):
        """创建信号选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 搜索:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入信号名、消息名或ID...")
        self.search_edit.textChanged.connect(self.filter_signals)
        search_layout.addWidget(self.search_edit)
        
        # 过滤选项
        self.cb_show_important = QCheckBox("仅显示重要消息")
        self.cb_show_important.setChecked(True)
        self.cb_show_important.toggled.connect(self.filter_signals)
        search_layout.addWidget(self.cb_show_important)
        
        layout.addLayout(search_layout)
        
        # 分割窗口
        splitter = QSplitter(Qt.Horizontal)
        
        # 左面板：信号树
        left_panel = QGroupBox("📋 可用信号")
        left_layout = QVBoxLayout()
        
        self.signal_tree = QTreeWidget()
        self.signal_tree.setHeaderLabels(["消息/信号", "ID", "单位", "范围", "类型"])
        self.signal_tree.setColumnWidth(0, 250)
        self.signal_tree.setColumnWidth(1, 100)
        self.signal_tree.setColumnWidth(2, 80)
        self.signal_tree.setColumnWidth(3, 150)
        self.signal_tree.setColumnWidth(4, 80)
        
        self.signal_tree.itemDoubleClicked.connect(self.on_signal_double_clicked)
        self.signal_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.signal_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        left_layout.addWidget(self.signal_tree)
        
        # 树控件按钮
        tree_buttons = QHBoxLayout()
        btn_expand = QPushButton("📂 展开")
        btn_expand.clicked.connect(self.expand_all)
        tree_buttons.addWidget(btn_expand)
        
        btn_collapse = QPushButton("📁 折叠")
        btn_collapse.clicked.connect(self.collapse_all)
        tree_buttons.addWidget(btn_collapse)
        
        tree_buttons.addStretch()
        
        btn_select_all = QPushButton("✅ 全选当前")
        btn_select_all.clicked.connect(self.select_current_message)
        tree_buttons.addWidget(btn_select_all)
        
        btn_add_selected = QPushButton("➕ 添加选中 →")
        btn_add_selected.clicked.connect(self.add_selected)
        tree_buttons.addWidget(btn_add_selected)
        
        left_layout.addLayout(tree_buttons)
        left_panel.setLayout(left_layout)
        
        # 右面板：已选信号
        right_panel = QGroupBox("⭐ 已选信号")
        right_layout = QVBoxLayout()
        
        self.selected_table = QTableWidget()
        self.selected_table.setColumnCount(8)
        self.selected_table.setHorizontalHeaderLabels([
            "显示名称", "消息", "信号", "单位", "范围", "颜色", "记录", "操作"
        ])
        self.selected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.selected_table.setColumnWidth(0, 150)
        self.selected_table.setColumnWidth(1, 120)
        self.selected_table.setColumnWidth(2, 120)
        self.selected_table.setColumnWidth(3, 80)
        self.selected_table.setColumnWidth(4, 120)
        self.selected_table.setColumnWidth(5, 60)
        self.selected_table.setColumnWidth(6, 60)
        self.selected_table.setColumnWidth(7, 80)
        
        self.selected_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        right_layout.addWidget(self.selected_table)
        
        # 表格操作按钮
        table_buttons = QHBoxLayout()
        btn_move_up = QPushButton("⬆ 上移")
        btn_move_up.clicked.connect(self.move_signal_up)
        table_buttons.addWidget(btn_move_up)
        
        btn_move_down = QPushButton("⬇ 下移")
        btn_move_down.clicked.connect(self.move_signal_down)
        table_buttons.addWidget(btn_move_down)
        
        table_buttons.addStretch()
        
        btn_edit = QPushButton("✏️ 编辑选中")
        btn_edit.clicked.connect(self.edit_selected_signal)
        table_buttons.addWidget(btn_edit)
        
        btn_remove = QPushButton("❌ 移除选中")
        btn_remove.clicked.connect(self.remove_selected)
        table_buttons.addWidget(btn_remove)
        
        right_layout.addLayout(table_buttons)
        right_panel.setLayout(right_layout)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])
        
        layout.addWidget(splitter)
        widget.setLayout(layout)
        return widget
    
    def create_editing_tab(self):
        """创建信号编辑标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 当前编辑的信号信息
        info_group = QGroupBox("📝 当前编辑信号")
        info_layout = QGridLayout()
        
        self.lbl_edit_signal = QLabel("未选择信号")
        self.lbl_edit_signal.setFont(QFont("Arial", 11, QFont.Bold))
        info_layout.addWidget(self.lbl_edit_signal, 0, 0, 1, 2)
        
        info_layout.addWidget(QLabel("消息:"), 1, 0)
        self.lbl_edit_message = QLabel("--")
        info_layout.addWidget(self.lbl_edit_message, 1, 1)
        
        info_layout.addWidget(QLabel("信号:"), 2, 0)
        self.lbl_edit_signal_name = QLabel("--")
        info_layout.addWidget(self.lbl_edit_signal_name, 2, 1)
        
        info_layout.addWidget(QLabel("单位:"), 3, 0)
        self.lbl_edit_unit = QLabel("--")
        info_layout.addWidget(self.lbl_edit_unit, 3, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 参数编辑
        edit_group = QGroupBox("⚙️ 参数设置")
        edit_layout = QFormLayout()
        
        # 显示名称
        self.edit_display_name = QLineEdit()
        edit_layout.addRow("显示名称:", self.edit_display_name)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        self.edit_color = QLineEdit("#FF6B6B")
        self.edit_color.setMaximumWidth(100)
        color_layout.addWidget(self.edit_color)
        
        btn_color_picker = QPushButton("🎨 选择颜色")
        btn_color_picker.clicked.connect(self.pick_color)
        color_layout.addWidget(btn_color_picker)
        color_layout.addStretch()
        edit_layout.addRow("显示颜色:", color_layout)
        
        # 自定义范围
        range_layout = QHBoxLayout()
        self.edit_min = QDoubleSpinBox()
        self.edit_min.setRange(-999999, 999999)
        self.edit_min.setDecimals(3)
        self.edit_min.setSpecialValueText("自动")
        range_layout.addWidget(self.edit_min)
        
        range_layout.addWidget(QLabel(" 到 "))
        
        self.edit_max = QDoubleSpinBox()
        self.edit_max.setRange(-999999, 999999)
        self.edit_max.setDecimals(3)
        self.edit_max.setSpecialValueText("自动")
        range_layout.addWidget(self.edit_max)
        edit_layout.addRow("自定义范围:", range_layout)
        
        # 自定义缩放
        scale_layout = QHBoxLayout()
        self.edit_scale = QDoubleSpinBox()
        self.edit_scale.setRange(0.0001, 10000)
        self.edit_scale.setDecimals(6)
        self.edit_scale.setValue(1.0)
        self.edit_scale.setSpecialValueText("原始")
        scale_layout.addWidget(self.edit_scale)
        
        scale_layout.addWidget(QLabel(" 偏移: "))
        
        self.edit_offset = QDoubleSpinBox()
        self.edit_offset.setRange(-999999, 999999)
        self.edit_offset.setDecimals(3)
        self.edit_offset.setSpecialValueText("原始")
        scale_layout.addWidget(self.edit_offset)
        edit_layout.addRow("自定义缩放/偏移:", scale_layout)
        
        # 记录设置
        self.cb_recording = QCheckBox("启用记录")
        self.cb_recording.setChecked(True)
        edit_layout.addRow("记录设置:", self.cb_recording)
        
        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)
        
        # 预览
        preview_group = QGroupBox("👁️ 预览")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        edit_group.setLayout(preview_layout)
        layout.addWidget(edit_group)
        
        # 保存按钮
        btn_save_edit = QPushButton("💾 保存修改")
        btn_save_edit.clicked.connect(self.save_edit)
        layout.addWidget(btn_save_edit)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_config_tab(self):
        """创建配置管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 导入导出
        io_group = QGroupBox("📁 配置导入导出")
        io_layout = QVBoxLayout()
        
        # 批量操作
        batch_layout = QHBoxLayout()
        
        btn_export = QPushButton("📤 导出当前配置")
        btn_export.clicked.connect(self.export_configuration)
        batch_layout.addWidget(btn_export)
        
        btn_import = QPushButton("📥 导入配置")
        btn_import.clicked.connect(self.import_configuration)
        batch_layout.addWidget(btn_import)
        
        btn_template = QPushButton("📄 生成模板")
        btn_template.clicked.connect(self.generate_template)
        batch_layout.addWidget(btn_template)
        
        io_layout.addLayout(batch_layout)
        
        # 文件信息
        file_info = QGroupBox("文件信息")
        file_layout = QFormLayout()
        
        self.lbl_file_status = QLabel("未选择文件")
        file_layout.addRow("状态:", self.lbl_file_status)
        
        self.lbl_file_signals = QLabel("0 个信号")
        file_layout.addRow("信号数量:", self.lbl_file_signals)
        
        file_info.setLayout(file_layout)
        io_layout.addWidget(file_info)
        
        io_group.setLayout(io_layout)
        layout.addWidget(io_group)
        
        # 预设管理
        preset_group = QGroupBox("📋 预设管理")
        preset_layout = QVBoxLayout()
        
        preset_combo_layout = QHBoxLayout()
        preset_combo_layout.addWidget(QLabel("选择预设:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["常用发动机信号", "常用车速信号", "电池监控信号", "自定义预设"])
        preset_combo_layout.addWidget(self.preset_combo)
        
        btn_load_preset = QPushButton("加载预设")
        btn_load_preset.clicked.connect(self.load_preset)
        preset_combo_layout.addWidget(btn_load_preset)
        
        preset_layout.addLayout(preset_combo_layout)
        
        # 预设描述
        self.preset_desc = QTextEdit()
        self.preset_desc.setMaximumHeight(80)
        self.preset_desc.setReadOnly(True)
        self.preset_desc.setText("选择预设以查看描述...")
        preset_layout.addWidget(self.preset_desc)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # 配置设置
        settings_group = QGroupBox("⚙️ 配置设置")
        settings_layout = QFormLayout()
        
        self.cb_auto_color = QCheckBox("自动分配颜色")
        self.cb_auto_color.setChecked(True)
        settings_layout.addRow("颜色设置:", self.cb_auto_color)
        
        self.cb_auto_range = QCheckBox("自动检测范围")
        self.cb_auto_range.setChecked(True)
        settings_layout.addRow("范围检测:", self.cb_auto_range)
        
        self.spin_refresh_rate = QSpinBox()
        self.spin_refresh_rate.setRange(1, 1000)
        self.spin_refresh_rate.setValue(100)
        self.spin_refresh_rate.setSuffix(" Hz")
        settings_layout.addRow("刷新频率:", self.spin_refresh_rate)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_status_bar(self):
        """创建状态栏"""
        status = QHBoxLayout()
        
        self.lbl_total = QLabel("📊 总信号: 0")
        status.addWidget(self.lbl_total)
        
        self.lbl_selected = QLabel("⭐ 已选: 0/20")
        status.addWidget(self.lbl_selected)
        
        self.lbl_memory = QLabel("💾 内存: --")
        status.addWidget(self.lbl_memory)
        
        status.addStretch()
        
        self.lbl_status = QLabel("✅ 就绪")
        status.addWidget(self.lbl_status)
        
        return status
    
    def create_button_bar(self):
        """创建按钮栏"""
        buttons = QHBoxLayout()
        
        buttons.addStretch()
        
        self.btn_apply = QPushButton("✅ 应用")
        self.btn_apply.clicked.connect(self.apply_changes)
        self.btn_apply.setEnabled(False)
        buttons.addWidget(self.btn_apply)
        
        self.btn_ok = QPushButton("💾 保存并关闭")
        self.btn_ok.clicked.connect(self.accept)
        buttons.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("❌ 取消")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        
        return buttons
    
    # 以下为业务逻辑方法（需要你根据原有代码补充完整）
    # filter_signals, load_dbc_signals, add_signal_item, remove_row等
    # ...