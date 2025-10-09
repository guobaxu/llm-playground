# 使用 uv 管理项目

本项目使用 `uv` 作为 Python 包管理工具，它比 pip 更快更可靠。

## 安装 uv

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 基本使用

### 1. 安装依赖

```bash
# 安装所有依赖（包括开发依赖）
uv sync

# 只安装生产依赖
uv sync --no-dev
```

### 2. 运行代码

```bash
# 运行 Python 脚本
uv run python script.py

# 运行包中的模块
uv run python -m llm_playground.examples.basic_usage

# 运行测试
uv run pytest tests/ -v
```

### 3. 开发工具

```bash
# 代码格式化
uv run black llm_playground/ tests/

# 代码检查
uv run flake8 llm_playground/ tests/

# 类型检查
uv run mypy llm_playground/

# 运行所有测试
uv run pytest tests/ -v
```

### 4. 使用开发脚本

```bash
# 开发环境设置
python scripts/dev.py setup

# 运行测试
python scripts/dev.py test

# 格式化代码
python scripts/dev.py format

# 代码检查
python scripts/dev.py lint

# 类型检查
python scripts/dev.py type-check

# 清理缓存
python scripts/dev.py clean
```

## 添加新依赖

```bash
# 添加生产依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 添加可选依赖组
uv add --optional dev package-name
```

## 更新依赖

```bash
# 更新所有依赖
uv sync --upgrade

# 更新特定包
uv add package-name@latest
```

## 虚拟环境

uv 自动管理虚拟环境，位于 `.venv/` 目录。

```bash
# 激活虚拟环境（如果需要）
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate    # Windows

# 查看已安装的包
uv tree

# 查看包信息
uv show package-name
```

## 项目结构

```
llm-playground/
├── llm_playground/          # 主包
├── tests/                   # 测试
├── scripts/                 # 开发脚本
├── .venv/                   # 虚拟环境 (uv 自动创建)
├── pyproject.toml          # 项目配置
├── uv.lock                 # 锁定文件 (uv 自动创建)
└── README.md
```

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `uv sync` | 安装/同步依赖 |
| `uv run python script.py` | 运行脚本 |
| `uv run pytest` | 运行测试 |
| `uv add package` | 添加依赖 |
| `uv remove package` | 移除依赖 |
| `uv tree` | 查看依赖树 |
| `uv show package` | 查看包信息 |

## 优势

- **速度快**: 比 pip 快 10-100 倍
- **可靠**: 更好的依赖解析
- **简单**: 统一的命令行界面
- **现代**: 支持最新的 Python 标准
