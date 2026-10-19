# Oran AI — ผู้ช่วยตอบคำถามจากเอกสารองค์กร

พนักงานล็อกอินด้วยบัญชี Google (หรือชื่อผู้ใช้/รหัสผ่าน) แล้วถามคำถามเกี่ยวกับระเบียบและข้อมูลบริษัท AI จะตอบจากเอกสารในโฟลเดอร์ `docs/` พร้อมบอกแหล่งอ้างอิง ส่วนแอดมินจะเห็นหน้า Dashboard แสดงสถิติและประวัติการใช้งาน

**ค่าใช้จ่าย: 0 บาท** ทุกส่วนใช้บริการฟรี

| ส่วน | บริการ | โควตาฟรี |
|---|---|---|
| โฮสต์เว็บ | Streamlit Community Cloud | ฟรี (แอปจะ sleep เมื่อไม่มีคนใช้นาน กดปลุกได้) |
| AI ตอบคำถาม | Groq `llama-3.3-70b-versatile` | ~1,000 คำถาม/วัน เกินแล้วสลับไป `llama-3.1-8b-instant` (~14,400/วัน) อัตโนมัติ |
| ค้นหาเอกสาร | `multilingual-e5-small` (รันในแอปเอง) | ไม่จำกัด |
| เก็บประวัติแชท | Google Sheets | ฟรี |

## เพิ่ม/แก้ไขเอกสาร
อัปโหลดไฟล์ลงโฟลเดอร์ `docs/` ใน GitHub (รองรับ PDF, DOCX, TXT, MD, CSV, XLSX) แล้วแอปจะสร้างฐานความรู้ใหม่ให้อัตโนมัติ

- ⚠️ **ห้ามใส่ไฟล์ที่มีรหัสผ่านหรือข้อมูลลับ** เพราะพนักงานทุกคนจะถาม AI ได้
- ถ้า PDF ภาษาไทยอ่านแล้วตัวอักษรเพี้ยน ให้ใช้ไฟล์ .docx ต้นฉบับแทน

## ตั้งค่า (ทำครั้งเดียว)

### 1. Groq API key (ฟรี)
สมัครที่ https://console.groq.com/keys แล้วสร้าง key

### 2. Google Sheets สำหรับเก็บประวัติถาวร (ฟรี, แนะนำ)
1. เข้า https://console.cloud.google.com → สร้าง Project ใหม่
2. ไปที่ APIs & Services → Library → เปิดใช้ **Google Sheets API** และ **Google Drive API**
3. ไปที่ IAM & Admin → Service Accounts → Create → เข้าไปที่ Keys → Add key → JSON (ไฟล์จะดาวน์โหลดลงเครื่อง)
4. สร้าง Google Sheet เปล่า แล้วกด **Share** ให้อีเมล `client_email` ที่อยู่ในไฟล์ JSON โดยตั้งสิทธิ์เป็น **Editor**
5. นำค่าจากไฟล์ JSON ไปใส่ใน Secrets ใต้หัวข้อ `[gcp_service_account]` และใส่ลิงก์ชีตใน `GSHEET_URL`

ถ้าข้ามขั้นตอนนี้ แอปจะเก็บประวัติเป็นไฟล์ชั่วคราว ซึ่งจะหายเมื่อแอปรีสตาร์ท

### 3. Sign in with Google (ฟรี)
1. เข้า https://console.cloud.google.com แล้วใช้ Project เดียวกับข้อ 2 ได้
2. ไปที่ **APIs & Services → OAuth consent screen**
   - ถ้าบริษัทใช้ Google Workspace ให้เลือก **Internal** (จะล็อกอินได้เฉพาะอีเมลบริษัทเท่านั้น)
   - ถ้าไม่ใช่ ให้เลือก **External** แล้วกด **Publish app** ไม่ต้องส่งให้ Google ตรวจสอบ เพราะใช้แค่สิทธิ์อ่านอีเมลและชื่อ
3. ไปที่ **Credentials → Create credentials → OAuth client ID** แล้วเลือก **Web application**
   - ช่อง **Authorized redirect URIs** ให้ใส่ `https://<ชื่อแอป>.streamlit.app/oauth2callback`
4. คัดลอก **Client ID** และ **Client secret** ไปใส่ใน Secrets ใต้หัวข้อ `[auth]` (ดูตัวอย่างใน `secrets.toml.example`)
   - `redirect_uri` ต้องตรงกับที่กรอกในข้อ 3 ทุกตัวอักษร
   - `cookie_secret` คือข้อความสุ่มยาวๆ ตั้งเองได้เลย
5. กำหนดว่าใครเข้าใช้งานได้
   - `ALLOWED_DOMAINS = ["areetechnology.com"]` อนุญาตทุกคนที่ใช้อีเมลบริษัท
   - `ALLOWED_EMAILS` เพิ่ม Gmail ส่วนตัวเป็นรายคน
   - `ADMIN_USERS` ใส่อีเมลของคนที่จะเห็นหน้า Dashboard

ถ้ายังมีหัวข้อ `[passwords]` อยู่ ระบบจะยังให้ล็อกอินด้วยชื่อผู้ใช้และรหัสผ่านได้ด้วย ถ้าต้องการให้ใช้ Google อย่างเดียว ให้ลบหัวข้อนี้ทิ้ง

### 4. Secrets บน Streamlit Cloud
ไปที่แอปของคุณ → ⋮ → **Settings → Secrets** แล้ววางค่าตามตัวอย่างในไฟล์ `.streamlit/secrets.toml.example` (ใส่ API key, ค่า Google sign-in, รายชื่อแอดมิน และค่า Google Sheets)

### 5. ความปลอดภัย
- ตั้ง repo เป็น **Private** เพราะเอกสารบริษัทอยู่ใน repo นี้
- ห้าม commit ไฟล์ `secrets.toml` หรือไฟล์ JSON ของ service account เด็ดขาด

## รันบนเครื่องตัวเอง
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # แล้วแก้ค่า
streamlit run app.py
```

## โครงสร้างไฟล์
| ไฟล์ | หน้าที่ |
|---|---|
| `app.py` | หน้าจอ ล็อกอิน, แชท, Admin Dashboard |
| `rag.py` | อ่านเอกสาร, ค้นหา, เรียก AI |
| `storage.py` | บันทึก/โหลดประวัติแชท (Google Sheets หรือ CSV) |
| `styles.py` | CSS ธีม |
| `assets.py` | รูปโลโก้และแอนิเมชัน |
| `docs/` | เอกสารความรู้ขององค์กร |
