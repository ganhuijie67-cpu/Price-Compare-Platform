# 比价智能体专项规划

版本：v0.1  
当前重点：先把商品比价功能做好，推荐、RAG 问答、价格历史、降价提醒先后置。

## 1. 当前方向

接下来项目先只围绕一个目标推进：

```text
用户输入一个明确商品名称，后端返回可比较、可解释、可排序的多平台商品结果。
```

第一阶段暂时不追求完整购物助手，也不急着加入复杂风险分析。我们先把比价链路写清楚、跑稳定、测试覆盖好。

## 2. 暂时不做的内容

为了避免范围变大，下面这些先放后面：

```text
1. 商品推荐接口
2. RAG 选购问答
3. 价格历史图表
4. 降价提醒
5. 真实平台 API
6. Redis 缓存
7. PostgreSQL 落库
8. 复杂风险标签系统
```

如果后续比价主流程稳定了，再逐个接回来。

## 3. 比价智能体最小闭环

比价智能体可以先拆成 6 个节点：

```text
1. validate_input
   校验 query、platforms、max_results_per_platform。

2. parse_product
   把用户输入解析成品牌、型号、容量、版本等结构化字段。

3. platform_search
   从平台适配器拿候选商品。
   当前先使用 Mock 数据，后续再替换为真实平台 API。

4. product_match
   判断候选商品和用户查询是否同款，并计算 match_score。

5. rank_results
   按匹配度和价格排序，得到推荐平台和最低价平台。

6. build_response
   组装接口响应，返回 summary、items、agent_trace、buying_advice。
```

当前代码已经具备了其中一部分：

```text
已完成：
1. FastAPI /api/v1/compare 接口
2. CompareRequest 请求模型
3. ProductParseTool 商品解析工具
4. ProductMatchTool 同款匹配工具
5. compare_service 最小响应组装
6. compare 接口测试
7. MockPlatformAdapter 平台适配器
8. MockPlatformAdapter 基础测试

待补齐：
1. 更完整的 Mock 多平台数据
2. rank_results 排序逻辑独立出来
3. compare_agent 或 compare_graph 编排层
4. 更清晰的 agent_trace
```

## 4. 推荐目录结构

比价功能先按下面这个结构演进：

```text
backend/app/
  api/
    routes_compare.py
  schemas/
    compare.py
  services/
    compare_service.py
  agents/
    compare_agent.py
  adapters/
    mock_platform.py
  tools/
    product_parse.py
    product_match.py
    compare_rank.py
```

每一层的职责：

```text
routes_compare.py    只接收请求和返回响应
compare_service.py   调用比价智能体，保持业务入口稳定
compare_agent.py     编排比价节点
mock_platform.py     读取 Mock 商品数据，模拟平台查询
product_parse.py     解析商品名称
product_match.py     判断是否同款
compare_rank.py      负责排序、最低价、推荐平台
```

## 5. 分阶段推进

### 阶段 1：把平台查询拆出来（已完成）

目标：

```text
让 compare_service 不再直接读取 compare_mock.json。
```

要做：

```text
1. 新建 backend/app/adapters/mock_platform.py
2. 新建 MockPlatformAdapter
3. 提供 search(platforms, limit) 方法
4. compare_service 改为通过 adapter 获取商品
5. 测试保持通过
```

验收：

```text
POST /api/v1/compare 仍然返回现在测试里的结果。
```

### 阶段 2：丰富 Mock 多平台数据

目标：

```text
让一个 query 能返回京东、淘宝、拼多多三个平台的候选商品。
```

要做：

```text
1. 扩展 mock_data/platform_products/compare_mock.json
2. 每个平台至少 2 条商品
3. 包含同款、容量不一致、配件、二手这几类样例
4. 测试 max_results_per_platform 和 platforms 过滤
```

验收：

```text
输入 iPhone 17 Pro 256GB 国行，接口能返回多个平台结果。
```

建议本阶段先只支持一个固定查询：

```text
iPhone 17 Pro 256GB 国行
```

Mock 数据建议先放 6 条：

```text
1. jd：iPhone 17 Pro 256GB 国行，价格 7999，自营
2. jd：iPhone 17 Pro 128GB 国行，价格 7399，自营
3. taobao：iPhone 17 Pro 256GB 国行，价格 7899，旗舰店
4. taobao：iPhone 17 Pro 手机壳，价格 99，普通店铺
5. pdd：iPhone 17 Pro 256GB 国行，价格 7699，百亿补贴店铺
6. pdd：二手 iPhone 17 Pro 256GB 国行 99新，价格 6999，普通店铺
```

这样设计的原因：

```text
1. 有三平台同款商品，可以真正比价。
2. 有 128GB，可以验证容量不一致时匹配分较低。
3. 有手机壳，可以验证配件不会被当成主商品。
4. 有二手商品，可以验证匹配分会被降低。
5. 后续做排序和风险时，数据样例已经够用。
```

### 阶段 3：把排序逻辑拆出来

目标：

```text
让最低价、推荐平台、结果排序有独立工具维护。
```

要做：

```text
1. 新建 backend/app/tools/compare_rank.py
2. 把 _build_summary、_recommendation_sort_key、_item_effective_price 迁移进去
3. compare_service 只调用排序工具
4. 增加排序测试
```

验收：

```text
最低价平台由价格决定，推荐平台由匹配度优先决定。
```

### 阶段 4：建立比价智能体编排层

目标：

```text
让 compare_service 不再直接串所有步骤，而是调用 compare_agent。
```

要做：

```text
1. 新建 backend/app/agents/compare_agent.py
2. 定义 CompareAgent.run(request)
3. 在 agent 内部串 parse -> adapter search -> match -> rank -> response
4. agent_trace 由每个节点生成
```

验收：

```text
compare_service 变薄，只负责调用 CompareAgent。
```

## 6. 当前下一步建议

下一步只做阶段 2：

```text
扩展 compare_mock.json，让 /api/v1/compare 可以返回三平台候选商品。
```

原因：

```text
1. 现在 adapter 已经拆出来了，下一步应该让 adapter 真的像“平台搜索”。
2. 只有一条 jd 数据时，还不能验证多平台比价。
3. 多平台 Mock 数据是后续排序、推荐平台、最低价平台的基础。
4. 这一步仍然只改 Mock 数据和测试，不需要引入新技术。
```

建议改动文件：

```text
修改：
mock_data/platform_products/compare_mock.json
backend/tests/test_mock_platform.py
backend/tests/test_compare.py
```

暂时不要做：

```text
1. 不扩展风险分析
2. 不接真实平台 API
3. 不引入 LangGraph
4. 不改前端
5. 不改数据库
6. 不拆排序工具
```

## 7. 下一步完成后的项目状态

完成阶段 2 后，比价接口应该能回答两个问题：

```text
1. 哪个平台最低价？
2. 哪些商品更像用户要找的同款？
```

这一步完成后，再进入阶段 3，把 summary 和推荐平台排序逻辑从 compare_service.py 拆到 compare_rank.py。
