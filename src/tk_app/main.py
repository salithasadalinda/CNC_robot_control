
#!/usr/bin/env python3
"""
Universal G-Code Controller
Full G/M-code reference, BLTouch, external sensors, templates, terminal, flow manager.

Dependencies:
    pip install pyserial

Run:
    python cnc_controller.py
"""
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os

try:
    from tk_app.config import (
        ACCENT,
        ACCENT2,
        BG,
        BG2,
        BG3,
        BG4,
        BORDER,
        CAT_COLORS,
        DEFAULT_BAUD_RATE,
        DEFAULT_WINDOW_SIZE,
        ERROR,
        FONT_HEAD,
        FONT_MONO,
        FONT_MONO2,
        FONT_UI,
        FONT_UI9,
        MIN_WINDOW_SIZE,
        SUCCESS,
        TEXT,
        TEXT_DIM,
        TEXT_MID,
        WARN,
        APP_TITLE,
    )
    from tk_app.gcode import is_valid_gcode
    from tk_app.gcode.database import GCODE_DB
    from tk_app.gcode.templates import TEMPLATES
    from tk_app.serial_comm import MockPorts, MockSerial, SERIAL_AVAILABLE, serial
except ModuleNotFoundError:
    from config import (  # type: ignore
        ACCENT,
        ACCENT2,
        BG,
        BG2,
        BG3,
        BG4,
        BORDER,
        CAT_COLORS,
        DEFAULT_BAUD_RATE,
        DEFAULT_WINDOW_SIZE,
        ERROR,
        FONT_HEAD,
        FONT_MONO,
        FONT_MONO2,
        FONT_UI,
        FONT_UI9,
        MIN_WINDOW_SIZE,
        SUCCESS,
        TEXT,
        TEXT_DIM,
        TEXT_MID,
        WARN,
        APP_TITLE,
    )
    from gcode import is_valid_gcode  # type: ignore
    from gcode.database import GCODE_DB  # type: ignore
    from gcode.templates import TEMPLATES  # type: ignore
    from serial_comm import MockPorts, MockSerial, SERIAL_AVAILABLE, serial  # type: ignore

# ══════════════════════════════════════════════════════════

#  THEME
# ══════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
#  COMPLETE G-CODE / M-CODE DATABASE
# ══════════════════════════════════════════════════════════
# Format: (code, short_desc, full_desc, example, params)
# GCODE_DB is loaded from tk_app.gcode.

# ══════════════════════════════════════════════════════════
#  FLOW TEMPLATES
# ══════════════════════════════════════════════════════════
# TEMPLATES is loaded from tk_app.gcode.

# ══════════════════════════════════════════════════════════
#  SERIAL MOCK
# ══════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════
class CNCController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(DEFAULT_WINDOW_SIZE)
        self.minsize(*MIN_WINDOW_SIZE)
        self.configure(bg=BG)
        self.serial_conn  = None
        self.connected    = False
        self.flow_lines   = []
        self.current_file = None
        self.axes         = {
            "X": {"cm_per_step": 1.0, "enabled": True},
            "Y": {"cm_per_step": 1.0, "enabled": True},
            "Z": {"cm_per_step": 1.0, "enabled": True},
            "U": {"cm_per_step": 1.0, "enabled": True},
            "A": {"cm_per_step": 1.0, "enabled": True},
            "B": {"cm_per_step": 1.0, "enabled": True},
        }
        self.running_flow = False
        self.cmd_history  = []
        self.hist_idx     = -1
        self.last_valid   = None
        self._port_list   = []
        self._build_ui()
        self._scan_ports()
        self._log("Universal G-Code Controller ready.\n", "info")
        self._log(f"Loaded {sum(len(v) for v in GCODE_DB.values())} G/M codes in {len(GCODE_DB)} categories.\n", "info")

    # ════════════════════════════
    #  STYLE
    # ════════════════════════════
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=FONT_UI,
                    fieldbackground=BG2, bordercolor=BORDER, relief="flat")
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TNotebook", background=BG, bordercolor=BORDER, tabmargins=0)
        s.configure("TNotebook.Tab", background=BG3, foreground=TEXT_DIM,
                    padding=[14,6], font=FONT_HEAD)
        s.map("TNotebook.Tab",
              background=[("selected",BG2)], foreground=[("selected",ACCENT)])
        s.configure("TPanedwindow", background=BG)
        for name, bg_, fg_ in [
            ("Accent", ACCENT,  BG),
            ("Blue",   ACCENT2, BG),
            ("Warn",   WARN,    "#fff"),
            ("Red",    ERROR,   "#fff"),
        ]:
            s.configure(f"{name}.TButton", background=bg_, foreground=fg_,
                        font=("Segoe UI Semibold",10), relief="flat",
                        borderwidth=0, padding=[12,6])
            s.map(f"{name}.TButton",
                  background=[("active", bg_), ("disabled", BORDER)],
                  foreground=[("disabled", TEXT_DIM)])
        s.configure("Ghost.TButton", background=BG3, foreground=TEXT,
                    font=FONT_UI, relief="flat", borderwidth=0, padding=[10,5])
        s.map("Ghost.TButton", background=[("active", BG4)])
        s.configure("TScrollbar", background=BG3, troughcolor=BG2,
                    arrowcolor=TEXT_DIM, bordercolor=BG, relief="flat")
        s.configure("Treeview", background=BG2, foreground=TEXT,
                    fieldbackground=BG2, bordercolor=BORDER, rowheight=26)
        s.map("Treeview", background=[("selected",BG4)], foreground=[("selected",ACCENT)])
        s.configure("Treeview.Heading", background=BG3, foreground=TEXT_DIM,
                    font=FONT_HEAD, relief="flat")
        s.configure("TCombobox", fieldbackground=BG3, background=BG3,
                    foreground=TEXT, arrowcolor=ACCENT, bordercolor=BORDER)
        s.map("TCombobox", fieldbackground=[("readonly",BG3)])
        s.configure("TEntry", fieldbackground=BG3, foreground=TEXT,
                    insertcolor=ACCENT, bordercolor=BORDER)
        s.configure("TCheckbutton", background=BG2, foreground=TEXT, indicatorcolor=BG3)
        s.map("TCheckbutton", indicatorcolor=[("selected",ACCENT)])

    # ════════════════════════════
    #  UI BUILD
    # ════════════════════════════
    def _build_ui(self):
        self._style()
        self._build_toolbar()
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))
        left  = tk.Frame(paned, bg=BG, width=340)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  weight=0)
        paned.add(right, weight=1)
        left.pack_propagate(False)
        self._build_left(left)
        self._build_right(right)

    # ── TOOLBAR ──────────────────
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG2, height=54)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="⚙  UNIVERSAL G-CODE CONTROLLER", bg=BG2,
                 fg=ACCENT, font=("Consolas",12,"bold")).pack(side=tk.LEFT, padx=14)
        tk.Frame(bar, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8)
        cf = tk.Frame(bar, bg=BG2); cf.pack(side=tk.LEFT, padx=10)
        def lbl(t): tk.Label(cf, text=t, bg=BG2, fg=TEXT_DIM, font=FONT_UI9).pack(side=tk.LEFT, padx=3)
        lbl("Port")
        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(cf, textvariable=self.port_var, width=16, state="readonly")
        self.port_cb.pack(side=tk.LEFT, padx=3)
        lbl("Baud")
        self.baud_var = tk.StringVar(value=DEFAULT_BAUD_RATE)
        ttk.Combobox(cf, textvariable=self.baud_var,
                     values=["9600","19200","38400","57600","115200","250000"],
                     width=8, state="readonly").pack(side=tk.LEFT, padx=3)
        ttk.Button(cf, text="↺", style="Ghost.TButton",
                   command=self._scan_ports).pack(side=tk.LEFT, padx=2)
        self.conn_btn = ttk.Button(cf, text="Connect", style="Accent.TButton",
                                    command=self._toggle_connect)
        self.conn_btn.pack(side=tk.LEFT, padx=4)
        self.dot = tk.Label(bar, text="●", bg=BG2, fg=ERROR, font=("Consolas",18))
        self.dot.pack(side=tk.LEFT, padx=6)
        self.status_lbl = tk.Label(bar, text="Disconnected", bg=BG2,
                                    fg=TEXT_DIM, font=FONT_UI)
        self.status_lbl.pack(side=tk.LEFT)
        rf = tk.Frame(bar, bg=BG2); rf.pack(side=tk.RIGHT, padx=10)
        for txt, sty, cmd in [
            ("▶ Run Flow", "Accent.TButton", self._run_flow),
            ("■ Stop",     "Warn.TButton",   self._stop_flow),
            ("New",        "Ghost.TButton",  self._new_flow),
            ("Open",       "Ghost.TButton",  self._open_flow),
            ("Save",       "Ghost.TButton",  self._save_flow),
            ("Save As",    "Ghost.TButton",  self._saveas_flow),
        ]:
            ttk.Button(rf, text=txt, style=sty, command=cmd).pack(side=tk.LEFT, padx=2)

    # ── LEFT PANEL ───────────────
    def _build_left(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        t1 = tk.Frame(nb, bg=BG2); nb.add(t1, text=" Axes ")
        t2 = tk.Frame(nb, bg=BG2); nb.add(t2, text=" Jog ")
        t3 = tk.Frame(nb, bg=BG2); nb.add(t3, text=" Templates ")
        self._build_axes_tab(t1)
        self._build_jog_tab(t2)
        self._build_templates_tab(t3)

    def _build_axes_tab(self, p):
        hdr = tk.Frame(p, bg=BG2); hdr.pack(fill=tk.X, padx=8, pady=(8,4))
        tk.Label(hdr, text="AXIS CONFIGURATION", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="+ Add Axis", style="Ghost.TButton",
                   command=self._add_axis).pack(side=tk.RIGHT)
        self.axes_frame = tk.Frame(p, bg=BG2)
        self.axes_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        self._render_axes()

    def _render_axes(self):
        for w in self.axes_frame.winfo_children(): w.destroy()
        hdr = tk.Frame(self.axes_frame, bg=BG3); hdr.pack(fill=tk.X, pady=(0,2))
        for t, w in [("Axis",5),("cm/step",10),("Enabled",7),("",4)]:
            tk.Label(hdr, text=t, bg=BG3, fg=TEXT_DIM,
                     font=FONT_UI9, width=w).pack(side=tk.LEFT, padx=4, pady=4)
        for name, cfg in self.axes.items():
            row = tk.Frame(self.axes_frame, bg=BG2); row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=name, bg=BG2, fg=ACCENT,
                     font=("Consolas",11,"bold"), width=5).pack(side=tk.LEFT, padx=4)
            sv = tk.StringVar(value=str(cfg["cm_per_step"]))
            tk.Entry(row, textvariable=sv, width=11, bg=BG3, fg=TEXT,
                     insertbackground=ACCENT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1,
                     font=FONT_MONO).pack(side=tk.LEFT, padx=4, pady=4)
            sv.trace_add("write", lambda *a, n=name, s=sv: self._set_axis(n,s))
            bv = tk.BooleanVar(value=cfg["enabled"])
            tk.Checkbutton(row, variable=bv, bg=BG2, activebackground=BG2,
                           selectcolor=BG3, fg=ACCENT,
                           command=lambda n=name,v=bv: self._tog_axis(n,v)).pack(side=tk.LEFT, padx=6)
            if name not in ("X","Y","Z","U","A","B"):
                tk.Button(row, text="✕", bg=BG2, fg=ERROR, relief="flat", bd=0,
                          font=("Consolas",10), cursor="hand2",
                          command=lambda n=name: self._del_axis(n)).pack(side=tk.RIGHT, padx=4)

    def _set_axis(self, n, sv):
        try: self.axes[n]["cm_per_step"] = float(sv.get())
        except: pass
    def _tog_axis(self, n, bv): self.axes[n]["enabled"] = bv.get()
    def _del_axis(self, n):
        del self.axes[n]; self._render_axes()
    def _add_axis(self):
        d = tk.Toplevel(self); d.title("Add Axis"); d.geometry("260x130")
        d.configure(bg=BG2); d.resizable(False,False); d.grab_set()
        tk.Label(d, text="Axis name:", bg=BG2, fg=TEXT, font=FONT_UI).pack(padx=14, pady=(14,4), anchor="w")
        nv = tk.StringVar()
        e = tk.Entry(d, textvariable=nv, bg=BG3, fg=TEXT, relief="flat",
                     insertbackground=ACCENT, font=FONT_MONO,
                     highlightbackground=BORDER, highlightthickness=1)
        e.pack(padx=14, fill=tk.X); e.focus()
        def ok():
            nm = nv.get().strip().upper()
            if not nm or len(nm)>3: return messagebox.showerror("Error","1–3 chars", parent=d)
            if nm in self.axes:    return messagebox.showerror("Error","Already exists", parent=d)
            self.axes[nm] = {"cm_per_step":1.0,"enabled":True}
            self._render_axes(); d.destroy()
        tk.Button(d, text="Add", bg=ACCENT, fg=BG, relief="flat",
                  font=("Segoe UI Semibold",10), command=ok, cursor="hand2").pack(pady=10)
        e.bind("<Return>", lambda e: ok())

    def _build_jog_tab(self, p):
        tk.Label(p, text="JOG CONTROLS", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")
        df = tk.Frame(p, bg=BG2); df.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(df, text="Step mm:", bg=BG2, fg=TEXT, font=FONT_UI).pack(side=tk.LEFT)
        self.jog_dist = tk.DoubleVar(value=1.0)
        tk.Spinbox(df, textvariable=self.jog_dist, from_=0.01, to=100, increment=0.5,
                   width=8, bg=BG3, fg=TEXT, relief="flat",
                   buttonbackground=BG3, insertbackground=ACCENT,
                   font=FONT_MONO).pack(side=tk.LEFT, padx=6)
        ff = tk.Frame(p, bg=BG2); ff.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(ff, text="Feed mm/m:", bg=BG2, fg=TEXT, font=FONT_UI).pack(side=tk.LEFT)
        self.jog_feed = tk.IntVar(value=1000)
        tk.Spinbox(ff, textvariable=self.jog_feed, from_=10, to=20000, increment=100,
                   width=8, bg=BG3, fg=TEXT, relief="flat",
                   buttonbackground=BG3, insertbackground=ACCENT,
                   font=FONT_MONO).pack(side=tk.LEFT, padx=6)
        pad = tk.Frame(p, bg=BG2); pad.pack(pady=8)
        def jb(t, r, c, cmd):
            return tk.Button(pad, text=t, width=5, height=2,
                    bg=BG3, fg=TEXT, relief="flat", activebackground=ACCENT,
                    activeforeground=BG, font=("Segoe UI",11), cursor="hand2",
                    command=cmd).grid(row=r, column=c, padx=3, pady=3)
        jb("Y+",0,1,lambda:self._jog("Y",+1))
        jb("X-",1,0,lambda:self._jog("X",-1))
        jb("⌂",1,1,self._home_all)
        jb("X+",1,2,lambda:self._jog("X",+1))
        jb("Y-",2,1,lambda:self._jog("Y",-1))
        zf = tk.Frame(p, bg=BG2); zf.pack(pady=4)
        for t, d in [("▲ Z+",+1),("▼ Z-",-1)]:
            tk.Button(zf, text=t, width=10, bg=BG3, fg=TEXT, relief="flat",
                      activebackground=ACCENT, activeforeground=BG,
                      font=FONT_UI, cursor="hand2",
                      command=lambda d=d:self._jog("Z",d)).pack(pady=2)
        of = tk.Frame(p, bg=BG2); of.pack(fill=tk.X, padx=8, pady=4)
        for ax in ["U","A","B"]:
            r = tk.Frame(of, bg=BG2); r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=f"{ax}:", bg=BG2, fg=TEXT_DIM,
                     font=FONT_UI, width=3).pack(side=tk.LEFT)
            for t, d in [(f"◄{ax}-",-1),(f"{ax}+►",+1)]:
                tk.Button(r, text=t, width=7, bg=BG3, fg=TEXT, relief="flat",
                          activebackground=ACCENT, activeforeground=BG,
                          font=FONT_UI, cursor="hand2",
                          command=lambda a=ax, d=d:self._jog(a,d)).pack(side=tk.LEFT, padx=3)
        ttk.Button(p, text="Home All (G28)", style="Ghost.TButton",
                   command=self._home_all).pack(pady=6, fill=tk.X, padx=8)
        ttk.Button(p, text="Get Position (M114)", style="Ghost.TButton",
                   command=lambda:self._send_now("M114")).pack(pady=2, fill=tk.X, padx=8)
        ttk.Button(p, text="Endstops (M119)", style="Ghost.TButton",
                   command=lambda:self._send_now("M119")).pack(pady=2, fill=tk.X, padx=8)
        ttk.Button(p, text="Firmware Info (M115)", style="Ghost.TButton",
                   command=lambda:self._send_now("M115")).pack(pady=2, fill=tk.X, padx=8)

    def _jog(self, axis, direction):
        dist = self.jog_dist.get() * direction
        feed = self.jog_feed.get()
        for cmd in ["G91", f"G1 {axis}{dist:.4f} F{feed}", "G90"]:
            self._send_command(cmd)
        self._log(f"  Jog {axis}{'+'if direction>0 else ''}{dist:.3f} mm\n","cmd")
    def _home_all(self):
        self._send_command("G28"); self._log("  G28 Home All\n","cmd")
    def _send_now(self, cmd):
        self._send_command(cmd); self._log(f"  → {cmd}\n","cmd")

    def _build_templates_tab(self, p):
        tk.Label(p, text="FLOW TEMPLATES", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(padx=8, pady=(8,4), anchor="w")
        tk.Label(p, text="Click to load into Flow Editor", bg=BG2,
                 fg=TEXT_DIM, font=FONT_UI9).pack(padx=8, anchor="w")
        frm = tk.Frame(p, bg=BG2); frm.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        sb = ttk.Scrollbar(frm)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(frm, bg=BG3, fg=TEXT, relief="flat",
                        selectbackground=ACCENT, selectforeground=BG,
                        font=FONT_UI, yscrollcommand=sb.set,
                        highlightbackground=BORDER, highlightthickness=1,
                        activestyle="none", cursor="hand2")
        lb.pack(fill=tk.BOTH, expand=True)
        sb.configure(command=lb.yview)
        for name in TEMPLATES:
            lb.insert(tk.END, f"  {name}")
        def load(e):
            sel = lb.curselection()
            if not sel: return
            name = list(TEMPLATES.keys())[sel[0]]
            lines = TEMPLATES[name]
            if self.flow_lines:
                if not messagebox.askyesno("Load Template",
                    f"Replace current flow with\n'{name}'?\n({len(lines)} lines)"):
                    return
            self.flow_lines = list(lines)
            self.flow_title_lbl.configure(text=name)
            self._refresh_tree()
            self.current_file = None
            self._log(f"Loaded template: {name} ({len(lines)} lines)\n","info")
        lb.bind("<Double-1>", load)
        lb.bind("<Return>", load)
        ttk.Button(p, text="Load Selected Template", style="Accent.TButton",
                   command=lambda: load(None)).pack(fill=tk.X, padx=8, pady=6)

    # ── RIGHT PANEL ──────────────
    def _build_right(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        t1 = tk.Frame(nb, bg=BG);  nb.add(t1, text=" Flow Editor ")
        t2 = tk.Frame(nb, bg=BG);  nb.add(t2, text=" Terminal ")
        t3 = tk.Frame(nb, bg=BG);  nb.add(t3, text=" G-Code Reference ")
        self._build_flow_tab(t1)
        self._build_terminal_tab(t2)
        self._build_ref_tab(t3)

    # ── FLOW EDITOR ──────────────
    def _build_flow_tab(self, p):
        hdr = tk.Frame(p, bg=BG); hdr.pack(fill=tk.X, padx=6, pady=(4,0))
        self.flow_title_lbl = tk.Label(hdr, text="Untitled Flow", bg=BG,
                                        fg=TEXT, font=FONT_HEAD)
        self.flow_title_lbl.pack(side=tk.LEFT)
        self.flow_cnt = tk.Label(hdr, text="", bg=BG, fg=TEXT_DIM, font=FONT_UI)
        self.flow_cnt.pack(side=tk.LEFT, padx=10)
        br = tk.Frame(hdr, bg=BG); br.pack(side=tk.RIGHT)
        for t, s, c in [
            ("Add",    "Ghost.TButton", self._flow_add),
            ("Delete", "Ghost.TButton", self._flow_del),
            ("↑",      "Ghost.TButton", self._flow_up),
            ("↓",      "Ghost.TButton", self._flow_dn),
            ("Dup",    "Ghost.TButton", self._flow_dup),
            ("Clear",  "Warn.TButton",  self._flow_clear),
        ]:
            ttk.Button(br, text=t, style=s, command=c).pack(side=tk.LEFT, padx=1)
        pan = ttk.PanedWindow(p, orient=tk.HORIZONTAL)
        pan.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        lf = tk.Frame(pan, bg=BG2); pan.add(lf, weight=2)
        ef = tk.Frame(pan, bg=BG2); pan.add(ef, weight=1)
        # List
        cols = ("no","command","comment")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="browse")
        for col, txt, w in [("no","#",40),("command","G-Code",200),("comment","Comment",140)]:
            self.tree.heading(col, text=txt, anchor="w")
            self.tree.column(col, width=w, stretch=(col!="no"))
        sb = ttk.Scrollbar(lf, command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._tree_sel)
        self.tree.bind("<Double-1>", lambda e: self.edit_entry.focus())
        # Edit panel
        tk.Label(ef, text="EDIT LINE", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(8,4))
        tk.Label(ef, text="G-Code:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.edit_var = tk.StringVar()
        self.edit_entry = tk.Entry(ef, textvariable=self.edit_var,
                                    bg=BG3, fg=TEXT, relief="flat",
                                    insertbackground=ACCENT, font=FONT_MONO,
                                    highlightbackground=BORDER, highlightthickness=1)
        self.edit_entry.pack(fill=tk.X, padx=8, pady=(0,8))
        self.edit_entry.bind("<Return>", lambda e: self._flow_update())
        tk.Label(ef, text="Comment:", bg=BG2, fg=TEXT, font=FONT_UI).pack(anchor="w", padx=8)
        self.cmt_var = tk.StringVar()
        tk.Entry(ef, textvariable=self.cmt_var, bg=BG3, fg=TEXT_DIM, relief="flat",
                 insertbackground=ACCENT, font=FONT_MONO,
                 highlightbackground=BORDER,
                 highlightthickness=1).pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(ef, text="Update Line", style="Accent.TButton",
                   command=self._flow_update).pack(fill=tk.X, padx=8, pady=2)
        ttk.Button(ef, text="▶ Run This Line", style="Blue.TButton",
                   command=self._flow_run_sel).pack(fill=tk.X, padx=8, pady=2)
        tk.Frame(ef, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)
        tk.Label(ef, text="RAW G-CODE IMPORT", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(0,4))
        self.raw_text = scrolledtext.ScrolledText(ef, bg=BG3, fg=TEXT, relief="flat",
            insertbackground=ACCENT, font=FONT_MONO2,
            highlightbackground=BORDER, highlightthickness=1,
            wrap=tk.WORD, width=30, height=14)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,4))
        ttk.Button(ef, text="Import from Raw", style="Ghost.TButton",
                   command=self._import_raw).pack(fill=tk.X, padx=8, pady=4)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, line in enumerate(self.flow_lines, 1):
            cmd, *rest = line.split(";",1)
            cmt = rest[0].strip() if rest else ""
            cmd = cmd.strip()
            self.tree.insert("","end", iid=str(i), values=(i, cmd or f";{cmt}", cmt))
        self.flow_cnt.configure(text=f"{len(self.flow_lines)} lines")

    def _tree_sel(self, e):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        line = self.flow_lines[idx]
        cmd, *rest = line.split(";",1)
        self.edit_var.set(cmd.strip())
        self.cmt_var.set(rest[0].strip() if rest else "")

    def _flow_add(self):
        self.flow_lines.append("G0 X0 Y0")
        self._refresh_tree()
        iid = str(len(self.flow_lines))
        self.tree.selection_set(iid); self.tree.see(iid)
        self._tree_sel(None); self.edit_entry.focus()
    def _flow_del(self):
        sel = self.tree.selection()
        if not sel: return
        del self.flow_lines[int(sel[0])-1]; self._refresh_tree()
    def _flow_dup(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        self.flow_lines.insert(idx+1, self.flow_lines[idx])
        self._refresh_tree()
    def _flow_up(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        if idx>0:
            self.flow_lines[idx-1],self.flow_lines[idx] = self.flow_lines[idx],self.flow_lines[idx-1]
            self._refresh_tree(); iid=str(idx); self.tree.selection_set(iid)
    def _flow_dn(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        if idx<len(self.flow_lines)-1:
            self.flow_lines[idx],self.flow_lines[idx+1] = self.flow_lines[idx+1],self.flow_lines[idx]
            self._refresh_tree(); iid=str(idx+2); self.tree.selection_set(iid)
    def _flow_clear(self):
        if messagebox.askyesno("Clear","Remove all lines?"):
            self.flow_lines.clear(); self._refresh_tree()
    def _flow_update(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showinfo("Update","Select a line first.")
        idx = int(sel[0])-1
        cmd = self.edit_var.get().strip()
        cmt = self.cmt_var.get().strip()
        self.flow_lines[idx] = cmd + (f" ; {cmt}" if cmt else "")
        self._refresh_tree(); self.tree.selection_set(sel[0])
    def _flow_run_sel(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])-1
        cmd = self.flow_lines[idx].split(";")[0].strip()
        if cmd: self._send_command(cmd); self._log(f"  → {cmd}  [line {idx+1}]\n","flow")
    def _import_raw(self):
        raw = self.raw_text.get(1.0, tk.END).strip()
        if not raw: return
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if messagebox.askyesno("Import",f"Replace flow with {len(lines)} lines?"):
            self.flow_lines = lines; self._refresh_tree()
            self.raw_text.delete(1.0, tk.END)

    # ── TERMINAL ─────────────────
    def _build_terminal_tab(self, p):
        hdr = tk.Frame(p, bg=BG); hdr.pack(fill=tk.X, padx=6, pady=(4,0))
        tk.Label(hdr, text="SERIAL TERMINAL", bg=BG, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        ttk.Button(hdr, text="Clear", style="Ghost.TButton",
                   command=self._clear_term).pack(side=tk.RIGHT)
        self.terminal = scrolledtext.ScrolledText(p, bg="#060a10", fg="#b0ffb0",
            relief="flat", insertbackground=ACCENT, font=("Consolas",10),
            highlightbackground=BORDER, highlightthickness=1,
            state="disabled", wrap=tk.WORD)
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        for tag, color in [
            ("info","#5b9bd5"),("cmd","#00e5b0"),("resp","#7fff7f"),
            ("error","#ff3d6b"),("warn","#ffaa44"),("comment","#4a5270"),
            ("flow","#a78bfa"),("sys","#e879f9"),
        ]:
            self.terminal.tag_configure(tag, foreground=color)
        inp = tk.Frame(p, bg=BG2); inp.pack(fill=tk.X, padx=6, pady=6)
        self.cmd_var = tk.StringVar()
        self.cmd_entry = tk.Entry(inp, textvariable=self.cmd_var, bg=BG3, fg=TEXT,
                                   relief="flat", insertbackground=ACCENT,
                                   font=("Consolas",11),
                                   highlightbackground=ACCENT, highlightthickness=1)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6), ipady=7)
        self.cmd_entry.bind("<Return>", self._term_send)
        self.cmd_entry.bind("<Up>",     self._hist_up)
        self.cmd_entry.bind("<Down>",   self._hist_dn)
        ttk.Button(inp, text="Send", style="Accent.TButton",
                   command=self._term_send).pack(side=tk.LEFT, padx=(0,4))
        self.addflow_btn = ttk.Button(inp, text="+ Add to Flow",
                                       style="Ghost.TButton",
                                       command=self._add_to_flow,
                                       state="disabled")
        self.addflow_btn.pack(side=tk.LEFT)

    def _term_send(self, e=None):
        cmd = self.cmd_var.get().strip()
        if not cmd: return
        self.cmd_history.append(cmd); self.hist_idx = len(self.cmd_history)
        self.cmd_var.set("")
        tag = "comment" if cmd.startswith((";", "(")) else "cmd"
        self._log(f"  → {cmd}\n", tag)
        if self._valid_gcode(cmd):
            self.last_valid = cmd
            self.addflow_btn.configure(state="normal")
        else:
            self.addflow_btn.configure(state="disabled")
        self._send_command(cmd)

    def _valid_gcode(self, cmd):
        return is_valid_gcode(cmd)

    def _add_to_flow(self):
        if self.last_valid:
            self.flow_lines.append(self.last_valid)
            self._refresh_tree()
            self._log(f"  Added to flow: {self.last_valid}\n","flow")
            self.last_valid = None
            self.addflow_btn.configure(state="disabled")

    def _log(self, msg, tag="resp"):
        self.terminal.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        if tag in ("cmd","flow","sys"):
            self.terminal.insert(tk.END, f"[{ts}] ","comment")
        self.terminal.insert(tk.END, msg, tag)
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")

    def _clear_term(self):
        self.terminal.configure(state="normal")
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state="disabled")

    def _hist_up(self, e):
        if self.hist_idx>0:
            self.hist_idx -= 1; self.cmd_var.set(self.cmd_history[self.hist_idx])
    def _hist_dn(self, e):
        if self.hist_idx<len(self.cmd_history)-1:
            self.hist_idx += 1; self.cmd_var.set(self.cmd_history[self.hist_idx])
        else:
            self.hist_idx = len(self.cmd_history); self.cmd_var.set("")

    # ── G-CODE REFERENCE ─────────
    def _build_ref_tab(self, p):
        # Top: category filter + search
        top = tk.Frame(p, bg=BG); top.pack(fill=tk.X, padx=6, pady=(6,4))
        tk.Label(top, text="Category:", bg=BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT)
        self.cat_var = tk.StringVar(value="All")
        cats = ["All"] + list(GCODE_DB.keys())
        self.cat_cb  = ttk.Combobox(top, textvariable=self.cat_var, values=cats,
                                     width=18, state="readonly")
        self.cat_cb.pack(side=tk.LEFT, padx=6)
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_ref())
        tk.Label(top, text="Search:", bg=BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT, padx=(10,0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_ref())
        tk.Entry(top, textvariable=self.search_var, bg=BG3, fg=TEXT, relief="flat",
                 insertbackground=ACCENT, font=FONT_MONO,
                 highlightbackground=BORDER, highlightthickness=1,
                 width=20).pack(side=tk.LEFT, padx=6)
        self.ref_count_lbl = tk.Label(top, text="", bg=BG, fg=TEXT_DIM, font=FONT_UI9)
        self.ref_count_lbl.pack(side=tk.RIGHT, padx=10)
        # Paned: list | detail
        pan = ttk.PanedWindow(p, orient=tk.HORIZONTAL)
        pan.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        lf = tk.Frame(pan, bg=BG2); pan.add(lf, weight=1)
        df = tk.Frame(pan, bg=BG2); pan.add(df, weight=1)
        # List treeview
        cols = ("cat","code","desc")
        self.ref_tree = ttk.Treeview(lf, columns=cols, show="headings",
                                      selectmode="browse")
        for col, txt, w in [("cat","Category",100),("code","Code",70),("desc","Description",200)]:
            self.ref_tree.heading(col, text=txt, anchor="w")
            self.ref_tree.column(col, width=w, stretch=(col=="desc"))
        sb = ttk.Scrollbar(lf, command=self.ref_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.ref_tree.configure(yscrollcommand=sb.set)
        self.ref_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.ref_tree.bind("<<TreeviewSelect>>", self._ref_select)
        # Detail panel
        tk.Label(df, text="CODE DETAIL", bg=BG2, fg=ACCENT,
                 font=("Consolas",9,"bold")).pack(anchor="w", padx=8, pady=(8,4))
        self.det_code = tk.Label(df, text="", bg=BG2, fg=ACCENT,
                                  font=("Consolas",18,"bold"))
        self.det_code.pack(anchor="w", padx=10, pady=(0,2))
        self.det_short = tk.Label(df, text="", bg=BG2, fg=TEXT,
                                   font=("Segoe UI Semibold",11))
        self.det_short.pack(anchor="w", padx=10)
        self.det_cat = tk.Label(df, text="", bg=BG2, fg=TEXT_DIM, font=FONT_UI9)
        self.det_cat.pack(anchor="w", padx=10, pady=(0,6))
        tk.Frame(df, bg=BORDER, height=1).pack(fill=tk.X, padx=8)
        tk.Label(df, text="Description:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(8,2))
        self.det_desc = tk.Text(df, bg=BG3, fg=TEXT, relief="flat",
                                 font=FONT_UI, wrap=tk.WORD, height=5,
                                 highlightbackground=BORDER, highlightthickness=1,
                                 state="disabled")
        self.det_desc.pack(fill=tk.X, padx=8, pady=(0,6))
        tk.Label(df, text="Example:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(4,2))
        self.det_ex = tk.Text(df, bg="#0a1020", fg=ACCENT, relief="flat",
                               font=FONT_MONO, wrap=tk.WORD, height=4,
                               highlightbackground=BORDER, highlightthickness=1,
                               state="disabled")
        self.det_ex.pack(fill=tk.X, padx=8, pady=(0,6))
        tk.Label(df, text="Parameters:", bg=BG2, fg=TEXT_DIM,
                 font=FONT_UI9).pack(anchor="w", padx=10, pady=(4,2))
        self.det_params = tk.Text(df, bg=BG3, fg=TEXT_MID, relief="flat",
                                   font=FONT_MONO2, wrap=tk.WORD, height=3,
                                   highlightbackground=BORDER, highlightthickness=1,
                                   state="disabled")
        self.det_params.pack(fill=tk.X, padx=8, pady=(0,8))
        # Buttons
        bf = tk.Frame(df, bg=BG2); bf.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(bf, text="Send to Terminal", style="Accent.TButton",
                   command=self._ref_send_terminal).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Add to Flow", style="Blue.TButton",
                   command=self._ref_add_flow).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="Copy Example", style="Ghost.TButton",
                   command=self._ref_copy).pack(side=tk.LEFT, padx=4)
        self._ref_items = []  # cache for filter
        self._populate_ref()

    def _populate_ref(self):
        self.ref_tree.delete(*self.ref_tree.get_children())
        self._ref_items.clear()
        query  = self.search_var.get().lower().strip() if hasattr(self,'search_var') else ""
        filter_cat = self.cat_var.get() if hasattr(self,'cat_var') else "All"
        count  = 0
        for cat, codes in GCODE_DB.items():
            if filter_cat != "All" and cat != filter_cat:
                continue
            color = CAT_COLORS.get(cat, TEXT_DIM)
            for code, short, full, example, params in codes:
                if query and query not in code.lower() \
                         and query not in short.lower() \
                         and query not in full.lower():
                    continue
                iid = f"{cat}|{code}|{count}"
                self.ref_tree.insert("","end", iid=iid,
                                      values=(cat, code, short),
                                      tags=(cat,))
                self._ref_items.append((iid, cat, code, short, full, example, params))
                count += 1
            self.ref_tree.tag_configure(cat, foreground=color)
        self.ref_count_lbl.configure(text=f"{count} codes")

    def _filter_ref(self):
        self._populate_ref()

    def _ref_select(self, e):
        sel = self.ref_tree.selection()
        if not sel: return
        iid = sel[0]
        for item in self._ref_items:
            if item[0] == iid:
                _, cat, code, short, full, example, params = item
                self.det_code.configure(text=code,
                    fg=CAT_COLORS.get(cat, ACCENT))
                self.det_short.configure(text=short)
                self.det_cat.configure(text=f"Category: {cat}")
                for widget, txt in [
                    (self.det_desc, full),
                    (self.det_ex,   example),
                    (self.det_params, params),
                ]:
                    widget.configure(state="normal")
                    widget.delete(1.0, tk.END)
                    widget.insert(1.0, txt)
                    widget.configure(state="disabled")
                self._current_example = example.split("\n")[0].split(";")[0].strip()
                self._current_code    = code
                break

    def _ref_send_terminal(self):
        if hasattr(self,'_current_example') and self._current_example:
            self.cmd_var.set(self._current_example)
            self.cmd_entry.focus()
    def _ref_add_flow(self):
        if hasattr(self,'_current_example') and self._current_example:
            self.flow_lines.append(self._current_example)
            self._refresh_tree()
            self._log(f"  Added to flow: {self._current_example}\n","flow")
    def _ref_copy(self):
        if hasattr(self,'_current_example'):
            self.clipboard_clear()
            self.clipboard_append(self._current_example)
            self._log(f"  Copied: {self._current_example}\n","sys")

    # ════════════════════════════
    
    #  SERIAL
    # ════════════════════════════
    def _scan_ports(self):
        ports = serial.tools.list_ports.comports() if SERIAL_AVAILABLE else MockPorts.comports() # type: ignore
        self._port_list = [p.device for p in ports]
        names = [f"{p.device} — {p.description}" for p in ports]
        self.port_cb["values"] = names
        if names: self.port_cb.current(0)
        self._log(f"Found {len(names)} port(s).\n","sys")

    def _toggle_connect(self):
        if self.connected: self._disconnect()
        else: self._connect()

    def _connect(self):
        idx = self.port_cb.current()
        if idx<0 or not self._port_list:
            return messagebox.showerror("Error","Select a port.")
        port = self._port_list[idx]
        baud = int(self.baud_var.get())
        try:
            self.serial_conn = serial.Serial(port, baud, timeout=2) if SERIAL_AVAILABLE else MockSerial()  # type: ignore
            self.connected = True
            self.conn_btn.configure(text="Disconnect")
            self.dot.configure(fg=SUCCESS)
            self.status_lbl.configure(fg=SUCCESS, text=f"Connected  {port} @ {baud}")
            self._log(f"Connected to {port} at {baud} baud.\n","sys")
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            self._log(f"Connection failed: {ex}\n","error")

    def _disconnect(self):
        try: self.serial_conn and self.serial_conn.close() # type: ignore
        except KeyError as e:
            logging.exception('error while accessing the dict')
            raise e
        self.serial_conn = None; self.connected = False
        self.conn_btn.configure(text="Connect")
        self.dot.configure(fg=ERROR)
        self.status_lbl.configure(fg=TEXT_DIM, text="Disconnected")
        self._log("Disconnected.\n","warn")

    def _read_loop(self):
        while self.connected and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline()
                if line:
                    txt = line.decode("utf-8", errors="replace").strip()
                    if txt: self.after(0, self._log, f"  ← {txt}\n", "resp")
            except Exception:
                break

    def _send_command(self, cmd):
        cmd = cmd.strip()
        if not cmd: return
        if not self.connected:
            self._log("Not connected.\n","error"); return
        try: self.serial_conn.write((cmd+"\n").encode()) # type: ignore
        except Exception as ex: self._log(f"Send error: {ex}\n","error")

    # ════════════════════════════
    #  FLOW RUN
    # ════════════════════════════
    def _run_flow(self):
        if not self.flow_lines: return messagebox.showinfo("Run","Flow is empty.")
        if not self.connected:  return messagebox.showwarning("Run","Not connected.")
        if self.running_flow:   return
        self.running_flow = True
        threading.Thread(target=self._runner, daemon=True).start()

    def _runner(self):
        self.after(0, self._log,"▶ Flow started...\n","flow")
        for i, line in enumerate(self.flow_lines):
            if not self.running_flow:
                self.after(0, self._log,"■ Flow stopped.\n","warn"); return
            cmd = line.split(";")[0].strip()
            if not cmd: continue
            iid = str(i+1)
            self.after(0, self.tree.selection_set, iid)
            self.after(0, self.tree.see, iid)
            self.after(0, self._log, f"  [{i+1}/{len(self.flow_lines)}] → {cmd}\n","flow")
            self._send_command(cmd)
            time.sleep(0.06)
        self.running_flow = False
        self.after(0, self._log,"✓ Flow complete.\n","info")

    def _stop_flow(self): self.running_flow = False

    # ════════════════════════════
    #  FILE OPS
    # ════════════════════════════
    def _new_flow(self):
        if self.flow_lines:
            if not messagebox.askyesno("New","Discard current flow?"): return
        self.flow_lines.clear(); self.current_file = None
        self.flow_title_lbl.configure(text="Untitled Flow")
        self._refresh_tree()

    def _open_flow(self):
        path = filedialog.askopenfilename(title="Open G-Code",
            filetypes=[("G-Code","*.gcode"),("All","*.*")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                self.flow_lines = [l.rstrip("\n") for l in f if l.strip()]
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._refresh_tree()
            self.raw_text.delete(1.0, tk.END)
            self.raw_text.insert(1.0,"\n".join(self.flow_lines))
            self._log(f"Loaded: {path} ({len(self.flow_lines)} lines)\n","sys")
        except Exception as ex: messagebox.showerror("Error",str(ex))

    def _save_flow(self):
        if self.current_file: self._write(self.current_file)
        else: self._saveas_flow()

    def _saveas_flow(self):
        path = filedialog.asksaveasfilename(title="Save As",
            defaultextension=".gcode",
            filetypes=[("G-Code","*.gcode"),("All","*.*")])
        if path: self._write(path)

    def _write(self, path):
        try:
            with open(path,"w",encoding="utf-8") as f:
                f.write("\n".join(self.flow_lines)+"\n")
            self.current_file = path
            self.flow_title_lbl.configure(text=os.path.basename(path))
            self._log(f"Saved: {path}\n","sys")
        except Exception as ex: messagebox.showerror("Error",str(ex))

    def on_close(self):
        self._disconnect(); self.destroy()


def main():
    app = CNCController()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
