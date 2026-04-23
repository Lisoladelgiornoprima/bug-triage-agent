# Bug Triage Agent

自动化 GitHub Issue 分析和 Bug Triage 的 Multi-Agent 系统。

## 项目简介

Bug Triage Agent 是一个基于 Claude AI 的自动化工具，能够：
- 📊 **Phase 1**: 分析 GitHub Issue，提取结构化 bug 信息
- 🔍 **Phase 2**: 定位相关代码文件（多策略：堆栈跟踪、关键词、AST 分析）
- 🧪 **Phase 3**: 自动生成并执行复现测试代码
- 💡 **Phase 4**: 根因分析 + 生成修复建议（diff 格式）

## 技术架构

### Multi-Agent 协作系统

```
┌─────────────────┐
│ Issue Analyzer  │ → 分析 issue 描述，提取结构化信息
└────────┬────────┘
         ↓
┌─────────────────┐
│  Code Locator   │ → 多策略定位相关代码（5 个工具）
└────────┬────────┘
         ↓
┌─────────────────┐
│ Bug Reproducer  │ → 生成并执行复现测试
└────────┬────────┘
         ↓
┌─────────────────┐
│ Fix Generator   │ → 根因分析 + 修复建议
└─────────────────┘
```

**技术栈**：
- **LLM**: Anthropic Claude Sonnet 4.6（支持 tool use + prompt caching）
- **GitHub API**: PyGithub
- **代码分析**: Python AST + JavaScript/TypeScript 正则解析
- **支持语言**: Python, JavaScript, TypeScript, JSX, TSX
- **CLI**: Click + Rich（实时进度展示）
- **架构**: 自实现 Multi-Agent 编排（不依赖 LangChain）

## 快速开始

### 1. 环境配置

```bash
# 进入项目目录
cd D:\agentproject

# 激活虚拟环境
source venv/Scripts/activate

# 配置 API Keys
cp .env.example .env
# 编辑 .env 文件，填入你的 API keys
```

### 2. 获取 API Keys

**Anthropic API Key**
- 访问 https://console.anthropic.com/

**GitHub Personal Access Token**
1. 访问 https://github.com/settings/tokens/new
2. 勾选权限：`repo`（完整仓库访问）
3. 生成 token 并保存到 .env 文件

### 3. 运行示例

**Phase 1 only（仅分析 issue）**：
```bash
python -m src.main analyze https://github.com/psf/requests/issues/6655
```

**完整 Pipeline（分析 + 定位 + 复现 + 修复建议）**：
```bash
# 先 clone 目标仓库
git clone https://github.com/psf/requests.git test_repos/requests

# 运行完整 triage
python -m src.main triage https://github.com/psf/requests/issues/6655 --repo test_repos/requests
```

## 项目结构

```
D:\agentproject\
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置管理
│   ├── core/
│   │   ├── agent_base.py          # Agent 基类 + agentic loop
│   │   ├── coordinator.py         # 4-agent 协调器
│   │   └── state.py               # 状态管理
│   ├── agents/
│   │   ├── issue_analyzer.py      # Phase 1: Issue 分析
│   │   ├── code_locator.py        # Phase 2: 代码定位
│   │   ├── bug_reproducer.py      # Phase 3: Bug 复现
│   │   └── fix_generator.py       # Phase 4: 修复建议
│   └── tools/
│       ├── github_client.py       # GitHub API 封装
│       ├── file_system.py         # 文件搜索/读取/grep
│       ├── code_analyzer.py       # 多语言代码分析（Python AST）
│       ├── code_analyzer_js.py    # JavaScript/TypeScript 分析
│       └── test_runner.py         # 测试执行
├── tests/                         # 37 个单元测试
├── requirements.txt
└── README.md
```

## 演示案例

### 案例：psf/requests#6655（TLS 连接池复用 bug）

**Phase 1 输出**：
```
bug_type: logic_error
severity: critical
affected_components: ["connection pool", "TLS verification", "connection reuse logic"]
```

**Phase 2 输出**：
```
relevant_files: [
  {
    "path": "src/requests/adapters.py",
    "confidence": 0.95,
    "reason": "Contains _urllib3_request_context and connection pool logic"
  }
]
```

**Phase 3 输出**：
```
reproduced: true
output: "BUG CONFIRMED: verify=True does not set ssl_context in pool_kwargs"
```

**Phase 4 输出**：
```
root_cause: "verify=True 不设置 ssl_context，导致 urllib3 无法区分不同 TLS 配置的连接池"
fix_description: "在 _urllib3_request_context 中为 verify=True 创建并注入 ssl.SSLContext"
```

## 技术亮点

1. **Multi-Agent 架构** — 4 个专业 Agent 协作，每个 Agent 有独立工具集
2. **Agentic Loop** — Agent 自主决定调用哪些工具，多轮推理直到完成任务
3. **Tool Use** — 10+ 工具（GitHub API、文件系统、AST 分析、测试执行）
4. **Prompt Caching** — 自动缓存 system prompt，降低成本和延迟
5. **降级容错** — 每个 Phase 失败不阻塞后续（除 Phase 1）
6. **工程质量** — 类型注解、日志、错误处理、模块化设计

## 开发日志

**2026-04-21**
- ✅ Phase 1: Issue Analyzer（2 工具）
- ✅ Phase 2: Code Locator（5 工具）+ Bug Reproducer（3 工具）
- ✅ Phase 3: Fix Generator（3 工具）+ Prompt Caching
- ✅ 端到端测试通过（psf/requests#6655）

## 下一步

- [ ] 添加单元测试覆盖
- [ ] 支持更多语言（JavaScript、Go、Rust）
- [ ] PR 自动创建功能
- [ ] Web UI 界面

## License

MIT
