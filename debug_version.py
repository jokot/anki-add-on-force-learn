# Debug version of the Review Nudger addon
# Copy this content to __init__.py to enable debug logging
# Remember to backup your original __init__.py first!

from __future__ import annotations

import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from aqt import mw, gui_hooks
from aqt.utils import tooltip
from aqt.qt import QTimer, QMessageBox, QAction, qconnect

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('anki_nudger_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ReviewNudger')

ADDON_NAME = "Forced Review Every 30m (DEBUG)"
DEFAULT_CFG = {
    "interval_minutes": 30,
    "snooze_minutes": 5,
    "quiet_hours": {"start": 22, "end": 7},
    "enabled": True,
}

def get_cfg():
    cfg = mw.addonManager.getConfig(__name__) or {}
    merged = DEFAULT_CFG.copy()
    merged.update(cfg)
    if "quiet_hours" not in merged:
        merged["quiet_hours"] = DEFAULT_CFG["quiet_hours"]
    logger.debug(f"Configuration loaded: {merged}")
    return merged

def set_cfg(cfg):
    logger.debug(f"Saving configuration: {cfg}")
    mw.addonManager.writeConfig(__name__, cfg)

class ReviewNudger:
    def __init__(self):
        logger.info("Initializing ReviewNudger")
        self.cfg = get_cfg()
        self.timer = QTimer(mw)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._on_tick)
        self._last_activity_ts: float = time.time()
        self._disable_until_date: Optional[str] = None
        self._next_due_ts: float = self._last_activity_ts + self._interval_s()
        
        logger.debug(f"Initial state: last_activity={self._last_activity_ts}, next_due={self._next_due_ts}")
        
        self._install_menu()

        gui_hooks.profile_did_open.append(self._on_profile_open)
        gui_hooks.reviewer_did_answer_card.append(self._on_answer_card)
        gui_hooks.state_did_change.append(self._on_state_change)

        self._start_timer()
        logger.info("ReviewNudger initialized successfully")

    def _interval_s(self) -> int:
        interval = max(60, int(self.cfg.get("interval_minutes", 30)) * 60)
        logger.debug(f"Interval: {interval}s ({interval/60:.1f}m)")
        return interval

    def _snooze_s(self) -> int:
        snooze = max(60, int(self.cfg.get("snooze_minutes", 5)) * 60)
        logger.debug(f"Snooze: {snooze}s ({snooze/60:.1f}m)")
        return snooze

    def _is_quiet_now(self) -> bool:
        q = self.cfg.get("quiet_hours", {"start": 22, "end": 7})
        try:
            start, end = int(q["start"]), int(q["end"])
        except Exception as e:
            logger.warning(f"Invalid quiet hours config: {q}, error: {e}")
            start, end = 22, 7
        
        now_h = datetime.now().hour
        if start <= end:
            is_quiet = start <= now_h < end
        else:
            is_quiet = now_h >= start or now_h < end
        
        logger.debug(f"Quiet hours check: {start}-{end}, current hour: {now_h}, is_quiet: {is_quiet}")
        return is_quiet

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _on_profile_open(self):
        logger.info("Profile opened - resetting timer")
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()

    def _on_answer_card(self, *args, **kwargs):
        logger.debug("Card answered - resetting timer")
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()

    def _on_state_change(self, new_state: str, old_state: str):
        logger.debug(f"State changed: {old_state} -> {new_state}")
        if new_state == "review":
            logger.debug("Entered review state - resetting timer")
            self._last_activity_ts = time.time()
            self._next_due_ts = self._last_activity_ts + self._interval_s()

    def _start_timer(self):
        logger.info("Starting timer (15s intervals)")
        self.timer.start(1000 * 15)

    def _on_tick(self):
        now = time.time()
        time_until_due = self._next_due_ts - now
        
        logger.debug(f"Timer tick - enabled: {self.cfg.get('enabled')}, "
                    f"state: {mw.state}, time_until_due: {time_until_due:.1f}s, "
                    f"disabled_until: {self._disable_until_date}, "
                    f"today: {self._today_str()}")
        
        if not self.cfg.get("enabled", True):
            logger.debug("Addon disabled - skipping")
            return
            
        if self._disable_until_date == self._today_str():
            logger.debug("Disabled for today - skipping")
            return
            
        if self._is_quiet_now():
            logger.debug("In quiet hours - skipping")
            return
            
        if mw.state == "review":
            logger.debug("In review state - skipping")
            return
            
        if now >= self._next_due_ts:
            logger.info(f"Time to prompt! Due time reached: {time_until_due:.1f}s overdue")
            self._prompt_review()
        else:
            logger.debug(f"Not yet due - {time_until_due:.1f}s remaining")

    def _bring_to_front(self):
        """Try to bring the Anki main window to the foreground and give it focus."""
        try:
            from aqt.qt import Qt, QGuiApplication, QTimer as _QTimer
            # Restore if minimized and request activation
            mw.showNormal()
            try:
                # Clear minimized flag
                mw.setWindowState(mw.windowState() & ~Qt.WindowState.WindowMinimized)
                # Activate window
                mw.setWindowState(mw.windowState() | Qt.WindowState.WindowActive)
            except Exception:
                pass
            mw.raise_()
            mw.activateWindow()
            # Alert the user (taskbar flash) in case OS prevents focus stealing
            try:
                QGuiApplication.alert(mw, 0)
            except Exception:
                pass
            # Windows-specific nudge to the foreground
            try:
                import sys
                if sys.platform.startswith("win"):
                    import ctypes
                    user32 = ctypes.windll.user32
                    SW_RESTORE = 9
                    hwnd = int(mw.winId())
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                # As a last resort, briefly toggle always-on-top to raise, then revert
                try:
                    mw.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                    mw.show()
                    _QTimer.singleShot(200, lambda: (mw.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False), mw.show()))
                except Exception:
                    pass
        except Exception:
            pass

    def _prompt_review(self):
        logger.info("Showing review prompt dialog")
        # Bring Anki to the front before showing the dialog
        self._bring_to_front()
        msg = QMessageBox(mw)
        msg.setWindowTitle(ADDON_NAME)
        msg.setText("Time to review! Do you want to start now?")
        start_btn = msg.addButton("Start Review", QMessageBox.ButtonRole.AcceptRole)
        snooze_btn = msg.addButton(f"Snooze {self.cfg.get('snooze_minutes', 5)}m", QMessageBox.ButtonRole.ActionRole)
        disable_btn = msg.addButton("Disable for Today", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == start_btn:
            logger.info("User chose: Start Review")
            self._start_review()
            self._last_activity_ts = time.time()
            self._next_due_ts = self._last_activity_ts + self._interval_s()
        elif clicked == snooze_btn:
            logger.info(f"User chose: Snooze {self.cfg.get('snooze_minutes', 5)}m")
            self._next_due_ts = time.time() + self._snooze_s()
            tooltip(f"Snoozed for {self.cfg.get('snooze_minutes', 5)} minutes")
        elif clicked == disable_btn:
            logger.info("User chose: Disable for Today")
            self._disable_until_date = self._today_str()
            tooltip("Disabled for today")
        else:
            logger.info("User chose: Cancel (2min reminder)")
            self._next_due_ts = time.time() + 120

    def _start_review(self):
        logger.info("Attempting to start review session")
        def go():
            try:
                mw.onOverview()
                from aqt.qt import QTimer as _QTimer
                def _try_start():
                    try:
                        if getattr(mw, "overview", None) and hasattr(mw.overview, "onStudy"):
                            logger.debug("Starting study from overview")
                            mw.overview.onStudy()
                        else:
                            logger.debug("Overview not ready, retrying...")
                            _QTimer.singleShot(100, _try_start)
                    except Exception as e:
                        logger.error(f"Error starting study: {e}")
                        tooltip("Could not start review automatically. Open your deck to begin.")
                _QTimer.singleShot(100, _try_start)
            except Exception as e:
                logger.error(f"Error in start_review: {e}")
        mw.taskman.run_on_main(go)

    def _install_menu(self):
        logger.debug("Installing menu items")
        tools = mw.form.menuTools
        
        toggle = QAction("Forced Review: Toggle Enabled", mw)
        qconnect(toggle.triggered, self._toggle_enabled)
        tools.addAction(toggle)

        snooze = QAction("Forced Review: Snooze 5m", mw)
        qconnect(snooze.triggered, self._quick_snooze)
        tools.addAction(snooze)

        reset = QAction("Forced Review: Reset Today", mw)
        qconnect(reset.triggered, self._reset_today)
        tools.addAction(reset)
        
        # Debug menu item
        debug = QAction("Forced Review: Show Debug Info", mw)
        qconnect(debug.triggered, self._show_debug_info)
        tools.addAction(debug)

    def _toggle_enabled(self):
        self.cfg["enabled"] = not self.cfg.get("enabled", True)
        set_cfg(self.cfg)
        state = "ON" if self.cfg["enabled"] else "OFF"
        logger.info(f"Toggled enabled state: {state}")
        tooltip(f"{ADDON_NAME} {state}")

    def _quick_snooze(self):
        logger.info("Quick snooze activated")
        self._next_due_ts = time.time() + self._snooze_s()
        tooltip(f"Snoozed for {self.cfg.get('snooze_minutes', 5)} minutes")

    def _reset_today(self):
        logger.info("Reset today activated")
        self._disable_until_date = None
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()
        tooltip("Reset for today")
    
    def _show_debug_info(self):
        now = time.time()
        time_until_due = self._next_due_ts - now
        info = f"""Debug Information:
        
Enabled: {self.cfg.get('enabled', True)}
Current State: {mw.state}
Time Until Due: {time_until_due:.1f}s ({time_until_due/60:.1f}m)
Disabled Until: {self._disable_until_date}
Today: {self._today_str()}
Quiet Hours: {self._is_quiet_now()}
Interval: {self._interval_s()}s ({self._interval_s()/60:.1f}m)
Snooze: {self._snooze_s()}s ({self._snooze_s()/60:.1f}m)

Last Activity: {datetime.fromtimestamp(self._last_activity_ts).strftime('%H:%M:%S')}
Next Due: {datetime.fromtimestamp(self._next_due_ts).strftime('%H:%M:%S')}
Current Time: {datetime.fromtimestamp(now).strftime('%H:%M:%S')}
        """
        
        msg = QMessageBox(mw)
        msg.setWindowTitle("Review Nudger Debug Info")
        msg.setText(info)
        msg.exec()
        
        logger.info(f"Debug info shown: {info.replace(chr(10), ' | ')}")

def _init_after_profile():
    logger.info("Profile opened - initializing ReviewNudger")
    if not hasattr(mw, "_forced_review_nudger"):
        mw._forced_review_nudger = ReviewNudger()
    else:
        logger.debug("ReviewNudger already exists")

gui_hooks.profile_did_open.append(_init_after_profile)
logger.info("Review Nudger addon loaded")