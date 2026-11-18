"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401


def run(ds, cfg):
    lf = cfg["label_format"]
    overflow_tol = lf["overflow_tol"]
    min_box_px = lf["min_box_px"]
    max_box_frac = lf["max_box_frac"]
    dup_box_iou = lf["dup_box_iou"]
    n_classes = len(ds.classes)
    issues = []
    for p in ds.label_files():
        stem = p.stem
        lines = ds.read_label_lines(stem)
        if lines is None:
            continue
        size = ds.image_size(stem)  # (W, H) hoặc None
        prev = []  # các box hợp lệ trước đó: (cls, cx, cy, w, h)
        for lineno, text in lines:
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem,
                                    f"sai định dạng: {e} ({text!r})", line=lineno))
                continue
            if not 0 <= cls < n_classes:
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem,
                                    f"id lớp {cls} ngoài 0..{n_classes - 1}", line=lineno))
                continue
            box = (cx, cy, w, h)
            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem,
                                    f"box rỗng w={w} h={h}", line=lineno))
                continue
            # BOX_OUT_OF_IMAGE
            x1, x2 = cx - w / 2, cx + w / 2
            y1, y2 = cy - h / 2, cy + h / 2
            overflow = max(-x1, -y1, x2 - 1.0, y2 - 1.0)
            if overflow > overflow_tol:
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem,
                                    f"box tràn ảnh {overflow:.4f}", line=lineno,
                                    extra={"overflow": overflow}))
            # DUP_BOX: cùng lớp với một dòng trước đó, IoU > ngưỡng
            dup = any(p_cls == cls and iou_xywh(p_box, box) > dup_box_iou
                      for p_cls, *rest in prev
                      for p_box in [tuple(rest)])
            if dup:
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem,
                                    f"box lặp cùng lớp {cls}", line=lineno))
            # BOX_TINY (WARN): cạnh ngắn tính theo px
            if size is not None:
                img_w, img_h = size
                short_px = min(w * img_w, h * img_h)
                if short_px < min_box_px:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem,
                                        f"cạnh ngắn {short_px:.1f}px < {min_box_px}px", line=lineno))
            # BOX_HUGE (WARN)
            if w * h > max_box_frac:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem,
                                    f"box chiếm {w * h:.3f} diện tích ảnh", line=lineno))
            prev.append((cls, cx, cy, w, h))
    return issues
