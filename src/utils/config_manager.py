# src/utils/config_manager.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理工具
"""

import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.config.signal_config import signal_config
from src.dbc.dbc_manager import dbc_manager

class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def export_signal_config(filepath: str) -> bool:
        """导出信号配置"""
        try:
            config_data = {
                'version': '1.0',
                'export_time': datetime.now().isoformat(),
                'dbc_files': dbc_manager.loaded_files.copy(),
                'signals': []
            }
            
            for selected_signal in signal_config.selected_signals:
                signal_data = {
                    'display_name': selected_signal.display_name,
                    'message_name': selected_signal.message_ref.name,
                    'message_id': selected_signal.message_ref.can_id,
                    'signal_name': selected_signal.signal_ref.name,
                    'color': selected_signal.color,
                    'recording_enabled': selected_signal.recording_enabled,
                    'unit': selected_signal.signal_ref.unit,
                    'min_value': selected_signal.signal_ref.min,
                    'max_value': selected_signal.signal_ref.max
                }
                config_data['signals'].append(signal_data)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            if filepath.endswith('.json'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            else:
                # 默认用JSON
                filepath = filepath + '.json' if not filepath.endswith('.json') else filepath
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    @staticmethod
    def import_signal_config(filepath: str) -> tuple[bool, str]:
        """导入信号配置"""
        try:
            if not os.path.exists(filepath):
                return False, f"文件不存在: {filepath}"
            
            # 读取文件
            if filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                return False, "不支持的文件格式"
            
            # 验证版本
            if 'version' not in config_data:
                return False, "无效的配置文件格式"
            
            # 清空当前配置
            signal_config.clear_signals()
            
            success_count = 0
            failed_messages = []
            
            for sig_data in config_data.get('signals', []):
                try:
                    # 查找消息
                    message = None
                    if 'message_name' in sig_data:
                        message = dbc_manager.get_message_by_name(sig_data['message_name'])
                    
                    if not message and 'message_id' in sig_data:
                        message = dbc_manager.get_message(sig_data['message_id'])
                    
                    if not message:
                        failed_messages.append(f"找不到消息: {sig_data.get('message_name', 'Unknown')}")
                        continue
                    
                    # 查找信号
                    signal = message.get_signal(sig_data['signal_name'])
                    if not signal:
                        failed_messages.append(f"消息 {message.name} 中找不到信号: {sig_data['signal_name']}")
                        continue
                    
                    # 添加信号
                    display_name = sig_data.get('display_name', f"{message.name}.{signal.name}")
                    success = signal_config.add_signal(signal, message, display_name)
                    
                    if success:
                        # 设置额外属性
                        for selected_signal in signal_config.selected_signals:
                            if selected_signal.display_name == display_name:
                                if 'color' in sig_data:
                                    selected_signal.color = sig_data['color']
                                if 'recording_enabled' in sig_data:
                                    selected_signal.recording_enabled = sig_data['recording_enabled']
                        
                        success_count += 1
                        
                except Exception as e:
                    failed_messages.append(str(e))
                    continue
            
            message = f"导入完成: {success_count} 个信号"
            if failed_messages:
                message += f"\n失败: {len(failed_messages)} 个信号"
                if len(failed_messages) <= 5:
                    for fail_msg in failed_messages[:5]:
                        message += f"\n  - {fail_msg}"
                else:
                    message += f"\n  - 显示前5个失败原因..."
            
            return success_count > 0, message
            
        except Exception as e:
            return False, f"导入配置失败: {e}"
    
    @staticmethod
    def get_config_template() -> Dict[str, Any]:
        """获取配置模板"""
        return {
            'version': '1.0',
            'description': '重型车CAN监控工具信号配置',
            'signals': [
                {
                    'display_name': 'CCVS6.SelectedRoadwayVSLmt',
                    'message_name': 'CCVS6',
                    'message_id': 0x18FC28FE,
                    'signal_name': 'SelectedRoadwayVSLmt',
                    'color': '#FF6B6B',
                    'recording_enabled': True
                }
            ],
            'settings': {
                'recording_rate': 100,
                'auto_color': True
            }
        }