# Reddit Crawler — 用户吐槽点挖掘工具

自动爬取 Reddit 用户吐槽内容，输出结构化原始数据到 PostgreSQL。

## 功能特性

- **AI 驱动发现**：输入自然语言需求，自动发现相关子版块和关键词
- **手动配置**：支持手动指定子版块/关键词
- **多国对比**：支持单国家/多国对比，国家参数可配置
- **完整数据采集**：帖子、评论、用户画像的完整原始数据
- **多平台扩展**：架构预留 X (Twitter)、Facebook 等平台适配器接口
- **断点续爬**：记录爬取进度，中断后可恢复
- **定时调度**：支持 Cron 定时任务

## 环境要求

- Python 3.12+
- PostgreSQL 14+
- 阿里云 DashScope API Key（用于 AI 发现）
- Reddit API 凭证（Client ID + Client Secret）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API 凭证和数据库信息：

```env
# ========== AI / LLM ==========
DASHSCOPE_API_KEY=sk-xxxxxxxx        # 阿里云 DashScope API Key
LLM_MODEL=qwen3.7-plus               # 模型名称
LLM_ENABLE_THINKING=true              # 启用思考模式

# ========== Reddit API ==========
REDDIT_CLIENT_ID=xxxxxxxx             # Reddit App Client ID
REDDIT_CLIENT_SECRET=xxxxxxxx         # Reddit App Client Secret
REDDIT_USER_AGENT=crawl_reddit/1.0    # 自定义 User-Agent

# ========== PostgreSQL ==========
DB_HOST=localhost
DB_PORT=5432
DB_NAME=reddit_research
DB_USER=postgres
DB_PASSWORD=xxxxxxxx

# ========== 默认爬取配置 ==========
DEFAULT_COUNTRY=us
DEFAULT_SUBREDDITS=r/SkincareAddiction,r/AskAnAmerican
DEFAULT_KEYWORDS=
DEFAULT_LOOKBACK_DAYS=30
MAX_POSTS_PER_SUBREDDIT=100
MAX_COMMENTS_PER_POST=200

# ========== 调度配置 ==========
SCHEDULE_ENABLED=false
SCHEDULE_CRON=0 8 * * 1
```

### 3. 初始化数据库

```bash
python -c "from config import load_config; from writer.db import init_db; import asyncio; asyncio.run(init_db(load_config()))"
```

### 4. 运行

```bash
# AI 自动发现 + 爬取
python main.py run --query "美国市场护肤品类用户吐槽痛点"

# 手动指定子版块
python main.py run --country us --subreddits r/SkincareAddiction,r/30PlusSkinCare

# 手动指定关键词
python main.py run --country us --keywords "broke me out,irritated,worst product"

# 多国对比
python main.py run --query "护发产品吐槽" --countries us,uk,ca

# 仅预览 AI 发现结果（不实际爬取）
python main.py discover --query "美国市场户外露营装备痛点"

# 查看任务历史
python main.py tasks list

# 查看指定任务详情
python main.py tasks status --task-id <task-uuid>

# 启动定时任务
python main.py scheduler start
```

## CLI 命令参考

| 命令 | 说明 |
|------|------|
| `python main.py run` | 执行完整爬取流程 |
| `python main.py discover` | AI 发现子版块和关键词（预览） |
| `python main.py tasks list` | 列出最近 20 个研究任务 |
| `python main.py tasks status --task-id <id>` | 查看任务详情和采集数据量 |
| `python main.py scheduler start` | 启动定时调度器 |
| `python main.py scheduler stop` | 停止定时调度器 |

### run 命令参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--query` | `-q` | 自然语言研究需求 |
| `--country` | `-c` | 目标国家代码 (us, uk, jp...) |
| `--subreddits` | `-s` | 逗号分隔的子版块列表 |
| `--keywords` | `-k` | 逗号分隔的关键词列表 |
| `--max-posts` | | 每个子版块最大帖子数 |
| `--max-comments` | | 每个帖子最大评论数 |

## 项目结构

```
crawl_reddit/
├── .env                          # 环境配置（不入库）
├── .env.example                  # 环境配置模板
├── config.py                     # 配置加载与验证
├── main.py                       # CLI 入口
│
├── discovery/                    # AI 发现模块
│   └── engine.py                 # DashScope Qwen 调用
│
├── crawler/                      # 采集层（适配器模式）
│   ├── base.py                   # 抽象基类
│   ├── coordinator.py            # 并发调度器
│   ├── reddit/                   # Reddit 适配器
│   │   └── api.py                # 官方 API + OAuth2
│   └── twitter/                  # X/Twitter 适配器（占位）
│
├── pipeline/                     # 数据处理
│   ├── models.py                 # 通用数据类型
│   ├── normalize.py              # 标准化转换
│   └── dedup.py                  # 去重逻辑
│
├── writer/                       # 数据写入
│   ├── db.py                     # 数据库模型与连接
│   └── batch.py                  # 批量写入
│
├── scheduler/                    # 调度模块
│   └── jobs.py                   # 定时任务定义
│
├── tests/                        # 测试
│   ├── conftest.py               # 共享 fixtures
│   ├── test_config.py
│   ├── test_crawler_base.py
│   ├── test_crawler_reddit.py
│   ├── test_coordinator.py
│   ├── test_discovery.py
│   ├── test_pipeline_models.py
│   ├── test_pipeline_normalize.py
│   ├── test_pipeline_dedup.py
│   ├── test_writer_db.py
│   ├── test_writer_batch.py
│   └── test_cli.py
│
├── data/                         # 本地数据
│   └── crawl.log                 # 爬取日志
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `platforms` | 平台注册表（reddit, twitter, facebook...） |
| `countries` | 国家代码表 |
| `research_tasks` | 研究任务记录，追踪每次爬取 |
| `posts` | 帖子数据（跨平台通用），按 (platform_id, post_id) 唯一 |
| `comments` | 评论数据（跨平台通用），按 (platform_id, comment_id) 唯一 |
| `user_profiles` | 用户画像，按 (platform_id, user_id) 唯一 |

所有表均保留 `raw_json` 字段存储平台原始数据，方便下游大模型回溯。

## 数据流

```
用户输入（自然语言 / 手动配置）
    │
    ▼
discovery/engine.py ──调用 DashScope Qwen──▶ {subreddits, keywords}
    │
    ▼
crawler/coordinator.py ──并发调度──▶ Reddit API
    │
    ▼
pipeline/ ──去重 + 标准化──▶ CommonPost / CommonComment
    │
    ▼
writer/ ──批量写入──▶ PostgreSQL
```

## 扩展新平台

1. 在 `crawler/<platform>/` 下新建适配器，实现 `BaseAdapter` 抽象接口
2. 在 `crawler/coordinator.py` 注册新平台路由
3. 如新平台字段差异大，在 `pipeline/normalize.py` 加转换函数

## 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行指定模块测试
pytest tests/test_crawler_reddit.py -v
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| AI | 阿里云 DashScope Qwen 3.7-plus |
| 爬虫 | aiohttp 异步并发 |
| 数据库 | PostgreSQL + asyncpg |
| ORM | SQLAlchemy 2.0 async |
| CLI | Click |
| 调度 | APScheduler |
| 配置 | python-dotenv |
| 测试 | pytest + pytest-asyncio + pytest-mock |
