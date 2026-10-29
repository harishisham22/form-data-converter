# Form-Data Converter

Paste a raw `multipart/form-data` request body (the kind you copy from browser DevTools → Network → Payload) and get something usable back: nested JSON, flat JSON, or text you can paste straight into Postman's **Bulk Edit** form-data view.

Small, dependency-free Tkinter desktop app. No Python packages required at runtime.

## What it does

- Reads a raw multipart body, including the boundary lines and `Content-Disposition` headers
- Converts it to one of three outputs:
  - **Nested JSON** — `tags[]`, `meta[owner][email]`, `items[0][name]` become real arrays and objects
  - **Flat JSON** — keys stay exactly as they appear in the form (`tags[]`, `meta[owner][email]`)
  - **Postman Bulk Edit** — `key:value` lines, ready to paste into the form-data editor
- File fields are reported as `<file: filename>` (and in Bulk Edit as a comment to add manually)
- Live conversion while you type, plus trim, copy, save, and open-file options

## Requirements

- Python 3.9 or newer (Tkinter is included in the standard Python installers on Windows and macOS)
- On Linux you may need the Tk package for your distro, e.g. `sudo apt install python3-tk`

## Run it

```bash
python formdata_gui.py
```

Or just launch the prebuilt `dist/FormDataConverter.exe` on Windows.

## Usage

1. Open DevTools → Network, submit the form, select the request
2. Copy the raw request body from the **Payload** / **Request** tab (starts with a line like `------WebKitFormBoundary...`)
3. Paste it into the left pane (or use **Open file…**)
4. Pick an output format in the top bar
5. **Copy** or **Save…** the result

### Options

| Option        | Meaning                                                              |
| ------------- | -------------------------------------------------------------------- |
| Trim values   | Strips leading/trailing whitespace (including the trailing newline) from each field value. Default on. |
| Auto-convert  | Re-runs the conversion ~250 ms after you stop typing. Default on.     |

Turn **Auto-convert** off if you are pasting very large bodies.

## Example

Input:

```
------WebKitFormBoundaryABC123
Content-Disposition: form-data; name="title"

Quarterly report
------WebKitFormBoundaryABC123
Content-Disposition: form-data; name="tags[]"

finance
------WebKitFormBoundaryABC123
Content-Disposition: form-data; name="tags[]"

2026
------WebKitFormBoundaryABC123
Content-Disposition: form-data; name="meta[owner][email]"

haris@example.com
------WebKitFormBoundaryABC123
Content-Disposition: form-data; name="attachment"; filename="report.pdf"
Content-Type: application/pdf

<binary data>
------WebKitFormBoundaryABC123--
```

Nested JSON:

```json
{
  "title": "Quarterly report",
  "tags": [
    "finance",
    "2026"
  ],
  "meta": {
    "owner": {
      "email": "haris@example.com"
    }
  },
  "attachment": "<file: report.pdf>"
}
```

Bulk Edit:

```
title:Quarterly report
tags[]:finance
tags[]:2026
meta[owner][email]:haris@example.com
// file field 'attachment' (report.pdf) - add manually in Postman
```

## Building a standalone executable

Windows:

```bat
build_windows.bat
```

macOS / Linux:

```bash
chmod +x build_mac_linux.sh
./build_mac_linux.sh
```

Both scripts install PyInstaller and produce a single-file windowed app in `dist/`. The executable must be built on the OS you want to run it on — a Windows build does not run on macOS or Linux. The existing `FormDataConverter.spec` is the PyInstaller config used by those builds and can be committed/reused.

Note: `build/`, `dist/`, and the `.spec` file are PyInstaller artifacts. Rebuilding regenerates them, so treat `dist/FormDataConverter.exe` as a release output rather than source.

## Limitations

- **Flat JSON loses duplicate keys.** Repeated fields such as `tags[]` collapse into one entry (the last value wins) because JSON objects cannot hold the same key twice. Use nested JSON or Bulk Edit when repeated keys matter.
- **Everything is a string.** No attempt is made to convert `"42"` or `"true"` into numbers or booleans; the form data does not carry type information.
- **File contents are not decoded.** Only the filename is reported; `<binary data>` placeholders and real bytes are ignored.
- **Input must start at or before the first boundary line.** A leading byte-order mark or other junk before the first `--boundary` line causes the fields above the first recognized boundary to be skipped.
- **Assumes `Content-Disposition` headers** for field names. Parts without a `name=` are dropped.
- **Nested output is heuristic.** Gaps in array indices are filled with `null`, and mixing `a[0]` with `a[b]` in the same request produces whatever shape the first occurrence created.

## Project layout

```
formdata_gui.py        # entire app: multipart parser + conversion + Tkinter UI
FormDataConverter.spec # PyInstaller build config
build_windows.bat      # one-file .exe build for Windows
build_mac_linux.sh     # one-file build for macOS/Linux
dist/                  # build output
```

The conversion functions (`parse_multipart`, `to_nested`, `to_flat`, `to_bulk`) are importable and usable without the GUI:

```python
from formdata_gui import parse_multipart, to_nested

fields = parse_multipart(raw_body, strip_values=True)
print(to_nested(fields))
```
