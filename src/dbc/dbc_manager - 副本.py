#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBC文件管理器 - 简化跳过版本
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from .dbc_models import DBCSignal, DBCMessage

logger = logging.getLogger("CANMonitor")

class DBCManager:
    """DBC文件管理器"""
    
    def __init__(self):
        self.messages: Dict[int, DBCMessage] = {}  # can_id -> message
        self.message_names: Dict[str, DBCMessage] = {}  # name -> message
        self.loaded_files: List[str] = []
        self.skipped_messages: List[Dict[str, Any]] = []  # 跳过的消息
        
        # 信号值缓存
        self.signal_values: Dict[Tuple[int, str], float] = {}  # (can_id, signal_name) -> value
        self.message_counters: Dict[int, int] = defaultdict(int)  # can_id -> count
    
    def load_dbc_file(self, filepath: str, skip_problematic: bool = True) -> bool:
        """加载DBC文件 - 简化跳过版本"""
        try:
            import cantools
            
            logger.info(f"加载DBC文件: {filepath}")
            
            # 使用宽松模式加载
            try:
                db = cantools.database.load_file(filepath, strict=not skip_problematic)
            except Exception as e:
                if skip_problematic:
                    logger.warning(f"使用宽松模式重新加载: {e}")
                    db = cantools.database.load_file(filepath, strict=False)
                else:
                    raise
            
            skipped_count = 0
            total_messages = len(db.messages)
            
            for msg in db.messages:
                try:
                    # 检查信号重叠（简化检查）
                    if not self._check_message_validity(msg, skip_problematic):
                        skipped_count += 1
                        continue
                    
                    # 创建DBCMessage对象
                    dbc_msg = self._create_dbc_message_from_cantools(msg)
                    
                    # 存储消息
                    self.messages[msg.frame_id] = dbc_msg
                    self.message_names[msg.name] = dbc_msg
                    
                    logger.debug(f"加载消息: {msg.name} (ID: 0x{msg.frame_id:X}), {len(msg.signals)} 个信号")
                    
                except Exception as e:
                    if skip_problematic:
                        logger.warning(f"跳过消息 {msg.name}: {e}")
                        self.skipped_messages.append({
                            'file': os.path.basename(filepath),
                            'message': msg.name,
                            'id': msg.frame_id,
                            'reason': str(e),
                            'type': 'error'
                        })
                        skipped_count += 1
                        continue
                    else:
                        raise
            
            self.loaded_files.append(filepath)
            
            # 输出统计信息
            success_count = total_messages - skipped_count
            logger.info(f"DBC加载完成: {success_count}/{total_messages} 个消息")
            if skipped_count > 0:
                logger.warning(f"跳过了 {skipped_count} 个有问题的消息")
                
            return success_count > 0
            
        except ImportError:
            logger.error("未安装cantools库，无法解析DBC文件")
            return False
        except Exception as e:
            logger.error(f"加载DBC文件失败: {e}")
            return False
    
    def _check_message_validity(self, msg, skip_problematic: bool) -> bool:
        """检查消息有效性"""
        if skip_problematic:
            # 简化检查：只检查基本问题
            try:
                # 检查信号是否重叠
                occupied_bits = {}
                for signal in msg.signals:
                    for bit in range(signal.start, signal.start + signal.length):
                        if bit in occupied_bits:
                            overlapping = occupied_bits[bit]
                            raise ValueError(f"信号 {signal.name} 与 {overlapping} 在位 {bit} 重叠")
                        occupied_bits[bit] = signal.name
                
                # 检查起始位是否有效
                for signal in msg.signals:
                    if signal.start < 0 or signal.start >= msg.length * 8:
                        raise ValueError(f"信号 {signal.name} 起始位 {signal.start} 无效")
                    
                    if signal.length <= 0 or signal.length > 64:
                        raise ValueError(f"信号 {signal.name} 长度 {signal.length} 无效")
                
                return True
                
            except ValueError as e:
                if skip_problematic:
                    return False
                else:
                    raise
        
        return True
    
    def _create_dbc_message_from_cantools(self, msg) -> DBCMessage:
        """从cantools消息创建DBCMessage（快速修复版）"""
        # 判断是否为扩展帧（兼容不同版本）
        is_extended = False
        if hasattr(msg, 'is_extended'):
            is_extended = msg.is_extended
        elif hasattr(msg, 'is_extended_id'):
            is_extended = msg.is_extended_id
        else:
            # 根据ID范围判断
            is_extended = msg.frame_id >= 0x800
        
        # 获取描述
        description = getattr(msg, 'comment', getattr(msg, 'description', ""))
        
        # 获取周期时间
        cycle_time = getattr(msg, 'cycle_time', 0)
        
        # 创建消息
        dbc_msg = DBCMessage(
            name=msg.name,
            can_id=msg.frame_id,
            dlc=msg.length,
            description=description or "",
            is_extended=is_extended,
            cycle_time=cycle_time
        )
        
        # 添加信号
        for signal in msg.signals:
            dbc_signal = DBCSignal(
                name=signal.name,
                start_bit=signal.start,
                length=signal.length,
                scale=signal.scale,
                offset=signal.offset,
                min_val=getattr(signal, 'minimum', None),
                max_val=getattr(signal, 'maximum', None),
                unit=getattr(signal, 'unit', "") or "",
                is_signed=signal.is_signed,
                is_multiplexed=getattr(signal, 'is_multiplexer', False),
                multiplex_id=getattr(signal, 'multiplexer_ids', [None])[0]
            )
            dbc_msg.add_signal(dbc_signal)
        
        return dbc_msg
    
    def decode_message(self, can_id: int, data: bytes) -> Dict[str, float]:
        """解码CAN消息"""
        message = self.get_message(can_id)
        if not message:
            return {}
        
        # 更新计数器
        self.message_counters[can_id] += 1
        
        # 解码信号
        results = message.decode(data)
        
        # 更新缓存
        for signal_name, value in results.items():
            self.signal_values[(can_id, signal_name)] = value
        
        return results
    
    def get_message(self, can_id: int) -> Optional[DBCMessage]:
        """根据CAN ID获取消息"""
        return self.messages.get(can_id)
    
    def get_message_by_name(self, name: str) -> Optional[DBCMessage]:
        """根据名称获取消息"""
        return self.message_names.get(name)
    
    def get_all_messages(self) -> List[DBCMessage]:
        """获取所有消息"""
        return list(self.messages.values())
    
    def get_all_signals(self) -> List[DBCSignal]:
        """获取所有信号"""
        signals = []
        for message in self.messages.values():
            signals.extend(message.signals)
        return signals
    
    def search_signals(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索信号"""
        results = []
        keyword_lower = keyword.lower()
        
        for message in self.messages.values():
            for signal in message.signals:
                if (keyword_lower in signal.name.lower() or 
                    keyword_lower in message.name.lower() or
                    keyword_lower in message.description.lower()):
                    
                    results.append({
                        'message': message,
                        'signal': signal,
                        'full_name': f"{message.name}.{signal.name}",
                        'message_id': f"0x{message.can_id:X}",
                        'description': message.description,
                        'unit': signal.unit
                    })
        
        return results
    
    def clear(self):
        """清空所有数据"""
        self.messages.clear()
        self.message_names.clear()
        self.loaded_files.clear()
        self.skipped_messages.clear()
        self.signal_values.clear()
        self.message_counters.clear()
        logger.info("DBC管理器已清空")
    
    def get_skipped_messages_info(self) -> str:
        """获取跳过的消息信息"""
        if not self.skipped_messages:
            return ""
        
        info = f"跳过了 {len(self.skipped_messages)} 个消息:\n"
        for skipped in self.skipped_messages[:10]:  # 只显示前10个
            info += f"  - {skipped['message']} (0x{skipped['id']:X}): {skipped['reason']}\n"
        
        if len(self.skipped_messages) > 10:
            info += f"  ... 还有 {len(self.skipped_messages) - 10} 个\n"
        
        return info

# 全局DBC管理器实例
dbc_manager = DBCManager()