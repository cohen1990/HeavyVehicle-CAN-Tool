#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBC导入对话框 - 简化修复版
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QGroupBox, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from src.dbc.dbc_manager import dbc_manager

class DBCImportWorker(QThread):
    """DBC导入工作线程 - 简化版"""
    
    progress = pyqtSignal(int, str)  # 进度百分比, 消息
    finished = pyqtSignal(bool, str)  # 是否成功, 总结消息
    
    def __init__(self, filepaths):
        super().__init__()
        self.filepaths = filepaths
    
    def run(self):
        """执行导入 - 使用分批加载"""
        total_files = len(self.filepaths)
        success_count = 0
        
        for i, filepath in enumerate(self.filepaths):
            try:
                progress = int((i / total_files) * 100)
                filename = os.path.basename(filepath)
                self.progress.emit(progress, f"正在导入: {filename}")
                
                # 使用分批加载（最佳方案）
                success = dbc_manager.load_dbc_file_batch(filepath, batch_size=500)
                
                if success:
                    success_count += 1
                    msg_count = len(dbc_manager.get_all_messages())
                    self.progress.emit(
                        int(((i + 1) / total_files) * 100),
                        f"✓ {filename}: {msg_count} 个消息"
                    )
                else:
                    self.progress.emit(
                        int(((i + 1) / total_files) * 100),
                        f"✗ {filename}: 导入失败"
                    )
                    
            except Exception as e:
                self.progress.emit(
                    int(((i + 1) / total_files) * 100),
                    f"✗ {os.path.basename(filepath)}: {str(e)}"
                )
        
        # 构建总结消息
        total_messages = len(dbc_manager.get_all_messages())
        summary = f"导入完成: {success_count}/{total_files} 个文件成功\n"
        summary += f"总计 {total_messages} 个消息"
        
        self.finished.emit(success_count > 0, summary)

class ImportDBCDialog(QDialog):
    """DBC导入对话框 - 简化版"""
    
    dbc_imported = pyqtSignal()  # DBC导入完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入DBC文件")
        self.setMinimumSize(500, 400)
        
        self.import_worker = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面 - 简化版"""
        layout = QVBoxLayout()
        
        # 1. 标题
        title_label = QLabel("导入DBC文件")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 2. 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100)
        file_layout.addWidget(QLabel("已选择的文件:"))
        file_layout.addWidget(self.file_list)
        
        # 文件操作按钮
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加文件")
        self.btn_add.clicked.connect(self.add_files)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("移除选中")
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_remove)
        
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.btn_clear)
        
        file_layout.addLayout(btn_layout)
        
        # 加载选项
        self.skip_checkbox = QCheckBox("使用高效加载模式（推荐）")
        self.skip_checkbox.setChecked(True)
        self.skip_checkbox.setToolTip("使用分批加载，适合大型J1939 DBC文件")
        file_layout.addWidget(self.skip_checkbox)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 3. 进度区域
        progress_group = QGroupBox("导入进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 4. 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout()
        
        self.lbl_file_count = QLabel("文件数: 0")
        stats_layout.addWidget(self.lbl_file_count)
        
        self.lbl_msg_count = QLabel("消息数: 0")
        stats_layout.addWidget(self.lbl_msg_count)
        
        self.lbl_sig_count = QLabel("信号数: 0")
        stats_layout.addWidget(self.lbl_sig_count)
        
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 5. 按钮区域
        button_layout = QHBoxLayout()
        
        self.btn_import = QPushButton("开始导入")
        self.btn_import.clicked.connect(self.start_import)
        self.btn_import.setEnabled(False)
        
        self.btn_cancel = QPushButton("关闭")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_import)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 更新统计信息
        self.update_stats()
    
    def add_files(self):
        """添加文件"""
        file_filter = "DBC文件 (*.dbc);;所有文件 (*.*)"
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择DBC文件", "", file_filter
        )
        
        for filepath in files:
            # 避免重复添加
            existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if filepath not in existing:
                self.file_list.addItem(filepath)
        
        self.update_file_count()
        self.btn_import.setEnabled(self.file_list.count() > 0)
    
    def remove_selected(self):
        """移除选中的文件"""
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self.update_file_count()
        self.btn_import.setEnabled(self.file_list.count() > 0)
    
    def clear_files(self):
        """清空文件列表"""
        self.file_list.clear()
        self.update_file_count()
        self.btn_import.setEnabled(False)
    
    def update_file_count(self):
        """更新文件计数"""
        count = self.file_list.count()
        self.lbl_file_count.setText(f"文件数: {count}")
    
    def update_stats(self):
        """更新统计信息"""
        messages = dbc_manager.get_all_messages()
        signals = dbc_manager.get_all_signals()
        
        self.lbl_msg_count.setText(f"消息数: {len(messages)}")
        self.lbl_sig_count.setText(f"信号数: {len(signals)}")
    
    def start_import(self):
        """开始导入"""
        if self.import_worker and self.import_worker.isRunning():
            QMessageBox.warning(self, "警告", "导入正在进行中，请等待完成")
            return
        
        # 获取文件列表
        filepaths = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not filepaths:
            QMessageBox.warning(self, "警告", "请先选择要导入的文件")
            return
        
        # 创建并启动工作线程
        self.import_worker = DBCImportWorker(filepaths)
        self.import_worker.progress.connect(self.update_progress)
        self.import_worker.finished.connect(self.on_import_finished)
        
        # 禁用按钮
        self.set_buttons_enabled(False)
        
        # 清空日志
        self.log_text.clear()
        self.log_text.append("开始导入DBC文件...")
        
        # 开始导入
        self.import_worker.start()
    
    def update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log_text.append(message)
    
    def on_import_finished(self, success: bool, message: str):
        """导入完成"""
        self.progress_bar.setValue(100)
        self.status_label.setText("导入完成")
        self.log_text.append("\n" + message)
        
        # 启用按钮
        self.set_buttons_enabled(True)
        
        # 更新统计信息
        self.update_stats()
        
        if success:
            self.dbc_imported.emit()  # 发送导入完成信号
            QMessageBox.information(self, "完成", "DBC文件导入成功！")
        else:
            QMessageBox.warning(self, "警告", "导入完成，但有文件失败，请检查日志")
    
    def set_buttons_enabled(self, enabled: bool):
        """设置按钮状态"""
        self.btn_import.setEnabled(enabled)
        self.btn_add.setEnabled(enabled)
        self.btn_remove.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.skip_checkbox.setEnabled(enabled)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.import_worker and self.import_worker.isRunning():
            reply = QMessageBox.question(
                self, '确认',
                '导入正在进行中，确定要取消吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.import_worker.terminate()
                self.import_worker.wait()
            else:
                event.ignore()
                return
        
        event.accept()