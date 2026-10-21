"""Excel automation (Windows, COM): recalculate a workbook so that formula cells carry stored values."""
from __future__ import annotations

from pathlib import Path


def recalc(path: str | Path, out: str | Path | None = None) -> Path:
    """Open in Excel, force a full calculation and save (xlsx), so every formula cell has a cached value."""
    import pythoncom
    import win32com.client as w
    path = Path(path).resolve()
    out = Path(out).resolve() if out else path
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = w.DispatchEx("Excel.Application")
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(str(path))
        xl.CalculateFull()
        if out == path:
            wb.Save()
        else:
            wb.SaveAs(str(out), FileFormat=51)
        wb.Close(SaveChanges=False)
        wb = None
    finally:
        try:
            if xl is not None:
                xl.Quit()
        except Exception:                                          # noqa: BLE001
            pass
        del wb, xl
        pythoncom.CoUninitialize()
    return out
