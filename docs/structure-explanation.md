# 项目目录结构解释

这份文档解释当前项目为什么按这样的目录创建。目标不是一开始就做复杂工程，而是让后续开发能一步一步推进，每个文件该放哪里都比较清楚。

## 1. 总体目录

```text
Price Compare Platform/
  docs/
  backend/
  frontend/
  mock_data/
  scripts/
  docker/
```

这样拆分是因为这个项目不是单一网页，而是一个完整的 AI 应用：

```text
前端负责交互页面
后端负责接口和业务逻辑
智能体负责比价、推荐、问答流程
数据库和向量库负责数据存储
Mock 数据负责第一阶段开发
Docker 负责后续部署
```

## 2. docs

```text
docs/
  api.md
  database.md
  agent-workflow.md
  project-structure.md
  structure-explanation.md
```

`docs` 是项目的设计中心。

现在先写文档，是为了避免后面边写代码边改方向。这个项目涉及前端、后端、数据库、RAG、Agent、平台 API，如果没有文档先对齐，很容易写到一半发现接口、表结构和智能体流程对不上。

每份文档的作用：

```text
api.md                 前后端接口怎么约定
database.md            数据库表怎么设计
agent-workflow.md      智能体流程怎么跑
project-structure.md   目录应该怎么放
structure-explanation.md 为什么这样放
```

## 3. backend

```text
backend/
  app/
    api/
    schemas/
    core/
    agents/
    tools/
    adapters/
    services/
    repositories/
    db/
    models/
    workers/
  tests/
  migrations/
```

`backend` 是 FastAPI 后端目录。

后端不只是写几个接口，它还要负责：

```text
1. 接收前端请求
2. 调用智能体流程
3. 查询 Mock 或真实平台数据
4. 做同款匹配和风险分析
5. 调用 RAG 知识库
6. 读写 PostgreSQL
7. 使用 Redis 做缓存
8. 后续处理降价提醒任务
```

所以后端需要分层。

## 4. backend/app/api

```text
backend/app/api/
```

这里放 FastAPI 路由。

例如后续会有：

```text
routes_compare.py
routes_recommend.py
routes_chat.py
routes_health.py
```

这样设计是为了让接口入口清晰：

```text
/api/v1/compare    商品比价
/api/v1/recommend  商品推荐
/api/v1/chat       RAG 问答
/api/v1/health     健康检查
```

`api` 层只负责接请求和返回响应，不应该写太多业务逻辑。

## 5. backend/app/schemas（数据模型目录）

```text
backend/app/schemas/
```

这里放请求和响应的数据结构。

比如：

```text
CompareRequest
RecommendRequest
ChatRequest
CompareResponse
```

这样做的原因是接口需要稳定。前端传什么字段、后端返回什么字段，都应该由 schema 管起来，不要散落在各个函数里。

## 6. backend/app/core

```text
backend/app/core/
```

这里放全局基础能力，例如：

```text
配置读取
日志
错误处理
安全设置
跨域设置
```

这些东西不是某一个功能独有的，所以单独放在 `core`（核心）。

## 7. backend/app/agents

```text
backend/app/agents/
```

这里放智能体流程。

这个项目的核心不是普通 CRUD，而是 AI Agent。所以要单独有 `agents` 目录。

后续会对应三条主流程：

```text
compare_graph.py      商品比价智能体流程
recommend_graph.py    商品推荐智能体流程
rag_chat_graph.py     RAG 问答智能体流程
state.py              Agent 状态定义
```

这样拆分后，我们可以清楚知道：

```text
接口在 api/
业务入口在 services/
智能体流程在 agents/
具体工具在 tools/
```

## 8. backend/app/tools

```text
backend/app/tools/
```

这里放智能体可以调用的工具。

例如：

```text
product_parse.py          商品名称解析
platform_search.py        平台商品查询
product_match.py          同款匹配
risk_analysis.py          风险分析
rag_search.py             RAG 检索
recommendation_rank.py    推荐排序
```

为什么不直接写在 Agent 里？

因为 Agent 应该负责编排流程，而工具负责具体能力。这样以后某个工具要优化，比如同款匹配算法升级，不会影响整个智能体流程。

## 9. backend/app/adapters

```text
backend/app/adapters/
```

这里放平台适配器。

后续可能有：

```text
mock_platform.py
jd.py
taobao.py
pdd.py
```

这样设计是因为不同电商平台的接口格式肯定不一样。我们不能让业务代码到处判断“这是京东字段还是淘宝字段”。

Adapter 的作用是把不同平台的数据统一成我们自己的标准格式。

第一阶段：

```text
只做 MockPlatformAdapter
```

第二阶段：

```text
接入一个真实平台 API
```

第三阶段：

```text
再接京东、淘宝、拼多多多个平台
```

## 10. backend/app/services

```text
backend/app/services/
```

这里放业务服务层。

例如：

```text
compare_service.py
recommend_service.py
chat_service.py
```

Service 的作用是把接口和智能体连接起来。

比如比价接口收到请求后：

```text
api/routes_compare.py
  -> services/compare_service.py
  -> agents/compare_graph.py
```

这样做的好处是接口层保持简单，业务流程也不会直接暴露给路由文件。

## 11. backend/app/repositories（仓库）

```text
backend/app/repositories/
```

这里放数据库访问代码。

例如：

```text
product_repo.py
compare_repo.py
knowledge_repo.py
```

为什么需要 repository？

因为数据库操作会越来越多。如果直接在 service 或 agent 里写 SQL，后面会很乱。Repository 负责统一处理数据读写。

## 12. backend/app/db

```text
backend/app/db/
```

这里放数据库连接和基础配置。

例如：

```text
session.py
base.py
```

它和 `repositories` 的区别是：

```text
db/            负责怎么连接数据库
repositories/ 负责怎么读写具体业务数据
```

## 13. backend/app/models（数据库表在代码里的模型）
#解释：为什么叫 models？

因为它们是“数据模型”。简单理解：

数据库表 = 数据库里的结构
models = 代码里对应这些表的结构

```text
backend/app/models/
```

这里放 SQLAlchemy 数据模型。

它会对应 `docs/database.md` 里的表，比如：

```text
products
platform_products
price_records
compare_queries
knowledge_documents
chat_messages
```

## 14. backend/app/workers

```text
backend/app/workers/
```

这里放后台任务。

第一阶段可以先不用。

第二阶段做降价提醒时会用到：

```text
定时查询商品价格
判断是否低于目标价
生成站内提醒
```

所以提前留这个目录。

## 15. backend/tests

```text
backend/tests/
```

这里放后端测试。

第一阶段至少应该测试：

```text
健康检查接口
商品比价接口
商品推荐接口
RAG 问答接口
风险标签逻辑
```

测试目录提前建好，是为了提醒我们不要最后才补测试。

## 16. backend/migrations（专门保存这些数据库变更脚本的地方）

```text
backend/migrations/
```

这里放数据库迁移文件。

后续使用 Alembic 时，建表和改表都会放在这里。这样数据库结构变化有记录，不会靠手动改库。

## 17. frontend

```text
frontend/
  app/
  components/
  lib/
  public/
```

`frontend` 是 Next.js 前端目录。

第一阶段前端不是做营销页，而是做一个能实际使用的工作台：

```text
输入商品名称 -> 看多平台比价
输入购买需求 -> 看推荐商品
输入选购问题 -> 看 RAG 回答
```

## 18. frontend/app
#这是 Next.js 框架规定或推荐的目录名，不是我们自己随便起的。Next.js 会自动识别 frontend/app 下面的文件，把它们变成网页路由。
```text
frontend/app/
```

这里放 Next.js 页面和路由。

第一阶段可以先做一个主页面，后续再拆：

```text
比价页
推荐页
问答页
价格历史页
```

## 19. frontend/components

```text
frontend/components/
```

这里放可复用组件。

例如：

```text
ProductCard        商品卡片
RiskTag            风险标签
CompareResult      比价结果
RecommendList      推荐列表
ChatPanel          问答面板
PriceTrend         价格趋势
```

这样做是为了避免页面文件越来越大。

## 20. frontend/lib

```text
frontend/lib/
```

这里放前端工具代码。

例如：

```text
api.ts       请求后端接口
types.ts     前端类型定义
format.ts    价格、时间格式化
```

## 21. frontend/public

```text
frontend/public/
```

这里放静态资源。

例如：

```text
logo
占位图
平台图标
```

## 22. mock_data

```text
mock_data/
  platform_products/
  knowledge/
```

第一阶段还不接真实平台 API，所以需要 Mock 数据。

```text
platform_products/ 放模拟京东、淘宝、拼多多商品数据
knowledge/         放 RAG 知识库原始文档
```

这样可以先把完整业务流程跑通：

```text
用户输入 -> 后端处理 -> Mock 平台返回商品 -> 风险分析 -> 前端展示
```

等真实 API 审核完成后，再把 Mock 替换为真实 Adapter。

## 23. scripts

```text
scripts/
```

这里放一次性或辅助脚本。

例如：

```text
导入 Mock 商品数据
导入知识库文档
检查服务是否启动
生成测试数据
```

这些脚本不属于后端主服务，也不属于前端页面，所以单独放。

## 24. docker

```text
docker/
  backend/
  frontend/
  nginx/
```

这里为后续部署预留。

第二阶段或上线前会需要：

```text
后端容器
前端容器
PostgreSQL
Redis
Qdrant
Nginx 反向代理
```

现在先建目录，不急着写 Docker 配置。

## 25. 为什么现在只建目录

现在只建目录，不急着写代码，是因为我们要先保证：

```text
1. 项目边界清楚
2. 每一层职责清楚
3. 你能看懂每一步在做什么
4. 后续代码可以一点点加，不会突然冒出一大堆文件
```

接下来建议的节奏是：

```text
1. 你先审核目录结构
2. 确认后，我们只写 backend 最小 FastAPI 入口
3. 再只写 /health 接口
4. 再只写 /compare 的 Mock 版本
5. 每一步都可运行、可审核
```
