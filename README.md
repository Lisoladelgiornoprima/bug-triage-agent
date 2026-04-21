# Bug Triage Agent

自动化 GitHub Issue 分析和 Bug Triage 的 Multi-Agent 系统。

## 项目简介

Bug Triage Agent 是一个基于 Claude AI 的自动化工具，能够：
- 📊 分析 GitHub Issue，提取结构化 bug 信息
- 🔍 定位相关代码文件（开发中）
- 🧪 自动复现 bug（开发中）
- 💡 生成修复建议（开发中）

## 技术架构

```
Multi-Agent 协作系统
├── Issue Analyzer Agent    # 分析 issue 描述
├── Code Locator Agent      # 定位相关代码（开发中）
├── Bug Reproducer Agent    # 复现 bug（开发中）
└── Fix Generator Agent     # 生成修复方案（开发中）
```

**技术栈**：
- LLM: Anthropic Claude Sonnet 4
- GitHub API: PyGithub
- CLI: Click + Rich
- 架构: 自实现 Multi-Agent 编排（不依赖 LangChain）

## 快速开始

### 1. 环境配置

```bash
# 克隆项目
cd D:\agentproject

# 激活虚拟环境（已创建）
source venv/Scripts/activate

# 配置 API Keys
cp .env.example .env
# 编辑 .env 文件，填入你的 API keys
```

### 2. 获取 API Keys

**Anthropic API Key**（已有）
- 访问 https://console.anthropic.com/

**GitHub Personal Access Token**（需要创建）
1. 访问 https://github.com/settings/tokens/new
2. 勾选权限：`repo`（完整仓库访问）
3. 生成 token 并保存到 .env 文件

### 3. 运行示例

```bash
# 分析一个 GitHub issue
python -m src.main analyze https://github.com/psf/requests/issues/6234
```

## 当前进度

✅ **Phase 1 完成**（第 1-2 周）
- [x] 项目结构初始化
- [x] Agent 基类和 agentic loop
- [x] GitHub API 工具
- [x] Issue Analyzer Agent
- [x] Coordinator 编排器
- [x] CLI 入口

🚧 **Phase 2 开发中**（第 3-5 周）
- [ ] Code Locator Agent
- [ ] Bug Reproducer Agent
- [ ] 状态持久化

📋 **Phase 3 计划**（第 6-8 周）
- [ ] Fix Generator Agent
- [ ] Prompt Caching 优化
- [ ] 完整文档和演示

## 项目结构

```
D:\agentproject\
├── src/
│   ├── main.py              # CLI 入口
│   ├── config.py            # 配置管理
│   ├── core/
│   │   ├── agent_base.py    # Agent 基类
│   │   ├── coordinator.py   # 多 Agent 协调器
│   │   └── state.py         # 状态管理
│   ├── agents/
│   │   └── issue_analyzer.py  # Issue 分析 Agent
│   └── tools/
│       └── github_client.py   # GitHub API 封装
├── tests/                   # 测试（待完善）
├── requirements.txt
└── README.md
```

## 开发日志

**2026-04-20**
- ✅ 完成项目初始化
- ✅ 实现 Agent 基类和 agentic loop
- ✅ 实现 Issue Analyzer Agent
- ✅ CLI 可运行

## 下一步

1. 创建 GitHub Personal Access Token
2. 测试 Issue Analyzer 功能
3. 开始实现 Code Locator Agent

## License

MIT
