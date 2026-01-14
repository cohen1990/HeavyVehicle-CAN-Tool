#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理
"""

import os
import json
import yaml

class Settings:
    """配置管理类"""
    
    def __init__(self):
        self.config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "configs"
        )
        self.settings_file = os.path.join(self.config_dir, "settings.yaml")
        self.data = self.load_settings()
        
    def load_settings(self):
        """加载设置"""
        default_settings = {
            'app': {
                'name': '重型车CAN监控工具',
                'version': '1.0.0'
            },
            'ui': {
                'refresh_rate': 100,  # Hz
                'theme': 'light'
            },
            'hardware': {
                'interface': 'auto',
                'baudrate': 500000
            }
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except:
                return default_settings
        return default_settings
    
    def save_settings(self):
        """保存设置"""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.data, f, default_flow_style=False, allow_unicode=True)