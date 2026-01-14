#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模式 - 在没有真实硬件时使用
"""

import random
import time
from threading import Thread

class TestMode:
    """测试模式，模拟CAN消息"""
    
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
        
    def start(self, port="virtual0", rate=10):
        """开始发送测试消息"""
        if self.running:
            print("[TestMode] 已经在运行中")
            return
            
        self.running = True
        self.thread = Thread(target=self._send_messages, args=(port, rate), daemon=True)
        self.thread.start()
        print(f"[TestMode] 线程启动，rate={rate}")
        
    def stop(self):
        """停止发送测试消息"""
        if not self.running:
            print("[TestMode] 已经停止")
            return
            
        print("[TestMode] 开始停止...")
        self.running = False
        
        # 发送停止确认消息
        try:
            from src.hardware.can_manager import CANMessage
            stop_msg = CANMessage(
                can_id=0xFFFFFFFF,
                data=b"STOPPED",
                timestamp=time.time(),
                port="virtual0",
                is_extended=True
            )
            self.callback(stop_msg)
        except:
            pass
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
            if self.thread.is_alive():
                print("[TestMode] 警告：线程未在0.5秒内停止")
            else:
                print("[TestMode] 线程已正常停止")
            self.thread = None
        
        print("[TestMode] 已完全停止")
            
    def _send_messages(self, port, rate):
        """发送测试消息"""
        interval = 1.0 / rate if rate > 0 else 0.1
        
        # 模拟的J1939消息（重型车常用）
        test_messages = [
            {"id": 0x0CF00400, "name": "发动机转速"},
            {"id": 0x18F00400, "name": "车速"},
            {"id": 0x18FEF100, "name": "冷却液温度"},
            {"id": 0x18FEF200, "name": "机油压力"},
        ]
        
        message_index = 0
        
        while self.running:
            try:
                # 选择消息
                msg_info = test_messages[message_index % len(test_messages)]
                
                # 生成模拟数据
                if msg_info["id"] == 0x0CF00400:  # 发动机转速
                    rpm_value = 800 + (message_index * 10) % 2000
                    data = [
                        (rpm_value >> 8) & 0xFF,
                        rpm_value & 0xFF,
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255)
                    ]
                elif msg_info["id"] == 0x18F00400:  # 车速
                    speed_value = (message_index * 2) % 120
                    data = [
                        int(speed_value / 0.5),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255)
                    ]
                else:
                    # 其他信号
                    data = [random.randint(0, 255) for _ in range(8)]
                
                # 创建消息对象
                from src.hardware.can_manager import CANMessage
                can_msg = CANMessage(
                    can_id=msg_info["id"],
                    data=bytes(data),
                    timestamp=time.time(),
                    port=port,
                    is_extended=True
                )
                
                # 调用回调
                self.callback(can_msg)
                
                message_index += 1
                time.sleep(interval)
                
            except Exception as e:
                print(f"[TestMode] 发送消息异常: {e}")
                if not self.running:
                    break
                time.sleep(1.0)
        
        print("[TestMode] 线程退出")