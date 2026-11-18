import hashlib, zipfile
from pathlib import Path
ROOT = Path("/content/sdnet_extracted")      # edit: folder holding the SDNET runs/outputs
out = Path("sdnet_evidence.zip")
pats = ["**/metrics.json", "**/test_probs.csv", "**/history.csv", "**/splits_fold*.csv", "**/*.py", "**/config.json", "**/*Results*.csv"]
keep = sorted({p for pat in pats for p in ROOT.glob(pat) if p.is_file() and p.stat().st_size < 50_000_000})
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in keep: z.write(p, p.relative_to(ROOT))
    lines = []
    for p in ROOT.rglob("*.pt"):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
        lines.append(f"{h.hexdigest()}  {p.stat().st_size}  {p.relative_to(ROOT)}")
    z.writestr("checkpoints_sha256.txt", "\n".join(lines))
    z.writestr("tree.txt", "\n".join(str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob("*")) if p.is_file())[:200000])
print(out, out.stat().st_size // 1024, "KB;", len(keep), "files;", len(lines), "checkpoints hashed")