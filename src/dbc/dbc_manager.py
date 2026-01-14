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
    def load_dbc_file_simple(self, filepath: str) -> bool:
        """简单加载 - 跳过所有检查"""
        try:
            import cantools
            db = cantools.database.load_file(filepath, strict=False)
            
            for msg in db.messages:
                # 直接创建，不检查任何问题
                try:
                    dbc_msg = DBCMessage(
                        name=str(msg.name),
                        can_id=int(msg.frame_id),
                        dlc=int(msg.length),
                        is_extended=True,  # J1939默认扩展帧
                        cycle_time=int(msg.cycle_time) if hasattr(msg, 'cycle_time') else 0
                    )
                    
                    for signal in msg.signals:
                        dbc_signal = DBCSignal(
                            name=str(signal.name),
                            start_bit=int(signal.start),
                            length=int(signal.length),
                            scale=float(signal.scale),
                            offset=float(signal.offset)
                        )
                        dbc_msg.add_signal(dbc_signal)
                    
                    self.messages[msg.frame_id] = dbc_msg
                    self.message_names[msg.name] = dbc_msg
                    
                except:
                    continue  # 跳过有问题的消息
            
            print(f"简单加载完成: {len(self.messages)} 个消息")
            return True
        except Exception as e:
            print(f"简单加载失败: {e}")
            return False
    def load_dbc_file_tolerant(self, filepath: str) -> bool:
        """容错加载 - 只跳过重叠信号的消息"""
        try:
            import cantools
            
            print(f"[容错加载] 开始加载: {filepath}")
            
            db = cantools.database.load_file(filepath, strict=False)
            
            total_messages = len(db.messages)
            loaded_count = 0
            overlap_count = 0
            other_error_count = 0
            
            for msg in db.messages:
                # 检查信号重叠
                has_overlap = False
                try:
                    occupied = {}
                    for signal in msg.signals:
                        for bit in range(signal.start, signal.start + signal.length):
                            if bit in occupied:
                                print(f"  信号重叠: {msg.name} 中 {signal.name} 与 {occupied[bit]} 重叠")
                                has_overlap = True
                                break
                            occupied[bit] = signal.name
                        if has_overlap:
                            break
                except:
                    pass
                
                if has_overlap:
                    overlap_count += 1
                    continue  # 跳过这个有重叠的消息
                
                # 加载没有重叠的消息（使用和简单加载相同的方法）
                try:
                    dbc_msg = DBCMessage(
                        name=str(msg.name),
                        can_id=int(msg.frame_id),
                        dlc=int(msg.length),
                        description=str(msg.comment) if hasattr(msg, 'comment') and msg.comment else "",
                        is_extended=True,
                        cycle_time=int(msg.cycle_time) if hasattr(msg, 'cycle_time') and msg.cycle_time else 0
                    )
                    
                    for signal in msg.signals:
                        try:
                            dbc_signal = DBCSignal(
                                name=str(signal.name),
                                start_bit=int(signal.start),
                                length=int(signal.length),
                                scale=float(signal.scale),
                                offset=float(signal.offset),
                                unit=str(signal.unit) if hasattr(signal, 'unit') and signal.unit else "",
                                is_signed=bool(signal.is_signed) if hasattr(signal, 'is_signed') else False
                            )
                            dbc_msg.add_signal(dbc_signal)
                        except Exception as sig_e:
                            # 记录信号错误但继续
                            print(f"    信号 {signal.name} 创建失败: {sig_e}")
                            continue
                    
                    self.messages[msg.frame_id] = dbc_msg
                    self.message_names[msg.name] = dbc_msg
                    loaded_count += 1
                    
                except Exception as e:
                    other_error_count += 1
                    print(f"  消息 {msg.name} 加载失败: {e}")
                    continue
            
            self.loaded_files.append(filepath)
            
            print(f"[容错加载] 完成: {loaded_count}/{total_messages} 个消息")
            print(f"  跳过了 {overlap_count} 个有重叠信号的消息")
            print(f"  其他错误: {other_error_count} 个消息")
            return loaded_count > 0
            
        except Exception as e:
            print(f"[容错加载] 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    def load_j1939_selective(self, filepath: str, include_patterns=None) -> bool:
        """选择性加载J1939消息"""
        if include_patterns is None:
            include_patterns = ['ENG', 'EEC', 'EBC', 'CCVS', 'TPMS', 'VEP', 'HVESS', 'ETC']  # 常用J1939消息
        
        try:
            import cantools
            
            print(f"[选择性加载] 开始加载: {filepath}")
            print(f"  包含模式: {include_patterns}")
            
            db = cantools.database.load_file(filepath, strict=False)
            
            total_messages = len(db.messages)
            loaded_count = 0
            
            for msg in db.messages:
                msg_name = msg.name.upper()
                
                # 检查是否在包含列表中
                should_include = False
                for pattern in include_patterns:
                    if pattern.upper() in msg_name:
                        should_include = True
                        break
                
                if not should_include:
                    continue  # 跳过不需要的消息
                
                # 加载选中的消息（使用和简单加载相同的方法）
                try:
                    dbc_msg = DBCMessage(
                        name=str(msg.name),
                        can_id=int(msg.frame_id),
                        dlc=int(msg.length),
                        description=str(msg.comment) if hasattr(msg, 'comment') and msg.comment else "",
                        is_extended=True,
                        cycle_time=int(msg.cycle_time) if hasattr(msg, 'cycle_time') and msg.cycle_time else 0
                    )
                    
                    for signal in msg.signals:
                        try:
                            dbc_signal = DBCSignal(
                                name=str(signal.name),
                                start_bit=int(signal.start),
                                length=int(signal.length),
                                scale=float(signal.scale),
                                offset=float(signal.offset),
                                unit=str(signal.unit) if hasattr(signal, 'unit') and signal.unit else "",
                                is_signed=bool(signal.is_signed) if hasattr(signal, 'is_signed') else False
                            )
                            dbc_msg.add_signal(dbc_signal)
                        except:
                            continue
                    
                    self.messages[msg.frame_id] = dbc_msg
                    self.message_names[msg.name] = dbc_msg
                    loaded_count += 1
                    print(f"  ✓ 加载: {msg.name}")
                    
                except Exception as e:
                    print(f"  ✗ 跳过 {msg.name}: {e}")
                    continue
            
            self.loaded_files.append(filepath)
            
            print(f"[选择性加载] 完成: {loaded_count}/{total_messages} 个消息")
            return loaded_count > 0
            
        except Exception as e:
            print(f"[选择性加载] 失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_dbc_file_batch(self, filepath: str, batch_size=500) -> bool:
        """分批加载DBC文件"""
        try:
            import cantools
            
            print(f"[分批加载] 开始加载: {filepath}")
            print(f"  批次大小: {batch_size}")
            
            db = cantools.database.load_file(filepath, strict=False)
            all_messages = list(db.messages)
            
            total_batches = (len(all_messages) + batch_size - 1) // batch_size
            total_loaded = 0
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(all_messages))
                
                batch_messages = all_messages[start_idx:end_idx]
                batch_loaded = 0
                
                print(f"\n  处理批次 {batch_num + 1}/{total_batches} "
                      f"(消息 {start_idx + 1}-{end_idx})")
                
                for msg in batch_messages:
                    try:
                        dbc_msg = DBCMessage(
                            name=str(msg.name),
                            can_id=int(msg.frame_id),
                            dlc=int(msg.length),
                            description=str(msg.comment) if hasattr(msg, 'comment') and msg.comment else "",
                            is_extended=True,
                            cycle_time=int(msg.cycle_time) if hasattr(msg, 'cycle_time') and msg.cycle_time else 0
                        )
                        
                        for signal in msg.signals:
                            try:
                                dbc_signal = DBCSignal(
                                    name=str(signal.name),
                                    start_bit=int(signal.start),
                                    length=int(signal.length),
                                    scale=float(signal.scale),
                                    offset=float(signal.offset),
                                    unit=str(signal.unit) if hasattr(signal, 'unit') and signal.unit else "",
                                    is_signed=bool(signal.is_signed) if hasattr(signal, 'is_signed') else False
                                )
                                dbc_msg.add_signal(dbc_signal)
                            except:
                                continue
                        
                        self.messages[msg.frame_id] = dbc_msg
                        self.message_names[msg.name] = dbc_msg
                        batch_loaded += 1
                        
                    except Exception as e:
                        print(f"    跳过 {msg.name}: {e}")
                        continue
                
                total_loaded += batch_loaded
                print(f"    本批加载: {batch_loaded}/{len(batch_messages)} 个消息")
                print(f"    累计加载: {total_loaded} 个消息")
            
            self.loaded_files.append(filepath)
            
            print(f"\n[分批加载] 完成: {total_loaded}/{len(all_messages)} 个消息")
            return total_loaded > 0
            
        except Exception as e:
            print(f"[分批加载] 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    def load_dbc_file(self, filepath: str, skip_problematic: bool = True) -> bool:
        """
        主加载方法 - 使用分批加载（最佳方案）
        :param filepath: DBC文件路径
        :param skip_problematic: 是否跳过有问题的消息（保持兼容性）
        :return: 是否加载成功
        """
        # 默认使用分批加载，这是测试中表现最好的方法
        return self.load_dbc_file_batch(filepath, batch_size=500)
    
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