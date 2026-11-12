"""StockFlow — aplikasi inventaris Flask, SQLite/PostgreSQL.

Jalankan:
    flask --app app init-db
    flask --app app run --debug
"""
from __future__ import annotations

import csv
import hmac
import io
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import click
from flask import (
    Flask, abort, flash, g, redirect, render_template, request, Response,
    session, url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    sku = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="Lainnya")
    price = db.Column(db.Integer, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    min_stock = db.Column(db.Integer, nullable=False, default=5)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "sku", name="uq_owner_sku"),)

    @property
    def low_stock(self):
        return self.stock <= self.min_stock


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # in atau out
    quantity = db.Column(db.Integer, nullable=False)
    before_stock = db.Column(db.Integer, nullable=False)
    after_stock = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(250), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    product = db.relationship("Product", lazy="joined")


def rupiah(value):
    return "Rp " + f"{int(value or 0):,}".replace(",", ".")


def parse_nonnegative(value: str | None, label: str, *, minimum: int = 0) -> int:
    try:
        if value is None or not str(value).strip() or any(c in str(value) for c in (".", ",", "e", "E")):
            raise ValueError
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} harus berupa angka bulat.") from None
    if number < minimum:
        raise ValueError(f"{label} minimal {minimum}.")
    if number > 1_000_000_000:
        raise ValueError(f"{label} terlalu besar.")
    return number


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db_url = os.getenv("DATABASE_URL", "sqlite:///" + str(Path(app.instance_path) / "stockflow.db").replace("\\", "/"))
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if os.getenv("RENDER") and not os.getenv("SECRET_KEY"):
        raise RuntimeError("Atur environment variable SECRET_KEY sebelum deploy.")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "LOCAL-DEV-ONLY-change-me-before-deploy"),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    app.jinja_env.filters["rupiah"] = rupiah

    def current_user():
        if "current_user" not in g:
            g.current_user = db.session.get(User, session["user_id"]) if session.get("user_id") else None
        return g.current_user

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user() is None:
                flash("Silakan masuk terlebih dahulu.", "warning")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    def own_product(product_id: int, *, include_archived=False):
        query = Product.query.filter_by(id=product_id, user_id=current_user().id)
        if not include_archived:
            query = query.filter_by(active=True)
        return query.first_or_404()

    @app.before_request
    def csrf_and_user():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            submitted = request.form.get("csrf_token", "")
            if not hmac.compare_digest(session["csrf_token"], submitted):
                abort(400, description="Token keamanan tidak valid. Segarkan halaman dan ulangi.")

    @app.context_processor
    def inject_globals():
        return {"user": current_user(), "csrf_token": session.get("csrf_token", ""), "now": datetime.now(), "app_name": "StockFlow"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user() is not None:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            account = User.query.filter_by(email=email).first()
            if account and check_password_hash(account.password_hash, password):
                session.clear()
                session["user_id"] = account.id
                session["csrf_token"] = secrets.token_urlsafe(32)
                session.permanent = True
                flash("Selamat datang kembali!", "success")
                return redirect(url_for("dashboard"))
            flash("Email atau password tidak sesuai.", "danger")
        return render_template("login.html", title="Masuk")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("Kamu telah keluar dari StockFlow.", "success")
        return redirect(url_for("login"))

    def owner_products():
        return Product.query.filter_by(user_id=current_user().id, active=True)

    def owner_movements():
        return StockMovement.query.filter_by(user_id=current_user().id)

    @app.get("/")
    @login_required
    def dashboard():
        products = owner_products().all()
        product_ids = {p.id for p in products}
        movements = owner_movements().order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).all()
        cutoff = datetime.utcnow() - timedelta(days=30)
        month_count = sum(m.created_at >= cutoff for m in movements)
        low = sorted((p for p in products if p.low_stock), key=lambda p: (p.stock - p.min_stock, p.name))[:5]
        counts = {"products": len(products), "stock": sum(p.stock for p in products), "low": sum(p.low_stock for p in products), "transactions": month_count}
        chart_dates = [(datetime.utcnow().date() - timedelta(days=x)) for x in range(13, -1, -1)]
        incoming, outgoing = [], []
        for day in chart_dates:
            incoming.append(sum(m.quantity for m in movements if m.kind == "in" and m.created_at.date() == day and m.product_id in product_ids))
            outgoing.append(sum(m.quantity for m in movements if m.kind == "out" and m.created_at.date() == day and m.product_id in product_ids))
        categories = {}
        for p in products:
            categories[p.category] = categories.get(p.category, 0) + 1
        chart = {"labels": [d.strftime("%d %b") for d in chart_dates], "incoming": incoming, "outgoing": outgoing, "categories": list(categories.keys()), "category_counts": list(categories.values())}
        return render_template("dashboard.html", title="Dashboard", active="dashboard", counts=counts, low_products=low, recent=movements[:5], chart=chart)

    @app.get("/products")
    @login_required
    def products():
        query = owner_products()
        keyword = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "").strip()[:60]
        status = request.args.get("status", "")
        if keyword:
            query = query.filter(or_(Product.name.ilike(f"%{keyword}%"), Product.sku.ilike(f"%{keyword}%")))
        if category:
            query = query.filter_by(category=category)
        if status == "low":
            query = query.filter(Product.stock <= Product.min_stock)
        elif status == "healthy":
            query = query.filter(Product.stock > Product.min_stock)
        page = request.args.get("page", 1, type=int)
        results = query.order_by(Product.created_at.desc(), Product.id.desc()).paginate(page=max(page,1), per_page=8, error_out=False)
        category_options = sorted({p.category for p in owner_products().all()})
        return render_template("products.html", title="Produk", active="products", pagination=results, keyword=keyword, category=category, status=status, category_options=category_options)

    def product_form_values(product=None):
        values = {
            "sku": request.form.get("sku", "").strip().upper(),
            "name": request.form.get("name", "").strip(),
            "category": request.form.get("category", "").strip(),
            "price": request.form.get("price", ""),
            "stock": request.form.get("stock", ""),
            "min_stock": request.form.get("min_stock", ""),
        }
        if not values["sku"] or len(values["sku"]) > 40:
            raise ValueError("Kode SKU wajib diisi (maksimal 40 karakter).")
        if not values["name"] or len(values["name"]) > 150:
            raise ValueError("Nama produk wajib diisi (maksimal 150 karakter).")
        if not values["category"] or len(values["category"]) > 60:
            raise ValueError("Kategori wajib diisi (maksimal 60 karakter).")
        values["price"] = parse_nonnegative(values["price"], "Harga")
        values["stock"] = parse_nonnegative(values["stock"], "Stok awal")
        values["min_stock"] = parse_nonnegative(values["min_stock"], "Batas minimum stok")
        return values

    @app.route("/products/new", methods=["GET", "POST"])
    @login_required
    def product_new():
        if request.method == "POST":
            try:
                values = product_form_values()
                record = Product(user_id=current_user().id, **values)
                db.session.add(record)
                db.session.flush()
                if record.stock:
                    db.session.add(StockMovement(user_id=current_user().id, product_id=record.id, kind="in", quantity=record.stock, before_stock=0, after_stock=record.stock, note="Stok awal produk"))
                db.session.commit()
                flash("Produk baru berhasil ditambahkan.", "success")
                return redirect(url_for("products"))
            except ValueError as err:
                flash(str(err), "danger")
            except IntegrityError:
                db.session.rollback()
                flash("Kode SKU sudah digunakan. Gunakan kode lain.", "danger")
        return render_template("product_form.html", title="Tambah Produk", active="products", product=None)

    @app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
    @login_required
    def product_edit(product_id):
        product = own_product(product_id)
        if request.method == "POST":
            try:
                values = product_form_values(product)
                # Perubahan jumlah stok hanya boleh dilakukan lewat menu Stok Masuk/Keluar.
                values.pop("stock")
                for key, value in values.items():
                    setattr(product, key, value)
                db.session.commit()
                flash("Perubahan produk berhasil disimpan.", "success")
                return redirect(url_for("products"))
            except ValueError as err:
                flash(str(err), "danger")
            except IntegrityError:
                db.session.rollback()
                flash("Kode SKU sudah digunakan. Gunakan kode lain.", "danger")
        return render_template("product_form.html", title="Edit Produk", active="products", product=product)

    @app.post("/products/<int:product_id>/archive")
    @login_required
    def product_archive(product_id):
        product = own_product(product_id)
        product.active = False
        db.session.commit()
        flash("Produk diarsipkan. Riwayat transaksinya tetap tersimpan.", "success")
        return redirect(url_for("products"))

    @app.route("/stock/<kind>", methods=["GET", "POST"])
    @login_required
    def stock_form(kind):
        if kind not in ("in", "out"):
            abort(404)
        available = owner_products().order_by(Product.name.asc()).all()
        default_product = request.args.get("product", type=int)
        if request.method == "POST":
            try:
                product_id = parse_nonnegative(request.form.get("product_id"), "Produk", minimum=1)
                quantity = parse_nonnegative(request.form.get("quantity"), "Jumlah", minimum=1)
                note = request.form.get("note", "").strip()
                if len(note) > 250:
                    raise ValueError("Catatan maksimal 250 karakter.")
                product = own_product(product_id)
                if kind == "out":
                    # Conditional UPDATE menjaga stok dari menjadi negatif.
                    new_stock = db.session.execute(
                        update(Product).where(Product.id == product.id, Product.user_id == current_user().id, Product.active.is_(True), Product.stock >= quantity)
                        .values(stock=Product.stock - quantity).returning(Product.stock)
                    ).scalar_one_or_none()
                    if new_stock is None:
                        db.session.rollback()
                        raise ValueError("Stok tidak mencukupi untuk transaksi ini.")
                    old_stock = new_stock + quantity
                else:
                    new_stock = db.session.execute(
                        update(Product).where(Product.id == product.id, Product.user_id == current_user().id, Product.active.is_(True))
                        .values(stock=Product.stock + quantity).returning(Product.stock)
                    ).scalar_one_or_none()
                    if new_stock is None:
                        db.session.rollback()
                        raise ValueError("Produk tidak tersedia.")
                    old_stock = new_stock - quantity
                db.session.add(StockMovement(user_id=current_user().id, product_id=product.id, kind=kind, quantity=quantity, before_stock=old_stock, after_stock=new_stock, note=note))
                db.session.commit()
                flash("Transaksi stok berhasil disimpan.", "success")
                return redirect(url_for("movements"))
            except ValueError as err:
                flash(str(err), "danger")
        return render_template("stock_form.html", title="Stok Masuk" if kind == "in" else "Stok Keluar", active="stock-in" if kind == "in" else "stock-out", kind=kind, available=available, default_product=default_product)

    @app.get("/movements")
    @login_required
    def movements():
        kind = request.args.get("kind", "")
        query = owner_movements()
        if kind in ("in", "out"):
            query = query.filter_by(kind=kind)
        page = max(request.args.get("page", 1, type=int), 1)
        results = query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template("movements.html", title="Riwayat Transaksi", active="movements", pagination=results, kind=kind)

    @app.get("/movements/export")
    @login_required
    def movements_export():
        kind = request.args.get("kind", "")
        query = owner_movements()
        if kind in ("in", "out"):
            query = query.filter_by(kind=kind)
        records = query.order_by(StockMovement.created_at.desc()).all()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Tanggal (UTC)", "SKU", "Produk", "Jenis", "Jumlah", "Stok Sebelum", "Stok Sesudah", "Catatan"])

        def csv_safe(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text

        for row in records:
            writer.writerow([row.created_at.strftime("%Y-%m-%d %H:%M"), csv_safe(row.product.sku), csv_safe(row.product.name), "Masuk" if row.kind == "in" else "Keluar", row.quantity, row.before_stock, row.after_stock, csv_safe(row.note)])
        return Response("\ufeff" + buffer.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="stockflow-transaksi.csv"'})

    @app.get("/categories")
    @login_required
    def categories():
        data = owner_products().all()
        grouped = {}
        for p in data:
            item = grouped.setdefault(p.category, {"name": p.category, "products": 0, "stock": 0, "value": 0})
            item["products"] += 1
            item["stock"] += p.stock
            item["value"] += p.stock * p.price
        return render_template("categories.html", title="Kategori Produk", active="categories", categories=sorted(grouped.values(), key=lambda a: a["name"]))

    @app.get("/reports")
    @login_required
    def reports():
        products = owner_products().all()
        movements = owner_movements().all()
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent = [m for m in movements if m.created_at >= cutoff]
        stats = {"inventory_value": sum(p.price * p.stock for p in products), "in_count": sum(m.quantity for m in recent if m.kind == "in"), "out_count": sum(m.quantity for m in recent if m.kind == "out"), "low": sum(p.low_stock for p in products)}
        top = sorted(products, key=lambda p: p.price * p.stock, reverse=True)[:6]
        return render_template("reports.html", title="Laporan", active="reports", stats=stats, top=top)

    @app.cli.command("init-db")
    @click.option("--no-seed", is_flag=True, help="Buat tabel tanpa menambah data demo.")
    def init_db(no_seed):
        """Membuat tabel dan data demo; tidak menghapus data lama."""
        db.create_all()
        if no_seed:
            click.echo("Tabel database berhasil dibuat (tanpa data demo).")
            return
        demo_email = "demo@stockflow.local"
        demo = User.query.filter_by(email=demo_email).first()
        if demo:
            click.echo("Database sudah siap. Akun demo sudah tersedia; data lama tidak dihapus.")
            return
        demo = User(name="Admin Demo", email=demo_email, password_hash=generate_password_hash("Demo12345!"))
        db.session.add(demo)
        db.session.flush()
        examples = [
            ("KNP-R9", "Knalpot Racing R9", "Knalpot", 1750000, 15, 5),
            ("SPN-CNC", "Spion CNC Universal", "Spion", 250000, 3, 5),
            ("CVR-V125", "Cover Radiator Vario 125", "Cover & Body", 180000, 4, 5),
            ("HND-RCB", "Handgrip RCB", "Aksesoris", 135000, 12, 8),
            ("LMP-LED", "Lampu LED Projie", "Elektrikal", 320000, 24, 8),
            ("BRK-CNC", "Handle Rem CNC", "Aksesoris", 175000, 9, 5),
            ("FLR-MTX", "Filter Udara Racing", "Mesin", 115000, 18, 6),
            ("KPL-VAR", "Kampas Kopling Vario", "Mesin", 290000, 7, 5),
        ]
        now = datetime.utcnow()
        for idx, (sku, name, category, price, stock, min_stock) in enumerate(examples):
            product = Product(user_id=demo.id, sku=sku, name=name, category=category, price=price, stock=stock, min_stock=min_stock, created_at=now - timedelta(days=idx + 1))
            db.session.add(product)
            db.session.flush()
            db.session.add(StockMovement(user_id=demo.id, product_id=product.id, kind="in", quantity=stock + 3, before_stock=0, after_stock=stock + 3, note="Pengadaan awal", created_at=now - timedelta(days=12 - idx)))
            db.session.add(StockMovement(user_id=demo.id, product_id=product.id, kind="out", quantity=3, before_stock=stock + 3, after_stock=stock, note="Penjualan contoh", created_at=now - timedelta(days=(idx % 7) + 1)))
        db.session.commit()
        click.echo("Database dan data demo berhasil dibuat.")
        click.echo("Login: demo@stockflow.local / Demo12345! (hanya untuk demo)")

    @app.errorhandler(400)
    def bad_request(err):
        return render_template("error.html", title="Permintaan Tidak Valid", error_code=400, message=str(err.description)), 400

    @app.errorhandler(404)
    def not_found(err):
        return render_template("error.html", title="Tidak Ditemukan", error_code=404, message="Halaman atau produk tidak ditemukan."), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
