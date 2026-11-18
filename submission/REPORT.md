# Báo cáo Day 09 — Vũ Đức Toàn, 2A202604068

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước

Pipeline kết luận **Hold** (chưa Release, chưa Rework). Vào `224` ảnh thô (`01_intake.txt`: quét `224`, loại `19` = `5 images` + `14 duplicates`), ra `205` ảnh vào `submission/export/clean_v1` (`08_summary.json`: `decision=Hold`, `n_images=205`, `n_errors=0`, `n_warn_images=60`, `warn_ratio=0.2927`, `exported=submission/export/clean_v1`). Lý do: đã hết lỗi bắt buộc sau sửa tự động + duyệt 80/80 ảnh theo ngân sách (`07_error_list_v3` không còn ERROR), nhưng tỉ lệ ảnh còn cảnh báo `60/205=29.27%` vẫn vượt ngưỡng gate `warn_ratio_hold=0.10`, nên đây là bản nháp chờ xử lý cảnh báo, không phải bản phát hành.

## 2. Lỗi và phân việc

Gom từ `02_error_list_v1` (ảnh đã quét `205` sau intake; `02_error_list_v1.txt` theo module: `second_opinion 248`, `label_format 37`, `missing_labels 18`, `duplicates 14`, `images 5`, `stats 4`, `class_names 2` — tổng `328` dòng; bảng dưới theo mã lỗi, chỉ ghi mã có mặt trong lô).

| Mã lỗi     |                        Số ảnh/dòng | Ai sửa (máy/người)                       | Vì sao                                        |
| ---------- | ---------------------------------: | ---------------------------------------- | --------------------------------------------- |
| `BAD_SIZE` | 3 (`img_0107, img_0113, img_0122`) | Máy — loại ở Bước 1, không chép vào `ds` | Cạnh ngắn `180–226px < 250px` (`min_side_px`) |

**Bước 1 (intake, `01_intake.txt`):** ảnh hỏng/quá nhỏ/trùng/rò rỉ bị loại **trước** mọi bước khác nên không tốn công QC: `CORRUPT_IMAGE 2` (`img_0010, img_0136`), `BAD_SIZE 3`, `DUP_IMAGE_EXACT 8`, `DUP_IMAGE_NEAR 2`, `LEAK_TEST 4` (`img_0049, img_0167, img_0174, img_0221` trùng test/val) = `19` ảnh.

**ERROR còn lại sau intake → máy (`03_fixes.csv`, `04_error_list_v2.txt`):** `BAD_FORMAT 3`, `BAD_CLASS_ID 6`, `BOX_ZERO 4`, `DUP_BOX 7` → `drop_line`; `BOX_OUT_OF_IMAGE 8` → `clip_box`; `BAD_CLASS_NAME 2` (`Person→person`, `Bus→bus`) → `rename_classes`; `MISSING_LABEL_FILE 6` (`img_0031, img_0053, img_0126, img_0135, img_0170, img_0219`) → `needs_label` (máy không bịa nhãn, chuyển người gán — việc này giải thích vì sao REF 6 lỗi này còn lại tới vòng 2 vẫn là ERROR).

**WARN → người (hàng đợi `05_review_queue.csv`):** `POSSIBLE_MISSING 152`, `POSSIBLE_LOOSE_BOX 45` → **người**; `POSSIBLE_FALSE_POS 29`, `POSSIBLE_WRONG_CLASS 22` → **người**; `EMPTY_LABEL 12`, `BOX_TINY 6`, `BOX_HUGE 3`, `CLASS_RARE 4` (stats) → **người**. Các mã `POSSIBLE_*` là ngữ nghĩa nên chỉ người xác nhận; `EMPTY_LABEL` hỏi "ảnh nền hay thiếu nhãn?" nên cũng phải người.

**Vì sao hàng đợi xếp như vậy (`05_review_queue.csv`):** `pipeline/steps/review_queue.py`: điểm ảnh = Σ `review.weights` theo mã (vd. `POSSIBLE_WRONG_CLASS 3`, `POSSIBLE_MISSING/FALSE_POS 2`, `POSSIBLE_LOOSE_BOX 1.5`, `NEEDS_LABEL 10`, `FIXED_DROP_LINE 2`, `FIXED_CLIP_BOX 1`, `default 1`) × `(1 + conf)` nếu có `conf`, cộng thêm điểm khi máy đã sửa (`drop_line/clip_box/needs_label`) và `FIXED_*`/`NEEDS_LABEL`; xếp giảm dần theo điểm rồi theo tên ảnh. Với ngân sách `80` ảnh (`review.budget_images`), người xem được `80/145` ảnh (55,2%) ở vòng 2: top là `img_0160` (`35.692`, `POSSIBLE_MISSING;POSSIBLE_WRONG_CLASS`), `img_0127` (`22.753`), `img_0020` (`17.449`), `img_0058` (`16.468`), `img_0124` (`15.301`)… nghĩa là người xem trước hết các lỗi ngữ nghĩa chắc (cao conf + trọng số cao) và các ảnh máy vừa động vào; sau duyệt `80/80`, vòng 3 còn `60/205` ảnh cảnh báo (`07_error_list_v3`: `POSSIBLE_MISSING 94`, `POSSIBLE_LOOSE_BOX 35`, `POSSIBLE_FALSE_POS 25`, `POSSIBLE_WRONG_CLASS 11`, `BOX_*`/`EMPTY_LABEL` còn lại), vượt gate `10%` → Hold.

## 3. Calibration (2 ngưỡng)

| Tham số                 | Khởi đầu | Đã chọn | Precision / Recall (trước → sau)                                                                                                                                        | Lý do (đánh đổi)                                                                                                                                                                                                        |
| ----------------------- | -------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `duplicates.phash_dist` | 2        | **16**  | `DUP_IMAGE_NEAR`: 1.00 / 0.50 → 1.00 / 0.83                                                                                                                             | Ưu tiên precision vì cờ sai = xoá nhầm ảnh tốt; sweep calib giữ precision 1.00 mọi điểm nên tăng recall không tốn FP trên calib (4→16: 0.67→0.83)                                                                       |
| `second_opinion.conf`   | 0.25     | **0.5** | `WRONG_CLASS`: 0.56/0.83 → 0.56/0.83; `MISSING`: 0.50/1.00 → 0.57/1.00; `LOOSE_BOX`: 0.29/0.40 → 0.20/0.20; `FALSE_POS`: 0.31/1.00 → không đổi (dùng `fp_conf` cố định) | Tăng precision của `MISSING` mà không mất recall hai mã chính; 0.5 là điểm knee — lên 0.7 mới bắt đầu rớt `MISSING` recall (0.88), xuống 0.1 thì hàng đợi nổ (mô phỏng trên ds sau autofix: queue 149, 399 warn issues) |

**Cái "chỗ calib có thể đánh lừa" (trọng điểm):**

1. **Calib chỉ 39 ảnh, mỗi ô chỉ 3–8 lỗi chèn** nên P/R nhảy từng bước 17–33% cho mỗi lỗi; `phash_dist=16` tăng recall thêm đúng **1 lỗi** (5/6 thay vì 4/6) trên calib, nhưng trên `data/raw` (tự chạy `checks.duplicates` theo từng giá trị) 16 loại thêm **9 ảnh** so với 2 (31 thay vì 19), và mức phash ở raw cho thấy các cặp gần-threshold rất dày: khoảng cách phash tới ảnh giữ trước đó — d=6: 1 cặp, d=10: 1, d=16: 3, d=18: ~20, d=20: ~80, d=17–24: 189 ảnh. Nghĩa là ngưỡng 16 nằm ngay mép "sườn dốc" của raw: chỉ cần dịch ngưỡng một chút là số ảnh bị loại nhảy vọt (ở 20: 137 ảnh bị loại, chủ yếu LEAK_TEST). Calib không đo được dải nguy hiểm này vì chỉ có 6 ảnh NEAR cố ý chèn (mức biến đổi 0–4, dễ) — lỗi thật trong raw biến đổi mạnh hơn.
2. **Điểm lạ của sweep:** ở `phash_dist=20`, recall `DUP_IMAGE_EXACT` rơi xuống 0.33 (1/3) và NEAR xuống 0.50 — thấp hơn ở 16. Nguyên nhân là cơ chế trong `duplicates.py`: ảnh bị báo (LEAK/EXACT/NEAR) **không** vào tập `seen`, ảnh sau chỉ so với ảnh đã giữ; ngưỡng quá lớn gỡ chuỗi giống-nhau-xây-dựng-nhau. Người chỉ đọc bảng F1 sẽ tưởng "16 là F1 cao nhất nên chọn", mà không hiểu vì sao đường cong không đơn điệu.
3. **Calib không có ca `LEAK_TEST`** (MANIFEST chỉ có EXACT/NEAR + lỗi nhãn); raw có 4 ca rò rỉ rớt vào khoảng cách phash khác — ngưỡng tối ưu cho EXACT/NEAR trên calib không suy ra được độ rò rỉ trên raw.
4. **Calib dựng từ nhãn người (sạch), raw từ nhãn model** — `WRONG_CLASS` trên calib chủ yếu person→car/truck→bus, trong khi raw nghiêng car/truck/bus (theo `07_error_list_v3` toàn `model lớp 0/2 nhưng nhãn lớp khác`); recall `WRONG_CLASS` 0.83 trên calib không đảm bảo recall tương tự trên raw. Ngoài ra `POSSIBLE_LOOSE_BOX` trên calib precision chỉ 0.20–0.29 (FP do nhãn người/box lệch tự nhiên) — đây là FP "đúng nghĩa" (người kiểm mở xem uổng công), nhưng không qua `conf` nên hạ `conf` không cứu được nó.

**Vẫn là điểm mù đã biết sau calibrate:** `second_opinion.conf` chỉ lọc dự đoán cho `MISSING/LOOSE/WRONG_CLASS`; `FALSE_POS` đi theo `fp_conf=0.1` cố định nên P duy trì 0.31 trên mọi điểm — 11 FP trên calib không có cách giảm trong phạm vi 2 ngưỡng được phép chỉnh; nó vẫn là gánh nặng chính của hàng đợi (24 dòng `POSSIBLE_FALSE_POS` ở v2).

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

Đã train: `submission/results/{raw,clean}_seed{0,1}.json` (yolo26n, 20 epoch, 2 seed, `comparison.json/.md/.png` sinh bởi `scripts/train_compare.py`/`summarize_results.py` — không sửa tay; `clean` dùng đúng `submission/export/clean_v1/manifest.json` với `n_images=205` từ bản chạy ở trên, `raw` dùng `data/raw` `224` ảnh).

| biến thể | #ảnh train | mAP50 (TB ± SD)                | mAP50-95      | P             | R             |
| -------- | ---------- | ------------------------------ | ------------- | ------------- | ------------- |
| raw      | 224        | 0.726 ± 0.000 (0.7256, 0.7259) | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean    | 205        | 0.711 ± 0.021 (0.6958, 0.7256) | 0.501 ± 0.009 | 0.753 ± 0.054 | 0.620 ± 0.016 |

**Chênh mAP50 (clean − raw) = −0.015**, trong khi độ lệch chuẩn giữa 2 seed của `clean` là `0.021`, tức |chênh| < 1 SD của riêng clean; raw 2 seed gần như trùng nhau (SD 0.0002) còn clean hai seed cách nhau tới `0.030` (0.6958↔0.7256 — bằng đúng seed0 của raw). Nói cách khác, thứ tự raw>clean chỉ vững ở **trung bình**, không vững ở **seed**: seed1 của clean (0.7256) bằng seed0 của raw (0.7256) và gần như bằng seed1 của raw (0.7259). Kết luận trung thực: **chưa kết luận được "clean tốt hơn raw"**; chênh −0.015 nằm hoàn toàn trong nhiễu giữa seed trên lô 205 ảnh.

**Ít nhất hai giả thuyết giải thích (và cách kiểm):**

1. **`clean` chứa nhãn máy còn sót lại chứ không phải nhãn sạch.** Pipeline chỉ sửa được lỗi cú pháp (drop/clip) và mọi cảnh báo ngữ nghĩa còn lại (`94 POSSIBLE_MISSING + 35 POSSIBLE_LOOSE_BOX + 25 FALSE_POS + 11 WRONG_CLASS` ở v3) chưa được người sửa hết vì Hold — model học đúng các lệch của checker, nên không có kỳ vọng clean phải vượt raw về mAP. Kiểm: train lại trên các ảnh đã được người duyệt (80 ảnh) + mẫu 80 ảnh còn lại, hoặc so AP riêng các lớp dễ bị `FALSE_POS` (so `ap50_per_class`: `truck` raw 0.6574/0.6395 → clean 0.5452/0.6292, rớt nhiều nhất) với tỉ lệ warning của lớp đó.
2. **Test chỉ 100 ảnh, chênh lệch −0.015 không vượt được khoảng tin cậy theo mẫu test.** Với tập kiểm 100 ảnh, 1 ảnh đổi kết quả có thể nhấp nhô mAP khoảng ~0.01–0.02 — cùng cỡ chênh quan sát được. Kiểm: đánh giá lại trên `data/gold_val` thường xuyên hơn (nếu có) hoặc bootstrap lại tập test, và so `map50_95` (kênh khác: −0.011, cùng dấu, cùng cỡ nhiễu) với các seed để xem dấu chênh có ổn định theo metric khác không; nếu kết quả vẫn trong nhiễu, kết luận là "chưa đủ bằng chứng" (theo đúng RULES: không được kết luận "clean tốt hơn raw" khi số liệu không ủng hộ).

## 6. Quyết định và ghi chú AI

**(a) Quyết định cuối: Hold (chưa Release).** `submission/reports/08_summary.json`: `decision=Hold`, `n_errors=0`, `n_warn_images=60`, `n_images=205`, `warn_ratio=0.2927`, lý do `60/205 ảnh còn cảnh báo (29.27%) >= ngưỡng 10.00%` — tức không phải Rework (đã hết lỗi bắt buộc sau sửa tự động + duyệt), nhưng tỷ lệ ảnh còn cảnh báo vượt `cfg["gate"]["warn_ratio_hold"]=0.10` nên chưa được phát hành. Vào 224 ảnh ở bước 1 (`01_intake.txt`: loại 19 ảnh = 5 `images` + 14 `duplicates`), ra 205 ảnh trong `submission/export/clean_v1/manifest.json` (`n_images=205`, `decision=Hold`) — đây mới là bản nháp chờ xử lý cảnh báo, không phải bản Release.

Để thành Release, phải đưa `n_warn_images` từ 60 xuống ≤20 ảnh (`20/205=9.76% < 10%`; `21/205=10.24% ≥ 10%`), tức xử lý ít nhất 40/60 ảnh còn cảnh báo, **không được chỉ hạ ngưỡng gate**: mở rộng ngân sách duyệt / chạy thêm vòng người duyệt theo thứ tự ưu tiên ở `05_review_queue.csv` (hàng đợi có 145 ảnh, mới duyệt 80/80 ngân sách theo `08_summary.json`, còn lại ưu tiên `POSSIBLE_MISSING` (94 dòng), `POSSIBLE_LOOSE_BOX` (35), `POSSIBLE_FALSE_POS` (25), `POSSIBLE_WRONG_CLASS` (11) trong `07_error_list_v3.csv` — tổng 165 dòng `second_opinion` — cộng `EMPTY_LABEL` 10, `BOX_TINY` 6, `BOX_HUGE` 3), sửa nhãn thật cho các cảnh báo đúng (thêm box thiếu, siết box lỏng, xoá/giữ box thừa có căn cứ, sửa lớp, xác nhận ảnh nền hay thiếu nhãn), rồi chạy lại pipeline (`--resume-after-review`) và kiểm lại `07_error_list_v3` + `08_summary.json` trước khi kết luận Release. Nếu sau duyệt vẫn còn ≥21 ảnh cảnh báo thì vẫn phải giữ Hold và lặp vòng, không xuất bản chính thức.

**(b) Ghi chú AI (có dùng):**

- Prompt chính: “viết cho tôi file `pipeline/checks/label_format.py` để khi chạy `python -m pytest -q` xanh hết (79 test)” (sau đó mở rộng sang `second_opinion`, `autofix`, `gate` khi phát hiện mới chỉ 14/79 test qua).
- Cách tôi kiểm code AI: đọc đối chiếu từng test với docstring của module và `pipeline/common.py`/`tests/conftest.py` (số dòng gốc, `overflow_tol`, `DUP_BOX` báo dòng sau, cảnh báo không chạm tới, idempotent của autofix…), chạy `.\.venv\Scripts\python.exe -m pytest -q` được **79 passed**, rồi kiểm bằng chứng đầu ra thật (`01/03/05/07/08_summary.json`, `manifest.json`) thay vì tin kết luận miệng của AI.
- Một lần AI sai: AI tưởng chỉ cần viết xong `label_format.py` là đủ 79 test, nhưng chạy thật mới chỉ **14 pass** vì `second_opinion.py`, `steps/autofix.py`, `steps/gate.py` vẫn là stub `NotImplementedError`; AI cũng chạy nhầm Python hệ thống (`ModuleNotFoundError: yaml`) thay vì dùng `.venv` của dự án — cả hai đều phải sửa bằng cách rà toàn bộ stub và chạy lại bằng `.venv`.

_(Thưởng +2, tùy chọn)_ CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
