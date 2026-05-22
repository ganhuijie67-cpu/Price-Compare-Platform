# AI 商品比价与选购智能体接口文档

版本：v0.1  
阶段：第一阶段 MVP  
目标：支撑 20-30 人小团队试用，先跑通“比价 + 推荐 + RAG 问答 + 风险提示 + 查询记录”闭环。

## 1. 接口约定

### 1.1 基础信息

```text
Base URL: /api/v1
Content-Type: application/json
```

第一阶段可以暂不做用户登录，所有接口默认以匿名用户使用。后续接入登录后，前端在请求头中传入：

```http
Authorization: Bearer <access_token>
```

### 1.2 通用响应结构

成功响应：

```json
{
  "success": true,
  "data": {},
  "message": "ok",
  "request_id": "req_202601010001"
}
```

失败响应：

```json
{
  "success": false,
  "data": null,
  "message": "商品名称不能为空",
  "error": {
    "code": "INVALID_ARGUMENT",
    "detail": "query is required"
  },
  "request_id": "req_202601010001"
}
```

### 1.3 通用错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | ---: | --- |
| INVALID_ARGUMENT | 400 | 请求参数错误 |
| NOT_FOUND | 404 | 资源不存在 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| UPSTREAM_TIMEOUT | 504 | 外部平台 API 超时 |
| UPSTREAM_ERROR | 502 | 外部平台 API 异常 |
| AGENT_ERROR | 500 | Agent 工作流执行失败 |
| INTERNAL_ERROR | 500 | 服务内部错误 |

### 1.4 平台枚举

```text
jd        京东
taobao    淘宝/天猫
pdd       拼多多
mock      Mock 数据源
```

### 1.5 风险标签枚举

```text
abnormal_low_price        价格异常偏低
suspected_used            疑似二手
suspected_accessory       疑似配件
capacity_mismatch         容量不一致
version_mismatch          版本不一致
non_official_store        非官方店铺
coupon_uncertain          券后价不确定
after_sales_risk          售后风险
insufficient_title_info   标题信息不足
```

## 2. 商品比价

### 2.1 创建比价请求

```http
POST /api/v1/compare
```

用于用户输入明确商品名称后，系统返回多平台候选商品、匹配度、风险标签和购买建议。

请求体：

```json
{
  "query": "iPhone 17 Pro 256GB 国行",
  "platforms": ["jd", "taobao", "pdd"],
  "max_results_per_platform": 5,
  "enable_risk_analysis": true,
  "enable_price_history": true
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| query | string | 是 | 用户输入的商品名称 |
| platforms | string[] | 否 | 指定查询平台，默认查询全部支持平台 |
| max_results_per_platform | number | 否 | 每个平台最多返回数量，默认 5 |
| enable_risk_analysis | boolean | 否 | 是否启用风险分析，默认 true |
| enable_price_history | boolean | 否 | 是否写入价格记录，默认 true |

响应：

```json
{
  "success": true,
  "data": {
    "query_id": "cq_001",
    "normalized_product": {
      "brand": "Apple",
      "name": "iPhone 17 Pro",
      "model": "iPhone 17 Pro",
      "capacity": "256GB",
      "version": "国行",
      "color": null
    },
    "summary": {
      "lowest_price": 7599,
      "lowest_platform": "pdd",
      "recommended_platform": "jd",
      "result_count": 8,
      "updated_at": "2026-05-21T10:30:00+08:00"
    },
    "items": [
      {
        "platform": "jd",
        "platform_product_id": "jd_100001",
        "title": "Apple iPhone 17 Pro 256GB 国行 全网通",
        "price": 7999,
        "coupon_price": 7799,
        "currency": "CNY",
        "shop_name": "Apple 产品京东自营旗舰店",
        "shop_type": "self_operated",
        "product_url": "https://example.com/item/100001",
        "image_url": "https://example.com/item/100001.jpg",
        "match_score": 0.96,
        "risk_tags": [],
        "risk_level": "low",
        "recommendation_reason": "匹配度高，店铺可信度高，售后稳定。",
        "updated_at": "2026-05-21T10:30:00+08:00"
      }
    ],
    "agent_trace": [
      {
        "node": "parse_query",
        "status": "success",
        "duration_ms": 120
      },
      {
        "node": "platform_search",
        "status": "success",
        "duration_ms": 1800
      },
      {
        "node": "risk_analysis",
        "status": "success",
        "duration_ms": 230
      }
    ],
    "buying_advice": "京东自营价格略高但售后更稳；拼多多价格最低，但建议确认是否全新国行和是否支持官方保修。"
  },
  "message": "ok",
  "request_id": "req_001"
}
```

### 2.2 查询比价详情

```http
GET /api/v1/compare/{query_id}
```

用于前端刷新、详情页或历史记录页重新查看某次比价结果。

响应体同 `POST /compare` 的 `data` 结构。

## 3. 商品推荐

### 3.1 创建推荐请求

```http
POST /api/v1/recommend
```

用于用户只描述预算、用途、偏好时，系统结合 RAG 选购知识和比价工具推荐商品。

请求体：

```json
{
  "query": "预算 5000，想买拍照好、续航强的手机",
  "category": "phone",
  "budget_min": 3000,
  "budget_max": 5000,
  "preferences": ["拍照", "续航"],
  "platforms": ["jd", "taobao", "pdd"],
  "limit": 5
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| query | string | 是 | 用户自然语言需求 |
| category | string | 否 | 商品品类，第一阶段主要支持 phone、laptop、earphone、tablet |
| budget_min | number | 否 | 最低预算 |
| budget_max | number | 否 | 最高预算 |
| preferences | string[] | 否 | 偏好标签 |
| platforms | string[] | 否 | 查询平台 |
| limit | number | 否 | 推荐数量，默认 5 |

响应：

```json
{
  "success": true,
  "data": {
    "recommendation_id": "rec_001",
    "parsed_need": {
      "category": "phone",
      "budget_min": 3000,
      "budget_max": 5000,
      "preferences": ["拍照", "续航"]
    },
    "items": [
      {
        "product_name": "某品牌 Phone X Pro",
        "category": "phone",
        "price_range": {
          "min": 4299,
          "max": 4899
        },
        "recommended_platform": "jd",
        "best_offer": {
          "platform": "jd",
          "price": 4599,
          "coupon_price": 4399,
          "product_url": "https://example.com/item/200001"
        },
        "recommendation_score": 0.91,
        "suitable_for": ["重视拍照", "中高强度日常使用"],
        "reasons": [
          "主摄规格较强，适合拍照需求。",
          "电池容量和快充表现适合续航优先用户。",
          "当前价格在预算范围内。"
        ],
        "risk_tags": ["coupon_uncertain"],
        "alternatives": ["某品牌 Phone X", "某品牌 Phone Y"]
      }
    ],
    "rag_references": [
      {
        "title": "手机选购指南",
        "source": "knowledge_base",
        "chunk_id": "kb_phone_001"
      }
    ],
    "final_advice": "优先考虑拍照和续航均衡的中高端机型，不建议只按最低价选择。"
  },
  "message": "ok",
  "request_id": "req_002"
}
```

## 4. RAG 选购问答

### 4.1 创建问答请求

```http
POST /api/v1/chat
```

用于回答商品知识、参数区别、平台规则、售后政策等问题。

请求体：

```json
{
  "question": "京东自营和天猫旗舰店有什么区别？",
  "session_id": "sess_001",
  "top_k": 5
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| question | string | 是 | 用户问题 |
| session_id | string | 否 | 会话 ID，用于上下文追踪 |
| top_k | number | 否 | RAG 检索数量，默认 5 |

响应：

```json
{
  "success": true,
  "data": {
    "answer": "京东自营通常由京东负责销售、发货或售后履约，售后体验更统一；天猫旗舰店一般由品牌官方或授权主体经营，品牌可信度较高，但物流和售后规则以店铺说明为准。",
    "key_points": [
      "京东自营售后履约更统一。",
      "天猫旗舰店品牌可信度通常较高。",
      "最终仍需查看具体商品页的发货、保修和退换规则。"
    ],
    "references": [
      {
        "title": "京东自营说明",
        "source": "knowledge_base",
        "chunk_id": "kb_jd_001",
        "score": 0.88
      }
    ],
    "related_questions": [
      "拼多多百亿补贴靠谱吗？",
      "国行和港版有什么区别？"
    ]
  },
  "message": "ok",
  "request_id": "req_003"
}
```

## 5. 价格历史

### 5.1 查询商品价格历史

```http
GET /api/v1/products/{product_id}/price-history?platform=jd&days=30
```

用于展示商品近 7 天、30 天价格变化。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| platform | string | 否 | 指定平台 |
| days | number | 否 | 查询天数，默认 30 |

响应：

```json
{
  "success": true,
  "data": {
    "product_id": "prod_001",
    "product_name": "iPhone 17 Pro 256GB 国行",
    "current_price": 7799,
    "lowest_price": 7599,
    "average_price": 7899,
    "is_near_lowest": true,
    "trend": "down",
    "records": [
      {
        "platform": "jd",
        "price": 7999,
        "coupon_price": 7799,
        "recorded_at": "2026-05-21T10:30:00+08:00"
      }
    ]
  },
  "message": "ok",
  "request_id": "req_004"
}
```

## 6. 降价提醒

第一阶段可以只完成接口和数据库设计，后台定时任务在第二阶段启用。

### 6.1 创建降价提醒

```http
POST /api/v1/alerts
```

请求体：

```json
{
  "product_id": "prod_001",
  "target_price": 7500,
  "platforms": ["jd", "pdd"],
  "notify_channels": ["in_app"]
}
```

响应：

```json
{
  "success": true,
  "data": {
    "alert_id": "alert_001",
    "product_id": "prod_001",
    "target_price": 7500,
    "platforms": ["jd", "pdd"],
    "notify_channels": ["in_app"],
    "status": "active",
    "created_at": "2026-05-21T10:30:00+08:00"
  },
  "message": "ok",
  "request_id": "req_005"
}
```

### 6.2 查询降价提醒列表

```http
GET /api/v1/alerts
```

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "alert_id": "alert_001",
        "product_id": "prod_001",
        "product_name": "iPhone 17 Pro 256GB 国行",
        "target_price": 7500,
        "current_price": 7799,
        "status": "active",
        "created_at": "2026-05-21T10:30:00+08:00"
      }
    ]
  },
  "message": "ok",
  "request_id": "req_006"
}
```

### 6.3 更新降价提醒状态

```http
PATCH /api/v1/alerts/{alert_id}
```

请求体：

```json
{
  "status": "paused"
}
```

状态枚举：

```text
active    启用
paused    暂停
triggered 已触发
deleted   已删除
```

## 7. 知识库管理接口

第一阶段可以只提供内部管理接口，用于导入选购指南和平台规则文档。

### 7.1 上传知识文档

```http
POST /api/v1/admin/knowledge-documents
```

请求体：

```json
{
  "title": "手机选购指南",
  "category": "phone",
  "source": "manual",
  "content": "这里是文档正文..."
}
```

响应：

```json
{
  "success": true,
  "data": {
    "document_id": "doc_001",
    "chunk_count": 12,
    "index_status": "indexed"
  },
  "message": "ok",
  "request_id": "req_007"
}
```

### 7.2 查询知识文档列表

```http
GET /api/v1/admin/knowledge-documents?category=phone
```

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "document_id": "doc_001",
        "title": "手机选购指南",
        "category": "phone",
        "source": "manual",
        "chunk_count": 12,
        "index_status": "indexed",
        "created_at": "2026-05-21T10:30:00+08:00"
      }
    ]
  },
  "message": "ok",
  "request_id": "req_008"
}
```

## 8. 健康检查

### 8.1 服务健康检查

```http
GET /api/v1/health
```

响应：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "postgres": "ok",
    "redis": "ok",
    "qdrant": "ok",
    "version": "0.1.0"
  },
  "message": "ok",
  "request_id": "req_health"
}
```

## 9. 第一阶段接口优先级

必须实现：

```text
POST /api/v1/compare
POST /api/v1/recommend
POST /api/v1/chat
GET  /api/v1/health
```

建议实现：

```text
GET  /api/v1/compare/{query_id}
GET  /api/v1/products/{product_id}/price-history
POST /api/v1/admin/knowledge-documents
GET  /api/v1/admin/knowledge-documents
```

预留到第二阶段：

```text
POST  /api/v1/alerts
GET   /api/v1/alerts
PATCH /api/v1/alerts/{alert_id}
```
