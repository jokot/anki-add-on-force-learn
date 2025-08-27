# forced_review_every_30m/__init__.py
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

from aqt import mw, gui_hooks
from aqt.utils import tooltip
from aqt.qt import QTimer, QMessageBox, QAction, qconnect, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton, QComboBox

ADDON_NAME = "Forced Review Every 30m"
DEFAULT_CFG = {
    "interval_minutes": 0.1,
    "snooze_minutes": 5,
    "quiet_hours": {"start": 25, "end": 26},  # Never quiet (invalid hours)
    "enabled": True,
    "target_deck_id": None,
}

def get_cfg():
    cfg = mw.addonManager.getConfig(__name__) or {}
    # fill missing keys with defaults
    merged = DEFAULT_CFG.copy()
    merged.update(cfg)
    if "quiet_hours" not in merged:
        merged["quiet_hours"] = DEFAULT_CFG["quiet_hours"]
    if "target_deck_id" not in merged:
        merged["target_deck_id"] = None
    return merged

def set_cfg(cfg):
    mw.addonManager.writeConfig(__name__, cfg)

class ReviewNudger:
    def __init__(self):
        self.cfg = get_cfg()
        self.timer = QTimer(mw)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._on_tick)
        self._last_activity_ts: float = time.time()
        self._disable_until_date: Optional[str] = None  # "YYYY-MM-DD"
        self._next_due_ts: float = self._last_activity_ts + self._interval_s()
        self._install_menu()

        gui_hooks.profile_did_open.append(self._on_profile_open)
        gui_hooks.reviewer_did_answer_card.append(self._on_answer_card)
        gui_hooks.state_did_change.append(self._on_state_change)

        # start after profile is ready
        self._start_timer()

    def _interval_s(self) -> int:
        return max(60, int(self.cfg.get("interval_minutes", 30)) * 60)

    def _snooze_s(self) -> int:
        return max(60, int(self.cfg.get("snooze_minutes", 5)) * 60)

    def _is_quiet_now(self) -> bool:
        q = self.cfg.get("quiet_hours", {"start": 25, "end": 26})
        try:
            start, end = int(q["start"]), int(q["end"]) 
        except Exception:
            return False
        # Treat invalid hours (outside 0-23) as disabled
        if not (0 <= start <= 23 and 0 <= end <= 23):
            return False
        now_h = datetime.now().hour
        if start == end:
            # same hour -> disabled
            return False
        if start < end:
            return start <= now_h < end
        else:
            # overnight wrap (e.g., 22–7)
            return now_h >= start or now_h < end

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # ---------------- Hooks & events ----------------

    def _on_profile_open(self):
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()

    def _on_answer_card(self, *args, **kwargs):
        # Any answered card = active reviewing → reset timer
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()

    def _on_state_change(self, new_state: str, old_state: str):
        # If you just started/stopped reviewing, keep the timer healthy
        if new_state == "review":
            self._last_activity_ts = time.time()
            self._next_due_ts = self._last_activity_ts + self._interval_s()

    # ---------------- Timer logic ----------------

    def _start_timer(self):
        self.timer.start(1000 * 15)  # check every 15s

    def _on_tick(self):
        if not self.cfg.get("enabled", True):
            return
        # Respect "disable today"
        if self._disable_until_date == self._today_str():
            return
        # Respect quiet hours
        if self._is_quiet_now():
            return
        # Already in reviewer? Keep silent.
        if mw.state == "review":
            return
        now = time.time()
        if now >= self._next_due_ts:
            self._prompt_review()

    # ---------------- UI actions ----------------

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
            # Windows-specific nudge to the foreground (best effort)
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
                pass
            # Ensure on top briefly to defeat focus stealing prevention
            try:
                mw.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                mw.show()
                _QTimer.singleShot(400, lambda: (mw.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False), mw.show()))
            except Exception:
                pass
        except Exception:
            pass

    def _prompt_review(self):
        # Bring Anki to the front before showing the dialog
        self._bring_to_front()
        # Blocking dialog with choices
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
            self._start_review()
            # next reminder after a full interval
            self._last_activity_ts = time.time()
            self._next_due_ts = self._last_activity_ts + self._interval_s()
        elif clicked == snooze_btn:
            self._next_due_ts = time.time() + self._snooze_s()
            tooltip(f"Snoozed for {self.cfg.get('snooze_minutes', 5)} minutes")
        elif clicked == disable_btn:
            self._disable_until_date = self._today_str()
            tooltip("Disabled for today")
        else:
            # Cancel: remind again in 2 minutes (short nudge)
            self._next_due_ts = time.time() + 120

    def _start_review(self):
        # Navigate Overview → start study. Works on modern Anki builds.
        def go():
            # optionally select configured deck
            try:
                target_id = self.cfg.get("target_deck_id")
                if target_id:
                    try:
                        mw.col.decks.select(int(target_id))
                    except Exception:
                        try:
                            d = mw.col.decks.get(int(target_id))
                            if d:
                                did = d.get("id") or d.get("did")
                                if did:
                                    mw.col.decks.select(int(did))
                            else:
                                tooltip("Configured deck not found; using current deck")
                        except Exception:
                            tooltip("Configured deck not found; using current deck")
            except Exception:
                pass
            # jump to overview for current deck
            mw.onOverview()
            # after overview is built, call onStudy()
            from aqt.qt import QTimer as _QTimer
            def _try_start():
                try:
                    # overview may not be ready immediately
                    if getattr(mw, "overview", None) and hasattr(mw.overview, "onStudy"):
                        mw.overview.onStudy()
                    else:
                        _QTimer.singleShot(100, _try_start)
                except Exception:
                    # fallback: just show a tooltip
                    tooltip("Could not start review automatically. Open your deck to begin.")
            _QTimer.singleShot(100, _try_start)
        mw.taskman.run_on_main(go)

    def _open_settings(self):
        dlg = QDialog(mw)
        dlg.setWindowTitle(f"{ADDON_NAME} Settings")

        v = QVBoxLayout(dlg)

        # Interval
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Interval (minutes):"))
        interval_spin = QSpinBox(dlg)
        interval_spin.setRange(1, 1440)
        interval_spin.setValue(int(self.cfg.get("interval_minutes", 30)))
        row1.addWidget(interval_spin)
        v.addLayout(row1)

        # Snooze
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Snooze (minutes):"))
        snooze_spin = QSpinBox(dlg)
        snooze_spin.setRange(1, 240)
        snooze_spin.setValue(int(self.cfg.get("snooze_minutes", 5)))
        row2.addWidget(snooze_spin)
        v.addLayout(row2)

        # Quiet hours
        row3 = QHBoxLayout()
        quiet_enable = QCheckBox("Enable quiet hours")
        q = self.cfg.get("quiet_hours", {"start": 25, "end": 26})
        try:
            qs, qe = int(q.get("start", 25)), int(q.get("end", 26))
        except Exception:
            qs, qe = 25, 26
        enabled_quiet = 0 <= qs <= 23 and 0 <= qe <= 23 and qs != qe
        quiet_enable.setChecked(enabled_quiet)
        row3.addWidget(quiet_enable)
        v.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Start hour (0-23):"))
        qstart_spin = QSpinBox(dlg)
        qstart_spin.setRange(0, 23)
        qstart_spin.setValue(qs if 0 <= qs <= 23 else 22)
        row4.addWidget(qstart_spin)
        row4.addWidget(QLabel("End hour (0-23):"))
        qend_spin = QSpinBox(dlg)
        qend_spin.setRange(0, 23)
        qend_spin.setValue(qe if 0 <= qe <= 23 else 7)
        row4.addWidget(qend_spin)
        v.addLayout(row4)

        # Enable/disable hour spinboxes based on checkbox
        def _toggle_quiet(enabled: bool):
            qstart_spin.setEnabled(enabled)
            qend_spin.setEnabled(enabled)
        _toggle_quiet(quiet_enable.isChecked())
        def _on_toggle(state):
            _toggle_quiet(bool(state))
        quiet_enable.stateChanged.connect(_on_toggle)

        # Target deck selection
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Target deck:"))
        deck_combo = QComboBox(dlg)
        deck_combo.setMinimumWidth(240)
        # Populate decks
        pairs = []
        try:
            # Try modern API: list of objects/tuples
            an = getattr(mw.col.decks, "all_names_and_ids", None)
            if callable(an):
                an_list = an()
                # an_list may be list of NamedTuples or tuples
                for entry in an_list:
                    try:
                        name = entry.name
                        did = int(entry.id)
                    except Exception:
                        try:
                            name, did = entry
                            did = int(did)
                        except Exception:
                            continue
                    if name:
                        pairs.append((name, did))
            else:
                # Fallback to .all()
                for d in mw.col.decks.all():
                    try:
                        name = d.get("name")
                        did = d.get("id") or d.get("did") or d.get("deck_id")
                        if name is not None and did is not None:
                            pairs.append((name, int(did)))
                    except Exception:
                        continue
        except Exception:
            pass
        pairs = list({(n, d) for (n, d) in pairs})  # de-dup
        pairs.sort(key=lambda x: x[0].lower())
        deck_combo.addItem("Use current deck", userData=None)
        for name, did in pairs:
            deck_combo.addItem(name, userData=did)
        # Preselect current value if set
        sel_did = self.cfg.get("target_deck_id")
        if sel_did:
            for i in range(deck_combo.count()):
                if deck_combo.itemData(i) == sel_did:
                    deck_combo.setCurrentIndex(i)
                    break
        row5.addWidget(deck_combo)
        v.addLayout(row5)

        # Buttons
        btns = QHBoxLayout()
        save_btn = QPushButton("Save", dlg)
        cancel_btn = QPushButton("Cancel", dlg)
        btns.addStretch(1)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        v.addLayout(btns)

        def on_save():
            new_cfg = dict(self.cfg)
            new_cfg["interval_minutes"] = int(interval_spin.value())
            new_cfg["snooze_minutes"] = int(snooze_spin.value())
            if quiet_enable.isChecked():
                new_cfg["quiet_hours"] = {"start": int(qstart_spin.value()), "end": int(qend_spin.value())}
            else:
                # store invalid hours to effectively disable
                new_cfg["quiet_hours"] = {"start": 25, "end": 26}
            sel = deck_combo.currentData()
            try:
                new_cfg["target_deck_id"] = int(sel) if sel is not None else None
            except Exception:
                new_cfg["target_deck_id"] = None
            set_cfg(new_cfg)
            self.cfg = new_cfg
            # Reset schedule based on new interval
            self._last_activity_ts = time.time()
            self._next_due_ts = self._last_activity_ts + self._interval_s()
            # Update snooze action label to reflect new minutes
            try:
                if hasattr(self, "_snooze_action") and self._snooze_action is not None:
                    self._snooze_action.setText(f"Forced Review: Snooze {int(self.cfg.get('snooze_minutes', 5))}m")
            except Exception:
                pass
            tooltip("Settings saved")
            dlg.accept()

        def on_cancel():
            dlg.reject()

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(on_cancel)

        dlg.exec()

    # ---------------- Menu ----------------

    def _install_menu(self):
        tools = mw.form.menuTools
        settings = QAction("Forced Review: Settings", mw)
        qconnect(settings.triggered, self._open_settings)
        tools.addAction(settings)

        toggle = QAction("Forced Review: Toggle Enabled", mw)
        qconnect(toggle.triggered, self._toggle_enabled)
        tools.addAction(toggle)

        # Snooze minutes reflect current config
        try:
            snooze_label = f"Forced Review: Snooze {int(self.cfg.get('snooze_minutes', 5))}m"
        except Exception:
            snooze_label = "Forced Review: Snooze"
        self._snooze_action = QAction(snooze_label, mw)
        qconnect(self._snooze_action.triggered, self._quick_snooze)
        tools.addAction(self._snooze_action)

        reset = QAction("Forced Review: Reset Today", mw)
        qconnect(reset.triggered, self._reset_today)
        tools.addAction(reset)

    def _toggle_enabled(self):
        self.cfg["enabled"] = not self.cfg.get("enabled", True)
        set_cfg(self.cfg)
        state = "ON" if self.cfg["enabled"] else "OFF"
        tooltip(f"{ADDON_NAME} {state}")

    def _quick_snooze(self):
        self._next_due_ts = time.time() + self._snooze_s()
        tooltip(f"Snoozed for {self.cfg.get('snooze_minutes', 5)} minutes")

    def _reset_today(self):
        self._disable_until_date = None
        self._last_activity_ts = time.time()
        self._next_due_ts = self._last_activity_ts + self._interval_s()
        tooltip("Reset for today")

# Initialize when profile opens
def _init_after_profile():
    # Singleton
    if not hasattr(mw, "_forced_review_nudger"):
        mw._forced_review_nudger = ReviewNudger()

gui_hooks.profile_did_open.append(_init_after_profile)
