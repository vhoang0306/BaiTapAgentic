# Stage 02 Copy: Refund policy skill

`list_files`, `read_file`, `write_file` + skill catalog. Model tự load SKILL.md bằng `read_file`.

- Tools: `list_files(path)`, `read_file(path)`, `write_file(path, content)`, `update_project_memory(content)`
- Skills: `refund-policy`, `weekly-report`

## Cài đặt và chạy

Cần Python 3.11+ và [uv](https://docs.astral.sh/uv/). Chạy trong thư mục project này:

```bash
uv sync --all-packages --locked
cp -n .env.example .env
# Điền OPENAI_API_KEY, MODEL_NAME (và OPENAI_BASE_URL nếu dùng endpoint khác) vào .env
uv run streamlit run app.py
```

Mở **Local URL** in ra terminal (mặc định `http://localhost:8501`). `.streamlit/config.toml` của project bật `server.headless`, nên Streamlit không hỏi email ở lần chạy đầu và không tự mở trình duyệt; file này cũng đặt màu theme và tắt gửi thống kê sử dụng. Streamlit chỉ đọc file này khi chạy trong thư mục project.

## Cấu hình model

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | Có | API key của provider |
| `MODEL_NAME` | Có | Tên model, cần hỗ trợ native tool calling |
| `OPENAI_BASE_URL` | Không | OpenAI-compatible endpoint. Endpoint phải hỗ trợ tool calling theo chuẩn OpenAI Chat Completions (`tools`, `tool_calls`, message role `tool`). |

Thiếu `OPENAI_API_KEY` hoặc `MODEL_NAME`: UI hiện cảnh báo, ô chat bị khóa và app không gọi model. App không truyền `temperature` hay tham số model khác; key không được ghi vào trace/log.

## Prompt thử

1. `Tôi mua ngày 28/09/2026, yêu cầu hoàn ngày 06/10/2026, chưa kích hoạt. Tôi có được hoàn không?`
2. Trong cuộc trò chuyện mới: `Tôi mua ngày 02/10/2026, yêu cầu hoàn ngày 12/10/2026, chưa kích hoạt. Tôi có được hoàn không?`
3. Đổi tên hai file trong `workspace/data/policies/` (giữ nguyên nội dung), mở cuộc trò chuyện mới và chạy lại hai tình huống trên.
4. Trong cuộc trò chuyện mới: `Tôi mua ngày 02/10/2026, muốn hoàn ngày 12/10/2026.`

Kỳ vọng: A chọn chính sách trước tháng 10 và tính 8 ngày nên không đủ điều kiện; B chọn chính sách từ tháng 10 và tính 10 ngày nên đủ điều kiện, không phí. Đổi tên file không đổi kết quả. Khi thiếu trạng thái kích hoạt, agent phải hỏi lại trước khi kết luận. Kiểm tra trace có `list_files`, nội dung skill/reference và tài liệu đã đọc; các đường dẫn file phải là đường dẫn workspace thực tế.

## Xem output, trace, state và context

- **Bố cục**: trang không cuộn; chỉ cột chat và cột State & Context cuộn riêng, cao theo cửa sổ trình duyệt (khối CSS nhỏ `PAGE_CSS` trong `app.py`). Nội dung dài (trace, bảng, file output) hiện đầy đủ trong cột, không có khung cuộn lồng nhau.
- **Chat (cột trái)**: mỗi lượt assistant có expander **Các bước thực hiện (N model call, M tool call)**: từng model call, mỗi tool call trong một khung có badge ok/lỗi, thời gian chạy, arguments (lệnh bash hiện dạng code), result; content/stdout/stderr hiện đầy đủ. Final answer nằm ngoài expander. Nút **Cuộc trò chuyện mới** (cạnh tiêu đề) xóa history, counters, snapshots, skill đã load của conversation cũ; không xóa `traces/` hay file output.
- **State & Context (cột phải)**: badge trạng thái và 4 counters cập nhật trong lúc chạy (rê chuột vào biểu tượng ? để xem định nghĩa); **Tools được cấp** (schema); **Skills trong catalog** (metadata, chưa phải đã load); **Skill content đã vào history** (chỉ khi `read_file` SKILL.md thành công, kèm message index và tool_call_id); **Tài nguyên đã đọc**; **Message history hiện tại**; **Event log**.
- **Context gửi model (lớp LangChain)**: snapshot request chụp ngay trước mỗi model call: system prompt thực tế, messages theo thứ tự, tools schema, metadata (conversation_id, run_id, lượt, model call, event sequence, thời điểm, model name, số message, số ký tự, usage nếu provider trả về). Trước model call đầu tiên, panel hiện **Context cấu hình (chưa gửi)**. Sau khi lượt kết thúc có thể chọn lại snapshot cũ (chỉ đọc, không chạy lại agent) và tải snapshot JSON. Snapshot không phải provider wire payload, tokenizer output hay nội dung bên trong model.
- **Project memory**: nội dung `project-memory.md` ở thư mục project được inject vào system prompt mỗi khi tạo agent cho một lượt chat mới. Panel có expander **Project memory hiện hành** để kiểm tra nội dung đang lưu; snapshot request cũng ghi system prompt thực tế đã gửi. Khi người dùng xác nhận quy ước mới/thay đổi, agent dùng `update_project_memory` để thay toàn bộ Markdown hiện hành, giữ quy ước còn hiệu lực và bỏ quy tắc lỗi thời. File nằm ngoài `workspace/` nên lệnh reset workspace không xóa memory. Chỉ báo đã lưu khi tool trả thành công.
- **File đầu ra**: chọn file trong `workspace/output/`, xem Markdown/text và tải xuống. Xem file là thao tác UI, không gửi nội dung vào context của model.
- **Trace trên đĩa**: `traces/<thời gian>_<conversation>_turnNN_<run>.jsonl`, mỗi dòng một event (sequence, type, tool_call_id, tool_name, arguments, result, elapsed_ms; event `model_request` kèm snapshot request). Exception không mong đợi ghi thêm vào `traces/debug.log`.

## Định nghĩa trong State & Context

| Trường | Ý nghĩa |
|---|---|
| Lượt chat | Một lần gửi input; bắt đầu từ 1 trong mỗi conversation. |
| Lần gọi model trong lượt | Tăng ngay trước mỗi model request thực tế (middleware `wrap_model_call`); reset khi gửi lượt mới. Retry nội bộ của OpenAI SDK không quan sát được nên không đếm riêng. |
| Bước sự kiện trong lượt | Số thứ tự observer event (`user_submitted`, `model_request`, `model_response`, `tool_started`, `tool_finished`, `run_completed`, `run_failed`). Không phải LangGraph step. |
| Tool calls trong lượt | Số tool call đã thực thi, mỗi call có ID riêng. Một model response có thể yêu cầu nhiều tool calls. |
| Trạng thái | Sẵn sàng / Đang gọi model / Đang chạy tool / Hoàn tất / Lỗi. |

## Giới hạn thực thi

Mỗi lượt: tối đa 8 lần gọi model (`ModelCallLimitMiddleware`), 20 tool calls (`ToolCallLimitMiddleware`), recursion limit LangGraph 50 (số bước graph, không phải số tool calls). Giá trị nằm trong `config.py`.

Lỗi runtime/provider: UI hiện lỗi, giữ trace đã có, rollback model history về trước lượt lỗi. App không tự chạy lại lượt lỗi.

## Workspace và reset

Agent chỉ làm việc trong `workspace/`: `read_file` đọc file trong workspace, `write_file` chỉ ghi dưới `workspace/output/`. Lần chạy đầu, nếu chưa có workspace, app copy từ `fixtures/`; rerun không ghi đè.

Khôi phục dữ liệu gốc (xóa output, giữ traces):

```bash
uv run python reset_workspace.py
```

Lệnh chỉ chạy khi workspace có marker `.lab-workspace` của lab.

## Skills

`skill_catalog.py` quét `workspace/skills/*/SKILL.md`, chỉ đưa `name`, `description`, `location` vào system prompt. Body và reference không có trong context ban đầu. Model tự đọc SKILL.md bằng `read_file` khi task khớp description; tool result ở lại trong history cho các lượt sau. Skill thiếu metadata hoặc YAML sai bị bỏ qua kèm diagnostic; trùng `name` báo lỗi và giữ bản đầu (xem expander **Skills trong catalog**). Skill `refund-policy` hướng dẫn tìm tài liệu bằng `list_files`, chọn chính sách theo ngày mua và hỏi khi thiếu thông tin; nội dung chính sách chỉ nằm trong tài liệu ở `workspace/data/policies/`.

## Kiểm chứng persistent memory

1. Trong chat, thống nhất một quy ước rõ ràng rồi yêu cầu lưu, ví dụ: `Từ nay báo cáo dùng múi giờ UTC. Hãy lưu đây là quy ước của dự án.` Kiểm tra tool `update_project_memory` thành công và nội dung được hiển thị trong **Ppyroject memory hiện hành**.
2. Mở **Cuộc trò chuyện mới** rồi yêu cầu một việc chịu ảnh hưởng bởi quy ước. Kiểm tra **Context gửi model → Snapshot: system prompt** có quy ước đó và câu trả lời tuân thủ.
3. Yêu cầu thay đổi quy ước, ví dụ `Đổi quy ước: từ nay báo cáo dùng Asia/Ho_Chi_Minh, không còn dùng UTC.` Xác nhận memory đã được thay thế.
4. Mở session/cuộc trò chuyện mới lần nữa. Snapshot phải chứa quy ước mới và không chứa quy tắc UTC đã bị loại bỏ.

Memory là một tài liệu Markdown chuẩn duy nhất, được ghi khi có xác nhận tường minh (không tự trích mọi hội thoại); mỗi lượt chat mới đọc lại file. Agent đang chạy dùng system prompt chụp lúc tạo, nên thay đổi được áp dụng từ lượt chat mới tiếp theo. File được giới hạn 20 KB và chỉ có thể ghi qua tool chuyên biệt.

## Tests

```bash
uv run pytest
```

Tests dùng mock model, không cần API key.

## Giới hạn môi trường

- Chạy local, một người dùng cho mỗi project. Không có xác thực, không chia sẻ workspace đa người dùng.
