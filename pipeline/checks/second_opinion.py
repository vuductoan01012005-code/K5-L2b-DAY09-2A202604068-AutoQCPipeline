"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán gợi ý, với từng ảnh (bỏ qua ảnh không có trong preds hoặc không có file nhãn):
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)

Chi tiết các ca biên (test kiểm đúng các ca này)
- `cands` gồm nhãn MỌI lớp có IoU >= iou_missing; "tốt nhất cùng lớp" = cands cùng lớp có IoU lớn nhất; "tốt nhất khác lớp" tương tự với cands khác lớp.
- Thứ tự quyết định cho mỗi dự đoán: (1) cands rỗng -> MISSING. (2) có cands cùng lớp: IoU tốt nhất < iou_loose -> LOOSE_BOX, ngược lại KHÔNG cờ
  (nhãn đúng lớp đã phủ vật này, kể cả khi còn nhãn khác lớp chồng lên). (3) không có cands cùng lớp: nếu IoU tốt nhất khác lớp >= iou_match -> WRONG_CLASS;
  nếu chỉ có khác lớp với IoU trong [iou_missing, iou_match) -> không cờ gì (mơ hồ: để cho FALSE_POS / lần duyệt khác).
- Một dự đoán sinh tối đa MỘT issue (MISSING / LOOSE_BOX / WRONG_CLASS); một ảnh có thể có nhiều issue.
- Thứ tự issue: theo `ds.image_files()` rồi theo thứ tự dự đoán trong `preds[stem]`, cuối cùng là các FALSE_POS theo số dòng; `Issue.image` = stem, `Issue.line` chỉ đặt cho FALSE_POS.

Lưu ý số dòng: dùng `ds.read_label_lines(stem)` (giữ số dòng gốc, kể cả dòng hỏng/trống) để lấy `Issue.line`; `valid_boxes` KHÔNG giữ số dòng.

Tất cả severity WARN; `Issue.extra` nên có {"conf": ...} hoặc {"iou": ...} (hàng đợi duyệt dùng conf để xếp ưu tiên).

Gợi ý
- `iou_xywh` có sẵn. Dòng nhãn hỏng không được làm script chết (dùng `ds.valid_boxes` và `parse_yolo_line` trong try).
- Kết quả phụ thuộc mạnh vào ngưỡng: calibrate chúng ở Bước 3 thay vì đoán.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401
from ..model_cache import get_preds  # noqa: F401


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")
    so = cfg["second_opinion"]
    conf_thr = so["conf"]
    min_area = so["min_area_px"]
    fp_conf = so["fp_conf"]
    iou_missing = so["iou_missing"]
    iou_match = so["iou_match"]
    iou_loose = so["iou_loose"]
    n_classes = len(ds.classes)
    issues = []
    for p in ds.image_files():
        stem = p.stem
        if stem not in preds:
            continue
        lines = ds.read_label_lines(stem)
        if lines is None:
            continue
        labeled = []  # (line, cls, box) — giữ số dòng gốc
        for lineno, text in lines:
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
            except ValueError:
                continue
            if not 0 <= cls < n_classes:
                continue
            labeled.append((lineno, cls, (cx, cy, w, h)))
        size = ds.image_size(stem)
        img_w, img_h = size if size is not None else (0, 0)
        norm = []  # (cls, conf, box)
        for r in preds.get(stem) or []:
            try:
                pcls, pconf, pcx, pcy, pw, ph = r
            except Exception:
                continue
            norm.append((int(pcls), float(pconf),
                         (float(pcx), float(pcy), float(pw), float(ph))))
        filtered = []
        for pcls, pconf, pbox in norm:
            if pconf < conf_thr:
                continue
            if size is not None and pbox[2] * img_w * pbox[3] * img_h < min_area:
                continue
            filtered.append((pcls, pconf, pbox))
        for pcls, pconf, pbox in filtered:
            cands = []
            for _, lcls, lbox in labeled:
                iou = iou_xywh(pbox, lbox)
                if iou >= iou_missing:
                    cands.append((iou, lcls))
            if not cands:
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_MISSING", stem,
                                    f"model thấy vật lớp {pcls} (conf {pconf:.2f}) mà nhãn không có box",
                                    extra={"conf": pconf, "iou": 0.0}))
            else:
                same = [iou for iou, lcls in cands if lcls == pcls]
                if same:
                    best = max(same)
                    if best < iou_loose:
                        issues.append(Issue("second_opinion", WARN, "POSSIBLE_LOOSE_BOX", stem,
                                            f"box nhãn lớp {pcls} lỏng (IoU {best:.3f})",
                                            extra={"conf": pconf, "iou": best}))
                else:
                    best_other = max(iou for iou, _ in cands)
                    if best_other >= iou_match:
                        issues.append(Issue("second_opinion", WARN, "POSSIBLE_WRONG_CLASS", stem,
                                            f"model lớp {pcls} nhưng nhãn lớp khác (IoU {best_other:.3f})",
                                            extra={"conf": pconf, "iou": best_other}))
        fp_preds = [x for x in norm if x[1] >= fp_conf]
        for lineno, _lcls, lbox in labeled:
            best = 0.0
            for _, _, pbox in fp_preds:
                best = max(best, iou_xywh(lbox, pbox))
            if best < iou_missing:
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_FALSE_POS", stem,
                                    f"box nhãn dòng {lineno} không khớp dự đoán nào (IoU {best:.3f})",
                                    line=lineno, extra={"iou": best}))
    return issues
