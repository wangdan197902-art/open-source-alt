# OSSAF Local - 开源软件替代品查找器

OSSAF (Open Source Alternative Finder) 的本地开发环境，集成 Mock API 服务器、Hugo 静态站点、内容生产管道与端到端测试套件。

## 快速开始

### 1. 环境准备
```bash
cd ossaf-local
make setup
```

### 2. 启动开发环境
```bash
make dev
```

### 3. 访问网站
- Hugo站点: http://127.0.0.1:1313/
- Mock服务器: http://127.0.0.1:8765/health

### 4. 运行测试
```bash
make test
```

## 主要命令

| 命令 | 说明 |
|------|------|
| make help | 显示所有命令 |
| make setup | 安装依赖 |
| make mock-start | 启动Mock服务器 |
| make mock-stop | 停止Mock服务器 |
| make serve | 启动Hugo服务器 |
| make dev | 并行启动Mock和Hugo |
| make pipeline | 运行内容生产管道 |
| make build | 生产构建 |
| make test | 运行测试 |
| make health-check | 健康检查 |
| make clean | 清理生成的内容 |
| make pre-build-check | 构建前预检（reviewStatus 校验） |
| make validate | 运行项目校验 |

## 项目结构

```
ossaf-local/
├── .env.example          # 凭证模板
├── .env.mock             # Mock凭证
├── .env.local            # 本机凭证（gitignore）
├── .envrc                # direnv配置
├── .gitignore
├── .tool-versions        # 版本管理
├── Makefile              # 14个target
├── requirements.txt      # Python依赖
├── SECURITY.md           # 安全规范
├── CONTINGENCY_PLANS.md  # 应急预案
├── hugo.toml             # Hugo配置
├── schemas/              # 5份JSON Schema SSOT
├── adapters/             # AIClient适配器
├── pipeline/             # 6个生产脚本
├── mock_server/          # FastAPI Mock服务器
├── data/                 # 种子数据（46个JSON文件）
├── content/              # Hugo内容（25个页面×5语种）
├── layouts/              # Hugo模板
├── static/               # 静态资源
└── tests/                # 测试套件
```

## 多语言支持

支持5种语言：
- English (en)
- 中文 (zh)
- 日本語 (ja)
- 한국어 (ko)
- Español (es)

## 商业软件与开源替代

| 商业软件 | 开源替代 | 分类 |
|---------|---------|------|
| Adobe Photoshop | GIMP | 图像编辑 |
| Notion | Obsidian | 笔记软件 |
| Figma | Penpot | 设计协作 |
| Slack | Element | 团队通讯 |
| Zoom | BigBlueButton | 视频会议 |

## 测试套件

测试文件位于 `tests/` 目录下，共 9 个测试文件：

| 测试文件 | 测试范围 |
|---------|---------|
| `test_environment.py` | Python/Hugo/依赖/项目文件存在性 |
| `test_schemas.py` | 5 份 JSON Schema 与 Pydantic 模型一致性 |
| `test_mock_server.py` | Mock 服务器模块与 5 个 API Mock 端点格式 |
| `test_seed_data.py` | 5 类种子数据完整性、reviewStatus 与规模 |
| `test_pipeline.py` | AIClient 三层凭证降级 + pre_build_check 阻断 |
| `test_hugo_site.py` | Hugo 配置/模板/内容结构完整性 |
| `test_integration.py` | Hugo 服务器端到端实盘连通性 |

运行测试：
```bash
# 完整测试套件（需先启动 make dev）
make test

# 仅运行不依赖服务的测试
python3 -m pytest tests/test_environment.py tests/test_schemas.py tests/test_seed_data.py -v

# 详细输出 + 短错误回溯
python3 -m pytest tests/ -v --tb=short
```

## AI API 适配

`adapters/ai_client.py` 提供统一的 AIClient，支持三种 provider：
- **Claude** (Anthropic) - `content[].text` 一级嵌套
- **OpenAI** (GPT-4o) - `choices[].message.content` 二级嵌套
- **Gemini** (Google) - `candidates[].content.parts[].text` 三级嵌套

通过 `OSSAF_API_BASE_URL` 环境变量切换 Mock / Real 后端。三层凭证降级：
1. 构造函数 `api_key` 参数
2. 环境变量（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY`）
3. Mock 占位符 `SK-MOCK-{PROVIDER}-DEV-001`

## 内容生产管道

`pipeline/` 目录下 6 个脚本按序执行：

| 步骤 | 脚本 | 功能 |
|------|------|------|
| 1 | `collect_proprietary.py` | 采集商业软件数据（MVP 硬上限） |
| 2 | `generate_comparison.py` | 生成商业 vs 开源对比内容 |
| 3 | `translate_content.py` | 多语言翻译（5 语种） |
| 4 | `generate_image_meta.py` | 生成配图元数据 |
| 5 | `review_content.py` | 内容审核（标记 reviewStatus） |
| 6 | `pre_build_check.py` | Hugo 构建前预检（阻断非 approved） |

## 安全与合规

- 详见 `SECURITY.md`：API 密钥管理、CORS 白名单、AI 内容披露
- 详见 `CONTINGENCY_PLANS.md`：Mock 故障、Hugo 构建失败、配额耗尽等应急预案
- 所有 AI 生成内容必须标记 `aiGenerated: true` 并通过 `reviewStatus: approved` 人工审核方可发布
