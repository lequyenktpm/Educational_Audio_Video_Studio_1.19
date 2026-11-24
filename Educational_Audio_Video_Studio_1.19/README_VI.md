# Educational Audio Video Studio 1.19

Ứng dụng Windows tạo video giáo dục từ audio, transcript và storyboard; có Reading Along, karaoke subtitle, watermark/outro và tab ghép video + audio theo batch.

## Chạy ứng dụng
1. Giải nén toàn bộ ZIP vào một thư mục riêng.
2. Chạy `run_app.bat`. Lần đầu ứng dụng tự tạo môi trường ảo và cài dependencies cơ bản.
3. Để căn chỉnh Reading Along bằng Whisper, chạy `install_alignment.bat` theo hướng dẫn trong ứng dụng.

## Tab mới: Merge Video + Audio
- **Một video + một audio:** chọn riêng một file video và một file audio.
- **Batch – ghép theo tên file:** chọn thư mục video, thư mục audio và thư mục lưu kết quả. App ghép theo tên file không phân biệt chữ hoa/thường và bỏ qua phần mở rộng. Ví dụ `lesson01.mp4` sẽ ghép với `lesson01.mp3` hoặc `lesson01.wav`.
- File không có audio trùng tên sẽ được bỏ qua và ghi log. Nếu có nhiều audio cùng stem, batch dừng để tránh ghép nhầm.
- Kết quả có tên `<tên_video>_merged.mp4`.
- Audio ngoài thay thế audio gốc của video. Thời lượng kết quả lấy phần ngắn hơn giữa video và audio.
- Có thể bật watermark chữ, chọn góc và độ mờ; thêm outro tối đa 6 giây với hai dòng tùy chỉnh. Đặt outro = 0 để tắt.
- Có nút hủy batch; tiến độ hiển thị theo số cặp đã xử lý.

Lưu ý: để chèn watermark/outro, video được mã hóa lại bằng FFmpeg; không phải thao tác copy stream nên sẽ mất thời gian render. Giữ nguyên bản gốc vì kết quả được ghi sang thư mục output riêng.

## Các chức năng khác
Các tab Project, Storyboard / Scenes, Assets, Add Karaoke Sub và Reading Along Studio được giữ nguyên từ 1.18.
