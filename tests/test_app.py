"""Jalankan dengan: python -m unittest discover -s tests -v"""
import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash
from app import create_app, db, Product, StockMovement, User


class StockFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(self.tmp.name, "test.db").replace("\\", "/"),
        })
        with self.app.app_context():
            db.create_all()
            user = User(email="unit@example.com", name="Tester", password_hash=generate_password_hash("secret123"))
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.tmp.cleanup()

    def csrf(self):
        with self.client.session_transaction() as state:
            return state["csrf_token"]

    def login(self):
        self.client.get("/login")
        return self.client.post("/login", data={"email": "unit@example.com", "password": "secret123", "csrf_token": self.csrf()}, follow_redirects=True)

    def add_product(self, *, sku="SKU-001", stock=10):
        return self.client.post("/products/new", data={
            "csrf_token": self.csrf(), "sku": sku, "name": "Knalpot Racing", "category": "Knalpot", "price": "250000", "stock": str(stock), "min_stock": "5"
        }, follow_redirects=True)

    def test_dashboard_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_login_and_dashboard(self):
        response = self.login()
        self.assertIn(b"Selamat datang", response.data)
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_cannot_login(self):
        self.client.get("/login")
        response = self.client.post("/login", data={"email": "unit@example.com", "password": "wrong", "csrf_token": self.csrf()})
        self.assertIn(b"tidak sesuai", response.data)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_new_product_and_initial_movement(self):
        self.login()
        response = self.add_product(stock=12)
        self.assertIn(b"berhasil ditambahkan", response.data)
        with self.app.app_context():
            product = Product.query.filter_by(sku="SKU-001").first()
            self.assertEqual(product.stock, 12)
            self.assertEqual(StockMovement.query.filter_by(product_id=product.id).count(), 1)

    def test_duplicate_sku_rejected(self):
        self.login()
        self.add_product()
        response = self.add_product()
        self.assertIn(b"sudah digunakan", response.data)
        with self.app.app_context():
            self.assertEqual(Product.query.count(), 1)

    def test_stock_in_and_out(self):
        self.login()
        self.add_product(stock=10)
        with self.app.app_context():
            p = Product.query.first()
            product_id = p.id
        self.client.post("/stock/in", data={"csrf_token": self.csrf(), "product_id": str(product_id), "quantity": "5", "note": "Restock"})
        self.client.post("/stock/out", data={"csrf_token": self.csrf(), "product_id": str(product_id), "quantity": "3", "note": "Terjual"})
        with self.app.app_context():
            p = db.session.get(Product, product_id)
            self.assertEqual(p.stock, 12)
            self.assertEqual(StockMovement.query.filter_by(product_id=product_id).count(), 3)

    def test_cannot_take_more_than_available_stock(self):
        self.login()
        self.add_product(stock=3)
        with self.app.app_context():
            product_id = Product.query.first().id
        result = self.client.post("/stock/out", data={"csrf_token": self.csrf(), "product_id": str(product_id), "quantity": "99"})
        self.assertIn(b"tidak mencukupi", result.data)
        with self.app.app_context():
            self.assertEqual(db.session.get(Product, product_id).stock, 3)
            self.assertEqual(StockMovement.query.count(), 1)

    def test_invalid_quantity_is_rejected(self):
        self.login()
        self.add_product(stock=5)
        with self.app.app_context():
            product_id = Product.query.first().id
        result = self.client.post("/stock/out", data={"csrf_token": self.csrf(), "product_id": str(product_id), "quantity": "-1"})
        self.assertIn(b"minimal 1", result.data)

    def test_archive_preserves_history(self):
        self.login()
        self.add_product(stock=10)
        with self.app.app_context():
            product_id = Product.query.first().id
        self.client.post(f"/products/{product_id}/archive", data={"csrf_token": self.csrf()})
        with self.app.app_context():
            self.assertFalse(db.session.get(Product, product_id).active)
            self.assertEqual(StockMovement.query.count(), 1)
        self.assertNotIn(b"Knalpot Racing", self.client.get("/products").data)

    def test_csrf_is_required(self):
        self.login()
        response = self.client.post("/products/new", data={"sku": "INVALID"})
        self.assertEqual(response.status_code, 400)

    def test_csv_export(self):
        self.login()
        self.add_product()
        response = self.client.get("/movements/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"text/csv", response.content_type.encode())
        self.assertIn(b"SKU-001", response.data)

    def test_filter_products(self):
        self.login()
        self.add_product(stock=2)
        self.add_product(sku="SKU-002", stock=20)
        response = self.client.get("/products?status=low")
        self.assertIn(b"SKU-001", response.data)
        self.assertNotIn(b"SKU-002", response.data)


if __name__ == "__main__":
    unittest.main()
