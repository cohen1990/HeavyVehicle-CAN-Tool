#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统
"""

import logging
import os
from datetime import datetime

def setup_logger():
    """设置日志"""
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(
        log_dir,
        f"can_monitor_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    logger = logging.getLogger("CANMonitor")
    logger.setLevel(logging.INFO)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()