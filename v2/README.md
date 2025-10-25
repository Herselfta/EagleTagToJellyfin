# Eagle到Jellyfin标签同步工具 - 详细文档

> 这是 v2 模块的详细技术文档。用户指南请查看 [根目录 README](../README.md)。

## 功能特点

- ✅ 简洁的代码结构，易于维护
- ✅ 正确实现Jellyfin的元数据刷新流程
- ✅ 完整的日志记录
- ✅ 支持模拟运行（dry-run）
- ✅ 详细的进度显示
- ✅ **标签变更检测** - 自动识别标签的增加、删除和修改
- ✅ **智能刷新顺序** - 有标签删除时，先让Jellyfin重建NFO，再写入标签，避免标签丢失
- ✅ **增量更新** - 只更新有变化的文件，提高同步效率

## 工作流程（默认推荐）

**无标签删除时：**
1. 读取Eagle库，获取媒体文件与标签
2. 检测标签变更（对比Eagle当前标签与movie.nfo中的标签）
3. 直接更新或创建每个条目的 `movie.nfo`，写入 `<tag>` 元素
4. 调用 Jellyfin API 刷新（搜索缺少的元数据）
5. 标签在Jellyfin中生效

**有标签删除时（关键）：**
1. 读取Eagle库，检测到有标签被删除
2. **先**让Jellyfin执行"覆盖所有元数据"（会重建NFO，清空标签）
3. **严格等待**：连续确认任务队列空闲 + 额外等待5秒 + 验证样本NFO已重建
4. **然后**写入标签到movie.nfo（覆盖Jellyfin刚重建的空NFO）
5. 最后再刷新一次，让Jellyfin读取我们写入的标签
6. ✅ 标签持久保存，不会在后续被抹掉

## 配置说明

编辑 `config.json` 文件：

```json
{
  "eagle": {
    "library_path": "E:\\Medias.library"  // Eagle库路径
  },
  "jellyfin": {
    "url": "http://localhost:8096",      // Jellyfin服务器地址
    "api_key": "your-api-key-here",      // API密钥
    "library_id": "your-library-id"      // 媒体库ID
  }
}
```

### 如何获取Jellyfin配置信息

1. **API Key**: Jellyfin管理界面 → 设置 → API密钥
2. **Library ID**: 浏览器F12控制台，进入媒体库，URL中包含library ID

## 使用方法

### 基本使用

```powershell
# 推荐：自动同步（自动检测标签增加/删除/修改，并逐项刷新）
python sync_v2_simple.py

# 模拟运行（不实际修改文件，不调用Jellyfin）
python sync_v2_simple.py --dry-run

# 显示详细调试信息
python sync_v2_simple.py --log-level DEBUG
```

**重要提示**：
- 本版本通过"先刷新后写入"的顺序 + 严格等待机制解决标签持久化问题
- 有标签删除时会触发两次全库刷新，预刷新后会额外等待5秒确保NFO稳定
- 如果首次同步后标签未出现，查看日志中的验证信息，可能需要增加等待时间
- 无标签删除时只需一次标准刷新，速度快

### 通过主入口使用

推荐通过主入口 `main.py` 使用（位于上级目录）：

```powershell
# 从根目录运行
cd ..
python main.py sync                  # 自动同步（逐项刷新）
python main.py sync --dry-run        # 模拟运行
```

### 设置计划任务

使用提供的PowerShell脚本创建自动同步任务：

```powershell
# 创建每天自动同步的计划任务
.\setup_task.ps1
```

## 文件说明

- `sync_v2_simple.py` - 主程序（推荐：直接更新 movie.nfo）
- `config.json` - 配置文件
- `eagle_reader.py` - Eagle库读取模块
- `movie_nfo_updater.py` - 直接更新/创建 movie.nfo 的模块
- `nfo_writer.py` - NFO文件写入模块（提供基础NFO生成）
- `jellyfin_client.py` - Jellyfin API客户端
- `sync_v2.log` - 同步日志
- `setup_task.ps1` - 计划任务设置脚本

## 依赖安装

```powershell
pip install -r requirements.txt
```

## 故障排除

### 问题1: 标签删除后在Jellyfin中仍然显示

**原因**: 可能是刷新未完成或检测逻辑出错

**解决方法**: 
- 查看日志，确认是否执行了"预刷新"步骤
- 手动在Jellyfin中对该媒体库执行"覆盖所有元数据"
- 然后重新运行同步脚本

### 问题2: 标签未同步

- 检查movie.nfo文件是否正确生成/更新
- 确认Jellyfin已成功刷新（查看日志中的"等待刷新完成"）
- 查看 `sync_v2.log` 日志文件
- 尝试使用 `--clear-cache` 强制重新读取

### 问题3: 无法连接Jellyfin

- 确认Jellyfin服务正在运行
- 检查URL和API Key是否正确
- 确认防火墙设置

### 问题4: 找不到媒体文件

- 确认Eagle库路径是否正确
- 检查Eagle库结构是否完整（应包含 `images/*.info/` 文件夹）
- 查看日志中的详细错误信息

### 问题5: 为什么标签删除要刷新两次？

- 第一次刷新（ReplaceAllMetadata）让Jellyfin重建所有NFO，清除旧数据
- 然后我们写入新标签到NFO
- 第二次刷新让Jellyfin读取我们写入的标签
- 这样确保标签不会在后续被Jellyfin自动重建NFO时抹掉

## 详细测试指南

请查看 `../TESTING.md` 文件获取完整的测试场景和验证方法。

## 版本历史

### V2.2.1 (2025-10-25)
- 🔧 关键修复：改进等待逻辑，连续确认队列空闲 + 额外等待5秒
- 🔧 新增验证步骤：检查样本NFO确认重建完成
- 🔧 优化等待时间：预刷新额外等待5秒，最终刷新额外等待3秒
- 📝 详细日志输出等待和验证过程

### V2.2 (2025-10-25)
- 🎉 关键修复：调整刷新顺序，先让Jellyfin重建NFO，再写入标签
- 🎉 彻底解决"标签后续被抹掉"的问题
- 📝 改进：自动检测标签删除，智能选择刷新策略

### V2.1 (2025-10-25)
- 🎉 新增：标签变更检测（自动识别增加、删除、修改）
- 🎉 新增：Jellyfin元数据缓存清除功能（支持标签删除同步）
- 🎉 新增：增量更新（只处理有变化的文件）
- 📝 改进：更详细的变更日志记录
- 📝 改进：返回值包含变更统计

### V2 (2025-10-24)
- 完全重构代码
- 简化项目结构
- 修复标签同步问题
- 正确实现Jellyfin API调用流程
- 添加详细的日志和错误处理

## 许可证

仅供个人使用
