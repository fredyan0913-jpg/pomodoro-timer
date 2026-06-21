#!/usr/bin/env python3
"""
🍅 番茄时钟 — 布兰迪色系 · macOS 桌面小窗口
纯 Python + tkinter，双击 pomodoro_app.command 启动。
"""

import tkinter as tk
import os
import sys
import subprocess

# ═══════════════════════════════════════════
#  布兰迪色系 (Brandy Palette)
# ═══════════════════════════════════════════
CREAM       = "#FDF5E6"   # 暖奶油底色
CARD        = "#FFF8F0"   # 卡片白
TERRACOTTA  = "#C27A5A"   # 赤陶 / 布兰迪主色 — 专注
HOVER_TERRA = "#B56A4A"   # 深赤陶 hover
CORAL_LIGHT = "#E8C4A8"   # 浅珊瑚
SAGE        = "#8FA88F"   # 灰豆绿 — 短休
HOVER_SAGE  = "#7D9A7D"   # 深豆绿 hover
SLATE       = "#7A9EB5"   # 雾蓝灰 — 长休
HOVER_SLATE = "#6A8FA5"   # 深蓝灰 hover
DARK_BROWN  = "#4A3028"   # 深棕文字
MUTED       = "#A08070"   # 弱化文字
BORDER      = "#E8D5C4"   # 暖色边框
PROGRESS_BG = "#F0E0D0"   # 进度条底色

# ═══════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════
WIN_W = 340
WIN_H = 480

MODES = {
    "work":  {"label": "🍅 专注", "mins": 25, "color": TERRACOTTA, "hover": HOVER_TERRA},
    "break": {"label": "☕ 短休", "mins":  5, "color": SAGE,       "hover": HOVER_SAGE},
    "long":  {"label": "🌴 长休", "mins": 15, "color": SLATE,      "hover": HOVER_SLATE},
}


class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🍅 番茄时钟")
        self.root.resizable(False, False)
        self.root.configure(bg=CREAM)

        # 居中
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws - WIN_W) // 2
        y = (hs - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # 浮动置顶
        self.root.attributes("-topmost", True)

        # ── 状态 ──
        self.mode       = "work"
        self.time_left  = MODES["work"]["mins"] * 60
        self.total_time = self.time_left
        self.running    = False
        self.timer_id   = None
        self.sound      = True

        # 统计
        self.pomo_count  = 0
        self.focus_mins  = 0

        # ── 画布 ──
        self.cv = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                            bg=CREAM, highlightthickness=0)
        self.cv.pack()

        self._draw()
        self._bind_events()
        self._update_display()

    # ═══════════════════════════════════════
    #  绘制
    # ═══════════════════════════════════════
    def _draw(self):
        c = self.cv
        # ── 主卡片 ──
        c.create_rectangle(12, 36, WIN_W - 12, WIN_H - 12,
                           fill=CARD, outline=BORDER, width=1, tags="base")

        # ── 标题 ──
        c.create_text(WIN_W // 2, 18, text="🍅 番茄时钟",
                      fill=DARK_BROWN, font=("PingFang SC", 13, "bold"))

        # ── 计时器方框 ──
        bx1, by1 = 30, 72
        bx2, by2 = WIN_W - 30, 200
        c.create_rectangle(bx1, by1, bx2, by2,
                           fill=CREAM, outline=BORDER, width=1)

        # 时间
        c.create_text(WIN_W // 2, 120, text="25:00",
                      fill=DARK_BROWN, font=("Menlo", 36, "bold"), tags="time")

        # 状态
        c.create_text(WIN_W // 2, 160, text="第 1 个番茄",
                      fill=MUTED, font=("PingFang SC", 11), tags="status")

        # ── 进度条背景 ──
        c.create_rectangle(44, 215, WIN_W - 44, 225,
                           fill=PROGRESS_BG, outline="", tags="pbar_bg")

        # ── 模式按钮 ──
        bw, bh = 88, 34
        gap = 8
        total_w = 3 * bw + 2 * gap
        sx = (WIN_W - total_w) // 2
        by = 250
        self._mode_btns = {}
        for i, (key, cfg) in enumerate(MODES.items()):
            bx = sx + i * (bw + gap)
            self._mode_btns[key] = (bx, by, bx + bw, by + bh)
            c.create_rectangle(bx, by, bx + bw, by + bh,
                               fill=cfg["color"] if key == "work" else CARD,
                               outline=BORDER, width=1, tags=f"mbtn_{key}")
            c.create_text(bx + bw // 2, by + bh // 2,
                          text=cfg["label"],
                          fill="#FFF" if key == "work" else DARK_BROWN,
                          font=("PingFang SC", 11), tags=f"mbtn_{key}")

        # ── 控制按钮 ──
        cy = 310
        ch = 44
        # 左: 重置   中: 开始/暂停   右: 跳过
        self._ctrl = {
            "reset": (28, cy, 110, cy + ch),
            "play":  (115, cy, WIN_W - 115, cy + ch),
            "skip":  (WIN_W - 110, cy, WIN_W - 28, cy + ch),
        }

        rx1, ry1, rx2, ry2 = self._ctrl["reset"]
        c.create_rectangle(rx1, ry1, rx2, ry2,
                           fill=CARD, outline=BORDER, width=1, tags="btn_reset")
        c.create_text((rx1 + rx2) // 2, (ry1 + ry2) // 2,
                      text="↺ 重置", fill=DARK_BROWN,
                      font=("PingFang SC", 12), tags="btn_reset")

        px1, py1, px2, py2 = self._ctrl["play"]
        c.create_rectangle(px1, py1, px2, py2,
                           fill=TERRACOTTA, outline="", tags="btn_play")
        c.create_text((px1 + px2) // 2, (py1 + py2) // 2,
                      text="▶  开始", fill="#FFF",
                      font=("PingFang SC", 14, "bold"), tags="btn_play")

        sx1, sy1, sx2, sy2 = self._ctrl["skip"]
        c.create_rectangle(sx1, sy1, sx2, sy2,
                           fill=CARD, outline=BORDER, width=1, tags="btn_skip")
        c.create_text((sx1 + sx2) // 2, (sy1 + sy2) // 2,
                      text="⏭ 跳过", fill=DARK_BROWN,
                      font=("PingFang SC", 12), tags="btn_skip")

        # ── 统计 ──
        c.create_text(WIN_W // 2, 390, text="🍅 0 个番茄  ·  ⏱ 0 分钟专注",
                      fill=MUTED, font=("PingFang SC", 11), tags="stats")

        # ── 音效 ──
        c.create_rectangle(WIN_W // 2 - 64, 420, WIN_W // 2 + 64, 448,
                           fill=CARD, outline=BORDER, width=1, tags="btn_sound")
        c.create_text(WIN_W // 2, 434, text="🔔 音效开启",
                      fill=MUTED, font=("PingFang SC", 10), tags="btn_sound")

    # ═══════════════════════════════════════
    #  事件
    # ═══════════════════════════════════════
    def _bind_events(self):
        c = self.cv

        for key in MODES:
            c.tag_bind(f"mbtn_{key}", "<Button-1>",
                       lambda e, k=key: self._switch_mode(k))

        c.tag_bind("btn_play", "<Button-1>", lambda e: self._toggle())
        c.tag_bind("btn_reset", "<Button-1>", lambda e: self._reset())
        c.tag_bind("btn_skip", "<Button-1>", lambda e: self._skip())
        c.tag_bind("btn_sound", "<Button-1>", lambda e: self._toggle_sound())

        # Hover
        for key in MODES:
            c.tag_bind(f"mbtn_{key}", "<Enter>",
                       lambda e, k=key: self._h_mode(k, True))
            c.tag_bind(f"mbtn_{key}", "<Leave>",
                       lambda e, k=key: self._h_mode(k, False))
        c.tag_bind("btn_play", "<Enter>", lambda e: self._h_play(True))
        c.tag_bind("btn_play", "<Leave>", lambda e: self._h_play(False))
        for t in ("btn_reset", "btn_skip"):
            c.tag_bind(t, "<Enter>", lambda e, tag=t: self._h_ctrl(tag, True))
            c.tag_bind(t, "<Leave>", lambda e, tag=t: self._h_ctrl(tag, False))

        # 键盘
        self.root.bind("<space>", lambda e: self._toggle())
        self.root.bind("<Key-r>", lambda e: self._reset())
        self.root.bind("<Key-s>", lambda e: self._skip())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    # ═══════════════════════════════════════
    #  Hover
    # ═══════════════════════════════════════
    def _h_mode(self, key, enter):
        if key == self.mode:
            return
        c = self.cv
        cfg = MODES[key]
        x1, y1, x2, y2 = self._mode_btns[key]
        c.delete(f"mbtn_{key}")
        fill = CORAL_LIGHT if enter else CARD
        c.create_rectangle(x1, y1, x2, y2,
                           fill=fill, outline=BORDER, width=1, tags=f"mbtn_{key}")
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=cfg["label"], fill=DARK_BROWN,
                      font=("PingFang SC", 11), tags=f"mbtn_{key}")
        self._rebind_mode(key)

    def _h_play(self, enter):
        c = self.cv
        px1, py1, px2, py2 = self._ctrl["play"]
        c.delete("btn_play")
        fill = HOVER_TERRA if enter else TERRACOTTA
        c.create_rectangle(px1, py1, px2, py2,
                           fill=fill, outline="", tags="btn_play")
        label = "⏸  暂停" if self.running else "▶  开始"
        c.create_text((px1 + px2) // 2, (py1 + py2) // 2,
                      text=label, fill="#FFF",
                      font=("PingFang SC", 14, "bold"), tags="btn_play")
        self._rebind_play()

    def _h_ctrl(self, tag, enter):
        c = self.cv
        key = "reset" if tag == "btn_reset" else "skip"
        x1, y1, x2, y2 = self._ctrl[key]
        c.delete(tag)
        fill = CORAL_LIGHT if enter else CARD
        c.create_rectangle(x1, y1, x2, y2,
                           fill=fill, outline=BORDER, width=1, tags=tag)
        label = "↺ 重置" if key == "reset" else "⏭ 跳过"
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=label, fill=DARK_BROWN,
                      font=("PingFang SC", 12), tags=tag)
        self._rebind_ctrl(tag, key)

    def _rebind_mode(self, key):
        c = self.cv
        c.tag_bind(f"mbtn_{key}", "<Button-1>",
                   lambda e, k=key: self._switch_mode(k))
        c.tag_bind(f"mbtn_{key}", "<Enter>",
                   lambda e, k=key: self._h_mode(k, True))
        c.tag_bind(f"mbtn_{key}", "<Leave>",
                   lambda e, k=key: self._h_mode(k, False))

    def _rebind_play(self):
        c = self.cv
        c.tag_bind("btn_play", "<Button-1>", lambda e: self._toggle())
        c.tag_bind("btn_play", "<Enter>", lambda e: self._h_play(True))
        c.tag_bind("btn_play", "<Leave>", lambda e: self._h_play(False))

    def _rebind_ctrl(self, tag, key):
        c = self.cv
        action = self._reset if key == "reset" else self._skip
        c.tag_bind(tag, "<Button-1>", lambda e: action())

    # ═══════════════════════════════════════
    #  模式
    # ═══════════════════════════════════════
    def _switch_mode(self, new_mode):
        if self.running:
            self.running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None

        self.mode = new_mode
        cfg = MODES[new_mode]
        self.time_left  = cfg["mins"] * 60
        self.total_time = self.time_left

        # 重绘模式按钮
        c = self.cv
        bw, bh = 88, 34
        gap = 8
        total_w = 3 * bw + 2 * gap
        sx = (WIN_W - total_w) // 2
        by = 250
        for i, (key, cfg2) in enumerate(MODES.items()):
            bx = sx + i * (bw + gap)
            c.delete(f"mbtn_{key}")
            c.create_rectangle(bx, by, bx + bw, by + bh,
                               fill=cfg2["color"] if key == new_mode else CARD,
                               outline=BORDER, width=1, tags=f"mbtn_{key}")
            c.create_text(bx + bw // 2, by + bh // 2,
                          text=cfg2["label"],
                          fill="#FFF" if key == new_mode else DARK_BROWN,
                          font=("PingFang SC", 11), tags=f"mbtn_{key}")
            self._rebind_mode(key)

        self._redraw_play_btn()
        self._update_display()
        self._update_progress()

    # ═══════════════════════════════════════
    #  计时
    # ═══════════════════════════════════════
    def _toggle(self):
        if self.running:
            self.running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
            self._redraw_play_btn()
        else:
            self.running = True
            self._redraw_play_btn()
            self._tick()
        self._beep()

    def _tick(self):
        if not self.running:
            return
        if self.time_left <= 0:
            self._finish()
            return
        self.time_left -= 1
        self._update_display()
        self._update_progress()
        self.timer_id = self.root.after(1000, self._tick)

    def _finish(self):
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        # 提示音
        if self.sound:
            for _ in range(3):
                subprocess.run(["osascript", "-e", "beep"], capture_output=True)

        # 统计
        if self.mode == "work":
            self.pomo_count += 1
            self.focus_mins += MODES["work"]["mins"]
        self._update_stats()
        self._redraw_play_btn()

        # 弹窗提醒
        self.root.after(200, lambda: os.system(
            f"""osascript -e 'display notification "{"🍅 番茄完成！" if self.mode == "work" else "休息结束"}" with title "番茄时钟" sound name "Glass"' &"""
        ))

        # 自动切换
        self.root.after(1500, self._auto_switch)

    def _auto_switch(self):
        if self.mode == "work":
            nxt = "long" if self.pomo_count % 4 == 0 else "break"
        else:
            nxt = "work"
        self._switch_mode(nxt)

    def _reset(self):
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.time_left  = MODES[self.mode]["mins"] * 60
        self.total_time = self.time_left
        self._update_display()
        self._update_progress()
        self._redraw_play_btn()
        self._beep()

    def _skip(self):
        if self.running:
            self.running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
        self.time_left = 0
        self._update_display()
        self._update_progress()
        self._finish()

    # ═══════════════════════════════════════
    #  音效
    # ═══════════════════════════════════════
    def _beep(self):
        if self.sound:
            subprocess.run(["osascript", "-e", "beep"], capture_output=True)

    def _toggle_sound(self):
        self.sound = not self.sound
        c = self.cv
        c.delete("btn_sound")
        text = "🔔 音效开启" if self.sound else "🔕 音效关闭"
        c.create_rectangle(WIN_W // 2 - 64, 420, WIN_W // 2 + 64, 448,
                           fill=CARD, outline=BORDER, width=1, tags="btn_sound")
        c.create_text(WIN_W // 2, 434, text=text,
                      fill=MUTED, font=("PingFang SC", 10), tags="btn_sound")
        c.tag_bind("btn_sound", "<Button-1>", lambda e: self._toggle_sound())

    # ═══════════════════════════════════════
    #  更新
    # ═══════════════════════════════════════
    def _update_display(self):
        c = self.cv
        m, s = divmod(self.time_left, 60)
        c.delete("time")
        c.create_text(WIN_W // 2, 120, text=f"{m:02d}:{s:02d}",
                      fill=DARK_BROWN, font=("Menlo", 36, "bold"), tags="time")

        c.delete("status")
        if self.mode == "work":
            label = f"第 {self.pomo_count + 1} 个番茄"
        elif self.mode == "break":
            label = "☕ 休息中…"
        else:
            label = "🌴 长休息…"
        c.create_text(WIN_W // 2, 160, text=label,
                      fill=MUTED, font=("PingFang SC", 11), tags="status")

    def _update_progress(self):
        c = self.cv
        ratio = self.time_left / self.total_time if self.total_time > 0 else 0
        c.delete("pbar_fg")
        bar_x1, bar_y1 = 44, 215
        bar_x2, bar_y2 = WIN_W - 44, 225
        fill_x = bar_x1 + (bar_x2 - bar_x1) * (1 - ratio)
        if fill_x > bar_x1 + 2:
            c.create_rectangle(bar_x1, bar_y1, fill_x, bar_y2,
                               fill=MODES[self.mode]["color"],
                               outline="", tags="pbar_fg")

    def _update_stats(self):
        c = self.cv
        c.delete("stats")
        c.create_text(WIN_W // 2, 390,
                      text=f"🍅 {self.pomo_count} 个番茄  ·  ⏱ {self.focus_mins} 分钟专注",
                      fill=MUTED, font=("PingFang SC", 11), tags="stats")

    def _redraw_play_btn(self):
        c = self.cv
        px1, py1, px2, py2 = self._ctrl["play"]
        c.delete("btn_play")
        label = "⏸  暂停" if self.running else "▶  开始"
        c.create_rectangle(px1, py1, px2, py2,
                           fill=TERRACOTTA, outline="", tags="btn_play")
        c.create_text((px1 + px2) // 2, (py1 + py2) // 2,
                      text=label, fill="#FFF",
                      font=("PingFang SC", 14, "bold"), tags="btn_play")
        self._rebind_play()

    # ═══════════════════════════════════════
    #  运行
    # ═══════════════════════════════════════
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
