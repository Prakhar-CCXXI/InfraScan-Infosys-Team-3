"""
RDD2022 (India) Pascal-VOC -> Ultralytics YOLO detection dataset with a leakage-aware train/val/test split.

Class policy (agreed): keep structural road damage only
    D00 + D01 -> 0 (D00 longitudinal crack)      D10 + D11 -> 1 (D10 transverse crack)
    D20       -> 2 (alligator crack)             D40       -> 3 (D40 other corruption: rutting/bump/pothole/separation)
  dropped boxes: D43, D44 (road-marking blur), D50 (utility hole), D0w0 (label typo), anything unknown.  Images are KEPT (as background if nothing remains).
Split policy: the official test images have no labels, so val/test are carved from the labelled train images.
  * images are sorted by filename number and cut into contiguous blocks (adjacent frames stay together);
  * blocks linked by identical-perceptual-hash images are merged into one unit (duplicates never straddle splits);
  * units are assigned greedily to match the target fractions for images AND for each class (so rare classes reach val/test).

Usage:
  python ml/data/prepare_rdd2022_yolo.py --root RDD2022_India --out-dir rdd2022_yolo [--block-size 50] [--fractions 0.7 0.15 0.15]
Outputs: images/ labels/ (train|val|test), rdd2022_damage.yaml, conversion_report.json, split_assignment.csv, check/overlays.jpg
"""
import argparse, json, random, re, shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

KEEP = {"D00": 0, "D01": 0, "D10": 1, "D11": 1, "D20": 2, "D40": 3}
NAMES = ["D00", "D10", "D20", "D40"]
SPLITS = ["train", "val", "test"]


def dhash(p):
    with Image.open(p) as im:
        g = np.asarray(im.convert("L").resize((9, 8)), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def ham(a, b):
    return bin(a ^ b).count("1")


def num_id(stem):
    m = re.search(r"(\d+)$", stem)
    return int(m.group(1)) if m else 10 ** 9


def parse_voc(p):
    r = ET.parse(p).getroot()
    sz = r.find("size")
    W, H = int(float(sz.findtext("width"))), int(float(sz.findtext("height")))
    boxes = []
    for o in r.findall("object"):
        bb = o.find("bndbox")
        if bb is None:
            continue
        boxes.append(((o.findtext("name") or "").strip(), *[float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")]))
    return W, H, boxes


class DSU:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out-dir", default="rdd2022_yolo")
    ap.add_argument("--block-size", type=int, default=50)
    ap.add_argument("--fractions", type=float, nargs=3, default=[0.70, 0.15, 0.15])
    ap.add_argument("--hash-threshold", type=int, default=0, help="max Hamming distance of dHash treated as the same image (0 = identical)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-check", type=int, default=12)
    a = ap.parse_args()
    root, out = Path(a.root), Path(a.out_dir)
    random.seed(a.seed); rng = np.random.RandomState(a.seed)
    img_dir = root / "train" / "images"
    xmls = {p.stem: p for p in (root / "train").rglob("*.xml")}
    imgs = {p.stem: p for p in img_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}}
    stems = sorted(set(imgs) & set(xmls), key=lambda s: (num_id(s), s))
    rep = dict(images_found=len(imgs), xml_found=len(xmls), paired=len(stems), unpaired_images=len(set(imgs) - set(xmls)), unpaired_xml=len(set(xmls) - set(imgs)))

    # ---- parse + remap ----
    recs, dropped, unknown = [], Counter(), Counter()
    clipped = degenerate = 0
    for s in stems:
        W, H, boxes = parse_voc(xmls[s])
        kept = []
        for name, x0, y0, x1, y1 in boxes:
            if name not in KEEP:
                (dropped if name in {"D43", "D44", "D50", "D0w0"} else unknown)[name] += 1; continue
            cx0, cy0, cx1, cy1 = max(0.0, x0), max(0.0, y0), min(float(W), x1), min(float(H), y1)
            clipped += int((cx0, cy0, cx1, cy1) != (x0, y0, x1, y1))
            if cx1 - cx0 < 1 or cy1 - cy0 < 1:
                degenerate += 1; continue
            kept.append((KEEP[name], cx0, cy0, cx1, cy1, name))
        cc = np.zeros(4, int)
        for k in kept: cc[k[0]] += 1
        recs.append(dict(stem=s, num=num_id(s), W=W, H=H, boxes=kept, cc=cc))
    rep["boxes_dropped_by_class"] = dict(dropped); rep["boxes_unknown_class_dropped"] = dict(unknown)
    rep["boxes_clipped_to_image"] = clipped; rep["boxes_degenerate_after_clip_dropped"] = degenerate
    rep["boxes_kept_by_original_code"] = dict(Counter(k[5] for r in recs for k in r["boxes"]))

    # ---- hashes, adjacency diagnostic ----
    hs = [dhash(imgs[r["stem"]]) for r in recs]
    cons = [ham(hs[i], hs[i + 1]) for i in range(len(hs) - 1)]
    pairs = rng.randint(0, len(hs), (min(5000, len(hs) * 5), 2))
    rnd = [ham(hs[i], hs[j]) for i, j in pairs if i != j]
    rep["adjacency_diagnostic_dhash_bits"] = dict(consecutive_median=float(np.median(cons)), random_pairs_median=float(np.median(rnd)),
                                                  consecutive_share_le_10=float(np.mean(np.array(cons) <= 10)), random_share_le_10=float(np.mean(np.array(rnd) <= 10)),
                                                  note="if consecutive frames are much more similar than random pairs, block splitting is justified")

    # ---- blocks -> units (merge blocks linked by duplicate images) ----
    nb = (len(recs) + a.block_size - 1) // a.block_size
    block_of = [i // a.block_size for i in range(len(recs))]
    dsu = DSU(nb)
    if a.hash_threshold == 0:
        by_hash = defaultdict(list)
        for i, h in enumerate(hs): by_hash[h].append(i)
        for idx in by_hash.values():
            for j in idx[1:]: dsu.union(block_of[idx[0]], block_of[j])
    else:
        for i in range(len(hs)):
            for j in range(i + 1, len(hs)):
                if ham(hs[i], hs[j]) <= a.hash_threshold: dsu.union(block_of[i], block_of[j])
    unit_of = [dsu.find(b) for b in block_of]
    units = defaultdict(list)
    for i, u in enumerate(unit_of): units[u].append(i)
    rep["blocks"] = nb; rep["units"] = len(units); rep["blocks_merged_by_duplicates"] = nb - len(units)
    rep["largest_unit_images"] = max(len(v) for v in units.values())
    if rep["largest_unit_images"] > 0.10 * len(recs): rep.setdefault("warnings_early", []).append("one duplicate-linked unit holds more than 10% of the images: check --hash-threshold / blank images")

    # ---- greedy, class-aware assignment ----
    fr = np.array(a.fractions) / sum(a.fractions)
    tot_c = np.sum([r["cc"] for r in recs], axis=0).astype(float); tot_i = float(len(recs))
    tgt_c, tgt_i = fr[:, None] * tot_c[None, :], fr * tot_i
    cur_c, cur_i = np.zeros((3, 4)), np.zeros(3)
    ukeys = list(units); random.shuffle(ukeys)
    uc = {u: np.sum([recs[i]["cc"] for i in units[u]], axis=0) for u in ukeys}
    ukeys.sort(key=lambda u: -float((uc[u] / np.maximum(tot_c, 1)).sum()))
    assign = {}
    for u in ukeys:
        n = len(units[u])
        sc = [float(((uc[u] / np.maximum(tot_c, 1)) * (1 - cur_c[s] / np.maximum(tgt_c[s], 1))).sum() + 0.5 * (n / tot_i) * (1 - cur_i[s] / tgt_i[s])) for s in range(3)]
        s = int(np.argmax(sc)); assign[u] = SPLITS[s]; cur_c[s] += uc[u]; cur_i[s] += n
    split_of = [assign[unit_of[i]] for i in range(len(recs))]

    # ---- write dataset ----
    for sp in SPLITS:
        (out / "images" / sp).mkdir(parents=True, exist_ok=True); (out / "labels" / sp).mkdir(parents=True, exist_ok=True)
    rows = []
    for i, r in enumerate(recs):
        sp = split_of[i]; src = imgs[r["stem"]]
        shutil.copy2(src, out / "images" / sp / src.name)
        lines = [f"{k[0]} {(k[1] + k[3]) / 2 / r['W']:.6f} {(k[2] + k[4]) / 2 / r['H']:.6f} {(k[3] - k[1]) / r['W']:.6f} {(k[4] - k[2]) / r['H']:.6f}" for k in r["boxes"]]
        (out / "labels" / sp / f"{r['stem']}.txt").write_text("\n".join(lines))
        rows.append(dict(stem=r["stem"], split=sp, block=block_of[i], unit=unit_of[i], n_boxes=len(r["boxes"]), **{f"n_{NAMES[c]}": int(r["cc"][c]) for c in range(4)}))
    df = pd.DataFrame(rows); df.to_csv(out / "split_assignment.csv", index=False)
    (out / "rdd2022_damage.yaml").write_text(f"path: {out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))

    # ---- verification ----
    assert df.stem.is_unique, "duplicate stems"
    assert (df.groupby("unit").split.nunique() == 1).all(), "a unit spans splits"
    kept_total = int(df.n_boxes.sum())
    rep["conservation"] = dict(boxes_written=kept_total, boxes_kept_after_remap=int(sum(len(r["boxes"]) for r in recs)),
                               boxes_total_in_xml=kept_total + sum(dropped.values()) + sum(unknown.values()) + degenerate)
    rep["per_split"] = {sp: dict(images=int((df.split == sp).sum()), empty_images=int(((df.split == sp) & (df.n_boxes == 0)).sum()),
                                 boxes={n: int(df[df.split == sp][f"n_{n}"].sum()) for n in NAMES}) for sp in SPLITS}
    rep["target_fractions"] = list(map(float, fr)); rep["class_names"] = NAMES
    rep["warnings"] = [f"{sp}: only {rep['per_split'][sp]['boxes'][n]} {n} boxes (per-class results will be unreliable)" for sp in ("val", "test") for n in NAMES if rep["per_split"][sp]["boxes"][n] < 20]
    rep["leakage_checks"] = dict(stems_unique=bool(df.stem.is_unique), units_spanning_splits=0, test_images_unlabelled_official_test_excluded=True,
                                 note="splits are blocks of adjacent frames; frames at block boundaries can still resemble neighbours in another split")
    (out / "conversion_report.json").write_text(json.dumps(rep, indent=2, default=str))

    # ---- visual check, drawn back from the WRITTEN label files ----
    try:
        import cv2
        (out / "check").mkdir(exist_ok=True); cand = [r for r, sp in zip(recs, split_of) if r["boxes"] and sp in ("val", "test")]
        tiles = []
        for r in random.sample(cand, min(a.n_check, len(cand))):
            sp = split_of[recs.index(r)]; im = cv2.imread(str(out / "images" / sp / imgs[r["stem"]].name)); h, w = im.shape[:2]
            for ln in (out / "labels" / sp / f"{r['stem']}.txt").read_text().splitlines():
                c, cx, cy, bw, bh = ln.split(); c = int(c); cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
                cv2.rectangle(im, (int(cx - bw / 2), int(cy - bh / 2)), (int(cx + bw / 2), int(cy + bh / 2)), (0, 255, 0), 3)
                cv2.putText(im, NAMES[c], (int(cx - bw / 2), max(18, int(cy - bh / 2) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            tiles.append(cv2.resize(im, (360, 360)))
        if tiles:
            cols = 4; pad = [np.zeros_like(tiles[0])] * ((-len(tiles)) % cols); tl = tiles + pad
            cv2.imwrite(str(out / "check" / "overlays.jpg"), np.vstack([np.hstack(tl[i:i + cols]) for i in range(0, len(tl), cols)]))
    except Exception as e:
        rep["overlay_error"] = str(e)
    print(json.dumps({k: rep[k] for k in rep if k != "boxes_kept_by_original_code"}, indent=2, default=str)); print("\nYAML:", out / "rdd2022_damage.yaml")


if __name__ == "__main__":
    main()
