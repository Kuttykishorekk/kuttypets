"""
KuttyPets - Cross-Platform Hardware-Accelerated Transparent Overlay Canvas.
Supports Windows (PyQt6 / Win32), macOS (PyQt6 / Cocoa), and Linux (PyQt6 / GtkLayerShell).
"""

from __future__ import annotations
import sys
import os
import math
from typing import Dict, Optional
from PIL import Image

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QMenu
    from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
    from PyQt6.QtGui import QPainter, QPixmap, QImage, QColor, QFont, QAction
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False


class KuttyPetsOverlay(QWidget if HAS_PYQT else object):
    """Transparent, frameless, click-through desktop overlay for KuttyPets."""

    def __init__(self, engine, char_frames_dir: str):
        if not HAS_PYQT:
            raise RuntimeError("PyQt6 is required for desktop overlay rendering.")
        super().__init__()
        self.engine = engine
        self.char_frames_dir = char_frames_dir
        self.qpixmaps: Dict[str, QPixmap] = {}
        self._load_pixmaps()

        # Window flags: Frameless, Always On Top, Transparent Background, Tool window (no taskbar clutter)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Fullscreen bounds matching primary display
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Windows-specific click-through helper
        if sys.platform == "win32":
            self._setup_win32_clickthrough()

        # 60 FPS Engine Tick Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

        self.setMouseTracking(True)
        self.show()

    def _setup_win32_clickthrough(self) -> None:
        try:
            import win32gui
            import win32con
            hwnd = int(self.winId())
            # Enable layered window
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED)
        except Exception:
            pass

    def _load_pixmaps(self) -> None:
        """Loads all PNG frames from character directory into hardware-cached QPixmaps."""
        if not os.path.isdir(self.char_frames_dir):
            return
        for fn in os.listdir(self.char_frames_dir):
            if fn.endswith(".png"):
                k = os.path.splitext(fn)[0]
                fp = os.path.join(self.char_frames_dir, fn)
                pm = QPixmap(fp)
                if not pm.isNull():
                    self.qpixmaps[k] = pm

    def _on_tick(self) -> None:
        self.engine.tick()
        self.update()

    def get_current_frame_key(self) -> str:
        state = self.engine.state
        char = self.engine.current_char
        anim = self.engine.anim_tick
        st = self.engine.state_timer

        if self.engine.adapter.__class__.__name__ == "LinuxHyprlandAdapter":
            pass

        # Spider-Man frame selection
        if "shime1" in self.qpixmaps:
            if state == "SWINGING":
                hang = ["shime15", "shime16", "shime17"]
                return hang[int(anim * 3.5) % len(hang)]
            elif state in ("CLINGING", "TOP_CRAWL", "BOTTOM_CRAWL"):
                if self.engine.cling_side in ("LEFT", "RIGHT"):
                    climb = ["shime12", "shime13", "shime14"]
                    return climb[int(anim * 6.5) % len(climb)]
                elif self.engine.cling_side == "TOP":
                    climb = ["shime12", "shime13", "shime14"]
                    return climb[int(anim * 7.0) % len(climb)]
                else:
                    return "shime11"
            elif state == "CORNER_ARC":
                phase = getattr(self.engine, "corner_phase", "plant")
                if phase == "plant": return "shime12"
                elif phase == "reach": return "shime13"
                elif phase == "pull": return "shime14"
                return "shime12"
            elif state == "WALKING":
                walk = ["shime1", "shime2", "shime1", "shime3"]
                return walk[int(anim * 6.5) % len(walk)]
            elif state == "SITTING":
                return "shime11" if int(st) % 12 < 6 else "shime5"
            elif state == "FALLING":
                return "shime4" if self.engine.vy < 80 else "shime5"
            return "shime1"
        else:
            # Genshin format (Hu Tao, Klee, Ayaka, Venti)
            if state in ("CLINGING", "TOP_CRAWL", "BOTTOM_CRAWL"):
                climb = ["climb1", "climb2", "climb3"]
                return climb[int(anim * 6.0) % len(climb)] if "climb1" in self.qpixmaps else "id1_1"
            elif state == "WALKING":
                walk = ["walk1", "walk2", "walk3"]
                return walk[int(anim * 6.0) % len(walk)] if "walk1" in self.qpixmaps else "id1_1"
            elif state == "SITTING":
                return "id1_1" if int(st * 1.5) % 4 != 0 else "id2_1"
            elif state == "FALLING":
                fall = ["fall1", "fall2", "fall3"]
                return fall[int(anim * 4.5) % len(fall)] if "fall1" in self.qpixmaps else "id1_1"
            return "id1_1"

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Draw Active Web Lines (Spider-Man)
        if self.engine.web.web_active or self.engine.state == "SWINGING":
            hx = self.engine.x
            hy = self.engine.y - 10.0 * self.engine.render_scale
            ax = self.engine.web.web_anchor_x
            ay = self.engine.web.web_anchor_y
            painter.setPen(QColor(240, 245, 255, int(200 * self.engine.web.web_opacity)))
            painter.drawLine(int(hx), int(hy), int(ax), int(ay))

        # 2. Draw Particles
        for p in self.engine.particles.active_particles():
            painter.save()
            painter.translate(p.x, p.y)
            painter.setPen(Qt.PenStyle.NoPen)
            if p.ptype == "sparkle":
                painter.setBrush(QColor(255, 220, 110, int(200 * p.alpha)))
                painter.drawEllipse(QPoint(0, 0), int(2.5 * p.alpha), int(2.5 * p.alpha))
            elif p.ptype == "butterfly":
                painter.setBrush(QColor(255, 120, 60, int(180 * p.alpha)))
                painter.drawEllipse(QPoint(0, 0), int(3.5 * p.alpha), int(2.5 * p.alpha))
            elif p.ptype == "clover":
                painter.setBrush(QColor(60, 220, 100, int(180 * p.alpha)))
                painter.drawEllipse(QPoint(0, 0), int(3.0 * p.alpha), int(3.0 * p.alpha))
            elif p.ptype == "sakura":
                painter.setBrush(QColor(255, 180, 210, int(180 * p.alpha)))
                painter.drawEllipse(QPoint(0, 0), int(3.2 * p.alpha), int(4.0 * p.alpha))
            elif p.ptype == "feather":
                painter.setPen(QColor(80, 230, 210, int(200 * p.alpha)))
                painter.setFont(QFont("Sans", 10))
                painter.drawText(0, 0, "♪")
            painter.restore()

        # 3. Draw Character Sprite
        frame_key = self.get_current_frame_key()
        pixmap = self.qpixmaps.get(frame_key)
        if not pixmap:
            return

        painter.save()
        painter.translate(self.engine.x, self.engine.y - self.engine.step_bob_y)
        painter.rotate(math.degrees(self.engine.body_angle))

        # 3D Flip scaling
        turn_sx = -self.engine.facing_scale
        if abs(turn_sx) < 0.08:
            turn_sx = -0.08 if self.engine.facing_scale >= 0 else 0.08

        rs = self.engine.render_scale
        painter.scale(turn_sx * self.engine.scale_x * rs, self.engine.scale_y * rs)

        # Draw centered at 0, 0
        pw = pixmap.width()
        ph = pixmap.height()
        painter.drawPixmap(int(-pw * 0.5), int(-ph * 0.5), pixmap)
        painter.restore()

    def _pet_rect(self) -> QRectF:
        rs = self.engine.render_scale
        w = 90.0 * rs
        h = 100.0 * rs
        return QRectF(self.engine.x - w * 0.5, self.engine.y - h * 0.5, w, h)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._pet_rect().contains(pos):
            if event.button() == Qt.MouseButton.LeftButton:
                self.engine.is_dragging = True
                self.engine.drag_offset_x = pos.x() - self.engine.x
                self.engine.drag_offset_y = pos.y() - self.engine.y
                self.engine.mouse_history.clear()
            elif event.button() == Qt.MouseButton.RightButton:
                self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.engine.is_dragging:
            pos = event.position()
            self.engine.x = pos.x() - self.engine.drag_offset_x
            self.engine.y = pos.y() - self.engine.drag_offset_y
            self.engine.mouse_history.append((time.time(), pos.x(), pos.y()))
            if len(self.engine.mouse_history) > 8:
                self.engine.mouse_history.pop(0)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.engine.is_dragging:
            self.engine.is_dragging = False
            # Compute throw impulse
            if len(self.engine.mouse_history) >= 2:
                t0, x0, y0 = self.engine.mouse_history[0]
                t1, x1, y1 = self.engine.mouse_history[-1]
                dt = max(0.016, t1 - t0)
                self.engine.vx = (x1 - x0) / dt
                self.engine.vy = (y1 - y0) / dt
            self.engine.state = "FALLING"

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        
        # Character switcher submenu
        char_menu = menu.addMenu("Change Companion")
        from ..config import discover_characters
        chars = discover_characters()
        for cid, meta in chars.items():
            action = QAction(meta.get("name", cid), self)
            action.triggered.connect(lambda checked, c=cid: self._switch_character(c))
            char_menu.addAction(action)

        menu.addSeparator()

        # Autostart toggle
        from ..core.autostart import AutostartManager
        is_auto = AutostartManager.is_enabled()
        auto_action = QAction("Start with Windows" if sys.platform == "win32" else "Start on Login", self)
        auto_action.setCheckable(True)
        auto_action.setChecked(is_auto)
        auto_action.triggered.connect(lambda: AutostartManager.toggle())
        menu.addAction(auto_action)

        menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit KuttyPets", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        menu.exec(global_pos)

    def _switch_character(self, char_id: str) -> None:
        from ..config import discover_characters
        chars = discover_characters()
        if char_id in chars:
            self.engine.current_char = char_id
            self.char_frames_dir = chars[char_id]["path"]
            self.qpixmaps.clear()
            self._load_pixmaps()
            from ..core.rigs import SpriteRigAnalyzer
            rigs = SpriteRigAnalyzer.load_and_rig_character(self.char_frames_dir)
            self.engine.set_character_rigs(rigs)
