import cantools
db = cantools.database.load_file('j1939.dbc', strict=False)
print(f"严格模式关闭: {len(db.messages)} 消息")
for msg in db.messages:
    print(f"{msg.name}: {len(msg.signals)} 信号")