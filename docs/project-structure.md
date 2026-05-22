# 项目骨架说明

版本：v0.1  
状态：后端基础依赖文件已初始化，业务代码仍待创建。

## 1. 总体结构

```text
Price Compare Platform/
  docs/
  backend/
  frontend/
  mock_data/
  scripts/
  docker/
```

## 2. docs

```text
docs/
  api.md
  database.md
  agent-workflow.md
  project-structure.md
```

说明：

```text
api.md              接口合同
database.md         数据库设计
agent-workflow.md   智能体流程设计
project-structure.md 项目目录规划
```

## 3. backend

```text
backend/
  .python-version
  requirements.txt
  requirements-dev.txt
  README.md
  app/
    main.py
    api/
      routes_compare.py
      routes_health.py
    schemas/
      compare.py
    core/
    agents/
    tools/
      product_match.py
      product_parse.py
    adapters/
    services/
      compare_service.py
    repositories/
    db/
    models/
    workers/
  tests/
  migrations/
```

说明：

```text
requirements.txt     FastAPI 后端运行依赖
requirements-dev.txt 本地开发和测试依赖
README.md            Python 版本与依赖安装说明
main.py              FastAPI 应用入口
api/           FastAPI 路由
routes_compare.py    商品比价 Mock 接口
routes_health.py     健康检查接口
schemas/       请求和响应模型
compare.py           商品比价请求模型
core/          配置、日志、异常处理
agents/        LangGraph 智能体流程
tools/         商品解析、同款匹配、风险分析、RAG 检索等工具
product_match.py     商品同款匹配工具
product_parse.py     商品名称解析工具
adapters/      京东、淘宝、拼多多、Mock 平台适配器
services/      业务编排层
compare_service.py   商品比价 Mock 业务服务
repositories/  数据库访问层
db/            数据库连接和基础配置
models/        SQLAlchemy 数据模型
workers/       降价提醒等后台任务
tests/         后端测试
migrations/    数据库迁移
```

## 4. frontend

```text
frontend/
  app/
  components/
  lib/
  public/
```

说明：

```text
app/         Next.js App Router 页面
components/ 业务组件，例如商品卡片、风险标签、问答面板
lib/         API 请求封装、类型定义、工具函数
public/      静态资源
```

## 5. mock_data

```text
mock_data/
  platform_products/
    compare_mock.json
  knowledge/
```

说明：

```text
platform_products/ 第一阶段 Mock 三平台商品数据
compare_mock.json   商品比价接口当前使用的固定 Mock 数据
knowledge/         RAG 选购知识库原始文档
```

## 6. scripts

```text
scripts/
  seed_mock_data
  index_knowledge
  check_services
```

说明：

```text
seed_mock_data    导入 Mock 商品数据
index_knowledge   切分并索引知识库文档
check_services    检查 PostgreSQL、Redis、Qdrant 等服务状态
```

## 7. docker

```text
docker/
  backend/
  frontend/
  nginx/
```

说明：

```text
backend/   后端容器配置
frontend/  前端容器配置
nginx/     后续上线反向代理配置
```

## 8. 建议推进顺序

```text
1. 先确认这份目录结构
2. 再创建空目录
3. 再写后端最小 FastAPI 入口
4. 再写第一个 /health 接口
5. 再逐步实现 /compare、/chat、/recommend
```
