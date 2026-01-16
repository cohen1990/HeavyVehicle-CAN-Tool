# advanced_signal_dialog.py
# 将第2-12行的 PyQt6 改为 PyQt5
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QRadioButton,
    QWidget, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class AdvancedSignalDialog(QDialog):
    def __init__(self, parent=None, dbc_manager=None):
        super().__init__(parent)
        self.dbc_manager = dbc_manager
        self.selected_signal = None
        self.selected_config_row = -1
        self.max_signals = 20
        self.signal_configs = []
        
        # 设置窗口属性
        self.setWindowTitle("高级信号配置")
        self.setGeometry(100, 100, 1400, 700)
        
        # 初始化UI
        self.init_ui()
        
        # 加载数据
        self.load_signals()
        self.update_config_table()
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        
        # 1. 搜索区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索信号名称或PGN...")
        self.search_input.textChanged.connect(self.filter_signals)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        main_layout.addLayout(search_layout)
        
        # 2. 主体内容区域
        content_layout = QHBoxLayout()
        
        # 左侧：可用信号
        left_panel = QGroupBox("可用信号")
        left_layout = QVBoxLayout()
        
        # 信号列表表格
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(9)
        self.signal_table.setHorizontalHeaderLabels([
            "", "信号名称", "PGN", "源地址", "起始位", 
            "长度", "系数", "偏移", "单位"
        ])
        self.signal_table.horizontalHeader().setStretchLastSection(True)
        self.signal_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.signal_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.signal_table.itemSelectionChanged.connect(self.on_signal_selected)
        
        left_layout.addWidget(self.signal_table)
        left_panel.setLayout(left_layout)
        
        # 中间：操作按钮
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_layout.addStretch()
        
        self.btn_add = QPushButton("添加 →")
        self.btn_add.setFixedSize(100, 40)
        self.btn_add.clicked.connect(self.add_signal_to_config)
        self.btn_add.setToolTip("将选中的信号添加到选中的配置行")
        
        center_layout.addWidget(self.btn_add)
        center_layout.addStretch()
        center_panel.setLayout(center_layout)
        
        # 右侧：信号配置
        right_panel = QGroupBox("信号配置")
        right_layout = QVBoxLayout()
        
        # 配置操作按钮
        config_buttons_layout = QHBoxLayout()
        self.btn_clear_all = QPushButton("清空全部")
        self.btn_clear_all.clicked.connect(self.clear_all_configs)
        config_buttons_layout.addWidget(self.btn_clear_all)
        config_buttons_layout.addStretch()
        
        right_layout.addLayout(config_buttons_layout)
        
        # 配置表格
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(10)
        self.config_table.setHorizontalHeaderLabels([
            "序号", "信号名称", "PGN", "源地址", "起始位", 
            "长度", "系数", "偏移", "单位", "操作"
        ])
        self.config_table.horizontalHeader().setStretchLastSection(True)
        self.config_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.config_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.config_table.itemSelectionChanged.connect(self.on_config_selected)
        
        right_layout.addWidget(self.config_table)
        right_panel.setLayout(right_layout)
        
        # 添加到主布局
        content_layout.addWidget(left_panel, 45)  # 45%宽度
        content_layout.addWidget(center_panel, 10)  # 10%宽度
        content_layout.addWidget(right_panel, 45)  # 45%宽度
        main_layout.addLayout(content_layout, 1)
        
        # 3. 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_save = QPushButton("保存配置")
        self.btn_save.clicked.connect(self.save_configuration)
        self.btn_save.setEnabled(False)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(button_layout)
    
    def load_signals(self):
        """加载信号到表格"""
        signals = self.get_all_signals()
        self.signal_table.setRowCount(len(signals))
        
        for row, signal in enumerate(signals):
            # 添加单选按钮
            radio_btn = QRadioButton()
            radio_widget = QWidget()
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.addWidget(radio_btn)
            radio_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            self.signal_table.setCellWidget(row, 0, radio_widget)
            
            # 连接单选按钮事件
            radio_btn.toggled.connect(lambda checked, r=row: self.on_signal_radio_toggled(r, checked))
            
            # 填充信号数据
            for col, key in enumerate(['name', 'pgn', 'source_address', 'start_bit', 
                                       'length', 'factor', 'offset', 'unit'], start=1):
                value = str(signal.get(key, ''))
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 设置为只读
                self.signal_table.setItem(row, col, item)
        
        # 调整列宽
        self.signal_table.resizeColumnsToContents()
    
    def update_config_table(self):
        """更新配置表格显示"""
        # 确保显示指定行数
        row_count = max(len(self.signal_configs), self.max_signals)
        self.config_table.setRowCount(row_count)
        
        for row in range(row_count):
            # 序号列
            seq_item = QTableWidgetItem(str(row + 1))
            seq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.config_table.setItem(row, 0, seq_item)
            
            if row < len(self.signal_configs):
                config = self.signal_configs[row]
                # 填充配置数据
                for col, key in enumerate(['name', 'pgn', 'source_address', 'start_bit', 
                                           'length', 'factor', 'offset', 'unit'], start=1):
                    value = str(config.get(key, ''))
                    item = QTableWidgetItem(value)
                    self.config_table.setItem(row, col, item)
            else:
                # 显示空行占位符
                for col in range(1, 9):
                    item = QTableWidgetItem("")
                    self.config_table.setItem(row, col, item)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_config_row(r))
            self.config_table.setCellWidget(row, 9, delete_btn)
        
        # 调整列宽
        self.config_table.resizeColumnsToContents()
    
    def get_all_signals(self):
        """获取所有CAN信号"""
        signals = []
        
        if self.dbc_manager and hasattr(self.dbc_manager, 'db'):
            db = self.dbc_manager.db
            
            # 遍历所有消息
            for message in db.messages:
                message_id = message.frame_id
                
                # 遍历消息中的所有信号
                for signal in message.signals:
                    signal_info = {
                        'name': signal.name,
                        'pgn': f"{message_id:#x}",  # 十六进制显示
                        'source_address': '',
                        'start_bit': signal.start_bit,
                        'length': signal.size,
                        'factor': signal.scale,
                        'offset': signal.offset,
                        'unit': signal.unit,
                        'comment': signal.comment,
                        'message_name': message.name,
                        'message_id': message_id,
                        'byte_order': signal.byte_order,
                        'is_signed': signal.is_signed,
                        'min': signal.minimum,
                        'max': signal.maximum
                    }
                    signals.append(signal_info)
        
        return signals
    
    def get_signal_data_from_row(self, row):
        """从表格行获取信号数据"""
        if row < 0 or row >= self.signal_table.rowCount():
            return None
        
        signal_data = {
            'name': self.signal_table.item(row, 1).text() if self.signal_table.item(row, 1) else '',
            'pgn': self.signal_table.item(row, 2).text() if self.signal_table.item(row, 2) else '',
            'source_address': self.signal_table.item(row, 3).text() if self.signal_table.item(row, 3) else '',
            'start_bit': self.signal_table.item(row, 4).text() if self.signal_table.item(row, 4) else '',
            'length': self.signal_table.item(row, 5).text() if self.signal_table.item(row, 5) else '',
            'factor': self.signal_table.item(row, 6).text() if self.signal_table.item(row, 6) else '1.0',
            'offset': self.signal_table.item(row, 7).text() if self.signal_table.item(row, 7) else '0.0',
            'unit': self.signal_table.item(row, 8).text() if self.signal_table.item(row, 8) else '',
        }
        
        return signal_data
    
    def on_signal_radio_toggled(self, row, checked):
        """处理单选按钮选择"""
        if checked:
            self.selected_signal = self.get_signal_data_from_row(row)
            print(f"选中信号: {self.selected_signal.get('name', '未知')}")
            
            # 取消其他行的选择
            for r in range(self.signal_table.rowCount()):
                if r != row:
                    radio_widget = self.signal_table.cellWidget(r, 0)
                    if radio_widget:
                        radio_btn = radio_widget.findChild(QRadioButton)
                        if radio_btn:
                            radio_btn.setChecked(False)
    
    def on_signal_selected(self):
        """处理表格行选择"""
        selected_rows = self.signal_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            radio_widget = self.signal_table.cellWidget(row, 0)
            if radio_widget:
                radio_btn = radio_widget.findChild(QRadioButton)
                if radio_btn:
                    radio_btn.setChecked(True)
    
    def on_config_selected(self):
        """处理配置表选择"""
        selected_rows = self.config_table.selectionModel().selectedRows()
        if selected_rows:
            self.selected_config_row = selected_rows[0].row()
            print(f"选中配置行: {self.selected_config_row}")
            self.btn_add.setEnabled(self.selected_signal is not None)
    
    def filter_signals(self):
        """过滤信号列表"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.signal_table.rowCount()):
            should_show = False
            
            if not search_text:
                should_show = True
            else:
                # 检查信号名称
                name_item = self.signal_table.item(row, 1)
                if name_item and search_text in name_item.text().lower():
                    should_show = True
                
                # 检查PGN
                pgn_item = self.signal_table.item(row, 2)
                if not should_show and pgn_item and search_text in pgn_item.text().lower():
                    should_show = True
            
            self.signal_table.setRowHidden(row, not should_show)
    
    def add_signal_to_config(self):
        """添加信号到配置"""
        if self.selected_signal is None:
            QMessageBox.warning(self, "警告", "请先在左侧选择一个信号")
            return
        
        if self.selected_config_row < 0:
            QMessageBox.warning(self, "警告", "请先在右侧选择一个配置行")
            return
        
        # 确保配置列表足够长
        while len(self.signal_configs) <= self.selected_config_row:
            self.signal_configs.append(self.create_empty_config())
        
        # 复制信号数据
        config = self.selected_signal.copy()
        self.signal_configs[self.selected_config_row] = config
        
        # 更新表格
        self.update_config_table()
        self.btn_save.setEnabled(True)
        
        QMessageBox.information(self, "成功", 
            f"已将信号 '{config['name']}' 添加到配置行 {self.selected_config_row + 1}")
    
    def create_empty_config(self):
        """创建空配置"""
        return {
            'name': '',
            'pgn': '',
            'source_address': '',
            'start_bit': '',
            'length': '',
            'factor': 1.0,
            'offset': 0.0,
            'unit': '',
            'comment': ''
        }
    
    def clear_all_configs(self):
        """清除所有配置"""
        reply = QMessageBox.question(
            self, 
            "确认", 
            "确定要清除所有配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.signal_configs = []
            self.selected_signal = None
            self.selected_config_row = -1
            self.update_config_table()
            self.btn_save.setEnabled(False)
            print("已清除所有配置")
    
    def delete_config_row(self, row):
        """删除指定行的配置"""
        if 0 <= row < len(self.signal_configs):
            self.signal_configs.pop(row)
            self.update_config_table()
            print(f"已删除配置行 {row}")
            
            # 如果没有配置了，禁用保存按钮
            if not any(config.get('name') for config in self.signal_configs):
                self.btn_save.setEnabled(False)
        elif row < len(self.config_table.rowCount()):
            # 如果是空行，只需要更新显示
            self.update_config_table()
    
    def save_configuration(self):
        """保存配置"""
        if not self.signal_configs:
            QMessageBox.warning(self, "警告", "没有需要保存的配置")
            return
        
        # 过滤空配置
        valid_configs = []
        for config in self.signal_configs:
            if config['name']:  # 只要有信号名称就认为是有效配置
                valid_configs.append(config)
        
        if not valid_configs:
            QMessageBox.warning(self, "警告", "没有有效的配置需要保存")
            return
        
        # 这里实现保存逻辑，例如保存到文件或数据库
        print(f"保存了 {len(valid_configs)} 个信号配置")
        
        # 保存成功后提示
        QMessageBox.information(self, "成功", f"已保存 {len(valid_configs)} 个信号配置")
        self.accept()


if __name__ == "__main__":
    # 测试代码
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = AdvancedSignalDialog()
    dialog.show()
    sys.exit(app.exec())