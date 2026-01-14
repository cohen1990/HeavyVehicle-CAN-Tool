#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBC数据模型类
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger("CANMonitor")

class DBCSignal:
    """DBC信号类"""
    
    def __init__(self, name: str, start_bit: int = 0, length: int = 1,
                 scale: float = 1.0, offset: float = 0.0,
                 min_val: Optional[float] = None, max_val: Optional[float] = None,
                 unit: str = "", is_signed: bool = True, 
                 is_multiplexed: bool = False, multiplex_id: Optional[int] = None):
        
        self.name = name
        self.start_bit = start_bit
        self.length = length
        self.scale = scale
        self.offset = offset
        self.min = min_val
        self.max = max_val
        self.unit = unit
        self.is_signed = is_signed
        self.is_multiplexed = is_multiplexed
        self.multiplex_id = multiplex_id
        self.value = 0.0  # 当前值
        self.raw_value = 0  # 原始值
        self.timestamp = 0.0  # 最后更新时间
    
    def decode(self, data: bytes) -> float:
        """从字节数据解码信号值"""
        try:
            # 计算字节和位偏移
            start_byte = self.start_bit // 8
            start_bit_in_byte = self.start_bit % 8
            
            # 提取原始数据
            raw_value = 0
            bits_extracted = 0
            
            for i in range((self.length + 7) // 8):
                if start_byte + i >= len(data):
                    break
                    
                byte_value = data[start_byte + i]
                
                # 如果是第一个字节，需要移位
                if i == 0:
                    byte_value >>= start_bit_in_byte
                    bits_in_this_byte = 8 - start_bit_in_byte
                else:
                    bits_in_this_byte = 8
                
                # 提取有效位
                bits_to_extract = min(self.length - bits_extracted, bits_in_this_byte)
                mask = (1 << bits_to_extract) - 1
                byte_bits = byte_value & mask
                
                raw_value |= (byte_bits << bits_extracted)
                bits_extracted += bits_to_extract
            
            # 处理有符号数
            if self.is_signed and raw_value & (1 << (self.length - 1)):
                raw_value = raw_value - (1 << self.length)
            
            # 保存原始值
            self.raw_value = raw_value
            
            # 应用缩放和偏移
            value = raw_value * self.scale + self.offset
            
            # 检查范围限制
            if self.min is not None and value < self.min:
                value = self.min
            if self.max is not None and value > self.max:
                value = self.max
            
            self.value = value
            return value
            
        except Exception as e:
            logger.error(f"解码信号 {self.name} 失败: {e}")
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'start_bit': self.start_bit,
            'length': self.length,
            'scale': self.scale,
            'offset': self.offset,
            'min': self.min,
            'max': self.max,
            'unit': self.unit,
            'is_signed': self.is_signed,
            'is_multiplexed': self.is_multiplexed,
            'multiplex_id': self.multiplex_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DBCSignal':
        """从字典创建"""
        return cls(
            name=data.get('name', ''),
            start_bit=data.get('start_bit', 0),
            length=data.get('length', 1),
            scale=data.get('scale', 1.0),
            offset=data.get('offset', 0.0),
            min_val=data.get('min'),
            max_val=data.get('max'),
            unit=data.get('unit', ''),
            is_signed=data.get('is_signed', True),
            is_multiplexed=data.get('is_multiplexed', False),
            multiplex_id=data.get('multiplex_id')
        )
    
    def __str__(self):
        return f"DBCSignal(name={self.name}, start={self.start_bit}, len={self.length})"

class DBCMessage:
    """DBC消息类"""
    
    def __init__(self, name: str, can_id: int, dlc: int = 8,
                 description: str = "", signals: Optional[List[DBCSignal]] = None,
                 is_extended: bool = False, cycle_time: int = 0):
        
        self.name = name
        self.can_id = can_id
        self.dlc = dlc
        self.description = description
        self.signals = signals or []
        self.is_extended = is_extended
        self.cycle_time = cycle_time
        self.signal_dict = {sig.name: sig for sig in self.signals}
        self.last_update = 0.0
        self.update_count = 0
    
    def add_signal(self, signal: DBCSignal):
        """添加信号"""
        self.signals.append(signal)
        self.signal_dict[signal.name] = signal
    
    def decode(self, data: bytes) -> Dict[str, float]:
        """解码消息中的所有信号"""
        results = {}
        try:
            for signal in self.signals:
                value = signal.decode(data)
                results[signal.name] = value
            
            self.update_count += 1
            return results
            
        except Exception as e:
            logger.error(f"解码消息 {self.name} 失败: {e}")
            return results
    
    def get_signal(self, signal_name: str) -> Optional[DBCSignal]:
        """获取信号"""
        return self.signal_dict.get(signal_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'can_id': self.can_id,
            'dlc': self.dlc,
            'description': self.description,
            'is_extended': self.is_extended,
            'cycle_time': self.cycle_time,
            'signals': [sig.to_dict() for sig in self.signals]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DBCMessage':
        """从字典创建"""
        signals = [DBCSignal.from_dict(sig) for sig in data.get('signals', [])]
        return cls(
            name=data.get('name', ''),
            can_id=data.get('can_id', 0),
            dlc=data.get('dlc', 8),
            description=data.get('description', ''),
            signals=signals,
            is_extended=data.get('is_extended', False),
            cycle_time=data.get('cycle_time', 0)
        )
    
    def __str__(self):
        return f"DBCMessage(name={self.name}, id=0x{self.can_id:X}, signals={len(self.signals)})"

class SelectedSignal:
    """选定的信号配置"""
    
    def __init__(self, display_name: str, signal_ref: DBCSignal,
                 message_ref: DBCMessage, color: str = "#000000",
                 recording_enabled: bool = True):
        
        self.display_name = display_name  # 显示名称
        self.signal_ref = signal_ref      # 信号引用
        self.message_ref = message_ref    # 消息引用
        self.color = color                # 显示颜色
        self.recording_enabled = recording_enabled  # 是否记录
        
        # 实时数据
        self.current_value = 0.0
        self.last_value = 0.0
        self.update_time = 0.0
        self.value_history = []  # 历史值（用于图表）
        
    def update_value(self, value: float, timestamp: float):
        """更新信号值"""
        self.last_value = self.current_value
        self.current_value = value
        self.update_time = timestamp
        
        # 记录历史值（限制长度）
        self.value_history.append((timestamp, value))
        if len(self.value_history) > 1000:
            self.value_history.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'display_name': self.display_name,
            'message_name': self.message_ref.name,
            'message_id': self.message_ref.can_id,
            'signal_name': self.signal_ref.name,
            'color': self.color,
            'recording_enabled': self.recording_enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], dbc_manager) -> Optional['SelectedSignal']:
        """从字典创建"""
        try:
            message = dbc_manager.get_message_by_name(data['message_name'])
            if not message:
                # 尝试通过ID查找
                message = dbc_manager.get_message(data['message_id'])
            
            if not message:
                logger.error(f"找不到消息: {data['message_name']}")
                return None
            
            signal = message.get_signal(data['signal_name'])
            if not signal:
                logger.error(f"找不到信号: {data['signal_name']}")
                return None
            
            return cls(
                display_name=data.get('display_name', data['signal_name']),
                signal_ref=signal,
                message_ref=message,
                color=data.get('color', '#000000'),
                recording_enabled=data.get('recording_enabled', True)
            )
        except Exception as e:
            logger.error(f"创建SelectedSignal失败: {e}")
            return None