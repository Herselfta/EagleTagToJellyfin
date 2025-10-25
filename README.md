# Eagle to Jellyfin 标签同步工具

自动将 Eagle 图库管理工具中的标签同步到 Jellyfin 媒体服务器。

## 快速开始

### 1. 安装依赖

```powershell
cd v2
pip install -r requirements.txt
```

### 2. 配置

复制 `v2/config.json.example` 为 `v2/config.json` 并填入你的配置：

```json
{
  "eagle": {
    "library_path": "E:\\Medias.library"
  },
  "jellyfin": {
    "url": "http://localhost:8096",
    "api_key": "YOUR_API_KEY_HERE",
    "library_id": "YOUR_LIBRARY_ID_HERE"
  }
}
```

**获取 Jellyfin 配置信息：**
- **API Key**: Jellyfin 管理界面 → 设置 → API密钥
- **Library ID**: 浏览器访问媒体库，F12 查看网络请求中的 library ID

### 3. 运行同步

```powershell
# 测试运行（不实际修改）
python main.py sync --dry-run

# 正式同步
python main.py sync

# 查看详细日志
python main.py sync --log-level INFO
```

### 4. 设置自动同步（可选）

```powershell
# 以管理员身份运行 PowerShell
cd v2
.\setup_task.ps1
```

按提示选择执行频率和日志级别，脚本会自动创建 Windows 计划任务。

## 工作原理

### 正常同步（无标签删除）
1. 读取 Eagle 库中的媒体文件和标签
2. 更新 `movie.nfo` 文件，写入标签
3. 触发 Jellyfin 刷新元数据
4. 完成

### 标签删除同步（自动检测）
1. 检测到有标签被删除
2. **先**让 Jellyfin 执行"覆盖所有元数据"（重建 NFO）
3. 严格等待刷新完成（连续确认 + 验证 NFO）
4. **然后**写入新标签到 NFO（覆盖空 NFO）
5. 再次刷新让 Jellyfin 读取
6. ✅ 标签持久保存

**关键特性：**
- ✅ 完全自动化：自动检测标签增删改
- ✅ 智能刷新：根据变更类型选择最佳策略
- ✅ 持久保存：标签不会被后续操作抹掉
- ✅ 静默运行：计划任务无窗口弹出

## 文件说明

```
EagleToJellyfin/
├── main.py                    # 主入口
├── .gitignore                 # Git 忽略文件
└── v2/                        # V2 核心模块
    ├── config.json            # 配置文件（需自行创建）
    ├── config.json.example    # 配置示例
    ├── eagle_reader.py        # Eagle 库读取
    ├── jellyfin_client.py     # Jellyfin API 客户端
    ├── movie_nfo_updater.py   # NFO 文件更新
    ├── nfo_writer.py          # NFO 文件生成
    ├── sync_v2_simple.py      # 同步主程序
    ├── setup_task.ps1         # 计划任务设置脚本
    ├── requirements.txt       # Python 依赖
    └── README.md              # 详细文档
```

## 故障排除

### 标签未同步
- 检查 `v2/sync_v2.log` 日志文件
- 确认 config.json 配置正确
- 验证 Jellyfin 服务正常运行

### 计划任务不运行
- 检查任务计划程序中的任务状态
- 查看日志文件确认是否有错误
- 确保 Python 路径正确

### 标签删除后仍显示
- 查看日志中的验证信息
- 可能需要增加等待时间
- 手动在 Jellyfin 中执行"扫描媒体库"

## 版本历史

- **V2.2.1** (2025-10-25): 优化等待机制，添加 NFO 验证，静默运行
- **V2.2** (2025-10-25): 调整刷新顺序，解决标签持久化问题
- **V2.1** (2025-10-25): 自动检测标签删除，智能刷新
- **V2.0** (2025-10-24): 完全重构，模块化设计

## 许可证

仅供个人使用
