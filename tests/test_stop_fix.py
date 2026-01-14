# test_stop_fix.py
import sys
import time
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def test_stop():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    print("=== 测试停止功能 ===")
    
    # 模拟连接
    print("1. 模拟连接虚拟设备...")
    # 这里需要模拟连接过程
    
    print("2. 5秒后开始监控...")
    time.sleep(5)
    
    print("3. 点击开始监控...")
    window.on_start_clicked()
    
    print(f"   按钮文字: {window.btn_start.text()}")
    print("   等待5秒...")
    time.sleep(5)
    
    print("4. 点击停止监控...")
    window.on_start_clicked()
    
    print(f"   按钮文字: {window.btn_start.text()}")
    print("   观察10秒，信号是否停止刷新...")
    time.sleep(10)
    
    print("=== 测试完成 ===")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_stop()