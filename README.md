# Prescription OCR API

Backend FastAPI cho hệ thống số hóa toa thuốc, xử lý OCR, xác thực người dùng, quản lý thuốc và đơn thuốc.

## Tính năng chính

- Đăng ký / đăng nhập / reset mật khẩu
- OCR ảnh toa thuốc bằng Tesseract
- Trích xuất thuốc, số lượng, hướng dẫn dùng
- Quản lý đơn thuốc và lịch sử
- Quản lý thuốc, người dùng và role admin
- API cho Web và Mobile

## Yêu cầu

- Python 3.11+
- Tesseract OCR đã cài trên máy
- Pip và virtual environment

## Cài đặt

```bash
cd api-prescription-ocr
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements-api.txt -r requirements.txt
```

## Chạy local

```bash
uvicorn app.main:app --reload
```

- Base URL: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Link deloy: https://api-prescription-ocr-production-5155.up.railway.app/
- Health check: GET /api/v1/health

## Cấu trúc project

```text
api-prescription-ocr/
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
├── requirements.txt
├── requirements-api.txt
├── README.md
├── .gitignore
└── migrate_medicines.py
```

## Role và phân quyền

- user
- doctor
- pharmacist
- admin

## Auth flow

Response đăng nhập trả về token dạng:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "username": "doctor01",
  "role": "doctor"
}
```

Gửi token bằng header:

```http
Authorization: Bearer <jwt>
```

## Endpoint quan trọng

```text
POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/bootstrap
POST /api/v1/prescriptions/ocr
GET  /api/v1/prescriptions
GET  /api/v1/medicines
PATCH /api/v1/medicines/{id}
GET  /api/v1/admin/stats
```

## Ghi chú

- Dữ liệu dev đang lưu trong `app/database/` bằng file JSON.
- CORS cần được cập nhật phù hợp với frontend đang chạy.
- Nên thay secret JWT và cấu hình production trước khi deploy thực tế.
- Khi dùng ngrok hoặc IP LAN, cập nhật URL ở frontend/mobile tương ứng.

