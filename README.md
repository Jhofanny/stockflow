# StockFlow 📦 — Inventory Management System

Aplikasi **manajemen stok barang** dengan desain dashboard SaaS modern. Dibangun untuk portofolio **Junior Python / Backend Developer**.

**Stack:** Python, Flask, Flask-SQLAlchemy, SQLite (lokal), PostgreSQL (production), HTML, CSS, JavaScript, Chart.js.

## Fitur

- Login menggunakan akun demo (password disimpan sebagai hash)
- Dashboard: total produk, total stok, stok menipis, transaksi, grafik 14 hari, komposisi kategori
- CRUD produk (tambah, lihat, ubah, arsipkan; arsip tidak menghapus riwayat)
- Pencarian berdasarkan nama/SKU, filter kategori dan status stok, pagination
- Stok masuk dan stok keluar dengan validasi supaya stok tidak negatif
- Riwayat transaksi serta ekspor CSV
- Ringkasan nilai inventaris dan kategori
- Dark mode, sidebar mobile, tampilan responsif, konfirmasi arsip
- Proteksi CSRF pada seluruh form POST, pembatasan input, dan filter berdasarkan pemilik data
- 12 automated tests dengan unittest

> **Catatan:** Proyek ini adalah aplikasi portofolio dengan akun demo bersama. Jangan simpan data bisnis pribadi/rahasia di instalasi publik. Belum ditujukan sebagai sistem multi-tenant atau aplikasi produksi bisnis.

## Jalankan di Windows — VS Code + PowerShell

Buka terminal dari folder yang berisi `app.py`, **bukan dari folder induk**.

```powershell
cd "F:\Project Jho\stockflow"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app run --debug
```

Buka http://127.0.0.1:5000 . Jika PowerShell memblokir aktivasi, buka terminal **Command Prompt** lalu jalankan `.venv\Scripts\activate.bat`.

Untuk Python di beberapa Windows, gunakan `py` sebagai pengganti `python` saat membuat virtual environment.

### Akun demo

- Email: `demo@stockflow.local`
- Password: `Demo12345!`

Akun dan data contoh dibuat oleh `init-db`. Perintah `init-db` aman dijalankan lagi dan **tidak menghapus data lama**. Untuk database kosong tanpa demo, gunakan `python -m flask --app app init-db --no-seed`.

## Jalankan pengujian

```powershell
python -m unittest discover -s tests -v
```

Tes menggunakan database SQLite sementara, tidak memakai database personal kamu.

## Struktur proyek

```text
stockflow/
├── app.py                # Models, routes, auth, logika stok, perintah init-db
├── templates/            # Halaman Jinja2 (HTML)
├── static/css/style.css  # Desain modern & responsive
├── static/js/main.js     # Sidebar, dark mode, grafik, interaksi
├── static/img/logo.svg   # Logo StockFlow
├── tests/test_app.py     # Pengujian otomatis
├── start.sh              # Startup hosting online
├── render.yaml           # Konfigurasi Render
├── requirements.txt      # Dependensi Python
├── .env.example          # Contoh variabel lingkungan (tanpa rahasia)
├── .gitignore            # File yang tidak dikirim ke GitHub
└── PANDUAN_BELAJAR.md    # Tutorial tahap demi tahap
```

## Deploy demo online — Render + PostgreSQL (Neon)

**SQLite lokal tidak boleh dipakai untuk data permanen di hosting gratis Render** karena disk bisa reset.

1. Uji aplikasi di laptop. Jalankan semua pengujian.
2. Buat repository GitHub `stockflow`, pastikan `.env`, `instance/`, `.venv/` **tidak ikut di-commit**.
3. Buat database PostgreSQL di [Neon](https://neon.com/). Salin connection string PostgreSQL dengan SSL.
4. Buka [Render](https://dashboard.render.com/), pilih **New → Web Service**, hubungkan repository GitHub.
5. Gunakan `Python 3`, build command `pip install -r requirements.txt`, start command `sh start.sh` (atau deploy menggunakan `render.yaml`).
6. Tambahkan Environment Variables:
   - `DATABASE_URL`: connection string database PostgreSQL dari Neon. Jangan bagikan atau simpan di GitHub.
   - `SECRET_KEY`: string panjang acak (contoh buat dengan `python -c "import secrets; print(secrets.token_hex(32))"`).
7. Deploy. Script `start.sh` membuat tabel & data contoh jika akun demo belum ada, lalu menjalankan Gunicorn.
8. Buka URL publik Render, masuk dengan akun demo, coba fitur, kemudian tambahkan URL ke README dan CV.

**Perhatian:** Paket gratis Render bisa tidur ketika tidak aktif sehingga membuka pertama kali lebih lambat. Pada mode demo publik, siapa pun yang mengetahui akun demo bisa mengubah data bersama. Gunakan data fiktif dan siapkan reset melalui database jika diperlukan. Tidak ada halaman registrasi publik. Untuk skala produksi, tambahkan migrations, manajemen akses, hardening, dan monitoring.

## Upload ke GitHub

Dari folder `stockflow`:

```powershell
git init -b main
git status
git add .
git status
git commit -m "Initial commit: StockFlow inventory dashboard"
git remote add origin https://github.com/USERNAME/stockflow.git
git push -u origin main
```

Ganti `USERNAME` dengan username GitHub sendiri. Jangan melakukan `git init` di folder induk seperti `F:\Project Jho`.

## Ide pengembangan lanjutan

- Upload foto produk, barcode/SKU scanner, dashboard analitik bulanan
- Akses multi-user/role admin-staf, reset data demo otomatis
- REST API terdokumentasi, migrasi Alembic, CI GitHub Actions
- Integrasi supplier, notifikasi stok minimum, purchase orders

## Catatan desain

Tampilan dibuat sendiri dengan CSS custom (font Plus Jakarta Sans), ikon Lucide, dan Chart.js. **Font, ikon, dan grafik memakai CDN**, sehingga untuk tampil sempurna memerlukan koneksi internet. Fungsionalitas inti server tetap tersedia tanpa CDN.

## Portofolio (contoh setelah dipublikasikan)

**StockFlow — Inventory Management System**  
Built a responsive inventory management web application using Python, Flask, and PostgreSQL, implementing product management, transactional stock updates, dashboard analytics, CSV reporting, and automated tests.

## Referensi visual

![Konsep UI StockFlow](docs/design-reference.png)

*Gambar di atas merupakan **mockup desain awal** (ilustrasi), bukan screenshot aktual dari aplikasi. Angka dalam mockup adalah data fiktif.*
