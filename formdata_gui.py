#!/usr/bin/env python3
"""
Form-Data Converter - paste a raw multipart/form-data body (from browser
dev tools) and get nested JSON, flat JSON, or Postman Bulk Edit text.

Run directly:   python formdata_gui.py
Build an exe:   see build_windows.bat / build_mac_linux.sh
"""
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --------------------------------------------------------------------------
# Conversion logic
# --------------------------------------------------------------------------
NAME_RE = re.compile(r'name="((?:[^"\\]|\\.)*)"')
FILENAME_RE = re.compile(r'filename="((?:[^"\\]|\\.)*)"')


def parse_multipart(text, strip_values=False):
    """Return a list of (name, value, filename_or_None) tuples, in order."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    boundary = None
    for ln in lines:
        if ln.strip().startswith("--"):
            boundary = ln.strip()
            break
    if not boundary:
        raise ValueError("No multipart boundary found (a line starting with '--').")

    closing = boundary + "--"
    fields = []
    current = None

    def flush():
        if current is None or current["name"] is None:
            return
        value = "\n".join(current["value_lines"])
        if strip_values:
            value = value.strip()
        fields.append((current["name"], value, current["filename"]))

    for ln in lines:
        s = ln.strip()
        if s == boundary or s == closing:
            flush()
            current = None if s == closing else {
                "name": None, "filename": None,
                "value_lines": [], "in_headers": True}
            continue
        if current is None:
            continue
        if current["in_headers"]:
            if ln == "":
                current["in_headers"] = False
            elif ln.lower().startswith("content-disposition"):
                m = NAME_RE.search(ln)
                if m:
                    current["name"] = m.group(1)
                f = FILENAME_RE.search(ln)
                if f:
                    current["filename"] = f.group(1)
        else:
            current["value_lines"].append(ln)

    flush()
    if not fields:
        raise ValueError("Boundary found, but no form fields could be parsed.")
    return fields


def split_key(key):
    m = re.match(r"^([^\[\]]+)((?:\[[^\[\]]*\])*)$", key)
    if not m:
        return [key]
    return [m.group(1)] + re.findall(r"\[([^\[\]]*)\]", m.group(2))


def set_nested(root, parts, value):
    node = root
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        nxt = None if last else parts[i + 1]
        new = lambda n: [] if (n == "" or n.isdigit()) else {}
        if isinstance(node, list):
            idx = len(node) if part == "" else int(part)
            while len(node) <= idx:
                node.append(None)
            if last:
                node[idx] = value
            else:
                if node[idx] is None:
                    node[idx] = new(nxt)
                node = node[idx]
        else:
            if last:
                node[part] = value
            else:
                if part not in node:
                    node[part] = new(nxt)
                node = node[part]


def to_nested(fields):
    root = {}
    for name, value, filename in fields:
        set_nested(root, split_key(name),
                   f"<file: {filename}>" if filename else value)
    return json.dumps(root, indent=2, ensure_ascii=False)


def to_flat(fields):
    out = {n: (f"<file: {fn}>" if fn else v) for n, v, fn in fields}
    return json.dumps(out, indent=2, ensure_ascii=False)


def to_bulk(fields):
    lines = []
    for name, value, filename in fields:
        if filename:
            lines.append(f"// file field '{name}' ({filename}) - add manually in Postman")
        else:
            lines.append(f"{name}:{value}")
    return "\n".join(lines)


FORMATS = {
    "nested": ("Nested JSON (raw body)", to_nested, ".json"),
    "flat": ("Flat JSON (keys as-is)", to_flat, ".json"),
    "bulk": ("Postman Bulk Edit (form-data)", to_bulk, ".txt"),
}


def convert(text, fmt, strip):
    fields = parse_multipart(text, strip_values=strip)
    return FORMATS[fmt][1](fields), len(fields)


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Form-Data Converter")
        self.geometry("1000x620")
        self.minsize(760, 440)

        self.fmt = tk.StringVar(value="nested")
        self.strip = tk.BooleanVar(value=True)
        self.auto = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Paste a raw multipart body on the left.")
        self._after_id = None

        self._build()

    def _build(self):
        # Options bar
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="Output:").pack(side="left")
        for key, (label, _, _) in FORMATS.items():
            ttk.Radiobutton(bar, text=label, value=key, variable=self.fmt,
                            command=self.run).pack(side="left", padx=(10, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=14)
        ttk.Checkbutton(bar, text="Trim values", variable=self.strip,
                        command=self.run).pack(side="left")
        ttk.Checkbutton(bar, text="Auto-convert", variable=self.auto
                        ).pack(side="left", padx=(10, 0))

        # Panes
        panes = ttk.PanedWindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=10)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=1)

        # Input
        lh = ttk.Frame(left)
        lh.pack(fill="x", pady=(0, 4))
        ttk.Label(lh, text="Raw form-data", font=("", 10, "bold")).pack(side="left")
        ttk.Button(lh, text="Clear", command=self.clear).pack(side="right")
        ttk.Button(lh, text="Paste", command=self.paste).pack(side="right", padx=4)
        ttk.Button(lh, text="Open file…", command=self.open_file).pack(side="right")
        self.inp = self._textbox(left)
        self.inp.bind("<<Modified>>", self._on_modified)

        # Output
        rh = ttk.Frame(right)
        rh.pack(fill="x", pady=(0, 4))
        ttk.Label(rh, text="Result", font=("", 10, "bold")).pack(side="left")
        ttk.Button(rh, text="Save…", command=self.save).pack(side="right")
        ttk.Button(rh, text="Copy", command=self.copy).pack(side="right", padx=4)
        ttk.Button(rh, text="Convert", command=self.run).pack(side="right")
        self.out = self._textbox(right, readonly=True)

        # Status bar
        ttk.Label(self, textvariable=self.status, anchor="w",
                  relief="sunken", padding=(8, 3)).pack(fill="x", side="bottom")

    def _textbox(self, parent, readonly=False):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=(0, 8))
        txt = tk.Text(frame, wrap="none", undo=True, font=("Consolas", 10)
                      if self.tk.call("tk", "windowingsystem") == "win32"
                      else ("Menlo", 11))
        ys = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        txt.pack(side="left", fill="both", expand=True)
        return txt

    # ----- actions -----
    def _on_modified(self, _event=None):
        if self.inp.edit_modified():
            self.inp.edit_modified(False)
            if self.auto.get():
                if self._after_id:
                    self.after_cancel(self._after_id)
                self._after_id = self.after(250, self.run)

    def _set_output(self, text):
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)

    def run(self):
        text = self.inp.get("1.0", "end").strip()
        if not text:
            self._set_output("")
            self.status.set("Paste a raw multipart body on the left.")
            return
        try:
            result, n = convert(text, self.fmt.get(), self.strip.get())
        except Exception as e:
            self._set_output("")
            self.status.set(f"Error: {e}")
            return
        self._set_output(result)
        self.status.set(f"Converted {n} field(s).")

    def paste(self):
        try:
            data = self.clipboard_get()
        except tk.TclError:
            self.status.set("Clipboard is empty.")
            return
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", data)
        self.run()

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt *.log *.dat"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                data = fh.read()
        except OSError as e:
            messagebox.showerror("Error", str(e))
            return
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", data)
        self.run()

    def clear(self):
        self.inp.delete("1.0", "end")
        self._set_output("")
        self.status.set("Cleared.")

    def copy(self):
        text = self.out.get("1.0", "end").rstrip("\n")
        if not text:
            self.status.set("Nothing to copy.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Copied to clipboard.")

    def save(self):
        text = self.out.get("1.0", "end").rstrip("\n")
        if not text:
            self.status.set("Nothing to save.")
            return
        ext = FORMATS[self.fmt.get()][2]
        path = filedialog.asksaveasfilename(
            defaultextension=ext, filetypes=[("Output", f"*{ext}"), ("All", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            self.status.set(f"Saved to {path}")


if __name__ == "__main__":
    App().mainloop()
