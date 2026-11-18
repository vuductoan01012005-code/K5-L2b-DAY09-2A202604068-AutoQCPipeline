"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    fixes = []
    errors = [i for i in issues if i.severity == ERROR]
    removed = set()
    seen_remove = set()
    for i in errors:
        if i.code in REMOVE_CODES and i.image not in seen_remove:
            seen_remove.add(i.image)
            removed.add(i.image)
            img_path = ds.image_path(i.image)
            if img_path is not None and img_path.exists():
                img_path.unlink()
            lp = ds.label_path(i.image)
            if lp.exists():
                lp.unlink()
            fixes.append({"image": i.image, "line": None, "action": "remove_image",
                          "before": i.code, "after": "đã xoá ảnh + nhãn"})
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        yaml_path = ds.yaml_path
        data = {}
        if yaml_path.exists():
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}
        old_names = data.get("names")
        data["names"] = dict(enumerate(cfg["classes"]))
        if "path" not in data:
            data["path"] = "."
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        fixes.append({"image": "data.yaml", "line": None, "action": "rename_classes",
                      "before": str(old_names), "after": str(cfg["classes"])})
    seen_needs = set()
    for i in errors:
        if i.code == "MISSING_LABEL_FILE" and i.image not in seen_needs and i.image not in removed:
            seen_needs.add(i.image)
            fixes.append({"image": i.image, "line": None, "action": "needs_label",
                          "before": "(không có file)", "after": "chuyển người gán"})
    drop_by = defaultdict(set)
    clip_by = defaultdict(set)
    for i in errors:
        if i.line is None or i.image in removed:
            continue
        if i.code in DROP_CODES:
            drop_by[i.image].add(i.line)
        elif i.code == "BOX_OUT_OF_IMAGE":
            clip_by[i.image].add(i.line)
    for stem in sorted(set(drop_by) | set(clip_by)):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        raw = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        drop_set = drop_by.get(stem, set())
        clip_set = clip_by.get(stem, set()) - drop_set
        new_lines = []
        file_fixes = []
        for idx, original in enumerate(raw, start=1):
            if idx in drop_set:
                file_fixes.append({"image": stem, "line": idx, "action": "drop_line",
                                   "before": original, "after": ""})
                continue
            if idx in clip_set:
                try:
                    cls, cx, cy, w, h = parse_yolo_line(original)
                except ValueError:
                    new_lines.append(original)
                    continue
                x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
                nx1 = min(max(x1, 0.0), 1.0)
                ny1 = min(max(y1, 0.0), 1.0)
                nx2 = min(max(x2, 0.0), 1.0)
                ny2 = min(max(y2, 0.0), 1.0)
                nw, nh = nx2 - nx1, ny2 - ny1
                if nw <= 0 or nh <= 0:
                    file_fixes.append({"image": stem, "line": idx, "action": "drop_line",
                                       "before": original, "after": ""})
                    continue
                ncx, ncy = (nx1 + nx2) / 2, (ny1 + ny2) / 2
                clipped = f"{cls} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(clipped)
                file_fixes.append({"image": stem, "line": idx, "action": "clip_box",
                                   "before": original, "after": clipped})
                continue
            new_lines.append(original)
        if file_fixes:
            lp.write_text(("\n".join(new_lines) + "\n") if new_lines else "", encoding="utf-8")
            fixes.extend(file_fixes)
    return fixes
