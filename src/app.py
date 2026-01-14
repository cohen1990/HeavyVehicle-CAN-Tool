#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用主类 - 修复版
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class CANMonitorApp:
    """应用主类"""
    
    def __init__(self, argv):
        self.argv = argv
        self.app = None
        self.main_window = None
        
    def setup_application(self):
        """设置应用"""
        try:
            # 创建QApplication
            self.app = QApplication(self.argv)
            self.app.setApplicationName("重型车CAN监控工具")
            self.app.setApplicationVersion("1.0.0")
            
            # 设置字体（支持中文）
            font = QFont("Microsoft YaHei", 10)
            self.app.setFont(font)
            
            # 设置样式
            self.app.setStyle("Fusion")
            
            # 导入主窗口
            from src.ui.main_window import MainWindow
            self.main_window = MainWindow()
            
            return True
            
        except Exception as e:
            print(f"应用设置失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self):
        """运行应用"""
        try:
            if not self.setup_application():
                return 1
            
            # 显示主窗口
            self.main_window.show()
            
            # 运行应用 - 确保应用对象被引用
            result = self.app.exec_()
            
            # 清理资源
            if hasattr(self.main_window, 'cleanup'):
                self.main_window.cleanup()
                
            return result
            
        except Exception as e:
            print(f"应用运行错误: {e}")
            import traceback
            traceback.print_exc()
            return 1