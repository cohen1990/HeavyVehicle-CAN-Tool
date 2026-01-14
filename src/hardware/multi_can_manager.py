#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多CAN设备管理器
支持同时连接多个CAN接口
"""

import threading
import queue
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger("CANMonitor")

@dataclass
class DeviceConfig:
    """设备配置"""
    device_id: str
    name: str
    type: str  # "virtual", "ni_8502", "kvaser"
    port: str
    baudrate: int
    enabled: bool = True
    auto_reconnect: bool = True
    filter_ids: Optional[List[int]] = None

@dataclass
class CANMessageEx:
    """扩展的CAN消息，包含设备信息"""
    can_id: int
    data: bytes
    timestamp: float
    device_id: str
    device_name: str
    port: str
    is_extended: bool = False
    dlc: int = 8
    
    def __post_init__(self):
        if self.dlc == 0:
            self.dlc = len(self.data)

class MultiCANManager:
    """多CAN设备管理器"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceConfig] = {}  # device_id -> config
        self.device_status: Dict[str, Dict[str, Any]] = {}  # device_id -> status
        self.message_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.receive_threads: List[threading.Thread] = []
        self.callbacks = []  # 消息回调函数列表
        self.lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
        # 从现有的can_manager导入
        self.can_interface = None
        self.try_import_can()
        
        # 统计信息
        self.total_messages = 0
        self.start_time = time.time()
    
    def try_import_can(self):
        """尝试导入python-can"""
        try:
            import can
            self.can_interface = can
            logger.info("python-can库导入成功")
        except ImportError as e:
            logger.error(f"无法导入python-can库: {e}")
            self.can_interface = None
    
    def add_device(self, device_type: str, port: str, baudrate: int = 500000, 
                   name: Optional[str] = None) -> Optional[str]:
        """添加设备配置"""
        device_id = f"{device_type}_{port}"
        
        if device_id in self.devices:
            logger.warning(f"设备已存在: {device_id}")
            return device_id
        
        if not name:
            name = f"{device_type} ({port})"
        
        config = DeviceConfig(
            device_id=device_id,
            name=name,
            type=device_type,
            port=port,
            baudrate=baudrate
        )
        
        with self.lock:
            self.devices[device_id] = config
            self.device_status[device_id] = {
                'connected': False,
                'message_count': 0,
                'error_count': 0,
                'last_error': None,
                'last_message_time': 0,
                'start_time': time.time()
            }
        
        logger.info(f"添加设备配置: {name} ({device_id})")
        return device_id
    
    def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        if device_id not in self.devices:
            return False
        
        # 如果设备正在运行，先断开
        if self.device_status[device_id]['connected']:
            self.disconnect_device(device_id)
        
        with self.lock:
            del self.devices[device_id]
            del self.device_status[device_id]
        
        logger.info(f"移除设备: {device_id}")
        return True
    
    def connect_device(self, device_id: str) -> bool:
        """连接单个设备"""
        if device_id not in self.devices:
            logger.error(f"设备不存在: {device_id}")
            return False
        
        config = self.devices[device_id]
        
        if self.device_status[device_id]['connected']:
            logger.info(f"设备已连接: {device_id}")
            return True
        
        try:
            # 根据设备类型创建连接
            if config.type == "virtual":
                bus = self.can_interface.Bus(
                    interface='virtual',
                    channel=config.port,
                    receive_own_messages=True
                )
                logger.info(f"连接到虚拟设备: {config.name}")
                
            elif config.type == "ni_8502":
                bus = self.can_interface.Bus(
                    interface='ni',
                    channel=config.port,
                    bitrate=config.baudrate,
                    fd=False
                )
                logger.info(f"连接到NI设备: {config.name}, 波特率: {config.baudrate}")
                
            elif config.type == "kvaser":
                bus = self.can_interface.Bus(
                    interface='kvaser',
                    channel=int(config.port),
                    bitrate=config.baudrate
                )
                logger.info(f"连接到Kvaser设备: {config.name}, 波特率: {config.baudrate}")
                
            else:
                logger.error(f"不支持的设备类型: {config.type}")
                return False
            
            # 更新状态
            with self.lock:
                self.device_status[device_id]['connected'] = True
                self.device_status[device_id]['bus'] = bus
                self.device_status[device_id]['last_connect_time'] = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"连接设备 {device_id} 失败: {e}")
            with self.lock:
                self.device_status[device_id]['last_error'] = str(e)
                self.device_status[device_id]['error_count'] += 1
            return False
    
    def disconnect_device(self, device_id: str) -> bool:
        """断开单个设备"""
        if device_id not in self.devices:
            return False
        
        with self.lock:
            if not self.device_status[device_id]['connected']:
                return True
            
            try:
                if 'bus' in self.device_status[device_id]:
                    self.device_status[device_id]['bus'].shutdown()
                
                self.device_status[device_id]['connected'] = False
                if 'bus' in self.device_status[device_id]:
                    del self.device_status[device_id]['bus']
                
                logger.info(f"设备断开: {device_id}")
                return True
                
            except Exception as e:
                logger.error(f"断开设备 {device_id} 失败: {e}")
                return False
    
    def connect_all_devices(self) -> Dict[str, bool]:
        """连接所有设备"""
        results = {}
        
        for device_id in list(self.devices.keys()):
            success = self.connect_device(device_id)
            results[device_id] = success
        
        connected_count = sum(1 for success in results.values() if success)
        logger.info(f"连接完成: {connected_count}/{len(results)} 个设备成功")
        return results
    
    def disconnect_all_devices(self):
        """断开所有设备"""
        for device_id in list(self.devices.keys()):
            self.disconnect_device(device_id)
        
        logger.info("所有设备已断开")
    
    def start_receiving(self):
        """开始接收所有设备的数据"""
        if self.running:
            return
        
        self.running = True
        
        # 为每个连接的设备创建接收线程
        with self.lock:
            for device_id, status in self.device_status.items():
                if status['connected']:
                    thread = threading.Thread(
                        target=self._device_receive_loop,
                        args=(device_id,),
                        daemon=True,
                        name=f"CAN_Receiver_{device_id}"
                    )
                    thread.start()
                    self.receive_threads.append(thread)
        
        logger.info(f"启动 {len(self.receive_threads)} 个设备接收线程")
    
    def stop_receiving(self):
        """停止接收"""
        self.running = False
        
        # 等待所有线程结束
        for thread in self.receive_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        self.receive_threads.clear()
        logger.info("停止所有设备接收")
    
    def _device_receive_loop(self, device_id: str):
        """设备接收循环"""
        config = self.devices.get(device_id)
        status = self.device_status.get(device_id)
        
        if not config or not status or not status.get('connected'):
            return
        
        bus = status.get('bus')
        if not bus:
            return
        
        logger.info(f"开始接收设备 {device_id} 的数据")
        
        while self.running and status['connected']:
            try:
                # 非阻塞接收
                message = bus.recv(timeout=0.1)
                
                if message:
                    # 创建扩展消息
                    can_msg = CANMessageEx(
                        can_id=message.arbitration_id,
                        data=message.data,
                        timestamp=message.timestamp,
                        device_id=device_id,
                        device_name=config.name,
                        port=config.port,
                        is_extended=message.is_extended_id,
                        dlc=message.dlc
                    )
                    
                    # 放入队列
                    try:
                        self.message_queue.put_nowait(can_msg)
                    except queue.Full:
                        logger.warning("消息队列已满，丢弃消息")
                        continue
                    
                    # 更新统计
                    with self.stats_lock:
                        status['message_count'] += 1
                        status['last_message_time'] = time.time()
                        self.total_messages += 1
                    
                    # 调用回调函数
                    for callback in self.callbacks:
                        try:
                            callback(can_msg)
                        except Exception as e:
                            logger.error(f"回调函数执行失败: {e}")
                
                # 检查连接状态
                if time.time() - status.get('last_message_time', 0) > 10.0:
                    # 长时间没有消息，可能连接断开
                    pass
                    
            except Exception as e:
                with self.stats_lock:
                    status['error_count'] += 1
                    status['last_error'] = str(e)
                
                if not self.running:
                    break
                
                # 短暂休眠后继续
                time.sleep(0.01)
        
        logger.info(f"停止接收设备 {device_id} 的数据")
    
    def get_message(self, timeout: float = 1.0) -> Optional[CANMessageEx]:
        """从队列获取消息"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def send_message(self, device_id: str, can_id: int, data: bytes, 
                     is_extended: bool = False) -> bool:
        """通过指定设备发送消息"""
        if device_id not in self.devices:
            return False
        
        status = self.device_status.get(device_id)
        if not status or not status.get('connected'):
            return False
        
        bus = status.get('bus')
        if not bus:
            return False
        
        try:
            message = self.can_interface.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=is_extended
            )
            bus.send(message)
            logger.debug(f"设备 {device_id} 发送消息: ID=0x{can_id:03X}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def broadcast_message(self, can_id: int, data: bytes, 
                          is_extended: bool = False) -> Dict[str, bool]:
        """向所有连接的设备广播消息"""
        results = {}
        
        for device_id, status in self.device_status.items():
            if status.get('connected'):
                success = self.send_message(device_id, can_id, data, is_extended)
                results[device_id] = success
        
        return results
    
    def register_callback(self, callback):
        """注册消息回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            logger.info(f"注册回调函数，当前数量: {len(self.callbacks)}")
    
    def unregister_callback(self, callback):
        """取消注册消息回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.info(f"取消注册回调函数，当前数量: {len(self.callbacks)}")
    
    def get_connected_devices(self) -> List[str]:
        """获取已连接的设备列表"""
        with self.lock:
            return [device_id for device_id, status in self.device_status.items() 
                    if status.get('connected', False)]
    
    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备详细信息"""
        if device_id not in self.devices:
            return None
        
        config = self.devices[device_id]
        status = self.device_status.get(device_id, {})
        
        info = {
            'id': device_id,
            'name': config.name,
            'type': config.type,
            'port': config.port,
            'baudrate': config.baudrate,
            'connected': status.get('connected', False),
            'message_count': status.get('message_count', 0),
            'error_count': status.get('error_count', 0),
            'last_error': status.get('last_error'),
            'last_message_time': status.get('last_message_time', 0),
            'enabled': config.enabled
        }
        
        return info
    
    def get_all_device_info(self) -> List[Dict[str, Any]]:
        """获取所有设备信息"""
        devices_info = []
        
        for device_id in self.devices.keys():
            info = self.get_device_info(device_id)
            if info:
                devices_info.append(info)
        
        return devices_info
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.stats_lock:
            total_devices = len(self.devices)
            connected_devices = len(self.get_connected_devices())
            
            total_messages = self.total_messages
            total_errors = sum(status.get('error_count', 0) 
                             for status in self.device_status.values())
            
            uptime = time.time() - self.start_time
            
            message_rate = total_messages / uptime if uptime > 0 else 0
            
            return {
                'total_devices': total_devices,
                'connected_devices': connected_devices,
                'total_messages': total_messages,
                'total_errors': total_errors,
                'uptime': uptime,
                'message_rate': message_rate,
                'queue_size': self.message_queue.qsize()
            }
    
    def clear_statistics(self):
        """清除统计信息"""
        with self.stats_lock:
            self.total_messages = 0
            self.start_time = time.time()
            
            for status in self.device_status.values():
                status['message_count'] = 0
                status['error_count'] = 0
                status['last_error'] = None
        
        logger.info("统计信息已清除")
    
    def cleanup(self):
        """清理资源"""
        self.stop_receiving()
        self.disconnect_all_devices()
        
        # 清空队列
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        
        # 清空回调
        self.callbacks.clear()
        
        logger.info("多CAN管理器清理完成")

# 全局多CAN管理器实例
multi_can_manager = MultiCANManager()