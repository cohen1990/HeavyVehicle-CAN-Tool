#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号配置管理
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from src.dbc.dbc_models import SelectedSignal
from src.dbc.dbc_manager import dbc_manager

logger = logging.getLogger("CANMonitor")

class SignalConfiguration:
    """信号配置管理类"""
    
    def __init__(self):
        self.selected_signals: List[SelectedSignal] = []  # 选定的信号
        self.config_file: Optional[str] = None  # 配置文件路径
        self.recording_rate: int = 100  # 记录频率（Hz）
        self.max_selected_signals: int = 20  # 最大选定信号数
        
        # 颜色池（用于自动分配颜色）
        self.color_pool = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
        ]
    
    def add_signal(self, signal_ref, message_ref, 
                   display_name: Optional[str] = None) -> bool:
        """添加选定信号"""
        # 检查是否已达到上限
        if len(self.selected_signals) >= self.max_selected_signals:
            logger.warning(f"已达到最大选定信号数限制: {self.max_selected_signals}")
            return False
        
        # 检查是否已存在
        for selected in self.selected_signals:
            if (selected.signal_ref == signal_ref and 
                selected.message_ref == message_ref):
                logger.warning(f"信号已存在: {signal_ref.name}")
                return False
        
        # 确定显示名称
        if not display_name:
            display_name = f"{message_ref.name}.{signal_ref.name}"
        
        # 分配颜色
        color_index = len(self.selected_signals) % len(self.color_pool)
        color = self.color_pool[color_index]
        
        # 创建选定信号
        selected = SelectedSignal(
            display_name=display_name,
            signal_ref=signal_ref,
            message_ref=message_ref,
            color=color,
            recording_enabled=True
        )
        
        self.selected_signals.append(selected)
        logger.info(f"添加信号: {display_name}")
        return True
    
    def remove_signal(self, index: int) -> bool:
        """移除选定信号"""
        if 0 <= index < len(self.selected_signals):
            removed = self.selected_signals.pop(index)
            logger.info(f"移除信号: {removed.display_name}")
            return True
        return False
    
    def clear_signals(self):
        """清空所有选定信号"""
        self.selected_signals.clear()
        logger.info("清空所有选定信号")
    
    def update_signal_value(self, can_id: int, signal_name: str, 
                           value: float, timestamp: float):
        """更新信号值"""
        for selected in self.selected_signals:
            if (selected.message_ref.can_id == can_id and 
                selected.signal_ref.name == signal_name):
                selected.update_value(value, timestamp)
                break
    
    def save_configuration(self, filepath: str) -> bool:
        """保存配置到文件"""
        try:
            config_data = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'recording_rate': self.recording_rate,
                'selected_signals': [
                    signal.to_dict() for signal in self.selected_signals
                ],
                'loaded_dbc_files': dbc_manager.loaded_files.copy()
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            if filepath.endswith('.json'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            else:
                logger.error(f"不支持的配置文件格式: {filepath}")
                return False
            
            self.config_file = filepath
            logger.info(f"配置已保存到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_configuration(self, filepath: str) -> bool:
        """从文件加载配置"""
        try:
            if not os.path.exists(filepath):
                logger.error(f"配置文件不存在: {filepath}")
                return False
            
            if filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                logger.error(f"不支持的配置文件格式: {filepath}")
                return False
            
            # 清空当前配置
            self.clear_signals()
            
            # 加载配置
            self.recording_rate = config_data.get('recording_rate', 100)
            
            # 加载选定信号
            for signal_data in config_data.get('selected_signals', []):
                selected = SelectedSignal.from_dict(signal_data, dbc_manager)
                if selected:
                    self.selected_signals.append(selected)
            
            self.config_file = filepath
            
            logger.info(f"配置已加载: {filepath}, {len(self.selected_signals)} 个信号")
            return True
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False
    
    def export_to_csv(self, filepath: str, time_range: Optional[tuple] = None) -> bool:
        """导出数据到CSV"""
        try:
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入表头
                headers = ['Timestamp']
                for signal in self.selected_signals:
                    if signal.recording_enabled:
                        headers.append(signal.display_name)
                        if signal.signal_ref.unit:
                            headers.append(f"{signal.display_name}_Unit")
                
                writer.writerow(headers)
                
                # 这里需要实际的数据导出逻辑
                # 暂时只写个示例
                writer.writerow(['示例数据', '1.0', 'RPM'])
            
            logger.info(f"数据已导出到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return False
    
    def get_signal_status(self) -> Dict[str, Any]:
        """获取信号状态"""
        return {
            'total_selected': len(self.selected_signals),
            'recording_enabled': sum(1 for s in self.selected_signals if s.recording_enabled),
            'max_allowed': self.max_selected_signals,
            'recording_rate': self.recording_rate,
            'config_file': self.config_file
        }

# 全局信号配置实例
signal_config = SignalConfiguration()