# 业务事件目录（Event Catalog）

本目录定义平台的全部领域事件。事件承载"**已经发生的事实**"，由发布方通过 Kafka 发布，
订阅方按需消费；事件名、字段名与 `docs/design.md` §4.6、`contracts/proto/*.proto` 保持完全一致。

## 1. 通用约定

| 项目 | 约定 |
| --- | --- |
| 命名 | `<聚合>.<过去式事实>.v1`，例：`trip.matched.v1`；禁止命令式（如 `create.trip`） |
| Topic | 单元化部署下为 `<city>.<事件名>`（`sh.` / `hz.` / `nj.`）；供全局订阅的镜像 topic 为 `all.<事件名>` |
| 分区键 | 行程相关用 `trip_id`；位置相关用 `driver_id`；账号相关用 `account_id`。同一聚合的事件因此有序 |
| 语义 | 至少一次投递（at-least-once）+ 消费端按 `event_id` 去重 ⇒ 效果上恰好一次 |
| 顺序 | 同一 `partition_key` 内有序；跨聚合不保证顺序，订阅方用 `trip.version` 丢弃过期事件 |
| 大小 | 单条事件 ≤ 32 KB；超出的明细（轨迹、导出文件）改为引用（`track_id`、`file_url`） |
| 兼容 | 只增字段；语义变更或删字段升 `event_version`；消费者必须忽略未知字段 |
| 敏感信息 | 手机号脱敏（`138****8000`），证件号、身份证、支付卡信息**不得**出现在事件中 |
| 幂等键 | 事件的业务幂等键写在字段里（如 `cancellation_id`、`idempotency_key`），订阅方据此建唯一约束 |

统一信封（所有事件必须包含）：

```json
{
  "event_id": "evt_01J9Z3K7YQ2M4T8R",
  "event_type": "trip.matched.v1",
  "event_version": 1,
  "occurred_at": "2026-10-15T08:31:14+08:00",
  "producer": "trip-service",
  "city_code": "SH",
  "partition_key": "t_20261015_51bd",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "payload": { }
}
```

| 信封字段 | 类型 | 说明 |
| --- | --- | --- |
| `event_id` | string (ULID) | 全局唯一，消费端去重主键；保留 7 天 |
| `event_type` | string | 事件名（含版本后缀） |
| `event_version` | int32 | 事件结构版本，当前一律为 `1` |
| `occurred_at` | string (RFC3339, +08:00) | 业务事实发生时间（不是投递时间） |
| `producer` | string | 发布服务名，如 `trip-service` |
| `city_code` | string | `SH` / `HZ` / `NJ`；全局事件可为空 |
| `partition_key` | string | Kafka 分区键 |
| `trace_id` | string | 全链路追踪 ID（W3C trace context 的 trace-id） |
| `payload` | object | 事件载荷，见下表 |

## 2. 事件清单

### 2.1 行程交易域

| 事件 | 含义 | 触发条件 | 发布方 | 订阅方 | `payload` 字段 |
| --- | --- | --- | --- | --- | --- |
| `trip.requested.v1` | 行程已创建（叫车成功） | `trip` 落库为 `REQUESTED` | `trip-service` | `dispatch-service`、`ops-service` | `trip_id` string、`rider_id` string、`city_code` string、`origin` GeoPoint、`dest` GeoPoint、`quote_id` string、`total_amount` Money、`requested_at` timestamp |
| `dispatch.dispatch.started.v1` | 撮合已开始 | `dispatch_task` 创建为 `SEARCHING` | `dispatch-service` | `trip-service`、`ops-service` | `dispatch_id` string、`trip_id` string、`round` int32、`radius_m` int32、`candidate_count` int32、`started_at` timestamp |
| `dispatch.invitation.sent.v1` | 邀请已发出 | 创建 `dispatch_invitation(PENDING)` | `dispatch-service` | `notification-service`、`ops-service` | `invite_id` string、`dispatch_id` string、`trip_id` string、`driver_id` string、`round` int32、`pickup` GeoPoint、`dest` GeoPoint、`est_fare_amount` Money、`expire_at` timestamp |
| `dispatch.invitation.accepted.v1` | 司机已接受邀请 | 邀请 CAS 成功且 `ConfirmMatch` 成功 | `dispatch-service` | `ops-service`、`driver-service` | `invite_id` string、`dispatch_id` string、`trip_id` string、`driver_id` string、`accepted_at` timestamp |
| `dispatch.invitation.expired.v1` | 邀请超时未响应 | 15 秒 TTL 到期 | `dispatch-service` | `ops-service` | `invite_id` string、`trip_id` string、`driver_id` string、`round` int32 |
| `dispatch.failed.v1` | 撮合失败 | 无候选 / 5 轮用尽 / 位置数据缺失 | `dispatch-service` | `trip-service`、`ops-service` | `dispatch_id` string、`trip_id` string、`reason` enum(`NO_CANDIDATE`/`NO_LOCATION_DATA`/`ROUNDS_EXHAUSTED`)、`rounds` int32 |
| `trip.matched.v1` | 接单已确认（成交） | `trip.status: DISPATCHING → MATCHED` | `trip-service` | `notification-service`、`driver-service`、`pricing-service`、`ops-service` | `trip_id` string、`rider_id` string、`driver_id` string、`vehicle_id` string、`invite_id` string、`pickup` GeoPoint、`eta_seconds` int32、`matched_at` timestamp |
| `trip.arrived.v1` | 司机已到达上车点 | `trip.status → DRIVER_ARRIVED` | `trip-service` | `notification-service`、`ops-service` | `trip_id` string、`driver_id` string、`arrived_at` timestamp、`free_wait_until` timestamp、`arrival_anomaly` bool |
| `trip.boarded.v1` | 乘客已上车，行程开始 | `trip.status → RIDING` | `trip-service` | `location-service`、`notification-service`、`ops-service` | `trip_id` string、`driver_id` string、`boarded_at` timestamp、`waiting_s` int32 |
| `trip.ended.v1` | 行程已结束（计量封存） | `trip.status → ENDED` | `trip-service` | `pricing-service`、`ops-service` | `trip_id` string、`driver_id` string、`ended_at` timestamp、`distance_m` int32、`duration_s` int32、`waiting_s` int32、`estimate_mode` enum(`TRACK`/`HAVERSINE`)、`sealed_at` timestamp |
| `trip.cancellation.requested.v1` | 取消申请已受理 | `trip.status → CANCELLING` 且写 `cancellation(PENDING)` | `trip-service` | `pricing-service`、`ops-service` | `trip_id` string、`cancellation_id` string、`initiator` enum(`RIDER`/`DRIVER`/`SYSTEM`/`OPS`)、`phase` enum(`BEFORE_ACCEPT`/`AFTER_ACCEPT`/`AFTER_ARRIVAL`/`AFTER_RIDING`)、`reason_code` string、`requested_at` timestamp |
| `trip.cancellation.accepted.v1` | 取消已确认（含判责与费用） | `cancellation.status → ACCEPTED`，行程进入 `CANCELLED` | `trip-service` | `notification-service`、`payment-service`、`pricing-service`、`ops-service` | `trip_id` string、`cancellation_id` string、`initiator` enum、`phase` enum、`fee_amount` Money、`fee_status` enum(`NONE`/`UNPAID`/`PAID`/`WAIVED`)、`canceled_at` timestamp |
| `trip.expired.v1` | 无人接单超时 | `trip.status: DISPATCHING → EXPIRED`（180 秒） | `trip-service` | `notification-service`、`dispatch-service`、`ops-service` | `trip_id` string、`rider_id` string、`reason` string、`expired_at` timestamp |
| `trip.paid.v1` | 行程已支付（终态） | `trip.status: ENDED → PAID` | `trip-service` | `notification-service`、`ops-service` | `trip_id` string、`driver_id` string、`rider_id` string、`fare_id` string、`payment_id` string、`paid_at` timestamp |

### 2.2 计价结算域

| 事件 | 含义 | 触发条件 | 发布方 | 订阅方 | `payload` 字段 |
| --- | --- | --- | --- | --- | --- |
| `pricing.cancel_fee.calculated.v1` | 取消费用已计算 | 消费 `trip.cancellation.requested.v1` 后完成计算 | `pricing-service` | `payment-service`、`trip-service` | `cancel_fee_id` string、`trip_id` string、`cancellation_id` string、`phase` enum、`amount` Money、`rule_version` string、`note` string |
| `fare.calculated.v1` | 行程费用已生成 | 消费 `trip.ended.v1` 后完成计算 | `pricing-service` | `payment-service`、`trip-service`、`ops-service` | `fare_id` string、`trip_id` string、`fare_version` int32、`items` FareItem[]、`total_amount` Money、`rule_version` string、`estimate_mode` enum |
| `payment.bill.created.v1` | 账单已生成 | `bill` 落库为 `UNPAID` | `payment-service` | `notification-service`、`ops-service` | `bill_id` string、`trip_id` string、`rider_id` string、`bill_type` enum(`TRIP`/`CANCEL_FEE`)、`items` FareItem[]、`total_amount` Money、`due_at` timestamp |
| `payment.succeeded.v1` | 支付成功 | 渠道回调验签成功并结清账单 | `payment-service` | `trip-service`、`notification-service`、`ops-service` | `payment_id` string、`bill_id` string、`trip_id` string、`amount` Money、`channel` enum、`channel_txn_id` string、`paid_at` timestamp |
| `payment.failed.v1` | 支付失败 | 渠道返回失败或查单失败 | `payment-service` | `trip-service`、`notification-service`、`ops-service` | `payment_id` string、`bill_id` string、`trip_id` string、`amount` Money、`channel` enum、`channel_code` string、`retryable` bool |
| `payment.refunded.v1` | 退款完成 | 退款渠道回调成功 | `payment-service` | `ops-service`、`notification-service` | `refund_id` string、`payment_id` string、`trip_id` string、`amount` Money、`reason` string、`refunded_at` timestamp |

### 2.3 运力与位置域

| 事件 | 含义 | 触发条件 | 发布方 | 订阅方 | `payload` 字段 |
| --- | --- | --- | --- | --- | --- |
| `location.reported.v1` | 位置报点已上报（遥测） | 网关收到司机端 WebSocket 上报 | `realtime-gateway` | `location-service` | `driver_id` string、`lat` double、`lng` double、`heading` double、`speed` double、`accuracy` double、`reported_at` timestamp、`batch_size` int32 |
| `location.updated.v1` | 行程中车辆位置已更新 | 写入最新位置（**仅行程中司机**） | `location-service` | `realtime-gateway`、`trip-service` | `driver_id` string、`trip_id` string、`lat` double、`lng` double、`eta_seconds` int32、`seq` int32、`reported_at` timestamp |
| `driver.status.changed.v1` | 司机在线状态变更 | `online_status` 变化 | `driver-service` | `dispatch-service`、`ops-service` | `driver_id` string、`from` enum、`to` enum、`trip_id` string、`changed_at` timestamp |

### 2.4 身份域

| 事件 | 含义 | 触发条件 | 发布方 | 订阅方 | `payload` 字段 |
| --- | --- | --- | --- | --- | --- |
| `account.registered.v1` | 账号已注册 | 新账号创建成功 | `identity-service` | `notification-service`、`ops-service` | `account_id` string、`roles` string[]、`city_code` string、`registered_at` timestamp |

## 3. 事件与流程的对应

| 流程 | 涉及事件（按发生顺序） |
| --- | --- |
| 流程一 报价、叫车与接单 | `trip.requested.v1` → `dispatch.dispatch.started.v1` → `dispatch.invitation.sent.v1` →（`dispatch.invitation.expired.v1` / `dispatch.invitation.accepted.v1`）→ `trip.matched.v1`；失败路径：`dispatch.failed.v1` → `trip.expired.v1` |
| 流程二 取消与重新叫车 | `trip.cancellation.requested.v1` → `pricing.cancel_fee.calculated.v1` →（`payment.succeeded.v1` / `payment.failed.v1`）→ `trip.cancellation.accepted.v1` →（重新叫车）`trip.requested.v1` |
| 流程三 接驾、上车与支付 | `trip.arrived.v1` → `trip.boarded.v1` → `location.reported.v1` / `location.updated.v1`（循环）→ `trip.ended.v1` → `fare.calculated.v1` → `payment.bill.created.v1` → `payment.succeeded.v1` → `trip.paid.v1` |

## 4. 消息示例索引

`examples/` 目录下每个文件是一个完整的事件消息（含信封）：

| 文件 | 事件 |
| --- | --- |
| `examples/trip.requested.json` | `trip.requested.v1` |
| `examples/dispatch.invitation.sent.json` | `dispatch.invitation.sent.v1` |
| `examples/trip.matched.json` | `trip.matched.v1` |
| `examples/trip.arrived.json` | `trip.arrived.v1` |
| `examples/trip.boarded.json` | `trip.boarded.v1` |
| `examples/trip.ended.json` | `trip.ended.v1` |
| `examples/fare.calculated.json` | `fare.calculated.v1` |
| `examples/payment.bill.created.json` | `payment.bill.created.v1` |
| `examples/payment.succeeded.json` | `payment.succeeded.v1` |
| `examples/payment.failed.json` | `payment.failed.v1` |
| `examples/trip.cancellation.requested.json` | `trip.cancellation.requested.v1` |
| `examples/trip.cancellation.accepted.json` | `trip.cancellation.accepted.v1` |
| `examples/pricing.cancel_fee.calculated.json` | `pricing.cancel_fee.calculated.v1` |
| `examples/trip.expired.json` | `trip.expired.v1` |
| `examples/trip.paid.json` | `trip.paid.v1` |
| `examples/dispatch.failed.json` | `dispatch.failed.v1` |
| `examples/location.updated.json` | `location.updated.v1` |
| `examples/driver.status.changed.json` | `driver.status.changed.v1` |
