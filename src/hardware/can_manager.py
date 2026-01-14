#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAN设备管理器
支持NI USB-8502和Kvaser设备
"""

import threading
import queue
import time
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("CANMonitor")

class DeviceType(Enum):
    """设备类型"""
    NI_8502 = "ni_8502"
    Kvaser = "kvaser"
    VIRTUAL = "virtual"  # 虚拟设备，用于测试

class CANMessage:
    """CAN消息类"""
    def __init__(self, can_id: int, data: bytes, timestamp: float = None, 
                 port: str = None, is_extended: bool = False):
        self.can_id = can_id
        self.data = data
        self.timestamp = timestamp or time.time()
        self.port = port
        self.is_extended = is_extended
        self.dlc = len(data)
    
    def __str__(self):
        return f"CAN ID: 0x{self.can_id:03X}, Data: {self.data.hex()}, Port: {self.port}"

class CANManager:
    """CAN设备管理器"""
    
    def __init__(self):
        self.devices = {}  # 设备字典 {port: device_object}
        self.message_queue = queue.Queue(maxsize=1000)
        self.running = False
        self.receive_thread = None
        self.callbacks = []  # 消息回调函数列表
        self.lock = threading.Lock()
        
        # 硬件接口（延迟导入，避免未安装时出错）
        self.can_interface = None
        self.try_import_can()
    
    def try_import_can(self):
        """尝试导入python-can"""
        try:
            import can
            self.can_interface = can
            logger.info("python-can库导入成功")
        except ImportError as e:
            logger.error(f"无法导入python-can库: {e}")
            self.can_interface = None
    
    def list_available_devices(self) -> Dict[DeviceType, List[str]]:
        """列出可用设备"""
        available = {
            DeviceType.NI_8502: [],
            DeviceType.Kvaser: [],
            DeviceType.VIRTUAL: ["virtual0", "virtual1"]
        }
        
        # 虚拟设备始终可用
        available[DeviceType.VIRTUAL] = ["virtual0", "virtual1"]
        
        if not self.can_interface:
            logger.info("python-can库未导入，仅提供虚拟设备")
            return available
        
        try:
            # 尝试检测NI设备
            try:
                from can.interfaces.ni_can import NiCanBus
                # 这里可以添加实际的NI设备检测
                # 暂时模拟检测到设备
                logger.info("NI设备支持可用")
                # 虚拟NI设备用于测试
                available[DeviceType.NI_8502].append("Dev1/CNI0 (模拟)")
                available[DeviceType.NI_8502].append("Dev1/CNI1 (模拟)")
            except ImportError as e:
                logger.warning(f"NI设备支持未安装: {e}")
            
            # 尝试检测Kvaser设备
            try:
                from can.interfaces.kvaser import KvaserBus
                logger.info("Kvaser设备支持可用")
                # 虚拟Kvaser设备用于测试
                available[DeviceType.Kvaser].extend(["0 (模拟)", "1 (模拟)"])
            except ImportError as e:
                logger.warning(f"Kvaser设备支持未安装: {e}")
                
        except Exception as e:
            logger.error(f"设备检测失败: {e}")
        
        return available
    
    def connect(self, device_type: DeviceType, port: str, baudrate: int = 500000) -> bool:
        """连接设备"""
        if not self.can_interface:
            logger.error("python-can库未安装")
            return False
        
        try:
            if device_type == DeviceType.VIRTUAL:
                # ✅ 修复：先检查是否已连接，避免重复创建
                if port in self.devices:
                    try:
                        self.devices[port]['bus'].shutdown()
                    except:
                        pass
                
                # 虚拟设备连接
                bus = self.can_interface.Bus(
                    interface='virtual',
                    channel=port,
                    receive_own_messages=True
                )
                logger.info(f"连接到虚拟设备: {port}")
                
            elif device_type == DeviceType.NI_8502:
                # NI USB-8502连接
                bus = self.can_interface.Bus(
                    interface='ni',
                    channel=port,
                    bitrate=baudrate,
                    fd=False  # USB-8502不支持CAN FD
                )
                logger.info(f"连接到NI设备: {port}, 波特率: {baudrate}")
                
            elif device_type == DeviceType.Kvaser:
                # Kvaser设备连接
                bus = self.can_interface.Bus(
                    interface='kvaser',
                    channel=int(port),
                    bitrate=baudrate
                )
                logger.info(f"连接到Kvaser设备: 通道{port}, 波特率: {baudrate}")
                
            else:
                logger.error(f"不支持的设备类型: {device_type}")
                return False
            
            with self.lock:
                self.devices[port] = {
                    'bus': bus,
                    'type': device_type,
                    'baudrate': baudrate,
                    'connected': True
                }
            
            return True
            
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            return False
    
    def disconnect(self, port: str) -> bool:
        """断开设备连接"""
        with self.lock:
            if port in self.devices:
                try:
                    self.devices[port]['bus'].shutdown()
                    del self.devices[port]
                    logger.info(f"设备断开: {port}")
                    return True
                except Exception as e:
                    logger.error(f"断开设备失败: {e}")
                    return False
        return False
    
    def send_message(self, port: str, can_id: int, data: bytes, 
                     is_extended: bool = False) -> bool:
        """发送CAN消息"""
        if port not in self.devices:
            logger.error(f"设备未连接: {port}")
            return False
        
        try:
            bus = self.devices[port]['bus']
            message = self.can_interface.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=is_extended
            )
            bus.send(message)
            logger.debug(f"发送消息: 端口={port}, ID=0x{can_id:03X}, 数据={data.hex()}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def start_receiving(self):
        """开始接收消息"""
        if self.running:
            return
        
        self.running = True
        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True
        )
        self.receive_thread.start()
        logger.info("开始接收CAN消息")
    
    def stop_receiving(self):
        """停止接收消息"""
        self.running = False
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        logger.info("停止接收CAN消息")
    
    def _receive_loop(self):
        """接收消息循环"""
        while self.running:
            try:
                # 遍历所有连接的设备
                with self.lock:
                    devices_copy = self.devices.copy()
                
                for port, device_info in devices_copy.items():
                    if not device_info['connected']:
                        continue
                    
                    try:
                        bus = device_info['bus']
                        # 非阻塞接收
                        message = bus.recv(timeout=0.1)
                        
                        if message:
                            can_msg = CANMessage(
                                can_id=message.arbitration_id,
                                data=message.data,
                                timestamp=message.timestamp,
                                port=port,
                                is_extended=message.is_extended_id
                            )
                            
                            # 放入队列
                            try:
                                self.message_queue.put_nowait(can_msg)
                            except queue.Full:
                                logger.warning("消息队列已满，丢弃消息")
                            
                            # 调用回调函数
                            for callback in self.callbacks:
                                try:
                                    callback(can_msg)
                                except Exception as e:
                                    logger.error(f"回调函数执行失败: {e}")
                    
                    except Exception as e:
                        logger.error(f"接收消息失败: {e}")
                        continue
                
                time.sleep(0.001)  # 避免CPU占用过高
                
            except Exception as e:
                logger.error(f"接收循环异常: {e}")
                time.sleep(0.1)
    
    def get_message(self, timeout: float = 1.0) -> Optional[CANMessage]:
        """从队列获取消息"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def register_callback(self, callback):
        """注册消息回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """取消注册消息回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_connected_devices(self) -> List[str]:
        """获取已连接的设备列表"""
        with self.lock:
            return list(self.devices.keys())
    
    def get_device_info(self, port: str) -> Optional[Dict[str, Any]]:
        """获取设备信息"""
        with self.lock:
            if port in self.devices:
                return self.devices[port].copy()
        return None
    
    def cleanup(self):
        """清理资源"""
        self.stop_receiving()
        with self.lock:
            for port, device_info in self.devices.items():
                try:
                    device_info['bus'].shutdown()
                except:
                    pass
            self.devices.clear()
        logger.info("CAN管理器清理完成")
class MultiCANManager:
    """多CAN设备管理器"""
    
    def __init__(self):
        self.devices = {}  # {device_id: device_info}
        self.connections = {}  # {interface_type: [device_ids]}
        self.message_queue = queue.Queue(maxsize=5000)
        self.running = False
        self.receive_threads = []
        
    def connect_device(self, device_type, port, baudrate, name=None):
        """连接单个设备"""
        device_id = f"{device_type.value}_{port}"
        
        if device_id in self.devices:
            return device_id  # 已连接
        
        # 连接到设备
        success = can_manager.connect(device_type, port, baudrate)
        if success:
            device_info = {
                'id': device_id,
                'type': device_type,
                'port': port,
                'baudrate': baudrate,
                'name': name or f"{device_type.value} {port}",
                'connected': True,
                'message_count': 0,
                'error_count': 0
            }
            
            self.devices[device_id] = device_info
            
            # 添加到接口分组
            if device_type.value not in self.connections:
                self.connections[device_type.value] = []
            self.connections[device_type.value].append(device_id)
            
            logger.info(f"设备连接成功: {device_info['name']}")
            return device_id
        
        return None
    
    def disconnect_device(self, device_id):
        """断开设备"""
        if device_id in self.devices:
            device_info = self.devices[device_id]
            can_manager.disconnect(device_info['port'])
            del self.devices[device_id]
            logger.info(f"设备断开: {device_info['name']}")
            return True
        return False
    
    def start_all_devices(self):
        """启动所有设备"""
        if self.running:
            return
        
        self.running = True
        
        # 为每个设备创建接收线程
        for device_id, device_info in self.devices.items():
            if device_info['connected']:
                thread = threading.Thread(
                    target=self._device_receive_loop,
                    args=(device_id,),
                    daemon=True
                )
                thread.start()
                self.receive_threads.append(thread)
        
        logger.info(f"启动 {len(self.receive_threads)} 个设备接收线程")
    
    def _device_receive_loop(self, device_id):
        """设备接收循环"""
        device_info = self.devices.get(device_id)
        if not device_info:
            return
        
        while self.running and device_info['connected']:
            try:
                # 接收消息
                msg = can_manager.get_message(timeout=0.1)
                if msg:
                    # 标记来源设备
                    msg.device_id = device_id
                    msg.device_name = device_info['name']
                    
                    # 放入队列
                    self.message_queue.put(msg)
                    
                    # 更新统计
                    device_info['message_count'] += 1
                    
            except Exception as e:
                device_info['error_count'] += 1
                if not self.running:
                    break
    
    def get_combined_message(self):
        """获取组合消息（来自所有设备）"""
        try:
            return self.message_queue.get(timeout=0.1)
        except queue.Empty:
            return None
    
    def get_device_stats(self):
        """获取设备统计"""
        stats = []
        for device_id, info in self.devices.items():
            stats.append({
                'id': device_id,
                'name': info['name'],
                'type': info['type'].value,
                'port': info['port'],
                'baudrate': info['baudrate'],
                'message_count': info['message_count'],
                'error_count': info['error_count'],
                'connected': info['connected']
            })
        return stats



# 全局CAN管理器实例
can_manager = CANManager()