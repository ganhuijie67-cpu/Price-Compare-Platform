# AI 商品比价与选购智能体数据库设计

版本：v0.1  
阶段：第一阶段 MVP  
数据库：PostgreSQL + Redis + Qdrant  
目标：先支撑 Mock 数据、多平台比价、商品推荐、RAG 问答、风险标签和价格记录；为第二阶段真实平台 API、价格历史和降价提醒预留结构。

## 1. 设计原则

1. 商品分为“标准商品”和“平台商品”。标准商品表示系统理解的商品实体，平台商品表示京东、淘宝、拼多多等平台上的具体链接。
2. 实时价格与稳定知识分离。价格记录进入 PostgreSQL，选购知识进入 Qdrant，知识文档元数据进入 PostgreSQL。
3. 第一阶段允许匿名使用，所有用户相关表保留 `user_id` 字段但允许为空。
4. 外部平台数据可能不稳定，平台商品保留原始 JSON，方便排查和后续规则优化。
5. 风险标签使用可扩展结构，先用字符串数组或 JSONB，后续再拆成规则表。

## 2. 核心实体关系

```text
products 1 - n platform_products
products 1 - n price_records
compare_queries 1 - n compare_query_items
knowledge_documents 1 - n knowledge_chunks
products 1 - n price_alerts
price_alerts 1 - n alert_events
```

## 3. 表结构设计

### 3.1 users 用户表

第一阶段可不启用登录，但先预留匿名用户和正式用户结构。

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name VARCHAR(100),
  email VARCHAR(255),
  phone VARCHAR(32),
  user_type VARCHAR(32) NOT NULL DEFAULT 'anonymous',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| user_type | anonymous、registered |
| status | active、disabled |

### 3.2 products 标准商品表

保存系统识别后的标准商品，例如“iPhone 17 Pro 256GB 国行”。

```sql
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name VARCHAR(255) NOT NULL,
  brand VARCHAR(100),
  category VARCHAR(64),
  model VARCHAR(128),
  capacity VARCHAR(64),
  version VARCHAR(64),
  color VARCHAR(64),
  attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_brand_model ON products(brand, model);
CREATE INDEX idx_products_attributes_gin ON products USING GIN(attributes);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| canonical_name | 标准商品名称 |
| category | phone、laptop、earphone、tablet 等 |
| attributes | 屏幕、芯片、电池、保修等扩展参数 |

### 3.3 platform_products 平台商品表

保存具体平台上的商品链接和店铺信息。

```sql
CREATE TABLE platform_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id),
  platform VARCHAR(32) NOT NULL,
  external_product_id VARCHAR(128),
  title VARCHAR(500) NOT NULL,
  shop_name VARCHAR(255),
  shop_type VARCHAR(64),
  product_url TEXT,
  image_url TEXT,
  match_score NUMERIC(5,4),
  risk_tags TEXT[] NOT NULL DEFAULT '{}',
  risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
  raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(platform, external_product_id)
);

CREATE INDEX idx_platform_products_product_id ON platform_products(product_id);
CREATE INDEX idx_platform_products_platform ON platform_products(platform);
CREATE INDEX idx_platform_products_match_score ON platform_products(match_score DESC);
CREATE INDEX idx_platform_products_risk_tags_gin ON platform_products USING GIN(risk_tags);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| platform | jd、taobao、pdd、mock |
| external_product_id | 平台侧商品 ID；Mock 阶段也需要生成稳定 ID |
| shop_type | self_operated、flagship、authorized、third_party、unknown |
| match_score | 同款匹配度，0 到 1 |
| risk_tags | 风险标签数组 |
| raw_data | 平台原始返回，便于调试 |

### 3.4 price_records 价格记录表

保存每次查询或定时任务得到的价格。

```sql
CREATE TABLE price_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id),
  platform_product_id UUID REFERENCES platform_products(id),
  platform VARCHAR(32) NOT NULL,
  price NUMERIC(12,2) NOT NULL,
  coupon_price NUMERIC(12,2),
  currency VARCHAR(16) NOT NULL DEFAULT 'CNY',
  promotion_info JSONB NOT NULL DEFAULT '{}'::jsonb,
  source VARCHAR(32) NOT NULL DEFAULT 'compare_query',
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_price_records_product_time ON price_records(product_id, recorded_at DESC);
CREATE INDEX idx_price_records_platform_product_time ON price_records(platform_product_id, recorded_at DESC);
CREATE INDEX idx_price_records_platform_time ON price_records(platform, recorded_at DESC);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| price | 标价 |
| coupon_price | 券后价或到手价 |
| promotion_info | 优惠券、满减、补贴等信息 |
| source | compare_query、scheduled_task、manual_import |

### 3.5 compare_queries 比价查询表

记录用户每次比价请求。

```sql
CREATE TABLE compare_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  query_text TEXT NOT NULL,
  parsed_product JSONB NOT NULL DEFAULT '{}'::jsonb,
  platforms TEXT[] NOT NULL DEFAULT '{}',
  status VARCHAR(32) NOT NULL DEFAULT 'success',
  result_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  agent_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
  error_message TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_compare_queries_user_time ON compare_queries(user_id, created_at DESC);
CREATE INDEX idx_compare_queries_created_at ON compare_queries(created_at DESC);
CREATE INDEX idx_compare_queries_parsed_product_gin ON compare_queries USING GIN(parsed_product);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| parsed_product | Agent 解析出的品牌、型号、容量、版本 |
| result_summary | 最低价、推荐平台、结果数量等摘要 |
| agent_trace | LangGraph 节点执行过程 |

### 3.6 compare_query_items 比价结果明细表

保存某次比价请求返回过的候选商品。

```sql
CREATE TABLE compare_query_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  compare_query_id UUID NOT NULL REFERENCES compare_queries(id) ON DELETE CASCADE,
  platform_product_id UUID REFERENCES platform_products(id),
  platform VARCHAR(32) NOT NULL,
  title VARCHAR(500) NOT NULL,
  price NUMERIC(12,2) NOT NULL,
  coupon_price NUMERIC(12,2),
  shop_name VARCHAR(255),
  shop_type VARCHAR(64),
  product_url TEXT,
  image_url TEXT,
  match_score NUMERIC(5,4),
  risk_tags TEXT[] NOT NULL DEFAULT '{}',
  risk_level VARCHAR(32) NOT NULL DEFAULT 'unknown',
  recommendation_reason TEXT,
  rank_no INTEGER,
  raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_compare_query_items_query ON compare_query_items(compare_query_id, rank_no);
CREATE INDEX idx_compare_query_items_platform ON compare_query_items(platform);
```

### 3.7 recommendation_queries 推荐查询表

记录用户的推荐请求和 Agent 输出。

```sql
CREATE TABLE recommendation_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  query_text TEXT NOT NULL,
  category VARCHAR(64),
  budget_min NUMERIC(12,2),
  budget_max NUMERIC(12,2),
  preferences TEXT[] NOT NULL DEFAULT '{}',
  parsed_need JSONB NOT NULL DEFAULT '{}'::jsonb,
  result JSONB NOT NULL DEFAULT '{}'::jsonb,
  rag_references JSONB NOT NULL DEFAULT '[]'::jsonb,
  agent_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
  status VARCHAR(32) NOT NULL DEFAULT 'success',
  error_message TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recommendation_queries_user_time ON recommendation_queries(user_id, created_at DESC);
CREATE INDEX idx_recommendation_queries_category ON recommendation_queries(category);
```

第一阶段推荐结果可以先放在 `result` JSONB 中，等推荐链路稳定后再拆推荐明细表。

### 3.8 chat_sessions 问答会话表

```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  title VARCHAR(255),
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_sessions_user_time ON chat_sessions(user_id, created_at DESC);
```

### 3.9 chat_messages 问答消息表

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  role VARCHAR(32) NOT NULL,
  content TEXT NOT NULL,
  references JSONB NOT NULL DEFAULT '[]'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_messages_session_time ON chat_messages(session_id, created_at);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| role | user、assistant、system |
| references | RAG 引用来源 |
| metadata | top_k、模型、耗时、token 等信息 |

### 3.10 knowledge_documents 知识文档表

保存 RAG 文档元数据，正文切片向量存入 Qdrant。

```sql
CREATE TABLE knowledge_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255) NOT NULL,
  category VARCHAR(64),
  source VARCHAR(128),
  source_url TEXT,
  content_hash VARCHAR(128),
  chunk_count INTEGER NOT NULL DEFAULT 0,
  index_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_documents_category ON knowledge_documents(category);
CREATE INDEX idx_knowledge_documents_status ON knowledge_documents(index_status);
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| source | manual、markdown、pdf、web、platform_policy |
| index_status | pending、indexing、indexed、failed |

### 3.11 knowledge_chunks 知识切片表

保存切片元数据和 Qdrant point ID，便于追踪引用来源。

```sql
CREATE TABLE knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  chunk_no INTEGER NOT NULL,
  title VARCHAR(255),
  content TEXT NOT NULL,
  qdrant_collection VARCHAR(128) NOT NULL,
  qdrant_point_id VARCHAR(128) NOT NULL,
  token_count INTEGER,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(document_id, chunk_no)
);

CREATE INDEX idx_knowledge_chunks_document ON knowledge_chunks(document_id, chunk_no);
CREATE INDEX idx_knowledge_chunks_qdrant ON knowledge_chunks(qdrant_collection, qdrant_point_id);
```

### 3.12 price_alerts 降价提醒表

第一阶段可只建表和接口预留，第二阶段接入 Celery 定时任务。

```sql
CREATE TABLE price_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  product_id UUID NOT NULL REFERENCES products(id),
  target_price NUMERIC(12,2) NOT NULL,
  platforms TEXT[] NOT NULL DEFAULT '{}',
  notify_channels TEXT[] NOT NULL DEFAULT '{in_app}',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  last_checked_at TIMESTAMPTZ,
  triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_price_alerts_user_status ON price_alerts(user_id, status);
CREATE INDEX idx_price_alerts_product_status ON price_alerts(product_id, status);
```

状态说明：

```text
active    启用
paused    暂停
triggered 已触发
deleted   已删除
```

### 3.13 alert_events 提醒事件表

```sql
CREATE TABLE alert_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID NOT NULL REFERENCES price_alerts(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id),
  platform VARCHAR(32),
  matched_price NUMERIC(12,2) NOT NULL,
  target_price NUMERIC(12,2) NOT NULL,
  notify_channel VARCHAR(32) NOT NULL DEFAULT 'in_app',
  notify_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ
);

CREATE INDEX idx_alert_events_alert_time ON alert_events(alert_id, created_at DESC);
CREATE INDEX idx_alert_events_status ON alert_events(notify_status);
```

## 4. Qdrant 设计

### 4.1 Collection

第一阶段建议只建一个 collection：

```text
shopping_knowledge
```

后续如果品类和文档量明显增加，再拆分：

```text
shopping_phone_knowledge
shopping_laptop_knowledge
platform_policy_knowledge
```

### 4.2 Payload 字段

```json
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "title": "手机选购指南",
  "category": "phone",
  "source": "manual",
  "chunk_no": 1,
  "text": "切片正文",
  "created_at": "2026-05-21T10:30:00+08:00"
}
```

### 4.3 检索约定

| 场景 | collection | top_k | 过滤条件 |
| --- | --- | ---: | --- |
| RAG 问答 | shopping_knowledge | 5 | category 可选 |
| 商品推荐 | shopping_knowledge | 5-8 | category 优先 |
| 平台规则解释 | shopping_knowledge | 3-5 | source=platform_policy |

## 5. Redis 设计

Redis 主要用于缓存热门查询、平台接口结果和任务状态。

### 5.1 Key 设计

```text
compare:query:{query_hash}              比价结果缓存，TTL 5-15 分钟
platform:{platform}:search:{query_hash} 平台搜索结果缓存，TTL 5-15 分钟
rag:answer:{question_hash}              高频问答缓存，TTL 1-24 小时
agent:trace:{request_id}                Agent 执行状态，TTL 1 小时
rate_limit:{user_or_ip}                 限流计数，TTL 1 分钟
```

### 5.2 缓存策略

1. 平台搜索结果短缓存，避免同一商品频繁打外部 API。
2. RAG 高频问题可中等时间缓存。
3. 价格相关缓存必须带更新时间，前端明确展示“更新时间”。
4. 当真实平台 API 超时时，允许返回缓存数据，但响应中需要提示数据可能不是最新。

## 6. 枚举约定

### 6.1 platform

```text
jd
taobao
pdd
mock
```

### 6.2 category

```text
phone
laptop
earphone
tablet
other
```

### 6.3 shop_type

```text
self_operated
flagship
authorized
third_party
unknown
```

### 6.4 risk_level

```text
low
medium
high
unknown
```

### 6.5 risk_tags

```text
abnormal_low_price
suspected_used
suspected_accessory
capacity_mismatch
version_mismatch
non_official_store
coupon_uncertain
after_sales_risk
insufficient_title_info
```

## 7. 第一阶段建表优先级

必须创建：

```text
products
platform_products
price_records
compare_queries
compare_query_items
recommendation_queries
knowledge_documents
knowledge_chunks
chat_sessions
chat_messages
```

可以预留：

```text
users
price_alerts
alert_events
```

## 8. 后续演进建议

1. 接入真实平台 API 后，为 `platform_products.external_product_id` 建立更严格的数据清洗规则。
2. 当同款匹配逻辑稳定后，可以增加 `product_match_rules` 表保存规则和版本。
3. 当用户量增加后，将 `price_records` 按月份或时间范围分区。
4. 当推荐结果需要可分析时，将 `recommendation_queries.result` 拆分为 `recommendation_items`。
5. 当接入登录后，为用户收藏、偏好和通知渠道新增独立表。
