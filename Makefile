# =============================================================================
# OSSAF Local Development Makefile
# 兼容BSD make（macOS默认）与GNU make
# 所有Python命令使用python3，所有路径使用相对路径
# =============================================================================

.PHONY: help setup mock-start mock-stop pipeline content serve dev health-check build pre-build-check test clean validate

# 默认target
.DEFAULT_GOAL := help

help: ## 显示所有可用target及其说明
	@echo "OSSAF Local Development - 可用命令："
	@echo ""
	@echo "  Target              Description"
	@echo "  ------              -----------"
	@awk -F':.*## ' '/^[a-zA-Z_-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' Makefile

setup: ## 安装项目依赖（创建虚拟环境+安装Python包+校验Hugo）
	@echo "[setup] 创建Python虚拟环境..."
	python3 -m venv .venv
	@echo "[setup] 升级pip并安装依赖..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "[setup] 校验Hugo版本..."
	hugo version
	@echo "[setup] ✅ 依赖安装完成"

mock-start: ## 启动FastAPI Mock服务器（端口8765）
	@echo "[mock-start] 启动Mock服务器..."
	@if [ -f .mock.pid ] && kill -0 $$(cat .mock.pid) 2>/dev/null; then \
		echo "[mock-start] Mock服务器已在运行，PID: $$(cat .mock.pid)"; \
	else \
		nohup .venv/bin/uvicorn mock_server.main:app --host 127.0.0.1 --port 8765 > mock_server.log 2>&1 & \
		echo $$! > .mock.pid; \
		sleep 2; \
		if kill -0 $$(cat .mock.pid) 2>/dev/null; then \
			echo "[mock-start] ✅ Mock服务器已启动，PID: $$(cat .mock.pid)"; \
			echo "[mock-start] 日志文件: mock_server.log"; \
			echo "[mock-start] 服务地址: http://127.0.0.1:8765"; \
		else \
			echo "[mock-start] ❌ 启动失败，请查看 mock_server.log"; \
			rm -f .mock.pid; \
			exit 1; \
		fi; \
	fi

mock-stop: ## 停止Mock服务器
	@echo "[mock-stop] 停止Mock服务器..."
	@if [ -f .mock.pid ]; then \
		PID=$$(cat .mock.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID 2>/dev/null || true; \
			sleep 1; \
			kill -9 $$PID 2>/dev/null || true; \
			echo "[mock-stop] ✅ 已停止Mock服务器，PID: $$PID"; \
		else \
			echo "[mock-stop] PID $$PID 进程不存在"; \
		fi; \
		rm -f .mock.pid; \
	else \
		echo "[mock-stop] 未找到 .mock.pid 文件，Mock服务器可能未运行"; \
	fi

pipeline: ## 运行完整内容生产管道
	@echo "[pipeline] 启动完整内容生产管道..."
	python3 scripts/run_pipeline.py --full
	@echo "[pipeline] ✅ 管道执行完成"

content: ## 仅生成内容（不构建Hugo站点）
	@echo "[content] 生成内容（不构建站点）..."
	python3 scripts/run_pipeline.py --content-only
	@echo "[content] ✅ 内容生成完成"

serve: ## 启动Hugo开发服务器（端口1313，绑定127.0.0.1）
	@echo "[serve] 启动Hugo开发服务器..."
	hugo server --bind 127.0.0.1 --port 1313 --environment development

dev: mock-start ## 并行启动Mock和Hugo（Mock后台运行，Hugo前台运行）
	@echo "[dev] 启动Hugo开发服务器..."
	@echo "[dev] Mock服务器已在后台运行，Hugo将前台运行"
	hugo server --bind 127.0.0.1 --port 1313 --environment development

health-check: ## 执行5项健康检查
	@echo "[health-check] 开始5项健康检查..."
	@echo ""
	@echo "[1/5] 检查Python环境..."
	@python3 --version || (echo "  ❌ Python3 未安装" && exit 1)
	@echo ""
	@echo "[2/5] 检查Hugo环境..."
	@hugo version || (echo "  ❌ Hugo 未安装" && exit 1)
	@echo ""
	@echo "[3/5] 检查Mock服务器连通性..."
	@if curl -s -o /dev/null -w "  HTTP状态码: %{http_code}\n" http://127.0.0.1:8765/health 2>/dev/null; then \
		: ; \
	else \
		echo "  ⚠️  Mock服务器未运行（可执行 make mock-start 启动）"; \
	fi
	@echo ""
	@echo "[4/5] 检查环境变量文件..."
	@if [ -f .env.local ]; then \
		echo "  ✅ .env.local 存在"; \
	else \
		echo "  ⚠️  .env.local 缺失（可从 .env.mock 复制）"; \
	fi
	@echo ""
	@echo "[5/5] 检查Python虚拟环境..."
	@if [ -d .venv ]; then \
		echo "  ✅ .venv 虚拟环境存在"; \
	else \
		echo "  ⚠️  .venv 缺失（请执行 make setup）"; \
	fi
	@echo ""
	@echo "[health-check] ✅ 健康检查完成"

build: pre-build-check ## 生产构建（依赖pre-build-check预检通过）
	@echo "[build] 开始生产构建..."
	hugo --environment production --minify
	@echo "[build] ✅ 构建完成，输出目录: public/"

pre-build-check: ## 构建前预检（环境/依赖/配置完整性）
	@echo "[pre-build-check] 执行构建前预检..."
	@test -f .env.local || (echo "  ❌ .env.local 缺失" && exit 1)
	@test -d .venv || (echo "  ❌ .venv 缺失，请执行 make setup" && exit 1)
	@hugo version >/dev/null 2>&1 || (echo "  ❌ Hugo 未安装" && exit 1)
	@.venv/bin/python -c "import fastapi, uvicorn, httpx" 2>/dev/null || (echo "  ❌ Python核心依赖未安装，请执行 make setup" && exit 1)
	@echo "  ✅ .env.local 存在"
	@echo "  ✅ .venv 虚拟环境存在"
	@echo "  ✅ Hugo 已安装"
	@echo "  ✅ Python核心依赖已安装"
	@echo "[pre-build-check] ✅ 预检通过"

test: ## 运行测试套件（pytest + 覆盖率）
	@echo "[test] 运行测试套件..."
	@if [ -d tests ]; then \
		.venv/bin/pytest tests/ -v --cov=. --cov-report=term-missing; \
		echo "[test] ✅ 测试完成"; \
	else \
		echo "[test] ⚠️  tests/ 目录不存在，跳过测试"; \
	fi

clean: ## 清理生成的内容和缓存
	@echo "[clean] 清理生成的内容和缓存..."
	rm -rf public/
	rm -rf resources/
	rm -f .hugo_build.lock
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "[clean] ✅ 清理完成"

validate: ## 运行项目校验（目录结构+资源清单+提示词规范）
	@echo "[validate] 运行项目校验..."
	@if [ -f scripts/validate_project.py ]; then \
		python3 scripts/validate_project.py .; \
		echo "[validate] ✅ 校验完成"; \
	else \
		echo "[validate] ⚠️  scripts/validate_project.py 不存在，跳过校验"; \
	fi
