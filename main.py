#!/usr/bin/env python3
"""
CNC Machine Controller — G-Code Terminal & Flow Manager
A desktop GUI for connecting, jogging, and sending G-code to CNC machines.

Dependencies:
    pip install pyserial

Run:
    python cnc_controller.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import json
import os
import re

# Try importing pyserial; fall back to a mock for UI-only testing
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[WARN] pyserial not installed. Running in UI-only mode.")
    print("       Install with: pip install pyserial")


# ─────────────────────────────────────────────
#  THEME / CONSTANTS
# ─────────────────────────────────────────────
BG        = "#0f1117"
BG2       = "#181c27"
BG3       = "#1e2333"
ACCENT    = "#00d4aa"
ACCENT2   = "#0094ff"
WARN      = "#ff6b35"
SUCCESS   = "#00d4aa"
ERROR     = "#ff4466"
TEXT      = "#e8eaf0"
TEXT_DIM  = "#6b7280"
BORDER    = "#2d3348"
FONT_MONO = ("Consolas", 10)
FONT_UI   = ("Segoe UI", 10)
FONT_HEAD = ("Segoe UI Semibold", 11)


DEFAULT_AXES = {
    "X": {"cm_per_step": 1.0, "enabled": True},
    "Y": {"cm_per_step": 1.0, "enabled": True},
    "Z": {"cm_per_step": 1.0, "enabled": True},
    "U": {"cm_per_step": 1.0, "enabled": True},
    "A": {"cm_per_step": 1.0, "enabled": True},
    "B": {"cm_per_step": 1.0, "enabled": True},
}

BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 250000]

GCODE_HELP = {
    "G0":  "Rapid move — G0 X10 Y20",
    "G1":  "Linear move — G1 X10 F500",
    "G2":  "Arc CW     — G2 X5 Y5 I2 J0",
    "G3":  "Arc CCW    — G3 X5 Y5 I2 J0",
    "G28": "Home       — G28",
    "G90": "Absolute   — G90",
    "G91": "Relative   — G91",
    "G92": "Set pos    — G92 X0 Y0 Z0",
    "M3":  "Spindle ON — M3 S1000",
    "M5":  "Spindle OFF— M5",
    "M8":  "Coolant ON — M8",
    "M9":  "Coolant OFF— M9",
    "M114":"Get pos    — M114",
}

# ─────────────────────────────────────────────
#  SERIAL MOCK (when pyserial unavailable)
# ─────────────────────────────────────────────
class MockSerial:
    def __init__(self): self.is_open = True
    def write(self, data): pass
    def readline(self): time.sleep(0.05); return b"ok\n"
    def close(self): self.is_open = False

class MockPorts:
    @staticmethod
    def comports():
        class P:
            def __init__(self, d, desc):
                self.device = d
                self.description = desc
        return [P("COM1","Mock CNC Port"), P("COM2","Mock Port 2")]


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────
class CNCController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CNC Controller — G-Code Manager")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        # State
        self.serial_conn  = None
        self.connected    = False
        self.flow_lines   = []          # list of G-code strings in current flow
        self.current_file = None        # path of opened .gcode file
        self.axes         = {k: dict(v) for k, v in DEFAULT_AXES.items()}
        self.running_flow = False
        self.cmd_history  = []
        self.hist_idx     = -1

        self._build_ui()
        self._scan_ports()
        self._log_terminal("CNC Controller ready. Connect to a machine to begin.\n", "info")

    # ══════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════
    def _build_ui(self):
        self._style_ttk()
        self._build_toolbar()

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))

        left = tk.Frame(paned, bg=BG, width=320)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  weight=0)
        paned.add(right, weight=1)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=FONT_UI,
                     fieldbackground=BG2, bordercolor=BORDER, relief="flat")
        s.configure("TFrame",      background=BG)
        s.configure("TLabel",      background=BG,  foreground=TEXT)
        s.configure("TLabelframe", background=BG2, foreground=ACCENT, bordercolor=BORDER)
        s.configure("TLabelframe.Label", background=BG2, foreground=ACCENT, font=FONT_HEAD)
        s.configure("TCombobox",   fieldbackground=BG3, background=BG3,
                     foreground=TEXT, arrowcolor=ACCENT, bordercolor=BORDER)
        s.map("TCombobox", fieldbackground=[("readonly", BG3)])
        s.configure("TNotebook",   background=BG,  bordercolor=BORDER, tabmargins=0)
        s.configure("TNotebook.Tab", background=BG3, foreground=TEXT_DIM,
                     padding=[14,6], font=FONT_HEAD)
        s.map("TNotebook.Tab",
              background=[("selected", BG2)],
              foreground=[("selected", ACCENT)])
        s.configure("Accent.TButton", background=ACCENT, foreground=BG,
                     font=("Segoe UI Semibold",10), relief="flat", borderwidth=0, padding=[12,6])
        s.map("Accent.TButton",
              background=[("active","#00b894"),("disabled","#2d3348")],
              foreground=[("disabled", TEXT_DIM)])
        s.configure("Warn.TButton", background=WARN, foreground="#fff",
                     font=("Segoe UI Semibold",10), relief="flat", borderwidth=0, padding=[12,6])
        s.map("Warn.TButton", background=[("active","#e55a2b")])
        s.configure("Ghost.TButton", background=BG3, foreground=TEXT,
                     font=FONT_UI, relief="flat", borderwidth=0, padding=[10,5])
        s.map("Ghost.TButton", background=[("active", BORDER)])
        s.configure("TScrollbar", background=BG3, troughcolor=BG2,
                     arrowcolor=TEXT_DIM, bordercolor=BG, relief="flat")
        s.configure("Treeview", background=BG2, foreground=TEXT,
                     fieldbackground=BG2, bordercolor=BORDER, rowheight=24)
        s.map("Treeview", background=[("selected", BG3)], foreground=[("selected", ACCENT)])
        s.configure("Treeview.Heading", background=BG3, foreground=TEXT_DIM,
                     font=FONT_HEAD, relief="flat")
        s.configure("TEntry", fieldbackground=BG3, foreground=TEXT,
                     insertcolor=ACCENT, bordercolor=BORDER)
        s.configure("TCheckbutton", background=BG2, foreground=TEXT, indicatorcolor=BG3)
        s.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)])
        s.configure("TSpinbox", fieldbackground=BG3, foreground=TEXT,
                     background=BG3, arrowcolor=ACCENT, bordercolor=BORDER)

    # ──────── TOOLBAR ────────
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG2, height=52)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # Logo
        tk.Label(bar, text="⚙ CNC CONTROLLER", bg=BG2,
                 fg=ACCENT, font=("Consolas",13,"bold")).pack(side=tk.LEFT, padx=16)
        sep = tk.Frame(bar, bg=BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, pady=8)

        # Connection controls
        conn_frame = tk.Frame(bar, bg=BG2)
        conn_frame.pack(side=tk.LEFT, padx=12)

        tk.Label(conn_frame, text="Port", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI",9)).grid(row=0,column=0,padx=4)
        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(conn_frame, textvariable=self.port_var,
                                      width=14, state="readonly")
        self.port_cb.grid(row=0, column=1, padx=4)

        tk.Label(conn_frame, text="Baud", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI",9)).grid(row=0,column=2,padx=4)
        self.baud_var = tk.StringVar(value="115200")
        self.baud_cb  = ttk.Combobox(conn_frame, textvariable=self.baud_var,
                                      values=[str(b) for b in BAUD_RATES],
                                      width=8, state="readonly")
        self.baud_cb.grid(row=0, column=3, padx=4)

        ttk.Button(conn_frame, text="↺ Scan", style="Ghost.TButton",
                   command=self._scan_ports).grid(row=0, column=4, padx=4)
        self.conn_btn = ttk.Button(conn_frame, text="Connect",
                                    style="Accent.TButton",
                                    command=self._toggle_connect)
        self.conn_btn.grid(row=0, column=5, padx=4)

        # Status indicator
        self.status_dot = tk.Label(bar, text="●", bg=BG2, fg=ERROR,
                                    font=("Consolas",16))
        self.status_dot.pack(side=tk.LEFT, padx=6)
        self.status_lbl = tk.Label(bar, text="Disconnected", bg=BG2,
                                    fg=TEXT_DIM, font=FONT_UI)
        self.status_lbl.pack(side=tk.LEFT)

        # Right side — flow controls
        right_bar = tk.Frame(bar, bg=BG2)
        right_bar.pack(side=tk.RIGHT, padx=12)

        ttk.Button(right_bar, text="▶ Run Flow", style="Accent.TButton",
                   command=self._run_flow).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_bar, text="■ Stop",    style="Warn.TButton",
                   command=self._stop_flow).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_bar, text="New",    style="Ghost.TButton",
                   command=self._new_flow).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_bar, text="Open",   style="Ghost.TButton",
                   command=self._open_flow).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_bar, text="Save",   style="Ghost.TButton",
                   command=self._save_flow).pack(side=tk.LEFT, padx=3)
        ttk.Button(right_bar, text="Save As",style="Ghost.TButton",
                   command=self._saveas_flow).pack(side=tk.LEFT, padx=3)

    # ──────── LEFT PANEL ────────
    def _build_left_panel(self, parent):
        parent.pack_propagate(False)

        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Axes
        axes_tab = tk.Frame(nb, bg=BG2)
        nb.add(axes_tab, text=" Axes ")
        self._build_axes_tab(axes_tab)

        # Tab 2: Jog
        jog_tab = tk.Frame(nb, bg=BG2)
        nb.add(jog_tab, text=" Jog ")
        self._build_jog_tab(jog_tab)

        # Tab 3: G-Code Ref
        ref_tab = tk.Frame(nb, bg=BG2)
        nb.add(ref_tab, text=" Reference ")
        self._build_ref_tab(ref_tab)

    def _build_axes_tab(self, parent):
        hdr = tk.Frame(parent, bg=BG2)
        hdr.pack(fill=tk.X, padx=8, pady=(8,4))
        tk.Label(hdr, text="AXIS CONFIGURATION", bg=BG2,
                 fg=ACCENT, font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="+ Add Axis", style="Ghost.TButton",
                   command=self._add_custom_axis).pack(side=tk.RIGHT)

        self.axes_frame = tk.Frame(parent, bg=BG2)
        self.axes_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self._render_axes()

    def _render_axes(self):
        for w in self.axes_frame.winfo_children():
            w.destroy()
        # Header row
        hdr = tk.Frame(self.axes_frame, bg=BG3)
        hdr.pack(fill=tk.X, pady=(0,2))
        for col, width in [("Axis",5),("cm/step",10),("Enabled",7),("",4)]:
            tk.Label(hdr, text=col, bg=BG3, fg=TEXT_DIM,
                     font=("Segoe UI",9), width=width).pack(side=tk.LEFT, padx=4, pady=4)

        for name, cfg in self.axes.items():
            row = tk.Frame(self.axes_frame, bg=BG2)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name, bg=BG2, fg=ACCENT,
                     font=("Consolas",11,"bold"), width=5).pack(side=tk.LEFT, padx=4)
            sv = tk.StringVar(value=str(cfg["cm_per_step"]))
            e = tk.Entry(row, textvariable=sv, width=10, bg=BG3, fg=TEXT,
                         insertbackground=ACCENT, relief="flat",
                         highlightbackground=BORDER, highlightthickness=1,
                         font=FONT_MONO)
            e.pack(side=tk.LEFT, padx=4, pady=4)
            sv.trace_add("write", lambda *a, n=name, s=sv: self._update_axis(n, s))
            bv = tk.BooleanVar(value=cfg["enabled"])
            ck = tk.Checkbutton(row, variable=bv, bg=BG2,
                                 activebackground=BG2,
                                 selectcolor=BG3, fg=ACCENT,
                                 command=lambda n=name, v=bv: self._toggle_axis(n, v))
            ck.pack(side=tk.LEFT, padx=8)
            # Delete button only for custom axes (not default 6)
            if name not in DEFAULT_AXES:
                tk.Button(row, text="✕", bg=BG2, fg=ERROR,
                          relief="flat", bd=0, cursor="hand2", font=("Consolas",10),
                          command=lambda n=name: self._del_axis(n)).pack(side=tk.RIGHT, padx=4)

    def _update_axis(self, name, sv):
        try:
            self.axes[name]["cm_per_step"] = float(sv.get())
        except ValueError:
            pass

    def _toggle_axis(self, name, bv):
        self.axes[name]["enabled"] = bv.get()

    def _add_custom_axis(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Custom Axis")
        dlg.geometry("280x140")
        dlg.configure(bg=BG2)
        dlg.resizable(False, False)
        dlg.grab_set()
        tk.Label(dlg, text="Axis name (1-2 chars):", bg=BG2, fg=TEXT,
                 font=FONT_UI).pack(padx=16, pady=(16,4), anchor="w")
        nv = tk.StringVar()
        e = tk.Entry(dlg, textvariable=nv, bg=BG3, fg=TEXT, relief="flat",
                     insertbackground=ACCENT, font=FONT_MONO,
                     highlightbackground=BORDER, highlightthickness=1)
        e.pack(padx=16, fill=tk.X)
        e.focus()
        def _ok():
            name = nv.get().strip().upper()
            if not name or len(name) > 3:
                messagebox.showerror("Error", "Axis name must be 1–3 chars", parent=dlg)
                return
            if name in self.axes:
                messagebox.showerror("Error", "Axis already exists", parent=dlg)
                return
            self.axes[name] = {"cm_per_step": 1.0, "enabled": True}
            self._render_axes()
            dlg.destroy()
        tk.Button(dlg, text="Add Axis", bg=ACCENT, fg=BG, relief="flat",
                  font=("Segoe UI Semibold",10), command=_ok,
                  cursor="hand2").pack(pady=12)
        e.bind("<Return>", lambda e: _ok())

    def _del_axis(self, name):
        del self.axes[name]
        self._render_axes()

    def _build_jog_tab(self, parent):
        tk.Label(parent, text="JOG CONTROLS", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")

        dist_frame = tk.Frame(parent, bg=BG2)
        dist_frame.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(dist_frame, text="Step (mm):", bg=BG2, fg=TEXT,
                 font=FONT_UI).pack(side=tk.LEFT)
        self.jog_dist = tk.DoubleVar(value=1.0)
        tk.Spinbox(dist_frame, textvariable=self.jog_dist,
                   from_=0.01, to=100, increment=0.1, width=8,
                   bg=BG3, fg=TEXT, relief="flat", buttonbackground=BG3,
                   insertbackground=ACCENT, font=FONT_MONO).pack(side=tk.LEFT, padx=8)

        feed_frame = tk.Frame(parent, bg=BG2)
        feed_frame.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(feed_frame, text="Feed (mm/min):", bg=BG2, fg=TEXT,
                 font=FONT_UI).pack(side=tk.LEFT)
        self.jog_feed = tk.IntVar(value=500)
        tk.Spinbox(feed_frame, textvariable=self.jog_feed,
                   from_=10, to=10000, increment=50, width=8,
                   bg=BG3, fg=TEXT, relief="flat", buttonbackground=BG3,
                   insertbackground=ACCENT, font=FONT_MONO).pack(side=tk.LEFT, padx=8)

        # XY pad
        pad_outer = tk.Frame(parent, bg=BG2)
        pad_outer.pack(pady=10)
        tk.Label(pad_outer, text="X / Y", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI",9)).grid(row=0,column=1)
        self._jog_btn(pad_outer, "Y+", 1,1, "▲", lambda: self._jog("Y",+1))
        self._jog_btn(pad_outer, "X-", 2,0, "◄", lambda: self._jog("X",-1))
        self._jog_btn(pad_outer, "⌂",  2,1, "⌂", self._home_all)
        self._jog_btn(pad_outer, "X+", 2,2, "►", lambda: self._jog("X",+1))
        self._jog_btn(pad_outer, "Y-", 3,1, "▼", lambda: self._jog("Y",-1))

        # Z control
        z_frame = tk.Frame(parent, bg=BG2)
        z_frame.pack(pady=4)
        tk.Label(z_frame, text="Z", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI",9)).pack()
        self._jog_btn_pack(z_frame, "Z+", "▲ Z+", lambda: self._jog("Z",+1))
        self._jog_btn_pack(z_frame, "Z-", "▼ Z-", lambda: self._jog("Z",-1))

        # Other axes
        other = tk.Frame(parent, bg=BG2)
        other.pack(fill=tk.X, padx=8, pady=4)
        for ax in ["U","A","B"]:
            row = tk.Frame(other, bg=BG2)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{ax}:", bg=BG2, fg=TEXT_DIM,
                     font=FONT_UI, width=3).pack(side=tk.LEFT)
            self._jog_btn_inline(row, f"{ax}-", f"◄ {ax}-", lambda a=ax: self._jog(a,-1))
            self._jog_btn_inline(row, f"{ax}+", f"{ax}+ ►", lambda a=ax: self._jog(a,+1))

        ttk.Button(parent, text="Home All (G28)", style="Ghost.TButton",
                   command=self._home_all).pack(pady=8)

    def _jog_btn(self, parent, text, row, col, label, cmd):
        tk.Button(parent, text=label, width=4, height=2,
                  bg=BG3, fg=TEXT, relief="flat", bd=0,
                  activebackground=ACCENT, activeforeground=BG,
                  font=("Segoe UI",12), cursor="hand2",
                  command=cmd).grid(row=row, column=col, padx=3, pady=3)

    def _jog_btn_pack(self, parent, text, label, cmd):
        tk.Button(parent, text=label, width=8,
                  bg=BG3, fg=TEXT, relief="flat", bd=0,
                  activebackground=ACCENT, activeforeground=BG,
                  font=FONT_UI, cursor="hand2",
                  command=cmd).pack(pady=2)

    def _jog_btn_inline(self, parent, text, label, cmd):
        tk.Button(parent, text=label, width=7,
                  bg=BG3, fg=TEXT, relief="flat", bd=0,
                  activebackground=ACCENT, activeforeground=BG,
                  font=FONT_UI, cursor="hand2",
                  command=cmd).pack(side=tk.LEFT, padx=3)

    def _jog(self, axis, direction):
        dist = self.jog_dist.get() * direction
        feed = self.jog_feed.get()
        cmd  = f"G91\nG1 {axis}{dist:.4f} F{feed}\nG90"
        for line in cmd.strip().split("\n"):
            self._send_command(line.strip())
        self._log_terminal(f"Jog {axis}{'+' if direction>0 else '-'} {abs(dist)}mm\n", "cmd")

    def _home_all(self):
        self._send_command("G28")
        self._log_terminal("Homing all axes (G28)\n", "cmd")

    def _build_ref_tab(self, parent):
        tk.Label(parent, text="G-CODE REFERENCE", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")
        frame = tk.Frame(parent, bg=BG2)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        for code, desc in GCODE_HELP.items():
            row = tk.Frame(frame, bg=BG3, cursor="hand2")
            row.pack(fill=tk.X, pady=1)
            row.bind("<Button-1>", lambda e, d=desc: self._insert_ref(d))
            tk.Label(row, text=code, bg=BG3, fg=ACCENT2,
                     font=("Consolas",10,"bold"), width=6).pack(side=tk.LEFT, padx=6, pady=5)
            tk.Label(row, text=desc, bg=BG3, fg=TEXT_DIM,
                     font=("Segoe UI",9)).pack(side=tk.LEFT)
            row.bind("<Enter>", lambda e, r=row: r.configure(bg=BORDER))
            row.bind("<Leave>", lambda e, r=row: r.configure(bg=BG3))
            for c in row.winfo_children():
                c.bind("<Button-1>", lambda e, d=desc: self._insert_ref(d))
                c.bind("<Enter>", lambda e, r=row: r.configure(bg=BORDER))
                c.bind("<Leave>", lambda e, r=row: r.configure(bg=BG3))

    def _insert_ref(self, desc):
        # Insert example code into terminal entry
        example = desc.split("—")[-1].strip() if "—" in desc else desc
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, example)
        self.cmd_entry.focus()

    # ──────── RIGHT PANEL ────────
    def _build_right_panel(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        flow_tab = tk.Frame(nb, bg=BG)
        nb.add(flow_tab, text=" Flow Editor ")
        self._build_flow_tab(flow_tab)

        term_tab = tk.Frame(nb, bg=BG)
        nb.add(term_tab, text=" Terminal ")
        self._build_terminal_tab(term_tab)

    def _build_flow_tab(self, parent):
        # Header
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill=tk.X, pady=(4,0), padx=6)
        self.flow_title_lbl = tk.Label(hdr, text="Untitled Flow", bg=BG,
                                        fg=TEXT, font=FONT_HEAD)
        self.flow_title_lbl.pack(side=tk.LEFT)
        self.flow_status = tk.Label(hdr, text="", bg=BG, fg=TEXT_DIM, font=FONT_UI)
        self.flow_status.pack(side=tk.LEFT, padx=12)

        btn_row = tk.Frame(hdr, bg=BG)
        btn_row.pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Add Line", style="Ghost.TButton",
                   command=self._flow_add_line).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Delete", style="Ghost.TButton",
                   command=self._flow_delete_line).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="↑", style="Ghost.TButton",
                   command=self._flow_move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="↓", style="Ghost.TButton",
                   command=self._flow_move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear All", style="Warn.TButton",
                   command=self._flow_clear).pack(side=tk.LEFT, padx=2)

        # Flow list + editor
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Left: line list
        list_frame = tk.Frame(paned, bg=BG2)
        paned.add(list_frame, weight=1)

        tk.Label(list_frame, text="Lines", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI",9)).pack(anchor="w", padx=6, pady=(6,2))

        cols = ("no", "command", "comment")
        self.flow_tree = ttk.Treeview(list_frame, columns=cols,
                                       show="headings", selectmode="browse")
        self.flow_tree.heading("no",      text="#",        anchor="w")
        self.flow_tree.heading("command", text="Command",  anchor="w")
        self.flow_tree.heading("comment", text="Comment",  anchor="w")
        self.flow_tree.column("no",      width=40,  stretch=False)
        self.flow_tree.column("command", width=160, stretch=True)
        self.flow_tree.column("comment", width=120, stretch=True)
        self.flow_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.flow_tree.bind("<<TreeviewSelect>>", self._flow_on_select)
        self.flow_tree.bind("<Double-1>", lambda e: self._flow_edit_inline())

        sb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self.flow_tree.yview)
        self.flow_tree.configure(yscrollcommand=sb.set)

        # Right: inline editor
        edit_frame = tk.Frame(paned, bg=BG2)
        paned.add(edit_frame, weight=0)

        tk.Label(edit_frame, text="EDIT LINE", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(8,4))

        tk.Label(edit_frame, text="G-Code:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.edit_cmd_var = tk.StringVar()
        self.edit_cmd_entry = tk.Entry(edit_frame, textvariable=self.edit_cmd_var,
                                        bg=BG3, fg=TEXT, relief="flat",
                                        insertbackground=ACCENT, font=FONT_MONO,
                                        highlightbackground=BORDER, highlightthickness=1)
        self.edit_cmd_entry.pack(fill=tk.X, padx=8, pady=(0,8))

        tk.Label(edit_frame, text="Comment:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.edit_cmt_var = tk.StringVar()
        self.edit_cmt_entry = tk.Entry(edit_frame, textvariable=self.edit_cmt_var,
                                        bg=BG3, fg=TEXT_DIM, relief="flat",
                                        insertbackground=ACCENT, font=FONT_MONO,
                                        highlightbackground=BORDER, highlightthickness=1)
        self.edit_cmt_entry.pack(fill=tk.X, padx=8, pady=(0,8))

        ttk.Button(edit_frame, text="Update Line", style="Accent.TButton",
                   command=self._flow_update_line).pack(padx=8, pady=4, fill=tk.X)
        ttk.Button(edit_frame, text="Run This Line", style="Ghost.TButton",
                   command=self._flow_run_selected).pack(padx=8, pady=2, fill=tk.X)

        # Raw G-code text area
        tk.Label(edit_frame, text="RAW G-CODE", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(12,4))
        self.raw_text = scrolledtext.ScrolledText(
            edit_frame, bg=BG3, fg=TEXT, relief="flat",
            insertbackground=ACCENT, font=FONT_MONO,
            highlightbackground=BORDER, highlightthickness=1,
            wrap=tk.WORD, width=28, height=12)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,4))
        ttk.Button(edit_frame, text="Import from Raw", style="Ghost.TButton",
                   command=self._import_raw).pack(padx=8, pady=4, fill=tk.X)

    def _build_terminal_tab(self, parent):
        # Output
        out_frame = tk.Frame(parent, bg=BG)
        out_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6,0))

        hdr = tk.Frame(out_frame, bg=BG)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="TERMINAL OUTPUT", bg=BG, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="Clear", style="Ghost.TButton",
                   command=self._clear_terminal).pack(side=tk.RIGHT)

        self.terminal = scrolledtext.ScrolledText(
            out_frame, bg="#080c14", fg="#c8ffc8", relief="flat",
            insertbackground=ACCENT, font=("Consolas",10),
            highlightbackground=BORDER, highlightthickness=1,
            state="disabled", wrap=tk.WORD)
        self.terminal.pack(fill=tk.BOTH, expand=True, pady=(4,0))
        # Color tags
        self.terminal.tag_configure("info",    foreground="#6b9fff")
        self.terminal.tag_configure("cmd",     foreground="#00d4aa")
        self.terminal.tag_configure("resp",    foreground="#c8ffc8")
        self.terminal.tag_configure("error",   foreground="#ff4466")
        self.terminal.tag_configure("warn",    foreground="#ffaa33")
        self.terminal.tag_configure("comment", foreground="#555e7a")
        self.terminal.tag_configure("flow",    foreground="#aaaaff")

        # Input row
        in_frame = tk.Frame(parent, bg=BG2)
        in_frame.pack(fill=tk.X, padx=6, pady=6)

        self.cmd_var = tk.StringVar()
        self.cmd_entry = tk.Entry(in_frame, textvariable=self.cmd_var,
                                   bg=BG3, fg=TEXT, relief="flat",
                                   insertbackground=ACCENT, font=("Consolas",11),
                                   highlightbackground=ACCENT, highlightthickness=1)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6), ipady=6)
        self.cmd_entry.bind("<Return>",   self._terminal_send)
        self.cmd_entry.bind("<Up>",       self._hist_up)
        self.cmd_entry.bind("<Down>",     self._hist_down)

        ttk.Button(in_frame, text="Send", style="Accent.TButton",
                   command=self._terminal_send).pack(side=tk.LEFT, padx=(0,4))
        self.add_flow_btn = ttk.Button(in_frame, text="+ Add to Flow",
                                        style="Ghost.TButton",
                                        command=self._add_last_to_flow,
                                        state="disabled")
        self.add_flow_btn.pack(side=tk.LEFT)
        self.last_valid_cmd = None

    # ══════════════════════════════════════════
    #  SERIAL / CONNECTION
    # ══════════════════════════════════════════
    def _scan_ports(self):
        ports = serial.tools.list_ports.comports() if SERIAL_AVAILABLE else MockPorts.comports()
        names = [f"{p.device} — {p.description}" for p in ports]
        self.port_cb["values"] = names
        self._port_list = [p.device for p in ports]
        if names:
            self.port_cb.current(0)
        self._log_terminal(f"Found {len(names)} port(s).\n", "info")

    def _toggle_connect(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        idx = self.port_cb.current()
        if idx < 0 or not self._port_list:
            messagebox.showerror("Error", "Select a port first.")
            return
        port = self._port_list[idx]
        baud = int(self.baud_var.get())
        try:
            if SERIAL_AVAILABLE:
                self.serial_conn = serial.Serial(port, baud, timeout=2)
            else:
                self.serial_conn = MockSerial()
            self.connected = True
            self.conn_btn.configure(text="Disconnect")
            self.status_dot.configure(fg=SUCCESS)
            self.status_lbl.configure(fg=SUCCESS, text=f"Connected — {port} @ {baud}")
            self._log_terminal(f"Connected to {port} at {baud} baud.\n", "info")
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as ex:
            messagebox.showerror("Connection Error", str(ex))
            self._log_terminal(f"Connection failed: {ex}\n", "error")

    def _disconnect(self):
        if self.serial_conn:
            try: self.serial_conn.close()
            except: pass
        self.serial_conn = None
        self.connected   = False
        self.conn_btn.configure(text="Connect")
        self.status_dot.configure(fg=ERROR)
        self.status_lbl.configure(fg=TEXT_DIM, text="Disconnected")
        self._log_terminal("Disconnected.\n", "warn")

    def _read_loop(self):
        while self.connected and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline()
                if line:
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        self.after(0, self._log_terminal, f"  ← {text}\n", "resp")
            except Exception:
                break

    def _send_command(self, cmd):
        cmd = cmd.strip()
        if not cmd: return
        if not self.connected:
            self._log_terminal("Not connected.\n", "error")
            return
        try:
            self.serial_conn.write((cmd + "\n").encode())
        except Exception as ex:
            self._log_terminal(f"Send error: {ex}\n", "error")

    # ══════════════════════════════════════════
    #  TERMINAL
    # ══════════════════════════════════════════
    def _terminal_send(self, event=None):
        cmd = self.cmd_var.get().strip()
        if not cmd: return
        self.cmd_history.append(cmd)
        self.hist_idx = len(self.cmd_history)
        self.cmd_var.set("")

        tag = "cmd"
        if cmd.startswith(";") or cmd.startswith("("):
            tag = "comment"
        self._log_terminal(f"  → {cmd}\n", tag)

        valid = self._validate_gcode(cmd)
        if valid:
            self.last_valid_cmd = cmd
            self.add_flow_btn.configure(state="normal")
        else:
            self.add_flow_btn.configure(state="disabled")

        self._send_command(cmd)

    def _validate_gcode(self, cmd):
        cmd = cmd.strip().upper()
        if not cmd or cmd.startswith(";") or cmd.startswith("("):
            return False
        pattern = r"^[GMTF][0-9]+"
        return bool(re.match(pattern, cmd))

    def _add_last_to_flow(self):
        if self.last_valid_cmd:
            self._append_flow_line(self.last_valid_cmd, "Added from terminal")
            self._log_terminal(f"Added to flow: {self.last_valid_cmd}\n", "flow")
            self.add_flow_btn.configure(state="disabled")
            self.last_valid_cmd = None

    def _log_terminal(self, msg, tag="resp"):
        self.terminal.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        if tag == "cmd":
            self.terminal.insert(tk.END, f"[{ts}] ", "comment")
        self.terminal.insert(tk.END, msg, tag)
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")

    def _clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state="disabled")

    def _hist_up(self, event):
        if self.hist_idx > 0:
            self.hist_idx -= 1
            self.cmd_var.set(self.cmd_history[self.hist_idx])

    def _hist_down(self, event):
        if self.hist_idx < len(self.cmd_history) - 1:
            self.hist_idx += 1
            self.cmd_var.set(self.cmd_history[self.hist_idx])
        else:
            self.hist_idx = len(self.cmd_history)
            self.cmd_var.set("")

    # ══════════════════════════════════════════
    #  FLOW EDITOR
    # ══════════════════════════════════════════
    def _refresh_flow_tree(self):
        self.flow_tree.delete(*self.flow_tree.get_children())
        for i, line in enumerate(self.flow_lines, 1):
            cmd, *rest = line.split(";", 1)
            cmt = rest[0].strip() if rest else ""
            cmd = cmd.strip()
            tag = "comment_row" if cmd.startswith(";") or not cmd else ""
            self.flow_tree.insert("", "end", iid=str(i),
                                   values=(i, cmd or f"; {cmt}", cmt))
        count = len(self.flow_lines)
        self.flow_status.configure(
            text=f"{count} line{'s' if count!=1 else ''}")

    def _append_flow_line(self, cmd, comment=""):
        full = cmd.strip()
        if comment:
            full += f" ; {comment}"
        self.flow_lines.append(full)
        self._refresh_flow_tree()

    def _flow_add_line(self):
        self._append_flow_line("G0 X0 Y0", "New move")
        # Select new item
        iid = str(len(self.flow_lines))
        self.flow_tree.selection_set(iid)
        self.flow_tree.see(iid)
        self._flow_on_select(None)

    def _flow_delete_line(self):
        sel = self.flow_tree.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        del self.flow_lines[idx]
        self._refresh_flow_tree()

    def _flow_move_up(self):
        sel = self.flow_tree.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        if idx > 0:
            self.flow_lines[idx-1], self.flow_lines[idx] = \
                self.flow_lines[idx], self.flow_lines[idx-1]
            self._refresh_flow_tree()
            iid = str(idx)
            self.flow_tree.selection_set(iid)

    def _flow_move_down(self):
        sel = self.flow_tree.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        if idx < len(self.flow_lines) - 1:
            self.flow_lines[idx], self.flow_lines[idx+1] = \
                self.flow_lines[idx+1], self.flow_lines[idx]
            self._refresh_flow_tree()
            iid = str(idx+2)
            self.flow_tree.selection_set(iid)

    def _flow_clear(self):
        if messagebox.askyesno("Clear Flow", "Remove all lines?"):
            self.flow_lines.clear()
            self._refresh_flow_tree()

    def _flow_on_select(self, event):
        sel = self.flow_tree.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        line = self.flow_lines[idx]
        cmd, *rest = line.split(";", 1)
        cmt = rest[0].strip() if rest else ""
        self.edit_cmd_var.set(cmd.strip())
        self.edit_cmt_var.set(cmt)

    def _flow_update_line(self):
        sel = self.flow_tree.selection()
        if not sel:
            messagebox.showinfo("Update", "Select a line to update.")
            return
        idx = int(sel[0]) - 1
        cmd = self.edit_cmd_var.get().strip()
        cmt = self.edit_cmt_var.get().strip()
        full = cmd
        if cmt: full += f" ; {cmt}"
        self.flow_lines[idx] = full
        self._refresh_flow_tree()
        self.flow_tree.selection_set(sel[0])

    def _flow_edit_inline(self):
        self.edit_cmd_entry.focus()
        self.edit_cmd_entry.select_range(0, tk.END)

    def _flow_run_selected(self):
        sel = self.flow_tree.selection()
        if not sel: return
        idx = int(sel[0]) - 1
        line = self.flow_lines[idx]
        cmd = line.split(";")[0].strip()
        if cmd:
            self._send_command(cmd)
            self._log_terminal(f"  → {cmd}  (flow line {idx+1})\n", "flow")

    def _import_raw(self):
        raw = self.raw_text.get(1.0, tk.END).strip()
        if not raw: return
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if messagebox.askyesno("Import Raw", f"Replace flow with {len(lines)} lines?"):
            self.flow_lines = lines
            self._refresh_flow_tree()
        self.raw_text.delete(1.0, tk.END)

    # ══════════════════════════════════════════
    #  FLOW EXECUTION
    # ══════════════════════════════════════════
    def _run_flow(self):
        if not self.flow_lines:
            messagebox.showinfo("Run Flow", "Flow is empty.")
            return
        if not self.connected:
            messagebox.showwarning("Run Flow", "Not connected to a machine.")
            return
        if self.running_flow:
            messagebox.showinfo("Run Flow", "Flow already running.")
            return
        self.running_flow = True
        threading.Thread(target=self._flow_runner, daemon=True).start()

    def _flow_runner(self):
        self.after(0, self._log_terminal, "▶ Starting flow execution...\n", "flow")
        for i, line in enumerate(self.flow_lines):
            if not self.running_flow:
                self.after(0, self._log_terminal, "■ Flow stopped.\n", "warn")
                return
            cmd = line.split(";")[0].strip()
            if not cmd:
                continue
            iid = str(i+1)
            self.after(0, self.flow_tree.selection_set, iid)
            self.after(0, self.flow_tree.see, iid)
            self.after(0, self._log_terminal, f"  [{i+1}/{len(self.flow_lines)}] → {cmd}\n", "flow")
            self._send_command(cmd)
            time.sleep(0.05)  # small delay between commands
        self.running_flow = False
        self.after(0, self._log_terminal, "✓ Flow complete.\n", "info")

    def _stop_flow(self):
        self.running_flow = False

    # ══════════════════════════════════════════
    #  FILE OPERATIONS
    # ══════════════════════════════════════════
    def _new_flow(self):
        if self.flow_lines:
            if not messagebox.askyesno("New Flow", "Discard current flow?"):
                return
        self.flow_lines.clear()
        self.current_file = None
        self.flow_title_lbl.configure(text="Untitled Flow")
        self._refresh_flow_tree()
        self._log_terminal("New flow created.\n", "info")

    def _open_flow(self):
        path = filedialog.askopenfilename(
            title="Open G-Code Flow",
            filetypes=[("G-Code Files","*.gcode"), ("All Files","*.*")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.flow_lines = [l.rstrip("\n") for l in f.readlines()
                                   if l.strip()]
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._refresh_flow_tree()
            # Update raw view
            self.raw_text.delete(1.0, tk.END)
            self.raw_text.insert(1.0, "\n".join(self.flow_lines))
            self._log_terminal(f"Loaded: {path} ({len(self.flow_lines)} lines)\n", "info")
        except Exception as ex:
            messagebox.showerror("Open Error", str(ex))

    def _save_flow(self):
        if self.current_file:
            self._write_flow(self.current_file)
        else:
            self._saveas_flow()

    def _saveas_flow(self):
        path = filedialog.asksaveasfilename(
            title="Save Flow As",
            defaultextension=".gcode",
            filetypes=[("G-Code Files","*.gcode"), ("All Files","*.*")])
        if not path: return
        self._write_flow(path)

    def _write_flow(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.flow_lines) + "\n")
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._log_terminal(f"Saved: {path}\n", "info")
        except Exception as ex:
            messagebox.showerror("Save Error", str(ex))

    def on_close(self):
        if self.connected:
            self._disconnect()
        self.destroy()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = CNCController()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
