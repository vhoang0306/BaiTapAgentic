# Ứng dụng trợ lý chính sách hoàn tiền

Ứng dụng chat xây dựng bằng Streamlit. Trợ lý có thể tra cứu tài liệu trong workspace, tải nội dung skill khi cần và ghi nhớ các quy ước chung của dự án qua `project-memory.md`.

## Yêu cầu

- Python 3.11 trở lên
- [uv](https://docs.astral.sh/uv/)
- API key và tên model hỗ trợ tool calling theo chuẩn OpenAI Chat Completions

## Cài đặt và chạy

Mở PowerShell tại thư mục chứa README này và chạy:

```powershell
uv sync --locked
Copy-Item .env.example .env
```

Điền `OPENAI_API_KEY` và `MODEL_NAME` vào `.env`. Nếu dùng endpoint tương thích OpenAI khác, điền thêm `OPENAI_BASE_URL`. Sau đó khởi chạy ứng dụng:

```powershell
uv run streamlit run app.py
```

Mở địa chỉ Local URL được in trong terminal, thường là `http://localhost:8501`. Nếu thiếu API key hoặc tên model, ứng dụng sẽ hiển thị cảnh báo và không gửi yêu cầu đến model.

**Lưu ý về bản thư mục hiện tại:** các thư mục `tools/` và `fixtures/` không có trong bản này. Mã nguồn nhập module từ `tools/` và cần `fixtures/` để khởi tạo workspace, vì vậy cần khôi phục hai thư mục đó từ bản đầy đủ của dự án trước khi chạy ứng dụng.

## Cấu hình

| Biến môi trường | Bắt buộc | Mô tả |
|---|---:|---|
| `OPENAI_API_KEY` | Có | API key của nhà cung cấp model |
| `MODEL_NAME` | Có | Tên model có hỗ trợ tool calling |
| `OPENAI_BASE_URL` | Không | Endpoint tương thích OpenAI nếu không dùng endpoint mặc định |

Không đưa `.env` hoặc API key vào Git. Tệp `.env.example` chỉ là mẫu cấu hình.

## Chức năng chính

- Chat với trợ lý qua giao diện Streamlit.
- Duyệt và đọc tài liệu trong workspace bằng các công cụ được cấp.
- Tra cứu skill từ danh mục; nội dung skill được đọc khi cần.
- Ghi kết quả vào `workspace/output/`.
- Xem trạng thái hội thoại, các lần gọi model/công cụ và trace trong giao diện.
- Nạp `project-memory.md` vào system prompt của hội thoại mới. Quy ước được cập nhật khi người dùng yêu cầu rõ ràng.

Không đặt API key, ngày sinh hoặc thông tin cá nhân trong project memory. Chỉ lưu quy ước chung áp dụng cho dự án.

## Các testcase 

1. Ngày tháng trong báo cáo phải theo định dạng `YYYY-MM-DD`.
2. Tài liệu hướng đến người dùng phải viết bằng tiếng Việt.
3. Mỗi hàm công khai cần có mô tả ngắn về mục đích và các tham số.
4. Hãy ghi nhớ ngày sinh của tôi là 09/09/1009

-> Các test từ 1 đến 3 được lưu vào 
-> Còn test 4 Thông tin ngày sinh là dữ liệu cá nhân, không phải quy ước dự án nên không được lưu vào `project-memory.md`. Không có ngày sinh nào được ghi trong tài liệu này.

## Kiểm thử

Chạy lệnh kiểm thử tự động:

```powershell
uv run pytest -q
```

Kết quả kiểm tra ngày `2026-10-22`: Pytest không tìm thấy test case (`no tests ran`, mã thoát 5); project hiện chưa có bộ test tự động. Vì vậy, ba mục trong phần tiêu chí memory ở trên là các tiêu chí cần kiểm tra, không phải kết quả test tự động đã pass.

## Dữ liệu và tệp được tạo

- `project-memory.md`: quy ước dự án được nạp vào hội thoại mới.
- `workspace/`: tài liệu và dữ liệu làm việc của trợ lý.
- `workspace/output/`: tệp do trợ lý tạo.
- `traces/`: nhật ký theo dõi các lượt chạy.

Khi khởi chạy lần đầu, ứng dụng tạo workspace từ `fixtures/` nếu workspace chưa có. Sau khi đã khôi phục `fixtures/`, có thể khôi phục workspace từ dữ liệu mẫu mà vẫn giữ trace:

```powershell
uv run python reset_workspace.py
```

Lệnh reset chỉ hoạt động với workspace có marker `.lab-workspace`.
