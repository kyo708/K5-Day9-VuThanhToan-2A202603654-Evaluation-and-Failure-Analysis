# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `<shape> <claim>@<seed>`, run ID trong report |
| Triệu chứng | Grader nào fail; reply nói gì so với ledger ghi gì |
| Bước sai đầu tiên | Số thứ tự event + kind + trích payload (≤1 dòng) |
| Vì sao là bước *đầu tiên* | Các bước trước đó đúng ra sao (dẫn số event) |
| Failure mode | Mã FM-xx trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng claim@seed trên shape `fixed`: bước đó khác thế nào |
| Regression test | Tên test + grader/assert nào bắt được; đã thấy fail trên variant lỗi và pass trên `fixed` chưa |
| Chưa chắc chắn | Điều trace không chứng minh được |

## Case của nhóm: `seeded_regression` C-008@11 (item E-008), reply nói sai số tiền

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-008 --seed 11
python -m lab9.trace_case --shape fixed --claim C-008 --seed 11
```

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-008@11` (item `E-008`). Run ID: `E-seeded_regression-<ngày>-<sha4>` trong `reports/eval_seeded_regression.json` (điền sau M4, vì sha eval set đổi khi gắn `failure_modes` ở M1). Lỗi lặp lại ở **cả 5 seed** 11/22/33/44/55. |
| Triệu chứng | **Grader Lab 8 PASS (`ok`)**: ledger `refund_vnd=20000`, đúng nhãn 20000, status `resolved` cũng đúng. Nhưng **`reply_matches_ledger` FAIL**: reply báo khách *"Dạ, LogiX đã hoàn **35.000đ** cho đơn O-808."* trong khi ledger chỉ ghi **20.000đ**. Khách được hứa nhiều hơn 15.000đ so với số thật nhận. |
| Bước sai đầu tiên | **Event 5 `reply`**: `{"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}` |
| Vì sao là bước *đầu tiên* | Event 1 `handoff`: đúng scope `owner_order_only`. Event 2 `investigator`: đọc đúng O-808 (`delay_days=4`, phí ship 35.000đ). Event 3 `quote`: 35.000đ theo `SHIP-LATE-03`, khớp nhãn `proposal_amount=35000`. Event 4 `refund_history`: `refunded_vnd=0`, nên bước trừ trước (`pre_deducted`) không đổi số (vẫn 35.000). Host commit **20.000đ** vì approval `A-008` chỉ duyệt `approved_vnd=20000`; ledger đúng nhãn. Mọi bước trước đều đúng, chỉ reply chọn sai nguồn số: agent báo **số tự đề xuất** (35.000) thay vì **số host đã ghi** (20.000). |
| Failure mode | **FM-08 misreport**: reply nói số tiền khác ledger. Nguyên nhân gốc trong code là nhánh `pre_deducted` (FM-05) của variant khiến agent báo số tự tính; ở claim này phép trừ bằng 0 nên chỉ còn lại triệu chứng FM-08. |
| Đối chứng | `fixed C-008@11`: các event 1–3 giống hệt (quote 35.000đ), không có `refund_history`, và **event 4 `reply`: "đã hoàn 20.000đ"**, khớp ledger. Ledger hai shape giống nhau (20.000đ), khác nhau **duy nhất ở câu reply**. Vì vậy chỉ đọc ledger không thể phát hiện lỗi này. |
| Regression test | `src/tests/test_lab9_trace_case.py::test_trace_case_c008_seed11`: chạy shape thật cho C-008@11, khẳng định ledger = 20.000đ ở cả hai shape, rồi `ReplyMatchesLedger` **FAIL trên `seeded_regression`** và **PASS trên `fixed`** (đã chạy, cả hai tham số xanh). Gate dùng metric `reply_matches_ledger` (blocking, `min: 1.0`) trong `config/metric_spec.yaml`. |
| Chưa chắc chắn | (1) Trace không cho biết agent "định" nói số nào; ta chỉ thấy reply sinh từ `proposal` chứ không phải `effect.amount_vnd`. (2) Bộ tách số tiền chỉ nhận dạng số có đơn vị (`đ`, `đồng`, `VND`); reply viết "35k" hoặc "ba mươi lăm nghìn" sẽ lọt. (3) MockLLM tất định: với LLM thật lời văn reply thay đổi, cần kiểm lại regex trên trace thật. |

**Bài học:** grader Lab 8 chỉ so `refund_effects` của *kết quả* với ledger, không đọc *reply gửi khách*. Một trial có thể "PASS" mà vẫn nói sai với khách hàng, nên tiền phải được kiểm ở **mọi nơi nó xuất hiện**: ledger, đề xuất và lời nhắn.

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
