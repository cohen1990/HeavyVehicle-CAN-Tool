#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重型车CAN监控工具 - 主程序入口
"""

import sys
import os
import traceback

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    """主函数"""
    try:
        # 导入应用主类
        from src.app import CANMonitorApp
        
        # 创建应用
        app = CANMonitorApp(sys.argv)
        
        # 运行应用
        return app.run()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        traceback.print_exc()
        input("按回车键退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main())