"""第二组设计图：限界上下文映射图、数据模型图、三张时序图。

与 ``gen_diagrams.py`` 共用 ``diagram_kit`` 的画布原语；``gen_diagrams`` 在运行时
才导入本模块（避免循环导入），因此本模块直接复用其 ``container`` / ``kind_label`` 等辅助函数。
"""

from __future__ import annotations

import os

from diagram_kit import PALETTE as P
from diagram_kit import Canvas
from gen_diagrams import IMAGES, container, kind_label

ENTITY_FONT = 7.2


# --------------------------------------------------------------------------- 限界上下文映射图


def gen_context_map():
    W, H = 1240, 676
    c = Canvas(W, H, scale=2)
    c.text(W / 2, 14, "限界上下文映射图（Bounded Context Map）", size=19, bold=True, anchor="ma")
    c.text(
        W / 2,
        42,
        "上下文边界 = 模型边界 = 数据库边界；上下文之间只通过 ID 引用 + 事件协作，禁止共享模型与跨库 JOIN",
        size=9,
        color=P["muted"],
        anchor="ma",
    )

    cols = [40, 445, 850]
    rows = [76, 330]
    bw, bh = 350, 212

    boxes = {
        "identity": (
            cols[0], rows[0], "身份与账户上下文", "generic", "identity-service",
            "账号 / 角色 / 令牌 / 会话 / 乘客档案",
            ["• 认证、令牌签发与刷新（JWT + JWKS）",
             "• 角色与运营 RBAC、城市范围收敛",
             "• 乘客档案、常用地址、设备会话"],
            "对外：/v1/auth/*、/v1/me（经网关）",
        ),
        "trip": (
            cols[1], rows[0], "行程交易上下文", "core", "trip-service · dispatch-service",
            "行程 / 状态机 / 派单任务 / 邀请 / 取消判责阶段",
            ["• 撮合与接单裁决（ConfirmMatch 唯一权威）",
             "• 履约事实：到达、上车、行程结束",
             "• 取消受理与阶段判责、进度视图"],
            "事件：trip.*、dispatch.*（14 个）",
        ),
        "pricing": (
            cols[2], rows[0], "计价结算上下文", "core", "pricing-service · payment-service",
            "报价 / 费用项 / 行程费用 / 取消费 / 账单 / 支付单 / 欠费",
            ["• 路线与 ETA、报价、应付金额计算",
             "• 账单、支付、退款、欠费判定与结算",
             "• 地图与支付渠道适配（ACL 防腐层）"],
            "事件：quote/fare/payment/pricing.*",
        ),
        "ops": (
            cols[0], rows[1], "运营支撑上下文", "support", "ops-service",
            "业务记录 / 读模型 / 审计日志 / 介入工单",
            ["• 事件投影出可重放的读模型（CQRS）",
             "• 多维检索与异步导出（隔离在线库）",
             "• 人工介入与审计（唯一人工写入口）"],
            "订阅：全部业务事件（可重放重建）",
        ),
        "supply": (
            cols[1], rows[1], "运力与位置上下文", "support", "driver-service · location-service",
            "司机 / 车辆 / 资质 / 在线状态 / 位置报点 / 轨迹",
            ["• 供给侧资格：在线、资质、同城、无进行中行程",
             "• 最新位置索引（Redis GEO）与邻近查询",
             "• 轨迹留存与回放（只追加）"],
            "事件：driver.status.changed、location.*",
        ),
        "notify": (
            cols[2], rows[1], "通知触达上下文", "generic", "notification-service（+ realtime-gateway）",
            "模板 / 通道 / 通知消息 / 实时订阅 / 补推",
            ["• 短信、App 推送、站内信多通道触达",
             "• biz_key 去重、失败重试、到达回执",
             "• 订阅管理与断线增量补推"],
            "订阅：全部业务事件；ACL → 供应商",
        ),
    }

    for _key, (x, y, title, kind, services, terms, duties, footnote) in boxes.items():
        container(c, x, y, bw, bh, title, kind)
        c.text(x + 12, y + 36, services, size=8.6, bold=True, color=P["muted"])
        c.text(x + 12, y + 52, "术语：", size=8.2, bold=True, color=P["muted"])
        c.text(x + 40, y + 52, terms, size=8.2, color=P["ink"])
        yy = y + 74
        for duty in duties:
            c.text(x + 12, yy, duty, size=8.3, color=P["ink"])
            yy += 15
        c.text(x + 12, y + bh - 16, footnote, size=7.6, color=P["light"])

    # ① 行程 → 计价（同步）
    c.arrow([(795, 150), (848, 150)], color=P["sync"], width=1.5)
    c.numbered(821, 128, "1")
    # ② 计价 → 行程（异步）
    c.arrow([(848, 184), (795, 184)], color=P["async"], width=1.4, dash=(5, 3))
    c.numbered(821, 206, "2")
    # ③ 行程 → 运力（同步）
    c.arrow([(600, 288), (600, 328)], color=P["sync"], width=1.5)
    c.numbered(600, 308, "3")
    # ④ 运力 → 行程（异步）
    c.arrow([(645, 328), (645, 288)], color=P["async"], width=1.4, dash=(5, 3))
    c.numbered(645, 308, "4")
    # ⑤ 行程 → 通知（异步）
    c.arrow([(795, 250), (852, 342)], color=P["async"], width=1.4, dash=(5, 3))
    c.numbered(820, 296, "5")
    # ⑥ 全部 → 运营（异步事件投影）
    c.arrow([(445, 210), (415, 210), (415, 306), (300, 306), (300, 328)], color=P["async"], width=1.4, dash=(5, 3))
    c.numbered(415, 258, "6")
    # ⑦ 身份 → 行程（同步，ACL）
    c.arrow([(390, 176), (445, 176)], color=P["sync"], width=1.4)
    c.numbered(417, 196, "7", color=P["sync"])
    # ⑧ 身份 → 运营（同步）
    c.arrow([(180, 288), (180, 328)], color=P["sync"], width=1.4)
    c.numbered(180, 308, "8", color=P["sync"])

    c.tag(862, 208, "ACL：地图 / 支付渠道", size=7.4, fg="#a05a00", bg="#fff9db", border=P["external_border"])
    c.tag(862, 462, "ACL：短信 / 推送供应商", size=7.4, fg="#a05a00", bg="#fff9db", border=P["external_border"])

    c.band(30, 574, 1180, 78, fill="#ffffff", outline="#dee2e6")
    c.text(42, 580, "协作说明（编号与图中一致）", size=9.5, bold=True)
    legends = [
        ("1", "行程 → 计价：PricingService/CreateQuote、GetQuote（同步 gRPC）"),
        ("2", "计价 → 行程：fare.calculated.v1、pricing.cancel_fee.calculated.v1"),
        ("3", "行程 → 运力：FindNearbyDrivers、BatchCheckEligibility、SetDriverBusy/Free"),
        ("4", "运力 → 行程：driver.status.changed.v1（候选资格变化）"),
        ("5", "行程 → 通知：trip.* / dispatch.invitation.sent.v1（接单、到达、进度推送）"),
        ("6", "全部 → 运营：全部业务事件投影为 trip_record_view（可重放重建）"),
        ("7", "身份 → 行程：JWKS 验签 + 归属校验（ACL 防腐层）"),
        ("8", "身份 → 运营：运营 RBAC 与城市范围校验"),
    ]
    for index, (order, text) in enumerate(legends):
        col = index % 2
        row = index // 2
        x = 42 + col * 580
        y = 600 + row * 13
        c.numbered(x + 6, y + 4, order, r=5.2, size=7)
        c.text(x + 15, y, text, size=7.4, color=P["muted"])

    path = os.path.join(IMAGES, "context-map.png")
    c.save(path)
    return path


# --------------------------------------------------------------------------- 数据模型图


def entity_box(c: Canvas, x, y, w, title, keys, fields, h=44, owner=None):
    c.rect(x, y, w, h, fill="#ffffff", outline="#adb5bd", width=0.9, radius=4)
    c.rect(x, y, w, 13, fill="#e9ecef", outline=None, radius=4)
    c.text(x + 6, y + 2, title, size=8.2, bold=True, color=P["ink"])
    if owner:
        c.text(x + w - 6, y + 3, owner, size=6.4, color=P["light"], anchor="ra")
    c.text(x + 6, y + 16, keys, size=6.9, color="#1864ab")
    c.text(x + 6, y + 24, fields, size=ENTITY_FONT, color=P["muted"], spacing=1.34)


def gen_data_model():
    W, H = 1425, 876
    c = Canvas(W, H, scale=2)
    c.text(W / 2, 12, "数据模型图（按限界上下文分组，ER 表示）", size=19, bold=True, anchor="ma")
    c.text(
        W / 2,
        38,
        "PK 主键 · UK 唯一键 · 字段名前 → 表示跨上下文引用的 ID（不建外键）· 灰色实线 = 同上下文外键 · 紫色虚线 = 跨上下文引用",
        size=8.8,
        color=P["muted"],
        anchor="ma",
    )

    cols = [30, 375, 720, 1065]
    rows = [70, 500]
    pw, ph1, ph2 = 330, 420, 336
    bw = pw - 24
    bx = [x + 12 for x in cols]
    y = rows[0] + 44
    y2 = rows[1] + 44

    def panel(x, y, title, kind, owner, height, badges=True):
        container(c, x, y, pw, height, title, kind, badges=badges)
        c.text(x + 12, y + 31, owner, size=7.6, color=P["muted"])

    panel(cols[0], rows[0], "运力与位置上下文", "support", "权威：driver-service（前 3）· location-service（后 3）", ph1)
    entity_box(c, bx[0], y, bw, "driver", "PK driver_id · UK account_id", "service_city · online_status · rating · accept_rate · current_trip_id")
    entity_box(c, bx[0], y + 50, bw, "vehicle", "PK vehicle_id · FK driver_id → driver", "plate_no UK · model · seats · trans_cert_no · audit_status")
    entity_box(c, bx[0], y + 100, bw, "qualification", "PK qual_id · FK driver_id", "type（人证/车证）· cert_no · expire_at · audit_status")
    entity_box(c, bx[0], y + 156, bw, "latest_location", "PK driver_id", "lat/lng · heading · speed · accuracy · geohash · reported_at")
    entity_box(c, bx[0], y + 206, bw, "track", "PK track_id · UK trip_id", "→driver_id · start_at · end_at · point_count")
    entity_box(c, bx[0], y + 256, bw, "track_point", "PK (track_id, seq)", "lat/lng · speed · reported_at（只追加）")
    c.text(bx[0], y + 306, "约束：latest_location 覆盖写（Redis GEO），超 30 秒即不新鲜；", size=7, color=P["light"])
    c.text(bx[0], y + 316, "track 与行程 1:1，结束后只读。", size=7, color=P["light"])

    panel(cols[1], rows[0], "行程交易上下文", "core", "权威：trip-service（前 4）· dispatch-service（后 3）", ph1)
    entity_box(c, bx[1], y, bw, "trip", "PK trip_id", "→rider_id · →driver_id · status · version · →quote_id · →fare_id · →payment_id")
    entity_box(c, bx[1], y + 50, bw, "trip_state_log", "PK log_id · FK trip_id", "from_status → to_status · operator · reason（只追加）")
    entity_box(c, bx[1], y + 100, bw, "trip_metering", "PK trip_id", "distance_m · duration_s · waiting_s · sealed_at（封存后只读）")
    entity_box(c, bx[1], y + 150, bw, "cancellation", "PK cancellation_id · UK trip_id", "initiator · phase · reason_code · fee_amount · fee_status · status")
    entity_box(c, bx[1], y + 206, bw, "dispatch_task", "PK dispatch_id · UK trip_id", "status · round · radius_m · candidate_count · expire_at")
    entity_box(c, bx[1], y + 256, bw, "dispatch_invitation", "PK invite_id · FK dispatch_id", "→driver_id · round · status · sent_at · expire_at")
    entity_box(c, bx[1], y + 306, bw, "dispatch_candidate_snapshot", "PK (dispatch_id, driver_id)", "distance_m · rating · accept_rate · score · snapshot_at")

    panel(cols[2], rows[0], "计价结算上下文", "core", "权威：pricing-service", ph1)
    entity_box(c, bx[2], y, bw, "quote", "PK quote_id", "rider_id · est_distance_m/duration_s · surge_multiplier · items[] · expire_at")
    entity_box(c, bx[2], y + 50, bw, "fare", "PK fare_id · UK trip_id", "→trip_id · fare_version · items[] · total_amount · rule_version · estimate_mode")
    entity_box(c, bx[2], y + 100, bw, "cancellation_fee", "PK cancel_fee_id", "→trip_id · →cancellation_id · phase · amount · rule_version")
    entity_box(c, bx[2], y + 150, bw, "price_rule", "PK (city_code, version)", "base_fare · per_km · per_min · waiting_per_min · min_fare · surge_tiers[]")
    entity_box(c, bx[2], y + 200, bw, "cancel_fee_rule", "PK (city_code, version)", "after_accept_fee · after_arrival_fee · free_waiting_s · effective_from")
    c.text(bx[2], y + 254, "规则：fare 生成后不可改，复核调整生成 fare_version+1；", size=7, color=P["light"])
    c.text(bx[2], y + 264, "同一 trip_id 仅一个 ACTIVE 版本；金额=明细之和。", size=7, color=P["light"])

    panel(cols[3], rows[0], "支付账单上下文", "core", "权威：payment-service", ph1)
    entity_box(c, bx[3], y, bw, "bill", "PK bill_id · UK (trip_id, bill_type)", "→trip_id · →rider_id · items[] · total_amount · status · due_at")
    entity_box(c, bx[3], y + 50, bw, "payment_order", "PK payment_id · UK idempotency_key", "→bill_ids[] · amount · channel · status · channel_txn_id")
    entity_box(c, bx[3], y + 100, bw, "payment_transaction", "PK txn_id · UK channel_txn_id", "FK payment_id · attempt_no · channel_code · channel_msg")
    entity_box(c, bx[3], y + 150, bw, "refund", "PK refund_id · FK payment_id", "amount · status · channel_refund_no · reason")
    entity_box(c, bx[3], y + 200, bw, "settlement", "PK settlement_id", "→driver_id · →trip_id · fare_amount · platform_fee · settle_date")
    c.text(bx[3], y + 254, "约束：累计退款 ≤ 支付金额；回调按 channel_txn_id 幂等；", size=7, color=P["light"])
    c.text(bx[3], y + 264, "bill 由 (trip_id, bill_type) 唯一约束保证不重复生成。", size=7, color=P["light"])

    panel(cols[0], rows[1], "身份与账户上下文", "generic", "权威：identity-service", ph2)
    entity_box(c, bx[0], y2, bw, "account", "PK account_id · UK phone_hash", "phone_enc（加密）· roles[] · status · created_at")
    entity_box(c, bx[0], y2 + 50, bw, "session", "PK session_id · FK account_id", "device_id · refresh_token_hash · expire_at · revoked")
    entity_box(c, bx[0], y2 + 100, bw, "rider_profile", "PK account_id（= rider_id）", "nickname · avatar_url · emergency_contact · level")
    entity_box(c, bx[0], y2 + 150, bw, "favorite_place", "PK place_id · FK account_id", "label · lat/lng · address")
    entity_box(c, bx[0], y2 + 200, bw, "ops_role_binding", "PK binding_id · FK account_id", "role · city_scope[]")

    panel(cols[1], rows[1], "运营支撑上下文", "support", "权威：ops-service（全部为副本 / 只读模型 + 审计）", ph2)
    entity_box(c, bx[1], y2, bw, "trip_record_view", "PK trip_id（副本主键）", "status · fare_amount · bill_status · cancel_phase · source_version")
    entity_box(c, bx[1], y2 + 50, bw, "audit_log", "PK audit_id", "operator_id · action · target_type/id · before/after · reason")
    entity_box(c, bx[1], y2 + 100, bw, "intervention_ticket", "PK ticket_id", "trip_id · type · decision · status · operator_id")
    entity_box(c, bx[1], y2 + 150, bw, "export_job", "PK job_id", "filter · status · file_url · expire_at · requested_by")
    c.text(bx[1], y2 + 200, "说明：读模型由事件投影生成、可按事件重放重建；", size=7, color=P["light"])
    c.text(bx[1], y2 + 210, "source_version 用于判断投影是否滞后。", size=7, color=P["light"])

    panel(cols[2], rows[1], "通知触达上下文", "generic", "权威：notification-service", ph2)
    entity_box(c, bx[2], y2, bw, "template", "PK (template_id, version)", "event_type · role · channel · content · variables[] · enabled")
    entity_box(c, bx[2], y2 + 50, bw, "notification_message", "PK message_id · UK biz_key", "template_id · channel · receiver_id · status · retry_count · receipt")
    entity_box(c, bx[2], y2 + 100, bw, "subscription", "PK subscription_id", "account_id · subscribe_type · target_id · conn_id · last_seq")
    c.text(bx[2], y2 + 150, "biz_key = event_id + receiver + channel，同一事实不重复打扰；", size=7, color=P["light"])
    c.text(bx[2], y2 + 160, "last_seq 支持断线后增量补推。", size=7, color=P["light"])

    panel(cols[3], rows[1], "跨上下文引用（只读视图）", "support", "不新增权威数据，只通过 ID 查询或事件副本", ph2, badges=False)
    refs = [
        "• trip.driver_id → driver.driver_id（运力权威）",
        "• trip.rider_id → account.account_id（身份权威）",
        "• trip.quote_id → quote.quote_id（计价权威）",
        "• fare.trip_id → trip.trip_id（计价侧只读）",
        "• bill.trip_id / bill.fare_id → 保存 ID + 金额快照",
        "• dispatch_invitation.driver_id → driver_id 快照",
        "• trip_record_view ← trip.*/fare.*/payment.* 投影",
        "• notification 只存 receiver_id / target_id 引用",
        "• 冲突时一律以「权威维护方」为准（§2.3.3）",
    ]
    for index, text in enumerate(refs):
        c.text(bx[3], y2 + index * 15, text, size=7.2, color=P["muted"])

    def rail(edge, channel, y_from, y_to):
        """同一上下文内的外键连接轨（左侧通道），示例：vehicle → driver。"""
        c.line([(edge, y_from), (channel, y_from), (channel, y_to)], color="#868e96", width=0.9)
        c.arrow([(channel, y_to), (edge, y_to)], color="#868e96", width=0.9, head_size=3.6)

    rail(bx[0], bx[0] - 6, 186, 136)     # vehicle → driver
    rail(bx[0], bx[0] - 10, 236, 136)    # qualification → driver
    rail(bx[0], bx[0] - 14, 392, 342)    # track_point → track
    rail(bx[1], bx[1] - 6, 186, 136)     # trip_state_log → trip
    rail(bx[1], bx[1] - 10, 236, 136)    # trip_metering → trip
    rail(bx[1], bx[1] - 14, 392, 342)    # dispatch_invitation → dispatch_task
    rail(bx[3], bx[3] - 6, 186, 136)     # payment_order → bill
    rail(bx[3], bx[3] - 10, 236, 186)    # payment_transaction → payment_order

    def ref(x1, y1, x2, y2):
        """跨上下文 ID 引用：只在相邻上下文之间的空隙处画短箭头（字段名前的 → 表示引用）。"""
        c.arrow([(x1, y1), (x2, y2)], color=P["route"], width=1.3, dash=(3, 2), head_size=4.5)

    ref(387, 136, 352, 136)     # trip.driver_id → driver
    ref(693, 136, 728, 136)     # trip.quote_id → quote
    ref(732, 186, 697, 186)     # fare.trip_id → trip
    ref(1077, 136, 1042, 186)   # bill ← fare.fare_id

    path = os.path.join(IMAGES, "data-model.png")
    c.save(path)
    return path


# --------------------------------------------------------------------------- 时序图


SEQ_STYLE = {
    "sync": (P["sync"], None, 1.5),
    "return": (P["light"], (3, 2), 1.1),
    "event": (P["async"], (5, 3), 1.4),
    "ws": (P["ws"], (6, 3), 1.4),
}


def wrap_text(c: Canvas, text: str, max_width: float, size: float):
    if c.text_width(text, size) <= max_width:
        return [text]
    if "｜" in text:
        head, tail = text.split("｜", 1)
        return [head, tail]
    words, lines, current = text.split(" "), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.text_width(candidate, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3]


def gen_sequence(spec, filename):
    lanes = spec["participants"]
    lane_w = 128
    margin = 20
    W = margin * 2 + lane_w * len(lanes)
    xs = {key: margin + lane_w * (index + 0.5) for index, (key, _t, _s) in enumerate(lanes)}

    y = 120
    for block in spec["blocks"]:
        y += 24
        for step in block["steps"]:
            y += 20 if step["kind"] in ("return", "self") else 27
        y += 10
    H = int(y + 44)

    c = Canvas(W, H, scale=2)
    c.text(margin + 4, 14, spec["title"], size=18, bold=True)
    c.text(margin + 4, 42, spec["subtitle"], size=9, color=P["muted"])

    lx = margin + 4
    for label, kind in (("同步请求", "sync"), ("返回 / 响应", "return"), ("异步事件（Kafka）", "event"), ("WebSocket 推送", "ws")):
        color, dash, width = SEQ_STYLE[kind]
        c.arrow([(lx, 64), (lx + 32, 64)], color=color, width=width, dash=dash, head_size=4.2)
        c.text(lx + 38, 58, label, size=8.2, color=P["muted"])
        lx += 38 + c.text_width(label, 8.2) + 24
    c.text(W - margin - 4, 58, "编号与报告 §4.2–§4.4 的步骤表一一对应", size=8.2, color=P["light"], anchor="ra")

    lane_palette = {
        "客户端": ("#fff3bf", "#e67700"),
        "接入组件": ("#e9ecef", "#495057"),
        "外部系统": ("#fff9db", "#f59f00"),
        "事件总线": ("#fff0f6", "#d6336c"),
    }
    for key, title, sub in lanes:
        x = xs[key] - lane_w / 2 + 5
        fill, border = lane_palette.get(sub, ("#e7f5ff", P["support_border"]))
        c.rect(x, 78, lane_w - 10, 34, fill=fill, outline=border, width=1.0, radius=5)
        c.text(x + (lane_w - 10) / 2, 84, title, size=8.4, bold=True, anchor="ma")
        c.text(x + (lane_w - 10) / 2, 97, sub, size=7, color=P["muted"], anchor="ma")
        c.line([(xs[key], 112), (xs[key], H - 24)], color="#ced4da", width=1.0, dash=(4, 4))

    y = 120
    for block in spec["blocks"]:
        is_normal = block.get("kind", "normal") == "normal"
        color = P["muted"] if is_normal else "#c92a2a"
        label = f"【{block['label']}】"
        c.text(margin + 4, y, label, size=9.2, bold=True, color=color)
        c.line([(margin + 8 + c.text_width(label, 9.2, True), y + 5), (W - margin, y + 5)], color="#dee2e6", width=1.0)
        y += 24
        for step in block["steps"]:
            kind = step["kind"]
            if kind == "self":
                x = xs[step["frm"]]
                c.line([(x, y + 3), (x + 15, y + 3), (x + 15, y + 13), (x + 4, y + 13)], color=P["muted"], width=1.2)
                c.arrow([(x + 4, y + 13), (x + 1, y + 13)], color=P["muted"], width=1.2, head_size=4.2)
                c.text(x + 22, y, f"{step['n']}. {step['label']}", size=7.6, color=P["muted"])
                y += 20
                continue

            line_color, dash, width = SEQ_STYLE[kind]
            x1, x2 = xs[step["frm"]], xs[step["to"]]
            direction = 1 if x2 > x1 else -1
            c.arrow([(x1 + 3 * direction, y + 11), (x2 - 3 * direction, y + 11)], color=line_color, width=width, dash=dash, head_size=5.2)
            text = f"{step['n']}. {step['label']}" if step["n"] else step["label"]
            max_w = max(210, abs(x2 - x1) - 10)
            lines = wrap_text(c, text, max_w, 7.4)
            mid = (x1 + x2) / 2
            block_w = max(c.text_width(line, 7.4) for line in lines) + 6
            c.rect(mid - block_w / 2, y - 2, block_w, 9.6 * len(lines) + 3, fill="#ffffff", outline=None, radius=2)
            for index, line in enumerate(lines):
                c.text(mid, y + index * 9, line, size=7.4,
                       color=P["muted"] if kind == "return" else line_color, anchor="ma")
            y += 20 if kind == "return" else 27

        y += 10

    c.text(margin + 4, H - 20, spec["footer"], size=8, color=P["light"])
    path = os.path.join(IMAGES, filename)
    c.save(path)
    return path


# --------------------------------------------------------------------------- 三张时序图的数据


LANES_TRIP = [
    ("pax", "乘客 App", "客户端"),
    ("gw", "api-gateway", "接入组件"),
    ("pr", "pricing-service", "计价"),
    ("map", "地图服务", "外部系统"),
    ("trip", "trip-service", "行程"),
    ("pay", "payment-service", "支付"),
    ("dsp", "dispatch-service", "派单"),
    ("loc", "location-service", "位置"),
    ("drv", "driver-service", "运力"),
    ("kafka", "Kafka", "事件总线"),
    ("rt", "realtime-gateway", "接入组件"),
    ("dapp", "司机 App", "客户端"),
]


def flow1():
    return {
        "title": "流程一：报价、叫车与接单（含异常分支）",
        "subtitle": "目标：得到可解释、有时效的报价并发起叫车；平台在无人接单、超时、接单/取消冲突下给出确定结果。"
                    " 规则：报价有效期 5 分钟（R-01）、动态调价 1.0–2.5（R-02）、邀请 15 秒 × 最多 5 轮（R-04）、180 秒未成交转 EXPIRED（R-05）",
        "participants": LANES_TRIP,
        "blocks": [
            {
                "label": "正常路径：取报价 → 叫车 → 撮合 → 接单",
                "steps": [
                    {"n": "1", "frm": "pax", "to": "gw", "kind": "sync", "label": "POST /v1/quotes｜{origin, dest, city_code}"},
                    {"n": "2", "frm": "gw", "to": "pr", "kind": "sync", "label": "PricingService/CreateQuote"},
                    {"n": "3", "frm": "pr", "to": "map", "kind": "sync", "label": "GET /v3/direction/driving｜路径规划（60s 缓存，500ms 降级）"},
                    {"n": "4", "frm": "pr", "to": "pr", "kind": "self", "label": "计算费用项 + 调价系数 → quote 快照（5 分钟有效）"},
                    {"n": "5", "frm": "pr", "to": "pax", "kind": "return", "label": "200 {quote_id, items[], total_amount, expire_at}"},
                    {"n": "6", "frm": "pax", "to": "gw", "kind": "sync", "label": "POST /v1/trips｜{quote_id} + Idempotency-Key"},
                    {"n": "7", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/CreateTrip"},
                    {"n": "8", "frm": "trip", "to": "pr", "kind": "sync", "label": "PricingService/GetQuote｜校验未过期"},
                    {"n": "9", "frm": "trip", "to": "pay", "kind": "sync", "label": "PaymentService/HasUnsettledBill｜欠费拦截"},
                    {"n": "10", "frm": "trip", "to": "trip", "kind": "self", "label": "落库 trip(REQUESTED, version=0) + outbox（同事务）"},
                    {"n": "11", "frm": "trip", "to": "pax", "kind": "return", "label": "201 {trip_id, status=REQUESTED}"},
                    {"n": "12", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.requested.v1"},
                    {"n": "13", "frm": "kafka", "to": "dsp", "kind": "event", "label": "消费 trip.requested.v1"},
                    {"n": "14", "frm": "dsp", "to": "loc", "kind": "sync", "label": "LocationService/FindNearbyDrivers｜radius=3km"},
                    {"n": "15", "frm": "dsp", "to": "drv", "kind": "sync", "label": "DriverService/BatchCheckEligibility"},
                    {"n": "16", "frm": "dsp", "to": "dsp", "kind": "self", "label": "评分排序 + dispatch_task(SEARCHING) + 候选快照"},
                    {"n": "17", "frm": "dsp", "to": "kafka", "kind": "event", "label": "dispatch.dispatch.started.v1"},
                    {"n": "18", "frm": "dsp", "to": "dsp", "kind": "self", "label": "创建邀请（PENDING, 15s）+ Redis SETNX 派单锁"},
                    {"n": "19", "frm": "dsp", "to": "kafka", "kind": "event", "label": "dispatch.invitation.sent.v1"},
                    {"n": "20", "frm": "kafka", "to": "rt", "kind": "event", "label": "推送邀请（无连接转 PUSH）"},
                    {"n": "21", "frm": "rt", "to": "dapp", "kind": "ws", "label": "WS {invite_id, trip 摘要, pickup, expire_at}"},
                    {"n": "22", "frm": "dapp", "to": "gw", "kind": "sync", "label": "POST /v1/driver/invitations/{invite_id}/acceptance"},
                    {"n": "23", "frm": "gw", "to": "dsp", "kind": "sync", "label": "DispatchService/AcceptInvitation｜CAS PENDING→ACCEPTED"},
                    {"n": "24", "frm": "dsp", "to": "trip", "kind": "sync", "label": "TripService/ConfirmMatch｜权威 CAS DISPATCHING→MATCHED"},
                    {"n": "25", "frm": "trip", "to": "drv", "kind": "sync", "label": "DriverService/SetDriverBusy｜失败由事件兜底"},
                    {"n": "26", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.matched.v1"},
                    {"n": "27", "frm": "dsp", "to": "dapp", "kind": "return", "label": "200 {trip_id, pickup, eta_seconds}"},
                    {"n": "28", "frm": "kafka", "to": "rt", "kind": "event", "label": "trip.matched.v1 → 乘客端推送"},
                    {"n": "29", "frm": "rt", "to": "pax", "kind": "ws", "label": "WS {status=MATCHED, driver, vehicle, location, eta}"},
                    {"n": "30", "frm": "pax", "to": "gw", "kind": "sync", "label": "GET /v1/trips/{trip_id}/progress｜首帧基准校正"},
                ],
            },
            {
                "label": "异常 A1 / A2 / A3：报价过期 · 欠费拦截 · 重复提交",
                "kind": "alt",
                "steps": [
                    {"n": "A1", "frm": "pr", "to": "trip", "kind": "return", "label": "QUOTE_EXPIRED（410）→ trip-service 不下单、不写库"},
                    {"n": "A1", "frm": "trip", "to": "pax", "kind": "return", "label": "410 QUOTE_EXPIRED｜提示「报价已过期，请重新获取」"},
                    {"n": "A2", "frm": "pay", "to": "trip", "kind": "return", "label": "has_unsettled=true + 账单摘要"},
                    {"n": "A2", "frm": "trip", "to": "pax", "kind": "return", "label": "409 UNPAID_BILL_EXISTS｜引导先结清（R-10）"},
                    {"n": "A3", "frm": "gw", "to": "pax", "kind": "return", "label": "200 同一 trip_id（Idempotency-Key 命中，不产生新事件）"},
                ],
            },
            {
                "label": "异常 A4 / A5 / A6 / A7：拒绝 · 超时 · 无候选 · 无人接单（180 秒）",
                "kind": "alt",
                "steps": [
                    {"n": "A4", "frm": "dapp", "to": "dsp", "kind": "sync", "label": "rejection → 邀请 REJECTED，立即邀请下一位（不重置 15 秒）"},
                    {"n": "A5", "frm": "dsp", "to": "kafka", "kind": "event", "label": "dispatch.invitation.expired.v1 → round+1，第 2 轮起扩圈至 5km"},
                    {"n": "A6", "frm": "dsp", "to": "kafka", "kind": "event", "label": "dispatch.failed.v1{reason=NO_CANDIDATE / ROUNDS_EXHAUSTED}"},
                    {"n": "A7", "frm": "kafka", "to": "trip", "kind": "event", "label": "消费 dispatch.failed.v1 → CAS DISPATCHING→EXPIRED"},
                    {"n": "A7", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.expired.v1（无费用，可重新叫车）"},
                    {"n": "A7", "frm": "kafka", "to": "pax", "kind": "event", "label": "通知「附近暂无车辆」+ 建议重新叫车"},
                ],
            },
            {
                "label": "异常 A8 / A9 / A10：接单与取消冲突 · 一车多邀 · 位置服务降级",
                "kind": "alt",
                "steps": [
                    {"n": "A8", "frm": "trip", "to": "dsp", "kind": "return", "label": "409 TRIP_STATE_CONFLICT（行程已 CANCELLING/CANCELLED）"},
                    {"n": "A8", "frm": "dsp", "to": "dapp", "kind": "return", "label": "409「该订单已取消」；邀请置 CANCELLED、释放派单锁、司机不计责"},
                    {"n": "A9", "frm": "dsp", "to": "loc", "kind": "sync", "label": "SETNX driver:{id}:dispatch_lock（TTL 20s）失败 → 跳过该司机"},
                    {"n": "A10", "frm": "dsp", "to": "loc", "kind": "sync", "label": "熔断 → 改用 60 秒内候选快照；仍为空则 dispatch.failed{NO_LOCATION_DATA}"},
                ],
            },
        ],
        "footer": "对应报告 §4.2：正常路径 30 步 + 异常 A1–A10；接口名、事件名与 contracts/ 一致。",
    }


def flow2():
    lanes = [
        ("pax", "乘客 App", "客户端"),
        ("gw", "api-gateway", "接入组件"),
        ("trip", "trip-service", "行程"),
        ("dsp", "dispatch-service", "派单"),
        ("drv", "driver-service", "运力"),
        ("pr", "pricing-service", "计价"),
        ("pay", "payment-service", "支付"),
        ("chan", "支付渠道", "外部系统"),
        ("kafka", "Kafka", "事件总线"),
        ("notif", "notification-service", "通知"),
        ("rt", "realtime-gateway", "接入组件"),
        ("dapp", "司机 App", "客户端"),
    ]
    return {
        "title": "流程二：取消与重新叫车（含异常分支）",
        "subtitle": "目标：按「取消发生在哪个阶段」给出确定的判责与费用；取消不阻塞乘客，支持一键重新叫车。"
                    " 规则：免费等待 5 分钟（R-06）、取消费 0/5 元（R-07）、上车后禁止自助取消（R-08）、司机取消不收费（R-11）",
        "participants": lanes,
        "blocks": [
            {
                "label": "正常路径：受理取消（异步判责）→ 计费与扣款 → 结案 → 重新叫车",
                "steps": [
                    {"n": "1", "frm": "pax", "to": "gw", "kind": "sync", "label": "POST /v1/trips/{trip_id}/cancellations｜{reason_code}"},
                    {"n": "2", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/RequestCancellation｜归属校验"},
                    {"n": "3", "frm": "trip", "to": "trip", "kind": "self", "label": "计算 phase；CAS→CANCELLING；写 cancellation(PENDING) + outbox"},
                    {"n": "4", "frm": "trip", "to": "pax", "kind": "return", "label": "202 {cancellation_id, status=PENDING, phase}（结果异步）"},
                    {"n": "5", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.cancellation.requested.v1"},
                    {"n": "6", "frm": "kafka", "to": "pr", "kind": "event", "label": "消费 → CalculateCancellationFee"},
                    {"n": "7", "frm": "pr", "to": "pr", "kind": "self", "label": "读 cancel_fee_rule(city) + 免费等待 5 分钟 → amount"},
                    {"n": "8", "frm": "pr", "to": "kafka", "kind": "event", "label": "pricing.cancel_fee.calculated.v1"},
                    {"n": "9", "frm": "kafka", "to": "pay", "kind": "event", "label": "消费 → amount>0 生成取消费账单 / 免密代扣"},
                    {"n": "10", "frm": "pay", "to": "chan", "kind": "sync", "label": "免密代扣（HTTPS）"},
                    {"n": "11", "frm": "pay", "to": "kafka", "kind": "event", "label": "payment.succeeded.v1（或 payment.failed.v1）"},
                    {"n": "12", "frm": "kafka", "to": "trip", "kind": "event", "label": "消费费用结果 → cancellation=ACCEPTED（fee_amount / fee_status）"},
                    {"n": "13", "frm": "trip", "to": "trip", "kind": "self", "label": "CAS CANCELLING→CANCELLED + trip_state_log"},
                    {"n": "14", "frm": "trip", "to": "dsp", "kind": "sync", "label": "DispatchService/CancelDispatch"},
                    {"n": "15", "frm": "dsp", "to": "dsp", "kind": "self", "label": "dispatch_task→ABORTED；PENDING 邀请→CANCELLED；释放派单锁"},
                    {"n": "16", "frm": "trip", "to": "drv", "kind": "sync", "label": "DriverService/SetDriverFree｜司机回到 ONLINE"},
                    {"n": "17", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.cancellation.accepted.v1"},
                    {"n": "18", "frm": "kafka", "to": "notif", "kind": "event", "label": "通知乘客与司机（含费用及原因说明）"},
                    {"n": "19", "frm": "kafka", "to": "rt", "kind": "event", "label": "推送取消结果"},
                    {"n": "20", "frm": "rt", "to": "pax", "kind": "ws", "label": "WS {status=CANCELLED, fee_amount, can_rebook}"},
                    {"n": "21", "frm": "pax", "to": "gw", "kind": "sync", "label": "POST /v1/trips/{trip_id}/rebook｜一键重新叫车"},
                    {"n": "22", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/RebookTrip｜校验原行程已终态"},
                    {"n": "23", "frm": "trip", "to": "pr", "kind": "sync", "label": "PricingService/CreateQuote｜重新报价（调价可能变化）"},
                    {"n": "24", "frm": "trip", "to": "trip", "kind": "self", "label": "创建新 trip(REQUESTED, rebook_from_trip_id) + outbox"},
                    {"n": "25", "frm": "trip", "to": "pax", "kind": "return", "label": "201 {new_trip_id, quote, status=REQUESTED}"},
                    {"n": "26", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.requested.v1 → 进入流程一的撮合"},
                ],
            },
            {
                "label": "异常 B1 / B2：上车后取消（需人工介入）· 取消与接单并发",
                "kind": "alt",
                "steps": [
                    {"n": "B1", "frm": "trip", "to": "pax", "kind": "return", "label": "409 OPS_INTERVENE_REQUIRED（RIDING 不允许自助取消，R-08）"},
                    {"n": "B1", "frm": "pax", "to": "gw", "kind": "sync", "label": "转客服 → POST /v1/ops/trips/{id}/interventions（写审计）"},
                    {"n": "B2", "frm": "dsp", "to": "trip", "kind": "sync", "label": "ConfirmMatch 与 RequestCancellation 同时提交"},
                    {"n": "B2", "frm": "trip", "to": "dsp", "kind": "return", "label": "版本 CAS 只有一个成功；失败方 409，按当前状态补偿"},
                ],
            },
            {
                "label": "异常 B3 / B4 / B6 / B8：扣款失败 · 司机取消 · 等待超时 · 费用超时",
                "kind": "alt",
                "steps": [
                    {"n": "B3", "frm": "pay", "to": "kafka", "kind": "event", "label": "payment.failed.v1 → 生成欠费账单；trip 仍结案，fee_status=UNPAID"},
                    {"n": "B4", "frm": "dapp", "to": "trip", "kind": "sync", "label": "司机取消（initiator=DRIVER）：0 元、不结案 → 行程回 DISPATCHING 重新派单（R-11）"},
                    {"n": "B6", "frm": "pr", "to": "kafka", "kind": "event", "label": "等待超时 → amount=5.00，费用项 WAITING_TIMEOUT"},
                    {"n": "B8", "frm": "trip", "to": "trip", "kind": "self", "label": "30 秒未收到费用结果 → 按 0 元结案并打标 fee_pending=true，对账补账"},
                ],
            },
        ],
        "footer": "对应报告 §4.3：正常路径 26 步 + 异常 B1–B9；取消「同步受理 + 异步判责」是本流程的关键设计。",
    }


def flow3():
    lanes = [
        ("dapp", "司机 App", "客户端"),
        ("gw", "api-gateway", "接入组件"),
        ("trip", "trip-service", "行程"),
        ("loc", "location-service", "位置"),
        ("rt", "realtime-gateway", "接入组件"),
        ("pax", "乘客 App", "客户端"),
        ("kafka", "Kafka", "事件总线"),
        ("pr", "pricing-service", "计价"),
        ("map", "地图服务", "外部系统"),
        ("pay", "payment-service", "支付"),
        ("chan", "支付渠道", "外部系统"),
        ("notif", "notification-service", "通知"),
    ]
    return {
        "title": "流程三：接驾、上车与支付（含异常分支）",
        "subtitle": "目标：完成「到达—上车—行程—结束—计费—支付」闭环。计量口径：distance 来自轨迹、duration = ended_at − boarded_at、"
                    "waiting 为超出免费等待部分；三者与费用项一起封存，保证账单可复算。",
        "participants": lanes,
        "blocks": [
            {
                "label": "正常路径：到达 → 上车 → 行程中（位置推送）→ 结束 → 计费 → 支付",
                "steps": [
                    {"n": "1", "frm": "dapp", "to": "gw", "kind": "sync", "label": "POST /v1/trips/{trip_id}/arrival｜{lat, lng}"},
                    {"n": "2", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/RecordArrival"},
                    {"n": "3", "frm": "trip", "to": "trip", "kind": "self", "label": "校验距上车点 ≤200m；CAS→DRIVER_ARRIVED；free_wait_until=+5min"},
                    {"n": "4", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.arrived.v1"},
                    {"n": "5", "frm": "kafka", "to": "notif", "kind": "event", "label": "短信 + App 推送「司机已到达，免费等待 5 分钟」"},
                    {"n": "6", "frm": "kafka", "to": "rt", "kind": "event", "label": "推送到达事件与车辆位置"},
                    {"n": "7", "frm": "rt", "to": "pax", "kind": "ws", "label": "WS {status=DRIVER_ARRIVED, free_wait_until}"},
                    {"n": "8", "frm": "dapp", "to": "gw", "kind": "sync", "label": "POST /v1/trips/{trip_id}/boarding"},
                    {"n": "9", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/RecordBoarding"},
                    {"n": "10", "frm": "trip", "to": "trip", "kind": "self", "label": "校验 DRIVER_ARRIVED；记录 waiting_s；CAS→RIDING"},
                    {"n": "11", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.boarded.v1（计费起点 = boarded_at）"},
                    {"n": "12", "frm": "kafka", "to": "loc", "kind": "event", "label": "创建 track(trip_id) 开始记录轨迹"},
                    {"n": "13", "frm": "dapp", "to": "rt", "kind": "ws", "label": "WS 位置上报（2 秒/条，可 5 条批量）"},
                    {"n": "14", "frm": "rt", "to": "kafka", "kind": "event", "label": "location.reported.v1（按 driver_id 分区，2.5 QPS 限流）"},
                    {"n": "15", "frm": "kafka", "to": "loc", "kind": "event", "label": "批量写 Redis GEO（最新位置）+ 追加 track_point"},
                    {"n": "16", "frm": "loc", "to": "kafka", "kind": "event", "label": "location.updated.v1（仅行程中司机）"},
                    {"n": "17", "frm": "kafka", "to": "rt", "kind": "event", "label": "转发位置更新"},
                    {"n": "18", "frm": "rt", "to": "pax", "kind": "ws", "label": "WS {lat, lng, eta_seconds}｜乘客看车辆位置与进度"},
                    {"n": "19", "frm": "dapp", "to": "gw", "kind": "sync", "label": "POST /v1/trips/{trip_id}/completion｜{dest_lat, dest_lng}"},
                    {"n": "20", "frm": "gw", "to": "trip", "kind": "sync", "label": "TripService/CompleteTrip"},
                    {"n": "21", "frm": "trip", "to": "trip", "kind": "self", "label": "从 track 汇总计量 → 写 trip_metering（封存）→ CAS→ENDED"},
                    {"n": "22", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.ended.v1（含 distance_m / duration_s / waiting_s）"},
                    {"n": "23", "frm": "kafka", "to": "pr", "kind": "event", "label": "消费 → PricingService/CalculateFare"},
                    {"n": "24", "frm": "pr", "to": "map", "kind": "sync", "label": "路网校正（同一 OD 命中缓存则跳过）"},
                    {"n": "25", "frm": "pr", "to": "pr", "kind": "self", "label": "按 price_rule 生成 fare(ACTIVE, fare_version=1) 与费用项"},
                    {"n": "26", "frm": "pr", "to": "kafka", "kind": "event", "label": "fare.calculated.v1"},
                    {"n": "27", "frm": "kafka", "to": "pay", "kind": "event", "label": "生成 bill(UNPAID, due_at=+30min)"},
                    {"n": "28", "frm": "pay", "to": "kafka", "kind": "event", "label": "payment.bill.created.v1"},
                    {"n": "29", "frm": "kafka", "to": "notif", "kind": "event", "label": "推送账单（App 推送 + 站内信 + WS 卡片）"},
                    {"n": "30", "frm": "pax", "to": "gw", "kind": "sync", "label": "POST /v1/bills/{bill_id}/payments｜{channel} + Idempotency-Key"},
                    {"n": "31", "frm": "gw", "to": "pay", "kind": "sync", "label": "PaymentService/CreatePayment"},
                    {"n": "32", "frm": "pay", "to": "chan", "kind": "sync", "label": "统一下单（HTTPS，渠道 SDK）"},
                    {"n": "33", "frm": "pay", "to": "pax", "kind": "return", "label": "200 {payment_id, pay_params}｜唤起收银台"},
                    {"n": "34", "frm": "chan", "to": "pay", "kind": "event", "label": "支付结果回调（webhook）"},
                    {"n": "35", "frm": "pay", "to": "pay", "kind": "self", "label": "验签 + channel_txn_id 幂等 → bill=PAID、payment=SUCCEEDED"},
                    {"n": "36", "frm": "pay", "to": "kafka", "kind": "event", "label": "payment.succeeded.v1（同时记 settlement）"},
                    {"n": "37", "frm": "kafka", "to": "trip", "kind": "event", "label": "CAS ENDED→PAID"},
                    {"n": "38", "frm": "trip", "to": "kafka", "kind": "event", "label": "trip.paid.v1（终态）"},
                    {"n": "39", "frm": "kafka", "to": "notif", "kind": "event", "label": "推送收据；ops-service 同步更新业务记录读模型"},
                ],
            },
            {
                "label": "异常 C1 / C2 / C3：到达异常 · 未到达就上车 · 乘客爽约",
                "kind": "alt",
                "steps": [
                    {"n": "C1", "frm": "trip", "to": "trip", "kind": "self", "label": "距上车点 >200m 仍接受到达，但打标 arrival_anomaly=true（计入考核）"},
                    {"n": "C2", "frm": "trip", "to": "dapp", "kind": "return", "label": "409 TRIP_STATE_CONFLICT｜「请先上报到达」"},
                    {"n": "C3", "frm": "dapp", "to": "trip", "kind": "sync", "label": "PASSENGER_NO_SHOW 取消 → phase=AFTER_ARRIVAL → 取消费 5 元（走流程二）"},
                ],
            },
            {
                "label": "异常 C4 / C5 / C8：支付失败 · 回调丢失 · 代扣失败",
                "kind": "alt",
                "steps": [
                    {"n": "C4", "frm": "pay", "to": "kafka", "kind": "event", "label": "payment.failed.v1{channel_code} → 账单保持 UNPAID，可换渠道重试（≤3 次）"},
                    {"n": "C5", "frm": "pay", "to": "chan", "kind": "sync", "label": "回调丢失：每 30 秒主动查单（QueryChannel），按 channel_txn_id 幂等补记"},
                    {"n": "C8", "frm": "pay", "to": "kafka", "kind": "event", "label": "免密代扣失败 → 生成待支付账单 + 提醒手动支付，不阻塞行程结束"},
                ],
            },
            {
                "label": "异常 C6 / C7 / C9 / C10：计量缺失 · 计费争议 · 位置服务不可用 · 司机未结束",
                "kind": "alt",
                "steps": [
                    {"n": "C6", "frm": "trip", "to": "pr", "kind": "event", "label": "位置断流 → 直线距离 ×1.4 补算，estimate_mode=HAVERSINE"},
                    {"n": "C7", "frm": "pax", "to": "gw", "kind": "sync", "label": "计费申诉 → ops 介入 → fare_version+1 调整 + Refund 差额（全程审计）"},
                    {"n": "C9", "frm": "rt", "to": "pax", "kind": "ws", "label": "位置服务不可用：停止位置推送，降级为「状态 + 最后已知位置」"},
                    {"n": "C10", "frm": "trip", "to": "trip", "kind": "self", "label": "RIDING 超预计时长 3 倍或轨迹静止 30 分钟 → 标记 stale，通知运营介入"},
                ],
            },
        ],
        "footer": "对应报告 §4.4：正常路径 39 步 + 异常 C1–C10；计量封存（trip_metering）保证账单可复算、争议可回溯。",
    }


GENERATORS = {
    "context-map": gen_context_map,
    "data-model": gen_data_model,
    "seq-quote-dispatch": lambda: gen_sequence(flow1(), "seq-quote-dispatch.png"),
    "seq-cancel-rebook": lambda: gen_sequence(flow2(), "seq-cancel-rebook.png"),
    "seq-pickup-payment": lambda: gen_sequence(flow3(), "seq-pickup-payment.png"),
}
