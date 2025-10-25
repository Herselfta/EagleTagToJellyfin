# 贡献指南

感谢你考虑为 EagleTagToJellyfin 做出贡献！

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 检查 [Issues](https://github.com/Herselfta/EagleTagToJellyfin/issues) 确认问题尚未被报告
2. 创建新 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）
   - 相关日志（`v2/sync_v2.log`）

### 提出新功能

1. 先创建 Issue 讨论新功能的必要性和设计
2. 等待维护者反馈
3. 获得批准后再开始开发

### 提交代码

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 创建 Pull Request

### 代码规范

- 使用 Python 3.8+ 特性
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 确保代码可以通过基本测试

### Pull Request 检查清单

- [ ] 代码遵循项目的代码风格
- [ ] 已添加必要的注释
- [ ] 已更新相关文档
- [ ] 已测试更改是否正常工作
- [ ] 提交信息清晰明确

## 开发环境设置

```bash
# 克隆你的 fork
git clone https://github.com/YOUR_USERNAME/EagleTagToJellyfin.git
cd EagleTagToJellyfin

# 安装依赖
pip install -r v2/requirements.txt

# 配置
cp v2/config.json.example v2/config.json
# 编辑 config.json 填入你的配置

# 测试
python main.py sync --dry-run
```

## 提问

如有任何问题，欢迎在 Issues 中提问！

## 行为准则

请保持友善和尊重。我们致力于为每个人提供一个无骚扰的体验。

感谢你的贡献！ 🎉
