"""Search Macrobond time series and print key metadata (dev tool for the data dictionary).

Usage:
  python scripts/mb_search.py "free text" ...                 # text search
  python scripts/mb_search.py attr:UsBlsCode=CUSR0000SA0 ...  # exact metadata match (optionally + text with ';')
Prints: PrimName, frequency, first-last obs, release, full description.
"""
import sys
import warnings

warnings.filterwarnings("ignore")
import macrobond_data_api as mda  # noqa: E402

N = 15
for q in sys.argv[1:]:
    text, filt = None, {}
    for part in q.split(";"):
        part = part.strip()
        if part.startswith("attr:"):
            k, v = part[5:].split("=", 1)
            filt[k] = v
        elif part:
            text = part
    print(f"=== {q}")
    try:
        r = mda.entity_search(text or " ".join(filt.values()), entity_types=["TimeSeries"])
    except Exception as ex:  # noqa: BLE001
        print("ERR", type(ex).__name__, str(ex)[:200])
        continue
    ents = [e for e in r.entities if all(str(e.get(k)) == v for k, v in filt.items())]   # exact client-side match
    print(f"{len(ents)} hits{' (truncated)' if r.is_truncated else ''}")
    for e in ents[:N]:
        print(f"{e.get('PrimName'):<12} {e.get('Frequency', '')[:4]:<5} {str(e.get('StartDate'))[:7]}-{str(e.get('EndDate'))[:7]} "
              f"{e.get('Release', '')[:20]:<20} {e.get('FullDescription', '')[:120]}")
