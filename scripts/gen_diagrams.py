"""生成 Lab 2 的全部设计图（architecture.png 与 docs/images/*.png）。

用法：
    python scripts/gen_diagrams.py                    # 生成全部 6 张图
    python scripts/gen_diagrams.py --only architecture
    python scripts/gen_diagrams.py --only data-model,sequences

只依赖 Pillow 与系统自带中文字体，不联网、不需要 Graphviz 或浏览器。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diagram_kit import PALETTE as P  # noqa: E402
from diagram_kit import Canvas  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "docs", "images")


# --------------------------------------------------------------------------- 通用小部件


def band_title(c: Canvas, x, y, w, label, note=""):
    """绘制分层的标题条。"""
    c.text(x + 10, y + 5, label, size=10.5, bold=True, color=P["muted"])
    if note:
        c.text(x + 10 + c.text_width(label, 10.5, True) + 8, y + 6, note, size=9, color=P["light"])


def container(c: Canvas, x, y, w, h, title, kind, badges=True):
    """绘制子领域容器（带类型徽标与 GW / MQ 标记）。"""
    palette = {
        "core": (P["core_bg"], P["core_border"], P["core_header"]),
        "support": (P["support_bg"], P["support_border"], P["support_header"]),
        "generic": (P["generic_bg"], P["generic_border"], P["generic_header"]),
    }[kind]
    bg, border, header = palette
    c.rect(x, y, w, h, fill=bg, outline=border, width=1.4, radius=8)
    c.rect(x, y, w, 26, fill=header, outline=None, radius=8)
    c.text(x + 10, y + 13, title, size=11, bold=True, color="#ffffff", anchor="lm")
    if not badges:
        return
    w_badge = c.text_width(kind_label(kind), 8.5) + 12
    c.pill(x + w - w_badge - 58, y + 4.5, w_badge, 17, fill="#ffffff", text_color=border, content=kind_label(kind), size=8.5)
    c.pill(x + w - 52, y + 4.5, 26, 17, fill="#ffffff", text_color=border, content="GW", size=8.5)
    c.pill(x + w - 24, y + 4.5, 16, 17, fill="#ffffff", text_color=border, content="MQ", size=8.5)


def kind_label(kind):
    return {"core": "核心域", "support": "支撑域", "generic": "通用域"}[kind]


def service_box(c: Canvas, x, y, w, h, name, cn, duty, caps=""):
    c.rect(x, y, w, h, fill="#ffffff", outline="#ced4da", width=1.0, radius=6)
    c.text(x + 10, y + 8, name, size=11, bold=True, color=P["ink"])
    c.text(x + 10 + c.text_width(name, 11, True) + 6, y + 10, cn, size=9, color=P["muted"])
    c.text(x + 10, y + 25, duty, size=8.4, color=P["muted"], spacing=1.35)
    if caps:
        c.text(x + w - 10, y + h - 9, caps, size=7.8, color=P["light"], anchor="rb")


# --------------------------------------------------------------------------- 架构图


def gen_architecture():
    W, H = 1400, 1210
    c = Canvas(W, H, scale=2)
    c.text(W / 2, 14, "网约车平台系统整体架构图", size=21, bold=True, color=P["ink"], anchor="ma")
    c.text(
        W / 2,
        44,
        "第 32 组 · 9 个业务微服务 / 6 个子领域 · 上海（SH）杭州（HZ）南京（NJ）三城单元化部署 · 峰值 叫车 1k/s、位置上报 20k/s、状态查询 10k/s",
        size=9.2,
        color=P["muted"],
        anchor="ma",
    )

    # ---------------- 客户端层
    c.band(30, 56, 1340, 72, fill="#f8f9fa", outline="#dee2e6")
    band_title(c, 30, 56, 1340, "客户端层", "只使用 REST + WebSocket 两种协议，不直连内部服务")
    clients = [
        ("乘客端", "App / H5 / 小程序", 60, 330),
        ("司机端", "司机 App（含位置上报）", 490, 330),
        ("运营后台", "Web（检索 / 导出 / 人工介入）", 940, 330),
    ]
    for title, sub, x, w in clients:
        c.rect(x, 78, w, 42, fill="#ffffff", outline=P["gateway_border"], width=1.1, radius=6)
        c.text(x + w / 2, 89, title, size=10.5, bold=True, color=P["ink"], anchor="ma")
        c.text(x + w / 2, 105, sub, size=8.4, color=P["muted"], anchor="ma")

    # ---------------- 接入层
    c.band(30, 138, 1340, 74, fill="#f1f3f5", outline="#ced4da")
    band_title(c, 30, 138, 1340, "接入层", "无业务状态，可水平复制；鉴权 / 限流 / 路由 / 连接管理")
    c.rect(60, 160, 330, 46, fill=P["gateway_bg"], outline=P["gateway_border"], width=1.2, radius=6)
    c.text(70, 167, "realtime-gateway", size=10.5, bold=True, color=P["gw_text"])
    c.text(70, 184, "WebSocket 长连接 · 订阅 · 位置上行 · 推送下行 · 断线补推", size=8.2, color="#e9ecef")
    c.rect(490, 160, 860, 46, fill=P["gateway_bg"], outline=P["gateway_border"], width=1.2, radius=6)
    c.text(500, 167, "api-gateway", size=10.5, bold=True, color=P["gw_text"])
    c.text(590, 169, "JWT 校验 · 角色/归属授权 · 令牌桶限流 · 幂等键透传 · 路由与聚合 · OpenAPI /v1", size=8.2, color="#e9ecef")

    # ---------------- 客户端 → 接入
    c.arrow([(350, 120), (540, 160)], color=P["sync"], width=1.5)
    c.text(452, 130, "REST", size=7.6, color=P["sync"])
    c.arrow([(655, 120), (655, 160)], color=P["sync"], width=1.5)
    c.text(662, 138, "REST", size=7.6, color=P["sync"])
    c.arrow([(1105, 120), (1105, 160)], color=P["sync"], width=1.5)
    c.text(1112, 138, "REST", size=7.6, color=P["sync"])
    c.arrow([(225, 120), (225, 160)], color=P["ws"], width=1.5, dash=(5, 3))
    c.text(232, 138, "WS", size=7.6, color=P["ws"])
    c.arrow([(500, 120), (320, 160)], color=P["ws"], width=1.5, dash=(5, 3))
    c.text(368, 140, "WS", size=7.6, color=P["ws"])

    # ---------------- 网关总线
    c.line([(25, 226), (1364, 226)], color=P["light"], width=1.6)
    c.arrow([(225, 206), (225, 226)], color=P["light"], width=1.4, head="none")
    c.arrow([(920, 206), (920, 226)], color=P["light"], width=1.4, head="none")
    for x in (245, 695, 1145):
        c.arrow([(x, 226), (x, 260)], color=P["light"], width=1.4)
    c.text(1000, 229, "服务网格：网关 → 服务（gRPC / mTLS）", size=8, color=P["muted"])

    # ---------------- 服务层
    band_title(c, 30, 234, 1340, "业务服务层", "按子领域分组；GW = 经网关对外暴露，MQ = 接入 Kafka 事件总线（全部服务均接入）")

    cols = [40, 490, 940]
    cont_w = 410
    # row1: 计价 | 行程 | 运力
    container(c, cols[0], 260, cont_w, 198, "计价结算域", "core")
    container(c, cols[1], 260, cont_w, 198, "行程交易域", "core")
    container(c, cols[2], 260, cont_w, 198, "运力与位置域", "support")
    # row2: 身份 | 运营 | 通知
    container(c, cols[0], 478, cont_w, 182, "身份与账户域", "generic")
    container(c, cols[1], 478, cont_w, 182, "运营支撑域", "support")
    container(c, cols[2], 478, cont_w, 182, "通知触达域", "generic")

    inner_x = [x + 16 for x in cols]
    inner_w = cont_w - 32

    service_box(c, inner_x[0], 300, inner_w, 66, "pricing-service", "计价服务",
                "路线与 ETA 预估 · 报价 · 行程费用 · 取消费规则", "C07 C08 C18 C20")
    service_box(c, inner_x[0], 380, inner_w, 70, "payment-service", "支付账单服务",
                "账单 · 支付单与渠道回调 · 退款 · 欠费判定 · 结算流水", "C23 C24 C25")
    service_box(c, inner_x[1], 300, inner_w, 66, "trip-service", "行程服务",
                "行程状态机（唯一权威）· 确认接单 · 取消裁决 · 进度视图", "C09 C10 C11 C19")
    service_box(c, inner_x[1], 380, inner_w, 70, "dispatch-service", "派单服务",
                "候选筛选与排序 · 邀请与超时重派 · 扩圈 · 并发裁决", "C12 C13 C14")
    service_box(c, inner_x[2], 300, inner_w, 66, "driver-service", "运力服务",
                "司机档案 · 车辆绑定 · 资质审核 · 在线状态与接单资格", "C04 C05")
    service_box(c, inner_x[2], 380, inner_w, 70, "location-service", "位置服务",
                "最新位置索引（Redis GEO）· 邻近查询 · 轨迹留存与回放", "C06 C22")

    service_box(c, inner_x[0], 512, inner_w, 58, "identity-service", "账户认证服务",
                "账号 · 登录与令牌（JWT/JWKS）· 角色与运营 RBAC · 乘客档案", "C01 C02 C03")
    service_box(c, inner_x[1], 512, inner_w, 58, "ops-service", "运营支撑服务",
                "业务记录读模型（事件投影）· 检索与导出 · 审计日志 · 人工介入", "C15 C16")
    service_box(c, inner_x[2], 512, inner_w, 58, "notification-service", "通知服务",
                "模板 · 短信/推送/站内信 · 去重重试 · 订阅与断线补推", "C26 C27")
    for i, x in enumerate(inner_x):
        c.text(x, 582, {
            0: "数据：account / session / rider_profile / favorite_place / ops_role_binding",
            1: "数据：trip_record_view（只读副本）/ audit_log / intervention_ticket / export_job",
            2: "数据：template / notification_message / subscription",
        }[i], size=7.8, color=P["light"])
        c.text(x, 594, {
            0: "对外：POST /v1/auth/*、GET/PUT /v1/me",
            1: "对外：GET /v1/ops/trips、POST /v1/ops/trips/{id}/interventions",
            2: "被调用：SendNotification、RegisterSubscription、GetMissedUpdates",
        }[i], size=7.8, color=P["light"])

    # ---------------- 组间同步协作（编号）
    c.arrow([(490, 322), (452, 322)], color=P["route"], width=1.6)
    c.numbered(471, 322, "1")
    c.arrow([(490, 410), (452, 410)], color=P["route"], width=1.6)
    c.numbered(471, 410, "2")
    c.arrow([(898, 322), (938, 322)], color=P["route"], width=1.6)
    c.numbered(918, 322, "3")
    c.arrow([(898, 410), (938, 410)], color=P["route"], width=1.6)
    c.numbered(918, 410, "4")
    c.arrow([(800, 478), (800, 452)], color=P["route"], width=1.6)
    c.numbered(800, 465, "5")
    c.arrow([(695, 380), (695, 366)], color=P["route"], width=1.6, head="both")
    c.numbered(695, 373, "6", r=5.0, size=7.5)

    # ---------------- Kafka 事件总线
    c.rect(30, 676, 1340, 34, fill="#fff0f6", outline=P["async"], width=1.3, radius=6)
    c.text(44, 693, "Kafka 事件总线（发布/订阅）", size=10.5, bold=True, color=P["async"], anchor="lm")
    c.text(230, 687, "24 个领域事件 · topic = <city>.<event>.v1 · 分区键 trip_id / driver_id · 至少一次投递 + event_id 去重",
           size=8.4, color=P["async"])
    c.text(230, 698, "Outbox（本地事务发件箱）保证「状态已变 ⇒ 事件必发」；消费端幂等；按聚合有序",
           size=8.4, color=P["async"])
    # 行内服务 → Kafka（经列间空隙）
    for gap, left_x, right_x in ((464, 450, 490), (928, 900, 940)):
        c.arrow([(gap, 676), (gap, 446), (right_x - 4, 446), (right_x, 446)], color=P["async"], width=1.3, dash=(4, 3), head="end")
        c.arrow([(gap, 446), (left_x, 446)], color=P["async"], width=1.3, dash=(4, 3), head="end")
    for x in (245, 695, 1145):
        c.arrow([(x, 660), (x, 676)], color=P["async"], width=1.3, dash=(4, 3), head="end")

    # ---------------- 数据层
    c.band(30, 720, 1340, 100, fill="#f8f9fa", outline="#dee2e6")
    band_title(c, 30, 720, 1340, "数据层", "一服务一库（database per service）：每服务独立实例/schema，禁止跨库 JOIN，跨上下文只用 ID 引用 + 事件")
    data = [
        ("PostgreSQL", "trip · dispatch · pricing · payment\ndriver · identity · notification · ops", 40, 330),
        ("Redis", "最新位置 GEO · 报价缓存\n幂等键 · 派单锁 · 进度读缓存", 380, 290),
        ("ClickHouse", "track_point 轨迹点\n运营读模型投影", 680, 280),
        ("对象存储", "证件与头像 · 导出文件\n（预签名 URL 限时访问）", 970, 390),
    ]
    for title, body, x, w in data:
        c.rect(x, 748, w, 62, fill="#ffffff", outline=P["data_border"], width=1.1, radius=6)
        c.text(x + 10, 754, title, size=10, bold=True, color=P["ink"])
        c.text(x + 10, 770, body, size=8.2, color=P["muted"], spacing=1.5)

    # ---------------- 基础设施层
    c.band(30, 830, 1340, 74, fill="#f1f3f5", outline="#ced4da")
    band_title(c, 30, 830, 1340, "基础设施层", "三城各一套单元化部署，城市间故障隔离、按 city_code 路由")
    infra = [
        ("Kubernetes", "SH / HZ / NJ 独立单元", 40, 320),
        ("Nacos", "服务注册 · 配置中心", 380, 290),
        ("可观测", "Prometheus / Grafana\nLoki / Jaeger", 690, 300),
        ("KMS / Secrets", "渠道密钥 · 手机号加密\n内部 mTLS 证书", 1010, 350),
    ]
    for title, body, x, w in infra:
        c.rect(x, 852, w, 44, fill="#ffffff", outline=P["data_border"], width=1.0, radius=5)
        c.text(x + 9, 856, title, size=9.6, bold=True, color=P["ink"])
        c.text(x + 9, 869, body.replace("\n", "  "), size=8, color=P["muted"])

    # ---------------- 外部系统
    c.band(30, 914, 1340, 74, fill=P["external_bg"], outline=P["external_border"])
    band_title(c, 30, 914, 1340, "外部系统", "经服务内适配层以同步 HTTPS 调用，统一设置超时 / 熔断 / 降级（见 §3.4）")
    ext = [
        ("地图服务", "路径规划 · ETA · 地理编码\n调用方：pricing-service（缓存 60s）", 40, 400),
        ("支付渠道", "微信支付 · 支付宝 · 银联\n调用方：payment-service（回调为准）", 470, 400),
        ("短信 / App 推送供应商", "短信 · 厂商推送 · APNs\n调用方：notification-service", 900, 460),
    ]
    for title, body, x, w in ext:
        c.rect(x, 940, w, 42, fill="#ffffff", outline=P["external_border"], width=1.0, radius=5)
        c.text(x + 9, 944, title, size=9.6, bold=True, color="#a05a00")
        c.text(x + 9, 957, body.replace("\n", "  "), size=7.9, color="#8a6100")

    # ---------------- 图例
    c.band(30, 1000, 1340, 190, fill="#ffffff", outline="#dee2e6")
    c.text(42, 1008, "图例", size=11, bold=True, color=P["ink"])

    # 颜色图例（2 列 × 3 行）
    color_items = [
        (P["core_header"], "核心域服务（行程交易、计价结算）"),
        (P["gateway_bg"], "接入组件（无业务状态）"),
        (P["support_header"], "支撑域服务（运力与位置、运营支撑）"),
        (P["data_border"], "数据存储与基础设施"),
        (P["generic_header"], "通用域服务（身份与账户、通知触达）"),
        (P["external_border"], "外部系统"),
    ]
    c.text(42, 1028, "颜色", size=9, bold=True, color=P["muted"])
    for index, (color, label) in enumerate(color_items):
        col = index % 2
        row = index // 2
        x = 42 + col * 310
        y = 1044 + row * 18
        c.rect(x, y + 1, 13, 10, fill=color, outline=None, radius=2)
        c.text(x + 19, y, label, size=8.4, color=P["muted"])

    # 线条图例
    c.text(42, 1104, "线条与箭头", size=9, bold=True, color=P["muted"])
    line_items = [
        (P["sync"], None, "同步请求调用（对外 REST / 对内 gRPC）"),
        (P["light"], None, "网关路由 / 服务网格（经 api-gateway）"),
        (P["async"], (4, 3), "异步消息（Kafka 领域事件，发布/订阅）"),
        (P["ws"], (5, 3), "WebSocket 长连接（位置上行 / 推送下行）"),
        (P["route"], None, "服务间同步协作（编号 ①–⑥，见右栏）"),
    ]
    for index, (color, dash, label) in enumerate(line_items):
        y = 1120 + index * 15
        c.line([(42, y + 5), (82, y + 5)], color=color, width=1.6, dash=dash)
        c.text(90, y, label, size=8.2, color=P["muted"])

    c.text(700, 1008, "服务间同步协作（对应 §3.1 交互表）", size=11, bold=True, color=P["ink"])
    collab = [
        ("1", "trip-service → PricingService/GetQuote（下单校验报价，同步 gRPC）"),
        ("2", "trip-service → PaymentService/HasUnsettledBill（欠费拦截，同步 gRPC）"),
        ("3", "trip-service → DriverService/SetDriverBusy（接单后置忙，同步 + 事件兜底）"),
        ("4", "dispatch-service → LocationService/FindNearbyDrivers（邻近司机，同步 gRPC）"),
        ("5", "ops-service → TripService/ApplyIntervention（人工介入，同步 gRPC）"),
        ("6", "trip-service ↔ dispatch-service：ConfirmMatch（接单裁决）/ CancelDispatch"),
    ]
    for index, (order, label) in enumerate(collab):
        y = 1030 + index * 17
        c.numbered(716, y + 5, order, r=6.2, size=8)
        c.text(730, y, label, size=8.3, color=P["muted"])
    c.text(700, 1150, "其余协作：dispatch→DriverService/BatchCheckEligibility、trip→DriverService/SetDriverFree、"
                      "payment→PricingService/GetFare、api-gateway→IdentityService/JWKS。",
           size=7.8, color=P["light"])
    c.text(700, 1162, "GW：该子领域的服务经 api-gateway 对外暴露 REST 接口；MQ：接入 Kafka 事件总线（9 个服务全部接入）。",
           size=7.8, color=P["light"])

    path = os.path.join(ROOT, "architecture.png")
    c.save(path)
    return path


# --------------------------------------------------------------------------- 入口


GENERATORS = {
    "architecture": gen_architecture,
}


def _load_extra():
    """延迟导入，避免与本模块形成循环依赖。"""
    import diagrams_more

    GENERATORS.update(diagrams_more.GENERATORS)


def main():
    parser = argparse.ArgumentParser(description="生成 Lab 2 设计图")
    parser.add_argument("--only", default="", help="逗号分隔；默认生成全部")
    args = parser.parse_args()
    _load_extra()
    wanted = [name.strip() for name in args.only.split(",") if name.strip()] or list(GENERATORS)
    unknown = [name for name in wanted if name not in GENERATORS]
    if unknown:
        print(f"未知图名：{unknown}；可选：{list(GENERATORS)}")
        return 1
    for name in wanted:
        path = GENERATORS[name]()
        size = os.path.getsize(path)
        print(f"[OK] {name}: {os.path.relpath(path, ROOT)} ({size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
