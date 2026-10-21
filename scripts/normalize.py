"""Replace Cyrillic lookalikes accidentally typed in source identifiers."""
from pathlib import Path

BAD = {"\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c",
       "\u0443": "y", "\u0456": "i", "\u04bb": "h", "\u0410": "A", "\u0415": "E",
       "\u041e": "O", "\u0420": "P", "\u0421": "C", "\u0423": "Y"}
roots = [Path("apps/api"), Path("apps/web/src"), Path("scripts"), Path("docs"), Path("infra")]
roots += [f for f in Path(".").glob("*.yml")] + [f for f in Path(".").glob("*.yaml")]
changed = []
for root in roots:
    if not root.exists():
        continue
    walker = root.rglob("*") if root.is_dir() else [root]
    for path in walker:
        if path.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".yml", ".yaml", ".css", ".conf"}:
            continue
        text = path.read_text(encoding="utf-8")
        fixed = text
        for bad, good in BAD.items():
            fixed = fixed.replace(bad, good)
        if fixed != text:
            path.write_text(fixed, encoding="utf-8")
            changed.append(str(path))
print("normalized:", changed or "nothing")
