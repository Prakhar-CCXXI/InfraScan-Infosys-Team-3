"""
RDD2022 (one country) inspection: folder structure, annotation format, classes, class balance, box statistics,
image/annotation integrity, size distribution, optional train/test duplicate check. Reads everything from the files;
nothing about classes or counts is assumed (the class-meaning table below is only a labelled hint).

Usage:
  python ml/data/inspect_rdd2022.py --root "C:/path/RDD2022_India" --out-dir rdd2022_inspection [--hash] [--n-overlays 12]
Outputs: rdd2022_inspection.json, boxes.csv, classes.csv, class_counts.png, box_area_by_class.png, overlays.jpg, summary printed.
"""
import argparse, json, random, re, sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_NAMES = {"train", "test", "val", "valid", "validation"}
# ASSUMED meaning of codes from public RDD documentation - VERIFY against the dataset's own documentation before relying on it.
CODE_HINT = {"D00": "longitudinal crack (wheel-mark part)", "D01": "longitudinal crack (construction-joint part)", "D10": "lateral/transverse crack (equal-interval)",
             "D11": "lateral/transverse crack (construction-joint part)", "D20": "alligator crack", "D40": "other corruption (rutting, bump, pothole, separation)",
             "D43": "crosswalk blur (road marking)", "D44": "white-line blur (road marking)", "D50": "utility hole"}


def split_of(p, root):
    for part in p.relative_to(root).parts[:-1]:
        if part.lower() in SPLIT_NAMES:
            return part.lower()
    return "other"


def image_size(p):
    from PIL import Image
    with Image.open(p) as im:
        return im.size   # (w, h), header only


def dhash(p):
    from PIL import Image
    with Image.open(p) as im:
        g = np.asarray(im.convert("L").resize((9, 8)), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def parse_voc(p):
    r = ET.parse(p).getroot()
    sz = r.find("size")
    W = int(float(sz.findtext("width"))) if sz is not None and sz.findtext("width") else None
    H = int(float(sz.findtext("height"))) if sz is not None and sz.findtext("height") else None
    objs = []
    for o in r.findall("object"):
        bb = o.find("bndbox")
        if bb is None:
            objs.append(dict(cls=(o.findtext("name") or "").strip(), xmin=np.nan, ymin=np.nan, xmax=np.nan, ymax=np.nan)); continue
        objs.append(dict(cls=(o.findtext("name") or "").strip(), **{k: float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")}))
    return dict(filename=r.findtext("filename"), width=W, height=H, objects=objs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out-dir", default="rdd2022_inspection")
    ap.add_argument("--hash", action="store_true", help="perceptual-hash every image to find train/test duplicates (slower)")
    ap.add_argument("--n-overlays", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    root, out = Path(a.root), Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    assert root.is_dir(), f"not a folder: {root}"
    rep = dict(root=str(root))

    files = [p for p in root.rglob("*") if p.is_file()]
    rep["file_extensions"] = dict(Counter(p.suffix.lower() for p in files))
    folders = Counter(str(p.parent.relative_to(root)).replace("\\", "/") for p in files)
    rep["files_per_folder"] = dict(sorted(folders.items()))
    imgs = [p for p in files if p.suffix.lower() in IMG_EXT]
    xmls = [p for p in files if p.suffix.lower() == ".xml"]
    txts = [p for p in files if p.suffix.lower() == ".txt"]
    jsons = [p for p in files if p.suffix.lower() == ".json"]
    rep["images_per_split"] = dict(Counter(split_of(p, root) for p in imgs))
    rep["annotation_files"] = dict(xml=len(xmls), txt=len(txts), json=len(jsons))
    fmt = "pascal_voc_xml" if xmls else "yolo_txt_or_other_txt" if txts else "json (check COCO keys)" if jsons else "NONE FOUND"
    rep["annotation_format_detected"] = fmt
    if xmls:
        rep["annotation_sample_raw"] = xmls[0].read_text(errors="replace")[:900]
    elif txts:
        rep["annotation_sample_raw"] = txts[0].read_text(errors="replace")[:300]
    elif jsons:
        try: rep["json_top_keys"] = list(json.loads(jsons[0].read_text()).keys())[:10]
        except Exception as e: rep["json_error"] = str(e)
    rep["annotation_splits"] = dict(Counter(split_of(p, root) for p in xmls + txts + jsons))
    if not xmls:
        (out / "rdd2022_inspection.json").write_text(json.dumps(rep, indent=2)); print(json.dumps(rep, indent=2))
        print("\nNo XML annotations: this script parses Pascal VOC XML. Send me the printed report (sample above) and I will adapt it."); return

    # ---- image headers ----
    sizes, bad_imgs = {}, []
    for p in imgs:
        try: sizes[p] = image_size(p)
        except Exception: bad_imgs.append(str(p.relative_to(root)))
    rep["unreadable_images"] = bad_imgs[:20]; rep["n_unreadable_images"] = len(bad_imgs)
    ss = pd.DataFrame([dict(split=split_of(p, root), w=w, h=h) for p, (w, h) in sizes.items()])
    rep["image_sizes_by_split"] = {sp: {f"{w}x{h}": int(c) for (w, h), c in g.groupby(["w", "h"]).size().sort_values(ascending=False).head(8).items()} for sp, g in ss.groupby("split")}

    # ---- annotations ----
    rows, parse_err, per_img = [], [], []
    img_by_stem = {}
    for p in imgs: img_by_stem.setdefault((split_of(p, root), p.stem), p)
    for x in xmls:
        try: d = parse_voc(x)
        except Exception as e: parse_err.append(f"{x.name}: {e}"); continue
        sp = split_of(x, root); img = img_by_stem.get((sp, x.stem))
        iw, ih = sizes.get(img, (None, None)) if img else (None, None)
        W, H = (iw or d["width"]), (ih or d["height"])
        per_img.append(dict(split=sp, stem=x.stem, n_obj=len(d["objects"]), has_image=img is not None, xml_w=d["width"], xml_h=d["height"], img_w=iw, img_h=ih,
                            size_mismatch=bool(img and d["width"] and (d["width"], d["height"]) != (iw, ih))))
        for o in d["objects"]:
            w, h = o["xmax"] - o["xmin"], o["ymax"] - o["ymin"]
            rows.append(dict(split=sp, stem=x.stem, cls=o["cls"], xmin=o["xmin"], ymin=o["ymin"], xmax=o["xmax"], ymax=o["ymax"], w=w, h=h,
                             area_rel=(w * h) / float(W * H) if W and H else np.nan, aspect=(w / h if h else np.nan),
                             invalid=bool(not (w > 0 and h > 0)), outside=bool(W and H and (o["xmin"] < 0 or o["ymin"] < 0 or o["xmax"] > W or o["ymax"] > H))))
    B, I = pd.DataFrame(rows), pd.DataFrame(per_img)
    B.to_csv(out / "boxes.csv", index=False)
    rep["xml_parse_errors"] = parse_err[:20]; rep["n_xml_parse_errors"] = len(parse_err)
    rep["annotated_images"] = int(len(I)); rep["annotated_boxes"] = int(len(B))
    stems_img = {(s, st) for (s, st) in img_by_stem}
    stems_xml = {(r.split, r.stem) for r in I.itertuples()}
    train_img = {k for k in stems_img if k[0] == "train"}
    rep["pairing_train"] = dict(images=len(train_img), annotations=int(sum(1 for k in stems_xml if k[0] == "train")),
                                images_without_annotation=len(train_img - stems_xml), annotations_without_image=int(sum(1 for r in I.itertuples() if r.split == "train" and not r.has_image)),
                                examples_images_without_annotation=[f"{s}/{st}" for s, st in sorted(train_img - stems_xml)[:5]])
    rep["xml_vs_actual_image_size_mismatch"] = int(I.size_mismatch.sum())
    if len(B):
        cc = B.cls.value_counts()
        cls = pd.DataFrame(dict(boxes=cc, share_boxes=cc / cc.sum(), images=B.groupby("cls").stem.nunique(),
                                median_area_rel=B.groupby("cls").area_rel.median(), median_w=B.groupby("cls").w.median(), median_h=B.groupby("cls").h.median(),
                                median_aspect=B.groupby("cls").aspect.median()))
        cls["assumed_meaning_VERIFY"] = [CODE_HINT.get(c.upper(), "unknown code") for c in cls.index]
        cls.to_csv(out / "classes.csv"); rep["classes"] = json.loads(cls.round(4).to_json(orient="index"))
        rep["class_names_raw"] = sorted(B.cls.unique())
        rep["imbalance_ratio_max_over_min_boxes"] = float(cc.max() / cc.min())
        npi = B.groupby("stem").size()
        rep["boxes_per_annotated_image"] = dict(mean=float(npi.mean()), median=float(npi.median()), max=int(npi.max()))
        rep["images_with_zero_boxes"] = int((I.n_obj == 0).sum())
        k = B.groupby("stem").cls.nunique(); rep["images_with_2plus_classes"] = int((k >= 2).sum())
        rep["invalid_boxes"] = int(B.invalid.sum()); rep["boxes_outside_image"] = int(B.outside.sum())
        rep["tiny_boxes_area_rel_below_0.001"] = int((B.area_rel < 0.001).sum()); rep["duplicate_identical_boxes"] = int(B.duplicated(["stem", "cls", "xmin", "ymin", "xmax", "ymax"]).sum())
        try:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            cc.plot.bar(color="#4c72b0"); plt.ylabel("boxes"); plt.title("RDD2022 class balance (boxes)"); plt.tight_layout(); plt.savefig(out / "class_counts.png", dpi=120); plt.close()
            B.boxplot(column="area_rel", by="cls"); plt.yscale("log"); plt.suptitle(""); plt.title("box area / image area"); plt.tight_layout(); plt.savefig(out / "box_area_by_class.png", dpi=120); plt.close()
        except Exception as e: rep["plot_error"] = str(e)
        try:   # visual validation: boxes drawn on random annotated images
            import cv2
            random.seed(a.seed); picks = random.sample(sorted(set(B.stem[B.split == "train"])), min(a.n_overlays, B.stem.nunique())); tiles = []
            for st in picks:
                im = cv2.imread(str(img_by_stem[("train", st)]))
                if im is None: continue
                for r in B[(B.stem == st) & (B.split == "train")].itertuples():
                    cv2.rectangle(im, (int(r.xmin), int(r.ymin)), (int(r.xmax), int(r.ymax)), (0, 255, 0), max(2, im.shape[1] // 300))
                    cv2.putText(im, str(r.cls), (int(r.xmin), max(15, int(r.ymin) - 5)), cv2.FONT_HERSHEY_SIMPLEX, max(0.6, im.shape[1] / 1200), (0, 0, 255), 2)
                tiles.append(cv2.resize(im, (480, int(480 * im.shape[0] / im.shape[1]))))
            if tiles:
                h = max(t.shape[0] for t in tiles); tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
                cols = 4; rows_ = [np.hstack(tiles[i:i + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
                cv2.imwrite(str(out / "overlays.jpg"), np.vstack(rows_))
        except Exception as e: rep["overlay_error"] = str(e)
    # ---- filename pattern / duplicates ----
    nums = sorted(int(m.group(1)) for p in imgs if (m := re.search(r"(\d+)$", p.stem)))
    rep["filename_numeric_suffix_range"] = [nums[0], nums[-1]] if nums else None
    rep["example_filenames"] = sorted(p.name for p in imgs)[:3]
    if a.hash:
        H = {}
        for p in imgs:
            try: H.setdefault(dhash(p), []).append(split_of(p, root))
            except Exception: pass
        rep["duplicate_check"] = dict(hash_groups_with_multiple_images=int(sum(len(v) > 1 for v in H.values())), groups_spanning_train_and_test=int(sum(len(v) > 1 and {"train", "test"} <= set(v) for v in H.values())),
                                      note="identical 64-bit dHash = near-duplicate; train/test overlap would invalidate evaluation on the test images")
    rep["note_on_test_split"] = "If the test split has no annotation files, it cannot be used for evaluation here; a validation/test split must be carved out of train (keep near-duplicate and adjacent frames together)."
    (out / "rdd2022_inspection.json").write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("annotation_sample_raw",)}, indent=2, default=str))
    print("\n--- raw annotation sample (first 900 chars) ---\n" + str(rep.get("annotation_sample_raw", ""))); print("\nSaved to", out.resolve())


if __name__ == "__main__":
    main()
