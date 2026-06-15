#!/usr/bin/env python3
"""
meeting-transcriber — gui.py
Minimal GUI for one-click transcription. No extra dependencies beyond tkinter.

Usage: python gui.py
"""

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import config

TRANSCRIBE = Path(__file__).parent / "transcribe.py"

LANGUAGES = {
    "Auto-detect": None,
    "English":  "en",
    "Chinese":  "zh",
    "Japanese": "ja",
    "Korean":   "ko",
    "Spanish":  "es",
    "French":   "fr",
    "German":   "de",
}

BG       = "#1c1c1e"
BG2      = "#2c2c2e"
FG       = "#f5f5f7"
FG_DIM   = "#8e8e93"
ACCENT   = "#0a84ff"
SUCCESS  = "#30d158"
DANGER   = "#ff453a"
FONT     = ("SF Pro Display", 11) if sys.platform == "darwin" else ("Segoe UI", 10)
MONO     = ("SF Mono", 9)        if sys.platform == "darwin" else ("Consolas", 9)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("meeting-transcriber")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._video_path: Path | None = None
        self._output_path: Path | None = None
        self._running = False
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        pad = dict(padx=24, pady=0)

        # Header
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(20, 16))
        tk.Label(header, text="meeting-transcriber", bg=BG, fg=FG,
                 font=(FONT[0], 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Transcribe meetings with speaker labels",
                 bg=BG, fg=FG_DIM, font=FONT).pack(anchor="w", pady=(2, 0))

        _divider(self)

        # File picker
        file_row = tk.Frame(self, bg=BG)
        file_row.pack(fill="x", **pad, pady=(16, 0))
        _btn(file_row, "Select video…", self._pick_file, ACCENT).pack(side="left")
        self._file_label = tk.Label(file_row, text="No file selected",
                                     bg=BG, fg=FG_DIM, font=FONT)
        self._file_label.pack(side="left", padx=12)

        # Options
        opts = tk.Frame(self, bg=BG)
        opts.pack(fill="x", **pad, pady=14)

        tk.Label(opts, text="Language", bg=BG, fg=FG_DIM, font=FONT).grid(
            row=0, column=0, sticky="w")
        self._lang_var = tk.StringVar(value="Auto-detect")
        combo = ttk.Combobox(opts, textvariable=self._lang_var,
                              values=list(LANGUAGES.keys()),
                              state="readonly", width=16, font=FONT)
        combo.grid(row=0, column=1, sticky="w", padx=10)

        self._diarize_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(opts, text="Speaker diarization",
                             variable=self._diarize_var,
                             bg=BG, fg=FG, selectcolor=BG2,
                             activebackground=BG, activeforeground=FG,
                             font=FONT, cursor="hand2")
        cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        _divider(self)

        # Start button
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", **pad, pady=14)
        self._start_btn = _btn(btn_row, "Transcribe", self._start, SUCCESS)
        self._start_btn.pack(side="left")

        self._status_label = tk.Label(btn_row, text="", bg=BG, fg=FG_DIM, font=FONT)
        self._status_label.pack(side="left", padx=14)

        # Log
        tk.Label(self, text="LOG", bg=BG, fg=FG_DIM,
                 font=(FONT[0], 8)).pack(anchor="w", padx=24, pady=(0, 4))

        log_frame = tk.Frame(self, bg=BG2, padx=1, pady=1)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        self._log = tk.Text(log_frame, width=62, height=14,
                             bg=BG2, fg=FG, insertbackground=FG,
                             font=MONO, relief="flat",
                             state="disabled", wrap="word")
        sb = tk.Scrollbar(log_frame, command=self._log.yview, bg=BG2,
                          troughcolor=BG2, relief="flat")
        self._log.configure(yscrollcommand=sb.set)
        self._log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Output link
        self._open_btn = _btn(self, "Open transcript →", self._open_output, BG2)
        self._open_btn.pack(anchor="w", padx=24, pady=(0, 20))
        self._open_btn.pack_forget()

        self.geometry("580x540")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _pick_file(self):
        exts = " ".join(f"*{e}" for e in config.WATCH_EXTENSIONS)
        path = filedialog.askopenfilename(
            title="Select video or audio file",
            filetypes=[("Video/Audio", exts), ("All files", "*.*")],
        )
        if path:
            self._video_path = Path(path)
            name = self._video_path.name
            display = name if len(name) <= 42 else f"…{name[-40:]}"
            self._file_label.configure(text=display, fg=FG)
            self._open_btn.pack_forget()
            self._set_status("")

    def _start(self):
        if self._running:
            return
        if not self._video_path:
            self._set_status("Select a video file first.", DANGER)
            return
        if not self._video_path.exists():
            self._set_status("File not found.", DANGER)
            return

        self._running = True
        self._open_btn.pack_forget()
        self._start_btn.configure(state="disabled", bg=FG_DIM)
        self._set_status("Running…")
        self._clear_log()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        cmd = [sys.executable, str(TRANSCRIBE), str(self._video_path)]
        lang = LANGUAGES[self._lang_var.get()]
        if lang:
            cmd += ["--language", lang]
        if not self._diarize_var.get():
            cmd += ["--transcribe-only"]

        self._append_log(f"$ {' '.join(str(c) for c in cmd)}\n")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            self.after(0, self._append_log, line.rstrip())
        proc.wait()

        if proc.returncode == 0:
            stem = self._video_path.stem
            self._output_path = config.TRANSCRIPT_DIR / f"{stem}.md"
            self.after(0, self._on_done)
        else:
            self.after(0, self._on_error, proc.returncode)

    def _on_done(self):
        self._set_status(f"✓  {self._output_path.name}", SUCCESS)
        self._open_btn.pack(anchor="w", padx=24, pady=(0, 20))
        self._start_btn.configure(state="normal", bg=SUCCESS)
        self._running = False

    def _on_error(self, code: int):
        self._set_status(f"Failed (exit {code})", DANGER)
        self._start_btn.configure(state="normal", bg=SUCCESS)
        self._running = False

    def _open_output(self):
        if self._output_path and self._output_path.exists():
            import os
            os.startfile(str(self._output_path))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = FG_DIM):
        self._status_label.configure(text=text, fg=color)

    def _append_log(self, line: str):
        self._log.configure(state="normal")
        self._log.insert("end", line + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")


# ── Widget helpers ────────────────────────────────────────────────────────────

def _btn(parent, text: str, cmd, color: str) -> tk.Button:
    return tk.Button(parent, text=text, command=cmd,
                     bg=color, fg=FG, relief="flat",
                     padx=14, pady=7, cursor="hand2",
                     activebackground=color, activeforeground=FG,
                     font=FONT, bd=0)


def _divider(parent):
    tk.Frame(parent, bg=BG2, height=1).pack(fill="x", padx=24)


if __name__ == "__main__":
    App().mainloop()
