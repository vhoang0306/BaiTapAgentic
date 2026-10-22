# Báo cáo bài tập: tool tìm tài liệu và skill refund-policy

## 1. Mục tiêu và phạm vi

Hoàn thành bài tập trên hai bản sao tên `copy`, giữ nguyên project mẫu:

- `stage-01-files-copy`: bổ sung tool liệt kê thư mục `list_files`.
- `stage-02-skills-copy`: bổ sung cùng tool, tài liệu chính sách hoàn tiền và skill `refund-policy`.

Mọi tài liệu chính sách và skill được đặt trong `fixtures/` và `workspace/` tương ứng để workspace có thể được tạo lại từ fixtures. Hai tài liệu được kiểm tra trên ứng dụng ở `stage-02-skills-copy/workspace/data/policies/`. Sau khi đổi tên, chúng là `legacy-terms.md` và `current-terms.md`; bản stage 01 và stage gốc không bị đổi tên.

## 2. Các thay đổi đã thực hiện

### Tool `list_files`

Thêm tool trong `tools/files.py`, export qua `tools/__init__.py` và đăng ký trong schema tool của agent ở cả hai bản sao. Tool:

- Liệt kê các mục trực tiếp trong thư mục, không duyệt đệ quy.
- Trả tên, đường dẫn tương đối với workspace và loại `file` hoặc `directory`, sắp xếp theo tên.
- Dùng chung cách resolve đường dẫn và cấu trúc lỗi JSON của các file tool hiện có; từ chối đường dẫn tuyệt đối, traversal và mục symlink trỏ ra ngoài workspace.
- Trả lỗi rõ ràng nếu thư mục không tồn tại hoặc đường dẫn là file.

### Chính sách và skill

Trong `stage-02-skills-copy`, thêm hai tài liệu quy định thời hạn theo ngày mua, phí hoàn tiền và điều kiện sản phẩm chưa kích hoạt. Skill `workspace/skills/refund-policy/SKILL.md` hướng dẫn agent:

- Dùng `list_files` để tìm tài liệu trong `data/policies/`, rồi dùng `read_file` đọc tài liệu; không phụ thuộc vào tên cố định.
- Chọn chính sách theo ngày mua và tính chênh lệch ngày lịch theo ngày người dùng cung cấp.
- Hỏi lại nếu thiếu ngày mua, ngày yêu cầu hoàn hoặc trạng thái kích hoạt.
- Trả lời theo reference `references/answer-template.md`, gồm chính sách, số ngày, kết luận, phí nếu đủ điều kiện và đường dẫn tài liệu làm căn cứ.

Skill không nhúng nội dung chính sách hoặc đáp án. Các thay đổi, ví dụ chạy và kết quả kiểm thử được ghi trong README của từng bản copy.

## 3. Kết quả chạy bằng model và bằng chứng trace

Bốn lượt chạy đều kết thúc với `run_completed`, không có `run_failed`. Trong các ca tra cứu chính sách, trace thể hiện skill được đọc thành công, nội dung skill có mặt trong request tiếp theo, `list_files` tìm tên file hiện hành, và `read_file` đọc tài liệu theo đường dẫn tìm được.

| Ca kiểm tra | Trace | Bằng chứng chính | Kết quả |
|---|---|---|---|
| A, trước khi đổi tên: mua 28/09/2026, yêu cầu 06/10/2026, chưa kích hoạt | `traces/20261007-212740_69844df1_turn01_50b8378a.jsonl` | Danh sách gồm `policy-before-oct.md` và `policy-from-oct.md`; đọc cả hai chính sách, skill và reference. | Chọn chính sách trước tháng 10; 8 ngày so với giới hạn 7; không đủ điều kiện. |
| B, sau khi đổi tên: mua 02/10/2026, yêu cầu 12/10/2026, chưa kích hoạt | `traces/20261007-212827_df485d4b_turn01_8ab7694d.jsonl` | Cuộc trò chuyện mới; danh sách gồm `current-terms.md` và `legacy-terms.md`; đọc theo các đường dẫn mới. | Chọn chính sách từ tháng 10; 10 ngày so với giới hạn 14; đủ điều kiện, không mất phí. |
| Thiếu trạng thái kích hoạt: mua 02/10/2026, muốn hoàn 12/10/2026 | `traces/20261007-212854_fa451b01_turn01_fa55fbf3.jsonl` | Đọc skill rồi hỏi tiếp; chưa gọi `list_files` và chưa đọc tài liệu chính sách. | Hỏi sản phẩm đã kích hoạt hay chưa; chưa kết luận. |
| A chạy lại sau khi đổi tên: mua 28/09/2026, yêu cầu 06/10/2026, chưa kích hoạt | `traces/20261007-213030_d23fef94_turn01_8dc7c21f.jsonl` | Cuộc trò chuyện mới; tìm và đọc `legacy-terms.md` cùng `current-terms.md`. | Chọn `legacy-terms.md`; 8 ngày so với giới hạn 7; kết quả vẫn không đủ điều kiện. |

Như vậy, cả A và B đều đã chạy lại sau đổi tên trong các cuộc trò chuyện mới. Việc đổi tên không làm thay đổi lựa chọn chính sách hoặc kết luận.

## 4. Kiểm thử tự động

Chạy `uv run pytest -q` từ thư mục từng bản copy:

| Project | Kết quả |
|---|---:|
| `stage-01-files-copy` | 38 passed, 3 skipped |
| `stage-02-skills-copy` | 48 passed, 3 skipped |

Các test bổ sung kiểm tra thứ tự và cấu trúc kết quả `list_files`, lỗi với file/thư mục thiếu/đường dẫn ngoài workspace, việc đăng ký tool cho agent, đọc tài liệu sau khi đổi tên và metadata/nội dung hướng dẫn của skill. `uv lock --check` cũng thành công.

Mỗi project có ba test symlink bị skip: Windows từ chối tạo symlink với `WinError 1314` do thiếu quyền. Vì vậy, test trực tiếp nhánh symlink escape chưa chạy được trên máy này; phần traversal và đường dẫn tuyệt đối vẫn được kiểm tra.

## 5. Trả lời câu hỏi cuối bài

**Cần tool tìm file** vì agent phải quan sát workspace để biết thư mục hiện có những tài liệu nào và tên/đường dẫn hiện tại của chúng. `list_files` cho phép tìm tài liệu theo nội dung sau cả khi tên file thay đổi. `read_file` sau đó lấy nội dung tài liệu thực tế để agent có căn cứ trả lời.

**Cần skill hướng dẫn chọn chính sách** vì tìm và đọc được file chưa tự quy định cách áp dụng các tài liệu. Skill cung cấp quy trình nghiệp vụ: chọn theo ngày mua, tính số ngày lịch theo ngày người dùng nêu, xét trạng thái kích hoạt và thời hạn, hỏi lại khi thiếu thông tin, rồi trình bày kết luận theo mẫu có dẫn nguồn. Chính sách và số liệu cụ thể vẫn nằm trong các tài liệu được đọc, không bị đóng cứng trong hướng dẫn.

**Chỉ sửa prompt không giải quyết được yêu cầu đổi tên file nếu agent không có tool tìm file.** Prompt có thể nhắc agent dùng một đường dẫn đã biết hoặc yêu cầu tìm file, nhưng không thể tự liệt kê thư mục hay phát hiện tên mới nếu không có khả năng truy cập filesystem phù hợp. Ghi sẵn tên file trong prompt chỉ khiến cách làm hỏng khi file đổi tên và trái yêu cầu tìm tài liệu động. Tool cung cấp khả năng thao tác; skill/prompt hướng dẫn cách dùng khả năng đó và cách suy luận từ nội dung đã đọc.
