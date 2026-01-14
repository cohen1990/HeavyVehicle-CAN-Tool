# 重型车CAN监控工具

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
