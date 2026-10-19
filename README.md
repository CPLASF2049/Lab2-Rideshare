# lab2-rideshare — 网约车平台微服务架构设计

《高级软件工程》Lab 2 实验仓库。本仓库只包含**设计产物**：领域分析、微服务与数据设计、
通信设计、业务流程 / 接口 / 事件契约，以及一张系统整体架构图，不包含业务实现代码。

平台在上海、杭州、南京三城运营，峰值指标为：叫车提交 1,000 次/秒、司机位置上报 20,000 条/秒、
乘客状态查询 10,000 次/秒。设计中的容量与部署方案（三城单元化部署 + 城市内分片）即以此为基线。

---

## 1. 第 32 组小组成员与分工

| 角色 | 姓名 | 学号 | Git 身份（user.name） | 实际分工 |
| --- | --- | --- | --- | --- |
| 开发者 | 陈星岩 | 26113050014 | 陈星岩_26113050014 | 领域分析（业务需求梳理、子领域划分与类型判定）；限界上下文与术语表；微服务划分依据；系统整体架构图与上下文映射图 |
| 开发者 | 李思源 | 26213050248 | 李思源-26213050248 | 服务通信设计（同步/异步、协议选型、一致性方案）；三条关键流程的时序图与业务规则；数据模型图；接口与事件契约（OpenAPI / gRPC / 事件示例） |

---

## 2. 仓库结构

```text
lab2-rideshare/
├── README.md                       # 小组成员、分工、仓库说明
├── architecture.png                # 系统整体架构图（提交要求：根目录）
├── docs/
│   ├── design.md                   # 设计报告正文（四章设计 + 整体架构图章节）
│   └── images/
│       ├── context-map.png         # 限界上下文映射图
│       ├── data-model.png          # 数据模型图（ER，按上下文分组）
│       ├── seq-quote-dispatch.png  # 流程一：报价、叫车与接单
│       ├── seq-cancel-rebook.png   # 流程二：取消与重新叫车
│       └── seq-pickup-payment.png  # 流程三：接驾、上车与支付
├── contracts/
│   ├── README.md                   # 契约索引、通用约定（鉴权、版本、幂等、错误码）
│   ├── openapi/
│   │   ├── rider-api.yaml          # 乘客端 REST（12 个路径）
│   │   ├── driver-api.yaml         # 司机端 REST（11 个路径）
│   │   └── ops-api.yaml            # 运营端 REST（7 个路径）
│   ├── proto/
│   │   ├── common.proto            # 公共类型（Money / GeoPoint / 状态枚举）
│   │   ├── trip.proto              # rideshare.trip.v1.TripService（12 个方法）
│   │   ├── dispatch.proto          # rideshare.dispatch.v1.DispatchService（5）
│   │   ├── pricing.proto           # rideshare.pricing.v1.PricingService（5）
│   │   ├── payment.proto           # rideshare.payment.v1.PaymentService（6）
│   │   ├── supply.proto            # rideshare.supply.v1.DriverService（5）/ LocationService（3）
│   │   └── notification.proto      # rideshare.notification.v1.NotificationService（4）
│   └── events/
│       ├── events.md               # 24 个业务事件：语义、触发条件、发布/订阅方、字段
│       └── examples/*.json         # 18 个事件消息示例（含完整信封）
└── scripts/
    ├── gen_diagrams.py             # 生成全部 6 张设计图（入口）
    ├── diagrams_more.py            # 上下文映射图、数据模型图、时序图
    ├── diagram_kit.py              # Pillow 绘图原语（矩形 / 箭头 / 虚线 / 图例）
    ├── check_contracts.py          # OpenAPI 校验（YAML 子集解析 + 结构 + $ref）
    └── check_consistency.py        # 报告 ↔ 契约 ↔ 图 的名称一致性自检
```

## 3. 如何使用本仓库

1. **阅读设计报告**：`docs/design.md` 是主要交付物，按「领域分析 → 微服务与数据 → 通信设计 →
   流程/接口/事件 → 整体架构图」五章组织，所有设计图内嵌在对应章节。
2. **核对契约**：`contracts/` 下的 OpenAPI、`.proto`、事件示例与报告中出现的方法名、事件名、
   字段名一一对应，报告 4.7 节给出名称一致性自检表。
3. **重新生成设计图**（可选，只依赖 Pillow 与系统自带中文字体）：

   ```powershell
   python scripts/gen_diagrams.py                            # 生成全部 6 张图
   python scripts/gen_diagrams.py --only architecture        # 只生成架构图
   python scripts/gen_diagrams.py --only data-model,seq-quote-dispatch
   ```
4. **跑自检**（可选）：

   ```powershell
   python scripts/check_contracts.py       # 三份 OpenAPI：语法 + 结构 + $ref 完整性
   python scripts/check_consistency.py     # 报告 / 契约 / 图 的事件名、路径、服务名一致性
   ```

   两项检查当前均通过：24 个事件、29 条对外路径、40 个 gRPC 方法、11 个服务名完全对齐。

## 4. 设计要点速览

| 关注点 | 结论 |
| --- | --- |
| 子领域 | 6 个：行程交易、计价结算（核心域）；运力与位置、运营支撑（支撑域）；身份与账户、通知触达（通用域） |
| 微服务 | 9 个业务服务 + 2 个接入组件（`api-gateway`、`realtime-gateway`），一服务一库 |
| 数据归属 | 每类数据唯一权威方；跨上下文只用 ID 引用 + 事件副本，禁止跨库 JOIN |
| 通信 | 对外 REST（`/v1`）、对内 gRPC、状态传播走 Kafka、高频位置与推送走 WebSocket；取消 = 同步受理 + 异步判责 |
| 一致性 | Outbox + 幂等消费 + 乐观锁 + 编排式 Saga + 对账补偿 |
| 容量 | 位置 20k/s 批量写 Redis GEO；叫车 1k/s 按城市分片、撮合异步化；查询 85% 由推送替代 |
| 规则 | 本组自定义 12 条业务细则（R-01 ~ R-12），见报告 §0 与各章节 |

## 5. 与 Lab 1 的关系

Lab 1（`lab1-counter`）验证了单机 Docker Compose 多容器与数据持久化。本实验不要求实现，
因此不沿用 Lab 1 的技术选型约束；但沿用同一小组、同一 Git 身份与同一套文档/证据组织习惯。
