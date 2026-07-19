# OSSAF Local - 应急预案手册

> 本文档记录 OSSAF Local 项目常见故障的应急处理方案。遇到故障时按本手册逐项排查，无法解决时按"升级流程"上报。

---

## 故障 1：Mock 服务器启动失败

### 症状
- 执行 `make mock-start` 后立即退出
- `mock_server.log` 显示错误堆栈
- `curl http://127.0.0.1:8765/health` 无响应

### 排查步骤

1. **查看日志**
   ```bash
   cat mock_server.log
   ```

2. **检查端口占用**
   ```bash
   lsof -i :8765
   # 若被占用，执行 make mock-stop 或 kill <PID>
   ```

3. **校验虚拟环境与依赖**
   ```bash
   ls -la .venv/bin/uvicorn
   .venv/bin/python -c "import fastapi, uvicorn"
   # 失败则重新执行：make setup
   ```

4. **校验 mock_server 模块**
   ```bash
   .venv/bin/python -c "from mock_server import app; print(app)"
   # 若 ImportError，检查 mock_server.py 是否存在
   ```

5. **手动启动以观察实时输出**
   ```bash
   .venv/bin/uvicorn mock_server:app --host 127.0.0.1 --port 8765
   ```

### 应急方案

- **临时绕过**：使用 `.env.mock` 中的 Mock 凭证直接调用 Mock 响应逻辑，跳过 HTTP 服务
- **降级运行**：若仅 Mock 服务器故障，可继续执行 Hugo 构建（`make build`），内容生产管道延后

---

## 故障 2：Hugo 构建失败

### 症状
- 执行 `make build` 退出码非零
- 报错 `Error: ...` 来自 Hugo
- `public/` 目录未生成或内容不完整

### 排查步骤

1. **查看完整错误**
   ```bash
   hugo --environment production 2>&1 | tee build_error.log
   ```

2. **校验 Hugo 版本**
   ```bash
   hugo version
   # 要求 ≥ 0.121.1，不符则使用 asdf install
   ```

3. **校验配置文件语法**
   ```bash
   hugo config --environment production
   # 检查 YAML/TOML 语法错误
   ```

4. **清理缓存后重建**
   ```bash
   make clean
   hugo --environment production --minify --gc
   ```

5. **检查模板引用**
   ```bash
   hugo --templateMetrics --templateMetricsHints
   # 排查模板路径错误
   ```

### 应急方案

- **临时绕过**：使用 `hugo --environment development` 降级构建（不压缩、不启用生产优化）
- **回滚**：若构建配置最近改动，`git diff hugo.toml` 排查变更点，必要时回滚
- **降级发布**：使用上一次成功构建的 `public/` 产物临时上线

---

## 故障 3：Schema 校验失败

### 症状
- `make validate` 或 `make pipeline` 报错 `SchemaValidationError`
- 内容文件字段缺失或类型不符
- 资源清单.json 格式错误

### 排查步骤

1. **定位失败字段**
   ```bash
   python3 scripts/validate_project.py . --verbose
   # 查看具体哪个文件、哪个字段校验失败
   ```

2. **校验 JSON 格式**
   ```bash
   python3 -m json.tool 资源清单.json > /dev/null
   # 若报错，使用 jq 或编辑器修复 JSON 语法
   ```

3. **对比 Schema 定义**
   ```bash
   # 查看期望的 Schema
   cat schemas/content_schema.json
   # 对比实际内容文件，补齐缺失字段
   ```

4. **逐文件排查**
   ```bash
   for f in content/*/index.md; do
     echo "=== $f ==="
     python3 scripts/validate_single.py "$f"
   done
   ```

### 应急方案

- **跳过校验**：仅在紧急情况下使用 `python3 scripts/run_pipeline.py --skip-validate`（需事后补校验）
- **回滚内容**：若内容最近修改导致校验失败，`git diff` 排查并回滚
- **降级发布**：仅发布校验通过的部分内容，跳过失败项

---

## 故障 4：端口冲突

### 症状
- `make mock-start` 报错 `Address already in use`
- `make serve` 报错 `bind: address already in use`
- Hugo 或 Mock 服务器无法启动

### 排查步骤

1. **定位占用进程**
   ```bash
   # 检查 8765 端口（Mock）
   lsof -i :8765
   ps -p $(lsof -ti :8765) -o pid,command

   # 检查 1313 端口（Hugo）
   lsof -i :1313
   ps -p $(lsof -ti :1313) -o pid,command
   ```

2. **判断进程归属**
   - 若为 OSSAF 自身进程（uvicorn/hugo）：执行 `make mock-stop` 或 `kill <PID>`
   - 若为其他应用进程：选择切换端口或停止其他应用

3. **切换端口（临时）**
   ```bash
   # Mock 切换至 8766
   .venv/bin/uvicorn mock_server:app --host 127.0.0.1 --port 8766
   # 同步修改 .env.local: OSSAF_API_BASE_URL=http://127.0.0.1:8766

   # Hugo 切换至 1314
   hugo server --bind 127.0.0.1 --port 1314
   ```

### 应急方案

- **强制清理**：`kill -9 $(lsof -ti :8765)` 强制终止占用进程（谨慎使用，可能丢失未保存数据）
- **改用其他端口**：按上述步骤切换端口，并更新 `.env.local` 配置

---

## 故障 5：凭证缺失

### 症状
- API 调用返回 `401 Unauthorized`
- 环境变量为空或为占位符值
- `make health-check` 报告凭证问题

### 排查步骤

1. **检查环境变量加载**
   ```bash
   # 进入项目目录后检查
   cd /path/to/ossaf-local
   echo $ANTHROPIC_API_KEY
   # 若为空，检查 direnv 是否启用：direnv status
   ```

2. **校验 .env.local 文件**
   ```bash
   test -f .env.local && echo "存在" || echo "缺失"
   grep -E "^(ANTHROPIC|OPENAI|GOOGLE|GITHUB|ALTERNATIVETO)_API_KEY=" .env.local
   ```

3. **识别占位符**
   ```bash
   # 检查是否仍为占位符或 Mock 凭证
   grep -E "SK-PLACEHOLDER" .env.local && echo "⚠️ 仍为占位符"
   grep -E "SK-MOCK" .env.local && echo "⚠️ 仍为 Mock 凭证（真实调用将失败）"
   ```

4. **校验 direnv 授权**
   ```bash
   direnv allow
   # 修改 .envrc 后必须重新授权
   ```

### 应急方案

- **降级至 Mock 模式**：确保 `.env.local` 中 `OSSAF_AI_BACKEND=mock`，使用 Mock 凭证继续开发
- **复制 Mock 配置**：
  ```bash
  cp .env.mock .env.local
  direnv allow
  ```
- **临时硬编码**：仅在本机终端 `export ANTHROPIC_API_KEY=sk-...`（不入仓，重启终端失效）
- **申请密钥**：从各服务控制台申请真实密钥，写入 `.env.local`

---

## 升级流程

当本手册无法解决问题时，按以下顺序升级：

1. **自查日志**：完整收集 `mock_server.log`、`build_error.log`、终端输出
2. **团队求助**：在内部群组描述症状 + 复现步骤 + 已尝试的排查步骤
3. **维护者介入**：联系项目维护者，提供 `make health-check` 输出与相关日志
4. **外部支持**：若为第三方依赖故障，提交 Issue 至上游仓库

---

## 文档维护

- 本文档版本：v1.0
- 最后更新：2026-07-19
- 维护者：OSSAF 维护团队
- 审阅周期：每次重大故障后追加新预案，每季度审阅一次
