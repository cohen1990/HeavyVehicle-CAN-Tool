#!/usr/bin/env python3
"""
项目初始化脚本
运行: python setup_project.py
"""

import os
import sys

def create_structure(base_path):
    """创建项目目录结构"""
    
    directories = [
        # 源代码目录
        'src',
        'src/config',
        'src/hardware', 
        'src/ui',
        'src/ui/widgets',
        'src/dbc',
        'src/data',
        'src/utils',
        'src/resources',
        'src/resources/icons',
        'src/resources/styles',
        
        # 配置文件目录
        'configs',
        'configs/signal_templates',
        
        # 数据目录
        'dbc_files',
        'logs',
        'outputs',
        'docs',
        'tests',
    ]
    
    # 创建目录
    for directory in directories:
        dir_path = os.path.join(base_path, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"创建目录: {directory}")
    
    # 创建 __init__.py 文件
    init_dirs = [
        'src', 'src/config', 'src/hardware', 'src/ui',
        'src/ui/widgets', 'src/dbc', 'src/data', 'src/utils'
    ]
    
    for dir_name in init_dirs:
        init_file = os.path.join(base_path, dir_name, '__init__.py')
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('# ' + dir_name + ' 模块初始化\n')
        print(f"创建文件: {dir_name}/__init__.py")
    
    # 创建基本配置文件
    configs = {
        'requirements.txt': """# 重型车CAN监控工具 - 依赖列表

# 核心库
python-can>=4.2.0
cantools>=39.0.0
pandas>=1.5.0
numpy>=1.21.0

# 界面
PyQt5>=5.15.0
pyqtgraph>=0.13.0

# 数据处理
pyserial>=3.5
pyyaml>=6.0
sqlalchemy>=1.4.0

# 工具类
python-dateutil>=2.8.0
pytz>=2021.3

# 开发工具（不打包）
pyinstaller>=5.0
black>=22.0.0
pytest>=6.2.5
""",
        
        'README.md': """# 重型车CAN监控工具

## 项目描述
用于记录重型车的CAN广播报文中的选定信号，支持NI USB-8502和Kvaser硬件。

## 功能特点
1. 实时显示选定信号值
2. 数据记录功能
3. DBC文件导入和解析
4. 灵活的硬件配置
5. 用户友好的图形界面

## 系统要求
- Windows 10/11
- Python 3.8+
- NI USB-8502 或 Kvaser CAN设备

## 安装说明
1. 安装Python 3.8+
2. 安装依赖: `pip install -r requirements.txt`
3. 安装硬件驱动:
   - NI设备: NI-CAN驱动
   - Kvaser设备: Kvaser驱动

## 使用说明
1. 运行 `python src/main.py`
2. 配置硬件连接
3. 导入DBC文件
4. 选择要监控的信号
5. 开始监控和记录

## 项目结构
HeavyVehicle_CAN_Tool/
├── src/ # 源代码
├── configs/ # 配置文件
├── dbc_files/ # DBC文件
├── logs/ # 日志文件
├── outputs/ # 输出数据
├── docs/ # 文档
└── tests/ # 测试

## 开发说明
- 主入口: `src/main.py`
- 界面设计: 使用PyQt5
- CAN通信: 使用python-can
- DBC解析: 使用cantools
""",
        
        '.gitignore': """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 项目特定
logs/
outputs/
*.log
*.db
""",
        
        'configs/default_settings.yaml': """# 重型车CAN监控工具 - 默认配置

app:
  name: "重型车CAN监控工具"
  version: "1.0.0"
  author: "YourName"
  
ui:
  language: "zh_CN"
  theme: "light"  # light, dark
  font_size: 10
  refresh_rate: 100  # Hz
  
can:
  default_baudrate: 500000
  default_interface: "auto"
  
hardware:
  ni_8502:
    default_port: "Dev1/CNI0"
    supported_baudrates: [10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000]
  
  kvaser:
    default_channel: 0
    supported_baudrates: [10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000]

recording:
  default_format: "csv"  # csv, sqlite, both
  default_directory: "./outputs"
  auto_timestamp: true
  max_file_size_mb: 100
  
signals:
  max_selected: 20
  default_refresh_rate: 100  # Hz
  save_config_on_exit: true
  
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file_max_size: 10  # MB
  file_backup_count: 5
"""
    }
    
    # 写入配置文件
    for filename, content in configs.items():
        filepath = os.path.join(base_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"创建文件: {filename}")
    
    print(f"\n✅ 项目初始化完成！")
    print(f"项目路径: {os.path.abspath(base_path)}")
    print(f"\n下一步:")
    print("1. 安装依赖: pip install -r requirements.txt")
    print("2. 运行测试: python src/main.py")
    print("3. 开始开发!")

def main():
    """主函数"""
    print("=" * 60)
    print("重型车CAN监控工具 - 项目初始化")
    print("=" * 60)
    
    # 获取当前目录或指定目录
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = input("请输入项目路径 (默认为当前目录): ").strip()
        if not base_path:
            base_path = "."
    
    # 创建项目结构
    create_structure(base_path)

if __name__ == "__main__":
    main()