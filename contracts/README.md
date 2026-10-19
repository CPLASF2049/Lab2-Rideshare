# 契约（Contracts）

本目录是设计报告中接口与事件的**可机读版本**，与 `docs/design.md` §4.5、§4.6 一一对应。

```text
contracts/
├── README.md                  # 本文件：索引与通用约定
├── openapi/
│   ├── rider-api.yaml         # 乘客端 REST（12 个路径）
│   ├── driver-api.yaml        # 司机端 REST（11 个路径）
│   └── ops-api.yaml           # 运营端 REST（7 个路径）
├── proto/
│   ├── common.proto           # 公共类型：Money / GeoPoint / FareItem / TripStatus / CancellationPhase ...
│   ├── trip.proto             # rideshare.trip.v1.TripService（12 个方法）
│   ├── dispatch.proto         # rideshare.dispatch.v1.DispatchService（5 个方法）
│   ├── pricing.proto          # rideshare.pricing.v1.PricingService（5 个方法）
│   ├── payment.proto          # rideshare.payment.v1.PaymentService（6 个方法）
│   ├── supply.proto           # rideshare.supply.v1.DriverService（5）/ LocationService（3）
│   └── notification.proto     # rideshare.notification.v1.NotificationService（4 个方法）
└── events/
    ├── events.md              # 24 个业务事件的语义、触发条件、发布/订阅方、字段
    └── examples/*.json        # 18 个事件消息示例（含完整信封）
```

## 1. 三层接口的分工

| 层 | 形态 | 使用方 | 特点 |
| --- | --- | --- | --- |
| 对外 REST | OpenAPI 3.0（`/v1/...`） | 乘客 App/H5/小程序、司机 App、运营后台 | JSON、易调试、经网关统一鉴权与限流 |
| 对内 gRPC | Protobuf（`rideshare.<ctx>.v1`） | 服务之间 | 强类型、二进制、低延迟、支持 deadline 与流式 |
| 异步事件 | JSON over Kafka（`<聚合>.<事实>.v1`） | 服务之间（发布/订阅） | 事实传播、可重放、批量削峰 |

## 2. 通用约定（三份 OpenAPI 与全部 proto 共同遵守）

| 项目 | 约定 |
| --- | --- |
| 鉴权 | 对外 `Authorization: Bearer <JWT>`；网关验签后透传 `x-account-id`、`x-role`、`x-city-code`、`x-trace-id`；对内 mTLS + `service-token` |
| 授权 | 行程类接口校验归属（`trip.rider_id` / `trip.driver_id`）；运营接口校验角色 + `city_scope` |
| 版本 | REST `/v1`；gRPC 包名 `v1`；事件 `.v1`。只增字段，破坏性变更升主版本并双写过渡 |
| 幂等 | REST `Idempotency-Key`（24 小时，键 + 请求体指纹）；gRPC `RequestMeta.request_id`；事件消费按 `event_id` 去重 |
| 超时 | 网关→下游 300 ms（读）/ 800 ms（写）；`dispatch→location` P99 < 30 ms |
| 限流 | 乘客叫车 1 QPS、司机位置 2.5 QPS、司机接单 5 QPS、运营查询 10 QPS |
| 金额 | 字符串定点 `{ "amount": "38.60", "currency": "CNY" }`，避免浮点误差 |
| 坐标 | WGS84 `{ lat, lng }` |
| 时间 | RFC3339 带时区（`2026-10-15T08:31:02+08:00`） |
| 分页 | `page_size`（默认 20，最大 100）+ `page_token` → `next_page_token` |
| 错误体 | `{ "code", "message", "trace_id", "retryable", "details" }`，`code` 见 `docs/design.md` §4.5.1 |

## 3. 主要错误码与触发场景

| `code` | HTTP | 触发场景 | 定义处 |
| --- | --- | --- | --- |
| `INVALID_ARGUMENT` | 400 | 经纬度越界、缺少必填字段 | 全部 OpenAPI |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 | 令牌过期；跨账号访问行程；运营城市越权 | 全部 OpenAPI |
| `TRIP_STATE_CONFLICT` | 409 | 未到达即上车、重复接单、已取消仍接单 | `rider-api.yaml`、`driver-api.yaml` |
| `UNPAID_BILL_EXISTS` | 409 | 叫车时存在超 24 小时未结清账单（R-10） | `rider-api.yaml` |
| `TRIP_NOT_TERMINATED` | 409 | 原行程未终态就"重新叫车" | `rider-api.yaml` |
| `OPS_INTERVENE_REQUIRED` | 409 | 上车后（`RIDING`）申请取消（R-08） | `rider-api.yaml`、`driver-api.yaml` |
| `QUOTE_EXPIRED` | 410 | 报价超过 5 分钟（R-01） | `rider-api.yaml` |
| `INVITATION_EXPIRED` | 410 | 邀请 15 秒内未响应（R-04） | `driver-api.yaml` |
| `PAYMENT_FAILED` | 402 | 渠道返回余额不足/风控拒绝 | `rider-api.yaml` |
| `RATE_LIMITED` | 429 | 触发限流 | 全部 OpenAPI |
| `SERVICE_DEGRADED` | 503 | 地图服务熔断，报价为估算值 | `rider-api.yaml` |

## 4. 校验

```powershell
python scripts/check_contracts.py            # 校验三份 OpenAPI（语法 + 结构 + $ref 完整性）
```

校验脚本不依赖第三方库：内置一个 YAML 子集解析器，检查缩进、重复键、方法合法性、
`operationId` 唯一性、`tags` 声明、`$ref` 可解析性。当前三份契约均通过。

事件示例为纯 JSON，可直接用 `python -m json.tool` 验证；示例字段与 `events.md` 的字段表严格一致。
