# Panduan Belajar StockFlow dari Nol (Bahasa Indonesia)

## Target belajar

Setelah mempelajari StockFlow, kamu bisa menjelaskan alur request Flask → query database → template HTML → browser, serta cara menguji dan men-deploy aplikasi.

## Pertemuan 1 — Persiapan

1. Ekstrak ZIP ke `F:\Project Jho\stockflow`.
2. Buka **folder stockflow** melalui File → Open Folder di VS Code.
3. Terminal → New Terminal, lalu jalankan perintah ini:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app run --debug
```

4. Buka `http://127.0.0.1:5000`. Login dengan `demo@stockflow.local` / `Demo12345!`.
5. `-m` artinya menjalankan modul Python, `--app app` artinya mengambil Flask dari `app.py`, `init-db` membuat tabel & data demo.

## Pertemuan 2 — Memahami arsitektur

- `app.py`: tempat model SQLAlchemy, route URL, logika bisnis, dan perintah CLI.
- `templates/base.html`: layout bersama (sidebar, navbar, footer).
- `templates/dashboard.html`: isi dashboard, mengganti `{% block content %}` di base.
- `static/css/style.css`: warna, layout, responsive design, dark mode.
- `static/js/main.js`: grafik dan interaksi browser.
- Database SQLite disimpan di `instance/stockflow.db` dan tidak dikirim ke GitHub.

Baca baris `app = create_app()` di bawah `app.py`. `create_app()` menyiapkan aplikasi dan route. Alurnya:

`browser → Flask route → database → render_template() → HTML → browser`

Latihan: ubah tulisan “Selamat datang” di `dashboard.html`, simpan, refresh browser, lihat hasilnya.

## Pertemuan 3 — Mengenal database dan model

Di `app.py`, terdapat tiga model:

- `User`: id, email, nama, hash password.
- `Product`: id, pemilik, SKU, nama, kategori, harga, stok, stok minimum, status aktif.
- `StockMovement`: transaksi stok (produk, masuk/keluar, jumlah, stok sebelum/sesudah, catatan).

Setiap model SQLAlchemy menjadi tabel dalam SQLite/PostgreSQL ketika `db.create_all()` dijalankan.

Penting: **tidak menyimpan password dalam bentuk teks biasa**. `generate_password_hash()` membuat hash, `check_password_hash()` memeriksa password.

Latihan: buka menu Produk dan identifikasi data yang berasal dari tabel `Product`.

## Pertemuan 4 — CRUD Produk

- Create: route `POST /products/new`.
- Read: route `GET /products`.
- Update: route `POST /products/<id>/edit`.
- Archive: route `POST /products/<id>/archive` (soft-delete agar transaksi tetap tersimpan).

Perhatikan `product_form_values()` untuk validasi nama/SKU/kategori, harga, stok, dan batas minimum. Input angka diproses oleh `parse_nonnegative()`.

Latihan: buat produk `Knalpot Titanium`, SKU `KNP-TTN`, harga `2400000`, stok awal `6`, minimum `3`. Lihat di halaman Produk.

## Pertemuan 5 — Logika Stok

Route `GET/POST /stock/in` dan `/stock/out`:

1. Periksa login dan token CSRF.
2. Validasi produk, jumlah > 0, dan catatan.
3. Gunakan `UPDATE ... SET stock = stock ± jumlah` pada transaksi database.
4. Stok keluar memakai kondisi `stock >= jumlah` supaya jumlah tidak negatif.
5. Tambahkan `StockMovement` untuk menyimpan jejak audit.
6. `db.session.commit()` menyimpan perubahan stok dan log sebagai satu transaksi.

Latihan: stok awal 6 → masuk 10 → keluar 4 → hasil stok 12. Coba stok keluar 99, pastikan ditolak.

## Pertemuan 6 — UI/UX Modern

- `:root` di CSS: CSS variables untuk warna & background.
- `.sidebar`: navigasi desktop, `.sidebar.open`: navigasi ponsel.
- `.kpi-grid`: tata letak kartu statistik.
- `.dashboard-grid`: grafik + tabel dengan CSS Grid.
- `@media`: ukuran layar berbeda agar tetap rapi di HP.
- Tombol Dark Mode: menambah/menghapus class `.dark` di elemen `<html>`.
- Form: label jelas, error message, status badge, dan konfirmasi sebelum mengarsipkan.

Latihan: ubah `--primary: #4f46e5` menjadi warna favorit, refresh browser.

## Pertemuan 7 — Testing

```powershell
python -m unittest discover -s tests -v
```

Tes mencakup login, tambah produk, SKU duplikat, perubahan stok, penolakan stok negatif, validasi input, arsip produk, CSRF, ekspor CSV, dan filter produk. Unit test menggunakan database sementara agar data demo tidak berubah.

- `ok`: lolos.
- `FAIL`: hasil tidak sama seperti harapan.
- `ERROR`: terjadi exception saat menjalankan tes.

## Pertemuan 8 — GitHub & Deploy

Lihat `README.md` bagian GitHub dan Render + Neon. Sebelum upload, pastikan file rahasia (`.env`, database, `.venv`) terabaikan.

```powershell
git status
git add .
git status
git commit -m "Initial commit: StockFlow"
```

Setelah repo dibuat dan remote dikonfigurasi, lakukan `git push -u origin main`.

Saat hosting, gunakan PostgreSQL di Neon dan set `DATABASE_URL` serta `SECRET_KEY` di Render. Start command `sh start.sh` akan memanggil `init-db` lalu Gunicorn.

## Istilah untuk wawancara

- **CRUD**: create, read, update, delete/arsip.
- **ORM**: object relational mapper, menyederhanakan operasi SQL lewat objek Python.
- **CSRF**: serangan yang mencoba mengirim form dari situs lain; kita validasi token acak.
- **Password hashing**: menyimpan hash satu arah, bukan teks asli.
- **Atomic transaction**: perubahan stok dan catatan audit disimpan/dibatalkan bersama.
- **Deployment**: menempatkan aplikasi di server agar bisa diakses internet.
- **Responsive design**: UI menyesuaikan perangkat pengguna.

## Catatan jujur untuk portofolio

Ini proyek belajar yang bisa dikembangkan, bukan produk keamanan/ERP kelas enterprise. Sebelum mengklaim berhasil melakukan deployment dan testing di CV, jalankan tes di PC dan cek semua fitur pada URL live.
