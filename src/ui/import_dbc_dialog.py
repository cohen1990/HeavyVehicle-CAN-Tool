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
    
    def __init__(self, filepaths, dbc_manager):
        super().__init__()
        self.filepaths = filepaths
        self.dbc_manager = dbc_manager
        print(f"DBCImportWorker: 接收到dbc_manager: {self.dbc_manager}")
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
                success = self.dbc_manager.load_dbc_file_batch(filepath, batch_size=500)
                # === 关键：加载后立即进行“全面体检” ===
                print(f"\n=== 对 dbc_manager 进行全面检查 ===")
                print(f"1. dbc_manager 对象: {self.dbc_manager}")
                print(f"2. dbc_manager 类型: {type(self.dbc_manager)}")                
                # 检查所有属性
                print(f"3. dbc_manager 的所有属性:")
                for attr_name in dir(self.dbc_manager):
                    # 过滤掉私有方法，只查看重要属性
                    if not attr_name.startswith('_'):
                        try:
                            attr_value = getattr(self.dbc_manager, attr_name)
                            # 特别关注可能存储数据的属性
                            if attr_name in ['db', 'database', '_db', '_database', 'messages', 'signals']:
                                print(f"   !! {attr_name}: {attr_value} (类型: {type(attr_value)})")
                        except:
                            pass
                
                # 专门检查 db 属性
                if hasattr(self.dbc_manager, 'db'):
                    db = self.dbc_manager.db
                    print(f"4. db 属性详情:")
                    print(f"   值: {db}")
                    print(f"   类型: {type(db)}")
                    if db:
                        print(f"   db 的所有属性: {[a for a in dir(db) if not a.startswith('_')][:10]}...")
                else:
                    print(f"4. dbc_manager 没有 'db' 属性")
                    
                # 尝试直接调用 get_all_messages 看返回什么
                print(f"5. 测试 get_all_messages() 方法:")
                try:
                    all_msgs = self.dbc_manager.get_all_messages()
                    print(f"   调用成功，返回类型: {type(all_msgs)}， 长度: {len(all_msgs) if hasattr(all_msgs, '__len__') else '无长度属性'}")
                    if all_msgs and len(all_msgs) > 0:
                        print(f"   第一个元素: {all_msgs[0]}， 类型: {type(all_msgs[0])}")
                except Exception as e:
                    print(f"   调用失败: {e}")
                print(f"=== 检查结束 ===\n")
                # ==========================================

                if success:
                    success_count += 1
                    msg_count = len(self.dbc_manager.get_all_messages())
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
        total_messages = len(self.dbc_manager.get_all_messages())
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
        if parent and hasattr(parent, 'dbc_manager') and parent.dbc_manager is not None:
            self.dbc_manager = parent.dbc_manager
            print("ImportDBCDialog: 复用父窗口的dbc_manager")
        else:
            from src.dbc.dbc_manager import DBCManager
            self.dbc_manager = DBCManager()
            print("ImportDBCDialog: 创建了新的dbc_manager")
        # ---------------------------------
        
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
        self.import_worker = DBCImportWorker(filepaths, self.dbc_manager)
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
            # --- 关键新增：导入成功后，更新父窗口的引用 ---
            self.update_parent_dbc_manager()
            self.dbc_imported.emit()  # 发送导入完成信号
            QMessageBox.information(self, "完成", "DBC文件导入成功！")
        else:
            QMessageBox.warning(self, "警告", "导入完成，但有文件失败，请检查日志")

    def update_parent_dbc_manager(self):
        """将本对话框的dbc_manager更新到父窗口"""
        parent = self.parent()
        if parent and hasattr(parent, 'dbc_manager'):
            parent.dbc_manager = self.dbc_manager
            print(f"ImportDBCDialog: 已将dbc_manager同步到父窗口")
            
            # 统计消息和信号
            message_count = 0
            signal_count = 0
            
            if hasattr(self.dbc_manager, 'messages'):
                messages_dict = self.dbc_manager.messages
                message_count = len(messages_dict)
                
                # 统计信号
                for msg_id, message in messages_dict.items():
                    if hasattr(message, 'signals'):
                        msg_signals = message.signals
                        # 如果是字典
                        if isinstance(msg_signals, dict):
                            signal_count += len(msg_signals)
                        # 如果是列表或其他可迭代对象
                        elif hasattr(msg_signals, '__iter__'):
                            signal_count += len(list(msg_signals))
            
            print(f"  统计结果: {message_count} 个消息, {signal_count} 个信号")
            
            # 如果信号为0但消息不为0，需要进一步检查
            if message_count > 0 and signal_count == 0:
                print(f"  警告: 找到 {message_count} 个消息，但信号数为0。检查信号提取方式...")
                # 采样检查第一个消息
                if messages_dict:
                    first_msg = next(iter(messages_dict.values()))
                    print(f"  第一个消息: {getattr(first_msg, 'name', 'N/A')}")
                    if hasattr(first_msg, 'signals'):
                        signals = first_msg.signals
                        print(f"    signals属性类型: {type(signals)}")
                        print(f"    signals内容: {signals}")
        else:
            print("ImportDBCDialog: 父窗口不存在或没有dbc_manager属性")

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