---
name: refund-policy
description: "Tra cứu tài liệu chính sách hoàn tiền và xác định điều kiện theo ngày mua, ngày yêu cầu hoàn và trạng thái kích hoạt. Dùng khi người dùng hỏi có được hoàn tiền hay mức phí hoàn tiền."
---

# Tra cứu chính sách hoàn tiền

## Quy trình

1. Kiểm tra người dùng đã cung cấp ngày mua, ngày yêu cầu hoàn và trạng thái kích hoạt chưa. Nếu thiếu bất kỳ thông tin nào, hỏi lại thông tin đó trước khi kết luận.
2. Dùng `list_files` liệt kê trực tiếp `data/policies/`. Không giả định tên file; dùng các đường dẫn trả về và `read_file` để đọc tài liệu chính sách có liên quan.
3. Dựa trên phạm vi hiệu lực ghi trong tài liệu, chọn chính sách theo **ngày mua**, không theo ngày yêu cầu hoàn hoặc ngày hiện tại. Nếu không có tài liệu phù hợp hoặc tài liệu mâu thuẫn, nêu rõ và hỏi lại thay vì tự suy đoán.
4. Tính số ngày đã qua là chênh lệch ngày lịch giữa ngày yêu cầu hoàn và ngày mua. Dùng chính các ngày người dùng cung cấp; bằng đúng giới hạn vẫn nằm trong thời hạn.
5. Đối chiếu thời hạn và trạng thái kích hoạt với tài liệu. Sản phẩm đã kích hoạt không đủ điều kiện khi tài liệu quy định như vậy. Chỉ nêu phí khi đủ điều kiện và phí được tài liệu xác định.
6. Trả lời theo [mẫu câu trả lời](./references/answer-template.md), dẫn đường dẫn workspace của tài liệu đã đọc làm căn cứ. Nếu tool trả lỗi, báo lỗi và không bịa nội dung.
