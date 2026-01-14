# analyze_dbc.py - 放在项目根目录
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cantools
import traceback

def analyze_dbc_file(dbc_path):
    """分析DBC文件问题"""
    print(f"分析DBC文件: {dbc_path}")
    print("=" * 60)
    
    try:
        # 1. 尝试标准加载
        print("1. 尝试标准加载...")
        try:
            db = cantools.database.load_file(dbc_path, strict=True)
            print("✓ 标准加载成功")
            print(f"  消息数: {len(db.messages)}")
        except Exception as e:
            print(f"✗ 标准加载失败: {e}")
        
        # 2. 尝试宽松加载
        print("\n2. 尝试宽松加载...")
        try:
            db = cantools.database.load_file(dbc_path, strict=False)
            print("✓ 宽松加载成功")
            print(f"  消息数: {len(db.messages)}")
            
            # 检查前5个消息的问题
            print("\n3. 检查消息结构:")
            for i, msg in enumerate(list(db.messages)[:5]):
                print(f"\n消息 {i+1}: {msg.name} (ID: 0x{msg.frame_id:X})")
                
                try:
                    # 检查消息属性
                    attrs = ['comment', 'cycle_time', 'length', 'is_extended']
                    for attr in attrs:
                        if hasattr(msg, attr):
                            value = getattr(msg, attr)
                            print(f"  {attr}: {value}")
                        else:
                            print(f"  {attr}: 属性不存在")
                    
                    # 检查信号
                    print(f"  信号数: {len(msg.signals)}")
                    if msg.signals:
                        for j, sig in enumerate(list(msg.signals)[:3]):
                            print(f"    信号 {j+1}: {sig.name}")
                            sig_attrs = ['unit', 'minimum', 'maximum', 'scale', 'offset']
                            for attr in sig_attrs:
                                if hasattr(sig, attr):
                                    value = getattr(sig, attr)
                                    print(f"      {attr}: {value}")
                                
                except Exception as msg_e:
                    print(f"  消息检查失败: {msg_e}")
            
        except Exception as e:
            print(f"✗ 宽松加载也失败: {e}")
            traceback.print_exc()
        
        # 3. 尝试原始解析
        print("\n4. 尝试查看文件内容...")
        try:
            with open(dbc_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                print(f"  文件总行数: {len(lines)}")
                
                # 查找包含错误消息的行
                error_messages = ['HVESSD15', 'CCVS6', 'HVESSMS3', 'HVESSMS2']
                for error_msg in error_messages:
                    for i, line in enumerate(lines[:1000]):  # 只检查前1000行
                        if error_msg in line:
                            print(f"  在第 {i+1} 行找到 '{error_msg}':")
                            print(f"    {line.strip()}")
                            # 显示上下文
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            for j in range(start, end):
                                prefix = ">>> " if j == i else "    "
                                print(f"{prefix}{lines[j].rstrip()}")
                            break
        
        except Exception as e:
            print(f"  文件读取失败: {e}")
            
    except Exception as e:
        print(f"分析过程失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    dbc_path = "dbc_files/j1939.dbc"
    if not os.path.exists(dbc_path):
        print(f"错误: DBC文件不存在: {dbc_path}")
        print("请将j1939.dbc文件放在 dbc_files/ 目录下")
    else:
        analyze_dbc_file(dbc_path)