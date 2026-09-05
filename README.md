---
title: Prescription OCR API
emoji: 💊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Prescription OCR API

Backend FastAPI xử lý OCR toa thuốc, xác thực người dùng và quản lý dữ liệu thuốc/đơn thuốc.

## Cài đặt

Yêu cầu Python 3.11+ và Tesseract OCR đã được cài trên máy.

```bash
cd api-prescription-ocr
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements-api.txt -r requirements.txt
```

## Chạy API

```bash
uvicorn app.main:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `GET /api/v1/health`

## Chia sẻ API bằng ngrok

Khởi động API bằng `uvicorn`, sau đó mở terminal khác và chạy:

```bash
ngrok http 8000
```

Sử dụng HTTPS Forwarding URL dạng `https://<id>.ngrok-free.app` làm base URL cho Web và Mobile. Kiểm tra kết nối bằng `https://<id>.ngrok-free.app/api/v1/health`.

URL ngrok miễn phí thường thay đổi sau mỗi lần khởi động lại. Khi URL đổi, cập nhật Web tại `prescriptionocr-WebUi/.env` và Mobile tại `prescriptionmobile/lib/services/api_service.dart`.

## Xác thực

Đăng nhập hoặc đăng ký trả response dạng token phẳng:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "username": "doctor01",
  "role": "doctor"
}
```

Gửi token ở các request cần xác thực:

```http
Authorization: Bearer <jwt>
```

Role hiện có: `user`, `doctor`, `admin`.

## Endpoint chính

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Public | Đăng nhập; nhận JSON hoặc form |
| `POST` | `/api/v1/auth/register` | Public | Tạo tài khoản |
| `POST` | `/api/v1/auth/bootstrap` | Public | Tạo admin đầu tiên |
| `POST` | `/api/v1/auth/reset-password` | Public | Đặt lại mật khẩu bằng username và email |
| `PUT` | `/api/v1/auth/change-password` | Đã đăng nhập | Đổi mật khẩu bằng mật khẩu hiện tại |
| `POST` | `/api/v1/prescriptions/ocr` | `user`, `doctor` | Upload ảnh với multipart field `file` |
| `GET` | `/api/v1/prescriptions` | `user`, `doctor` | Lấy danh sách bản ghi đơn thuốc |
| `POST` | `/api/v1/prescriptions/{id}/medicines/{index}/use` | `user`, `doctor` | Giảm số lượng thuốc đã dùng |
| `GET` | `/api/v1/medicines` | `user`, `doctor` | Lấy kho thuốc |
| `PATCH` | `/api/v1/medicines/{id}` | `doctor` | Cập nhật `ten`, `so_luong`, `huong_dan` |
| `GET` | `/api/v1/users` | `admin` | Danh sách người dùng |
| `GET` | `/api/v1/admin/users` | `admin` | Danh sách người dùng quản trị |
| `POST` | `/api/v1/admin/users/create-admin` | `admin` | Tạo admin |
| `PUT` | `/api/v1/admin/users/{id}/role` | `admin` | Đổi role |
| `PUT` | `/api/v1/admin/users/{id}/toggle-active` | `admin` | Bật/tắt tài khoản |
| `PUT` | `/api/v1/admin/users/{id}/reset-password` | `admin` | Đặt lại mật khẩu |
| `DELETE` | `/api/v1/admin/users/{id}` | `admin` | Xóa người dùng |

## Dữ liệu response OCR

`POST /api/v1/prescriptions/ocr` trả trực tiếp object OCR, gồm các field chính:

```json
{
  "tep_anh": "prescription.png",
  "ho_ten": "...",
  "ten_benh_vien": "...",
  "bac_si": ["..."],
  "ngay_ke": "...",
  "chan_doan": "...",
  "thuoc": [
    {"ten": "...", "so_luong": "...", "huong_dan": "..."}
  ],
  "van_ban_ocr": "...",
  "ocr": {"so_doan_van_ban": 0, "do_tin_cay_trung_binh": 0.0, "engine": "tesseract"}
}
```

`GET /api/v1/prescriptions` trả một mảng record. Mỗi record có `id`, `owner_id`, `tep_anh`, `created_at` và `data`, trong đó `data` chứa object OCR như trên.

## Cấu trúc

```text
app/
├── main.py                 # Khởi tạo FastAPI và mount router
├── api/routes/             # Endpoint auth, OCR, resource, user
├── core/                   # OCR, xử lý ảnh, parser, cấu hình
├── services/               # Nghiệp vụ và lưu dữ liệu
├── schemas/                # Pydantic request/response schemas
└── database/               # JSON data cho môi trường phát triển
```

## Lưu ý

- API dùng file JSON trong `app/database/`; cần backup trước khi thay đổi dữ liệu.
- CORS hiện cho phép các cổng web local `5173` và `3000`.
- Trước production cần thay secret JWT, cấu hình CORS và chuyển sang database phù hợp.
"# api-prescription-ocr" 
