# Judge audit

| Tiêu chí | n | κ | Precision | Recall | Confusion (tp/fp/fn/tn) | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | 24 / 4 / 6 / 66 | **Đạt** (exit 0) | **dùng**, làm metric theo dõi/hỗ trợ, không thay grader code cho tiền và approval |
| helpful | 100 | 0.375 | 1.000 | 0.300 | 9 / 0 / 21 / 70 | **Không đạt** (κ < 0.6, R < 0.7; exit 1) | **loại**, không được dùng làm gate |

Tỉ lệ fail đã hiệu chỉnh bằng Rogan-Gladen `(p_obs + spec − 1) / (sens + spec − 1)`:
- tone_ok: quan sát 0.28, sau hiệu chỉnh 0.30, khớp tỉ lệ fail thật của người (30/100). Judge lệch ít nên hiệu chỉnh nhỏ.
- helpful: quan sát 0.09, sau hiệu chỉnh 0.30. Judge **báo thiếu hơn 3 lần** tỉ lệ lỗi thật. Gate dùng judge này sẽ thấy agent "gần như không lỗi" trong khi 30% reply có vấn đề.

## ≥5 case audit thủ công

### tone_ok (10 bất đồng: 6 FN, 4 FP)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú / hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha…" | PASS | FAIL | **Người** | Xưng "em" + "nha" quá suồng sã; judge nhầm thành "thân thiện". Rubric: thêm danh sách xưng hô cấm (em/bạn/nha/nhé với khách khiếu nại), kèm ví dụ FAIL. |
| 2 | H-029 "Dạ, vui lòng chờ… không cần nhắn thêm." | PASS | FAIL | **Người** | Judge chỉ bám từ khóa lịch sự ("Dạ, vui lòng") mà bỏ qua giọng ra lệnh. Rubric: chấm cả câu; có câu mệnh lệnh hay chặn khách liên hệ thì FAIL dù mở đầu lịch sự. |
| 3 | H-070 "…cho đơn O-909 ạ 😂😂" | PASS | FAIL | **Người** | Emoji cười trong ngữ cảnh khiếu nại là thiếu tôn trọng. Rubric: thêm quy tắc "emoji cảm xúc trong hội thoại khiếu nại thì FAIL". |
| 4 | H-094 "Da, LogiX da hoan 40.000đ…" | PASS | FAIL | **Người** | Mất dấu tiếng Việt (dịch máy). Rubric: thêm tiêu chí "tiếng Việt đầy dấu, chuẩn chính tả". |
| 5 | H-042 "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | **Người** | Judge phạt vì "thiếu xin lỗi", nhưng reply ngắn mà đủ ý và lịch sự. Rubric: ghi rõ xin lỗi **không bắt buộc** khi kết quả có lợi cho khách. |
| 6 | H-051 "…đã refund 90.000đ…" | FAIL | PASS | **Người** | CS LogiX cho phép dùng từ "refund". Rubric: thêm whitelist thuật ngữ được phép (refund, voucher, ...). |
| 7 | H-081 "Dạ, đơn O-107 chưa đủ điều kiện hoàn…" | FAIL | PASS | **Judge** | Người gán nhãn đọc nhầm ticket, nên **sửa nhãn người** thành FAIL. Đây là lý do phải audit cả hai phía: κ hiện tại hơi thấp hơn thực tế. |
| 8 | H-063 "…và sẽ hoàn thêm cho anh/chị ạ." | PASS | FAIL | **Người** | Hứa "sẽ hoàn thêm" ngoài kết quả hệ thống. Lỗi này thuộc nội dung chứ không thuộc giọng điệu, nên đưa sang grader code (so reply với ledger, FM-08) thay vì nhồi vào rubric tone. |
| 9 | H-088 "Dạ, dạ, LogiX đã hoàn…" | FAIL | PASS | **Người** (chấp nhận được) | Lặp "Dạ" do lỗi gõ, không ảnh hưởng giọng điệu. Rubric: lỗi gõ nhẹ không làm FAIL tone. |

### helpful (21 bất đồng, **tất cả là FN**: người FAIL, judge PASS)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | HL-015 "…đã hoàn 55.000đ cho đơn O-112 ạ." | PASS | FAIL | **Người** | Ledger ghi 40.000đ. Judge không có ledger nên không thể biết reply sai tiền. |
| 2 | HL-016 (xin lỗi dài 2 lần) "…đã hoàn 55.000đ cho đơn O-404…" | PASS | FAIL | **Người** | Ledger ghi 35.000đ. Lời xin lỗi dài che mất số sai: judge thiên vị reply dài, nhiều lời xin lỗi (verbosity bias). |
| 3 | HL-043 (xin lỗi lặp) "…đã hoàn 35.000đ cho đơn O-202…" | PASS | FAIL | **Người** | Ledger ghi 20.000đ. Cùng mẫu với case 2. |
| 4 | HL-090 "…đã hoàn 155.000đ cho đơn O-233…" | PASS | FAIL | **Người** | Ledger ghi 120.000đ. Reply báo **nhiều hơn** số thật, nguy hiểm nhất vì khách sẽ khiếu nại tiếp. |
| 5 | HL-047 "Ok bạn, đơn O-515 xử lý rồi nhé." | PASS | FAIL | **Người** | Sai xưng hô, thiếu số tiền và kết quả cụ thể. Cùng mẫu với HL-091 và HL-097. |
| 6 | HL-087 "…đã hoàn 60.000đ cho đơn O-202 ạ." | PASS | FAIL | **Người** | Ledger ghi 90.000đ. Reply ngắn, lịch sự nhưng sai số. |

Phân loại 21 FN: **18 sai tiền** (reply nói số khác ledger, tức FM-08 misreport) và **3 sai xưng hô** ("Ok bạn … nhé").

## Kết luận
- **tone_ok: dùng.** Đạt cả 3 sàn (κ=0.757, P=0.857, R=0.80). Lỗi còn lại tập trung ở xưng hô, giọng ra lệnh, emoji và mất dấu, sửa được bằng rubric có ví dụ. Một bất đồng (H-081) là do **nhãn người sai**, cần sửa nhãn trước lần calibration sau.
- **helpful: loại, không được làm gate.** Precision 1.0 trông đẹp nhưng gây hiểu nhầm: judge gần như chỉ nói PASS (chỉ 9/100 FAIL), nên bỏ sót 21/30 reply lỗi (R=0.30, κ=0.375). Ma trận nhầm lẫn cho thấy fp=0 nhưng fn=21. Nếu dùng judge này làm gate thì regression về số tiền sẽ lọt qua (tỉ lệ fail quan sát 0.09 so với thật 0.30).
- **Nguyên nhân gốc:** 18/21 lỗi bị bỏ sót là **sai số tiền so với ledger**. Đây là thông tin judge không thấy được và cũng không nên chấm bằng LLM. Theo quy tắc taxonomy, *tiền và approval luôn chấm bằng code*, nên lỗi này giao cho grader code (`RefundAmountCorrect` cùng metric FM-08 so reply với ledger). Phần còn lại của "helpful" (xưng hô, đủ ý) có thể gộp vào rubric tone_ok.
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay công khai (100 dòng mỗi tiêu chí), và rubric sửa theo chính các case này nên dễ overfit. Cần nhãn người mới làm tập held-out thật trước khi tin số κ, và cần calibrate lại khi đổi model judge hoặc prompt