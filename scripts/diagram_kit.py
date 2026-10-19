"""Pillow 绘图工具箱：为设计图提供矩形、箭头、虚线、图例等原语。

设计约定
--------
* 所有坐标以"逻辑像素"给出，内部按 ``scale`` 放大后绘制，因此同一份布局代码
  可以输出任意清晰度的 PNG（默认 2 倍，即逻辑 1400 px → 实际 2800 px）。
* 中文字体使用系统自带 Microsoft YaHei（msyh.ttc / msyhbd.ttc），
  无需安装 Graphviz、浏览器或任何第三方绘图库。
* 颜色集中定义在 ``PALETTE``，保证 6 张图的配色一致。
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

# 统一配色：核心域=橙，支撑域=蓝，通用域=绿，接入=深灰，数据/基础设施=浅灰，外部=黄
PALETTE = {
    "core_bg": "#fff1e6",
    "core_border": "#d9480f",
    "core_header": "#f08c00",
    "support_bg": "#e7f5ff",
    "support_border": "#1864ab",
    "support_header": "#1c7ed6",
    "generic_bg": "#ebfbee",
    "generic_border": "#2b8a3e",
    "generic_header": "#40c057",
    "gateway_bg": "#495057",
    "gateway_border": "#212529",
    "gw_text": "#ffffff",
    "data_bg": "#f1f3f5",
    "data_border": "#868e96",
    "external_bg": "#fff9db",
    "external_border": "#f59f00",
    "ink": "#212529",
    "muted": "#495057",
    "light": "#adb5bd",
    "sync": "#1864ab",
    "async": "#d6336c",
    "ws": "#0b7285",
    "route": "#7048e8",
    "owner": "#868e96",
    "white": "#ffffff",
}

_FONT_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)
    return _FONT_CACHE[key]


@dataclass
class Canvas:
    """逻辑坐标画布，``scale`` 倍超采样输出。"""

    width: int
    height: int
    scale: int = 2
    background: str = "#ffffff"

    def __post_init__(self) -> None:
        self.image = Image.new("RGB", (self.width * self.scale, self.height * self.scale), self.background)
        self.draw = ImageDraw.Draw(self.image)

    # ---------------------------------------------------------------- 基本换算

    def _p(self, value: float) -> float:
        return value * self.scale

    def _box(self, x, y, w, h):
        s = self.scale
        return [x * s, y * s, (x + w) * s, (y + h) * s]

    # ---------------------------------------------------------------- 文本

    def text_width(self, content: str, size: int = 12, bold: bool = False) -> float:
        return self.draw.textlength(content, font=font(int(size * self.scale), bold)) / self.scale

    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: int = 12,
        bold: bool = False,
        color: str | None = None,
        anchor: str = "la",
        spacing: float | None = None,
    ) -> None:
        """绘制（可多行）文本。``anchor`` 语义同 Pillow：la/ma/ra/mm/mt/mb 等。"""
        color = color or PALETTE["ink"]
        f = font(int(size * self.scale), bold)
        line_h = size * (1.42 if spacing is None else spacing)
        lines = str(content).split("\n")
        for index, line in enumerate(lines):
            dy = y + index * line_h
            self.draw.text((self._p(x), self._p(dy)), line, font=f, fill=color, anchor=anchor)

    # ---------------------------------------------------------------- 形状

    def rect(self, x, y, w, h, fill=None, outline=None, width: float = 1.0, radius: float = 4.0):
        self.draw.rounded_rectangle(
            self._box(x, y, w, h),
            radius=self._p(radius),
            fill=fill,
            outline=outline,
            width=max(1, int(round(width * self.scale))),
        )

    def band(self, x, y, w, h, fill="#f8f9fa", outline="#dee2e6", width=1.0, radius=6.0):
        self.rect(x, y, w, h, fill=fill, outline=outline, width=width, radius=radius)

    # ---------------------------------------------------------------- 线与箭头

    def line(self, points, color="#212529", width: float = 1.2, dash: tuple[float, float] | None = None):
        pts = [(self._p(px), self._p(py)) for px, py in points]
        w = max(1, int(round(width * self.scale)))
        if not dash:
            self.draw.line(pts, fill=color, width=w, joint="curve")
            return
        on, off = dash
        for start, end in zip(pts, pts[1:]):
            self._dashed_segment(start, end, color, w, on * self.scale, off * self.scale)

    def _dashed_segment(self, start, end, color, width, on, off):
        import math

        x1, y1 = start
        x2, y2 = end
        total = math.hypot(x2 - x1, y2 - y1)
        if total == 0:
            return
        ux, uy = (x2 - x1) / total, (y2 - y1) / total
        pos = 0.0
        while pos < total:
            seg_end = min(pos + on, total)
            self.draw.line(
                [(x1 + ux * pos, y1 + uy * pos), (x1 + ux * seg_end, y1 + uy * seg_end)],
                fill=color,
                width=width,
            )
            pos = seg_end + off

    def arrow(
        self,
        points,
        color="#212529",
        width: float = 1.4,
        dash: tuple[float, float] | None = None,
        head: str = "end",
        head_size: float = 6.0,
    ):
        """折线箭头。``head`` 取 end / start / both / none。"""
        import math

        pts = [tuple(p) for p in points]
        if not dash:
            self.line(pts, color=color, width=width)

        def draw_head(tip, previous):
            ang = math.atan2(tip[1] - previous[1], tip[0] - previous[0])
            size = head_size
            left = (tip[0] - size * math.cos(ang - 0.42), tip[1] - size * math.sin(ang - 0.42))
            right = (tip[0] - size * math.cos(ang + 0.42), tip[1] - size * math.sin(ang + 0.42))
            self.draw.polygon(
                [(self._p(tip[0]), self._p(tip[1])), (self._p(left[0]), self._p(left[1])), (self._p(right[0]), self._p(right[1]))],
                fill=color,
            )

        if head in ("end", "both"):
            draw_head(pts[-1], pts[-2])
        if head in ("start", "both"):
            draw_head(pts[0], pts[1])
        if dash:
            # 虚线箭头：先画头，再画虚线体和箭头之间的空隙
            self.line(pts, color=color, width=width, dash=dash)

    # ---------------------------------------------------------------- 复合元素

    def pill(self, x, y, w, h, fill, text_color="#ffffff", content="", size=9.5, bold=True):
        self.rect(x, y, w, h, fill=fill, outline=None, radius=h / 2)
        self.text(x + w / 2, y + h / 2, content, size=size, bold=bold, color=text_color, anchor="mm")

    def tag(self, x, y, content, size=9, fg="#495057", bg="#ffffff", border="#ced4da", pad=4):
        w = self.text_width(content, size) + pad * 2
        h = size + pad * 1.6
        self.rect(x, y, w, h, fill=bg, outline=border, width=0.8, radius=3)
        self.text(x + w / 2, y + h / 2, content, size=size, color=fg, anchor="mm")
        return w, h

    def numbered(self, x, y, order: str, color="#7048e8", size=9.5, r=7.0):
        """带数字/序号的圆标。"""
        self.draw.ellipse(self._box(x - r, y - r, r * 2, r * 2), fill=color, outline="#ffffff", width=max(1, int(self.scale)))
        self.text(x, y, order, size=size, bold=True, color="#ffffff", anchor="mm")

    def save(self, path: str) -> None:
        import os

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.image.save(path, format="PNG", optimize=True)
