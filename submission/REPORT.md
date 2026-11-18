# Báo cáo Day 09 — Vũ Đức Toàn, 2A202604068

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước

TODO(học viên): pipeline kết luận **Release / Hold / Rework**? Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset? Lý do chính (1–3 câu).

## 2. Lỗi và phân việc

Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi         | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
| -------------- | ----------: | ------------------ | ------ |
| TODO(học viên) |             |                    |        |

TODO(học viên): vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?

## 3. Calibration (2 ngưỡng)

| Tham số                 | Khởi đầu | Đã chọn        | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
| ----------------------- | -------- | -------------- | -------------------------------- | ---------------- |
| `duplicates.phash_dist` | 2        | TODO(học viên) |                                  |                  |
| `second_opinion.conf`   | 0.25     | TODO(học viên) |                                  |                  |

TODO(học viên): **một chỗ calibration có thể đánh lừa bạn**, kèm bằng chứng từ dữ liệu của bạn (vd. mở xem vài cặp ảnh bị cho là trùng; số ảnh bị loại ở bước 1 có hợp lý không?).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

**(a) Gate chặn đúng khi không có người duyệt.** Đã chạy (bằng `.venv` của dự án — Python hệ thống thiếu `yaml`, và `$env:PYTHONUTF8=1` để log tiếng Việt không vỡ trên console cp1252):

```
.\.venv\Scripts\python.exe -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb
```

Kết quả: **Rework, mã thoát 20**, không xuất dataset. Log: nhận 205/224 ảnh (loại 19), vòng 1 có 36 lỗi bắt buộc → sửa tự động 35 → vòng 2 còn 6 lỗi bắt buộc, hàng đợi 145 ảnh; ngân sách 0 → `reviewed=0` → vòng 3 vẫn còn 6 lỗi → `KHÔNG xuất: còn lỗi bắt buộc (Rework)`. `work/rep_nb/08_summary.json`: `decision=Rework, n_errors=6, n_warn_images=134, n_images=205, warn_ratio=0.6537, exported=null`, và `work/exp_nb/clean_v1` không tồn tại (`Test-Path=False`). 6 lỗi còn lại chính là 6 ảnh `MISSING_LABEL_FILE` (`img_0031, img_0053, img_0126, img_0135, img_0170, img_0219` trong `03_fixes.csv` với `needs_label`): autofix không được bịa/ tạo file nhãn rỗng (rỗng = "ảnh nền", khác "chưa gán"), nên chỉ người mới xóa được ERROR và gate phải chặn ở Rework — khác bản `submission` đầy đủ (Hold, `n_errors=0`, đã duyệt 80/80). Không sửa tay `work/run/ds` (pipeline dựng lại thư mục này từ `data/raw` mỗi lần chạy).

**(b) Tự mở xem 11 ảnh `work/viz/*.png`** (`img_0001`–`img_0009`, `img_0029`, `img_0030` — vẽ bằng `scripts/viz_labels.py` từ `data/raw`) đối chiếu nhãn thô `data/raw/labels/`, `02_error_list_v1.csv`, `05_review_queue.csv`, `07_error_list_v3.csv`. 3 lỗi tôi tự thấy bằng mắt thường:

1. **`img_0001.png` — thiếu hẳn người lính đứng giữa-phải.** Ảnh 640×427, văn phòng: người đàn ông cầm gậy bóng chày (trái) có box `1:person`, còn người lính mặc quân phục rõ mặt, đứng giữa-phải (x≈0.65–0.86, y≈0.18–0.90) **không có box nào**; box `2:person` duy nhất còn lại chỉ là vệt nửa đầu bị cắt ở mép phải (dòng 2: `1 0.955851 0.836215 ...`). Đây là lỗi ngữ nghĩa (thiếu vật), cú pháp đúng nên `label_format`/`missing_labels` im lặng; chỉ `second_opinion` cờ (02: 2×`POSSIBLE_MISSING` conf 0.95/0.42; hàng đợi 8.727) và vẫn còn ở v3.
2. **`img_0004.png` — nhãn rỗng nhưng ảnh không rỗng.** Ảnh 403×640, nhà ga VIA: file nhãn `data/raw/labels/img_0004.txt` trống, nhưng góc dưới-phải có 2 ô tô (xe bạc + xe đen) dưới biển hiệu và phía trái là đoàn tàu. Ô tô thuộc 4 lớp nhưng không có box nào: 02 có `EMPTY_LABEL` (warn) + 2×`POSSIBLE_MISSING` lớp 0 (conf 0.89/0.79), hàng đợi 8.357 (`EMPTY_LABEL;POSSIBLE_MISSING`). Đoàn tàu không thuộc `{car,person,truck,bus}` nên bỏ qua là đúng — cho thấy điểm mù nằm ở ranh giới ontology, không phải ở quy tắc cú pháp (file rỗng hợp lệ, chỉ warn).
3. **`img_0002.png` — box lỏng nhẹ bao cả khoảng trống.** Ảnh 640×480, thuyền trên biển (3 người đều có box): box trái (`1 0.173613 0.583691 0.134017 0.136716`) bao cả mũi thuyền trống bên dưới ngư dân nằm, không ôm sát thân người. Thị giác thấy lỏng, nhưng **không có bất kỳ dòng nào** của ảnh này trong 02/05/07 (không vào hàng đợi) — vì IoU với box model vẫn ≥ `iou_loose=0.5`, nên không bị `POSSIBLE_LOOSE_BOX`. Tương tự ở `img_0029.png`: box giữa bao luôn tấm ván trượt phía sau chân (6 ảnh còn lại `img_0003, 0007–0009, 0029` không vào hàng đợi, ví dụ `img_0008` trượt tuyết cả 2 người đều ôm sát, đúng).

Từ 3 lỗi trên có ≥2 điểm mù có bằng chứng: (i) **Lỗi ngữ nghĩa chỉ phát hiện được nhờ model checker** — nếu `yolo26l` cũng bỏ sót (người lính quay lưng/ngụy trang, ô tô trong bóng tối), pipeline sẽ gần như mù hoàn toàn vì mọi check cú pháp đều hợp lệ; (ii) **Box lỏng nhẹ dưới ngưỡng IoU 0.5 thì không bị cờ** (`img_0002`, `img_0029`), mắt người thấy thừa trống/vật kèm (mũi thuyền, snowboard) nhưng máy không có khái niệm "ôm sát" cho mức nhẹ này — chỉ người duyệt phân biệt được.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).

TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được); ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.

## 6. Quyết định và ghi chú AI

**(a) Quyết định cuối: Hold (chưa Release).** `submission/reports/08_summary.json`: `decision=Hold`, `n_errors=0`, `n_warn_images=60`, `n_images=205`, `warn_ratio=0.2927`, lý do `60/205 ảnh còn cảnh báo (29.27%) >= ngưỡng 10.00%` — tức không phải Rework (đã hết lỗi bắt buộc sau sửa tự động + duyệt), nhưng tỷ lệ ảnh còn cảnh báo vượt `cfg["gate"]["warn_ratio_hold"]=0.10` nên chưa được phát hành. Vào 224 ảnh ở bước 1 (`01_intake.txt`: loại 19 ảnh = 5 `images` + 14 `duplicates`), ra 205 ảnh trong `submission/export/clean_v1/manifest.json` (`n_images=205`, `decision=Hold`) — đây mới là bản nháp chờ xử lý cảnh báo, không phải bản Release.

Để thành Release, phải đưa `n_warn_images` từ 60 xuống ≤20 ảnh (`20/205=9.76% < 10%`; `21/205=10.24% ≥ 10%`), tức xử lý ít nhất 40/60 ảnh còn cảnh báo, **không được chỉ hạ ngưỡng gate**: mở rộng ngân sách duyệt / chạy thêm vòng người duyệt theo thứ tự ưu tiên ở `05_review_queue.csv` (hàng đợi có 145 ảnh, mới duyệt 80/80 ngân sách theo `08_summary.json`, còn lại ưu tiên `POSSIBLE_MISSING` (94 dòng), `POSSIBLE_LOOSE_BOX` (35), `POSSIBLE_FALSE_POS` (25), `POSSIBLE_WRONG_CLASS` (11) trong `07_error_list_v3.csv` — tổng 165 dòng `second_opinion` — cộng `EMPTY_LABEL` 10, `BOX_TINY` 6, `BOX_HUGE` 3), sửa nhãn thật cho các cảnh báo đúng (thêm box thiếu, siết box lỏng, xoá/giữ box thừa có căn cứ, sửa lớp, xác nhận ảnh nền hay thiếu nhãn), rồi chạy lại pipeline (`--resume-after-review`) và kiểm lại `07_error_list_v3` + `08_summary.json` trước khi kết luận Release. Nếu sau duyệt vẫn còn ≥21 ảnh cảnh báo thì vẫn phải giữ Hold và lặp vòng, không xuất bản chính thức.

**(b) Ghi chú AI (có dùng):**

- Prompt chính: “viết cho tôi file `pipeline/checks/label_format.py` để khi chạy `python -m pytest -q` xanh hết (79 test)” (sau đó mở rộng sang `second_opinion`, `autofix`, `gate` khi phát hiện mới chỉ 14/79 test qua).
- Cách tôi kiểm code AI: đọc đối chiếu từng test với docstring của module và `pipeline/common.py`/`tests/conftest.py` (số dòng gốc, `overflow_tol`, `DUP_BOX` báo dòng sau, cảnh báo không chạm tới, idempotent của autofix…), chạy `.\.venv\Scripts\python.exe -m pytest -q` được **79 passed**, rồi kiểm bằng chứng đầu ra thật (`01/03/05/07/08_summary.json`, `manifest.json`) thay vì tin kết luận miệng của AI.
- Một lần AI sai: AI tưởng chỉ cần viết xong `label_format.py` là đủ 79 test, nhưng chạy thật mới chỉ **14 pass** vì `second_opinion.py`, `steps/autofix.py`, `steps/gate.py` vẫn là stub `NotImplementedError`; AI cũng chạy nhầm Python hệ thống (`ModuleNotFoundError: yaml`) thay vì dùng `.venv` của dự án — cả hai đều phải sửa bằng cách rà toàn bộ stub và chạy lại bằng `.venv`.

_(Thưởng +2, tùy chọn)_ CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
