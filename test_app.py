import unittest
import json
from app import app, db
from models import User, Product, Transaction, TransactionItem, Cart, CartItem

class PedasPolTestCase(unittest.TestCase):
    def setUp(self):
        # Konfigurasi aplikasi untuk testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'testing-key'
        
        self.app = app.test_client()
        
        # Inisialisasi basis data dalam memori
        with app.app_context():
            db.create_all()
            
            # Seed Akun Pengujian
            self.admin = User(username='admin_test', email='admin_test@pedaspol.com', role='admin')
            self.admin.set_password('admin123')
            
            self.customer = User(username='budi_test', email='budi_test@pedaspol.com', role='customer')
            self.customer.set_password('customer123')
            
            # Seed Produk Pengujian
            self.basreng = Product(
                name='Basreng Level 5 Test',
                price=15000.0,
                stock=10,
                category='Basreng',
                spicy_level=5,
                description='Basreng test description'
            )
            
            db.session.add(self.admin)
            db.session.add(self.customer)
            db.session.add(self.basreng)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # 1. PENGUJIAN AUTENTIKASI (LOGIN & REGISTER)
    def test_user_registration(self):
        # Kirim data registrasi baru
        response = self.app.post('/register', data={
            'username': 'kasir_test',
            'email': 'kasir_test@pedaspol.com',
            'role': 'cashier',
            'password': 'kasirpassword',
            'confirm_password': 'kasirpassword'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi bahwa akun sudah ada di database dengan role customer (keamanan)
        with app.app_context():
            user = User.query.filter_by(email='kasir_test@pedaspol.com').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.username, 'kasir_test')
            self.assertEqual(user.role, 'customer')

    def test_user_login_success(self):
        # Lakukan login dengan username dan password yang benar
        response = self.app.post('/login', data={
            'username': 'budi_test',
            'password': 'customer123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi session lewat simulasi request dashboard
        with self.app as c:
            with c.session_transaction() as sess:
                self.assertEqual(sess['user_role'], 'customer')
                self.assertEqual(sess['username'], 'budi_test')

    def test_user_login_fail(self):
        # Lakukan login dengan password yang salah
        response = self.app.post('/login', data={
            'username': 'budi_test',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        # Session user_id tidak boleh terisi
        with self.app as c:
            with c.session_transaction() as sess:
                self.assertNotIn('user_id', sess)

    # 2. PENGUJIAN LOGIKA MANAJEMEN STOK
    def test_successful_checkout_deducts_stock(self):
        # Setup keranjang belanja di database
        with app.app_context():
            cart = Cart(user_id=2)
            db.session.add(cart)
            db.session.commit()
            cart_item = CartItem(cart_id=cart.id, product_id=1, quantity=2)
            db.session.add(cart_item)
            db.session.commit()

        # Login sebagai pelanggan budi_test
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 2
                sess['username'] = 'budi_test'
                sess['user_role'] = 'customer'
        
        response = self.app.post('/customer/checkout', data={
            'buyer_name': 'Budi Santoso',
            'notes': 'Pedas parah ya!'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi stok berkurang (dari 10 menjadi 8)
        with app.app_context():
            prod = Product.query.get(1)
            self.assertEqual(prod.stock, 8)
            
            # Verifikasi invoice transaksi tersimpan
            trans = Transaction.query.first()
            self.assertIsNotNone(trans)
            self.assertEqual(trans.total_price, 30000.0)
            self.assertEqual(trans.status, 'Completed')
            self.assertEqual(len(trans.items), 1)

    def test_stock_overflow_checkout_fails(self):
        # Setup keranjang belanja di database dengan 12 Basreng (stok 10)
        with app.app_context():
            cart = Cart(user_id=2)
            db.session.add(cart)
            db.session.commit()
            cart_item = CartItem(cart_id=cart.id, product_id=1, quantity=12)
            db.session.add(cart_item)
            db.session.commit()

        # Login sebagai pelanggan budi_test
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 2
                sess['username'] = 'budi_test'
                sess['user_role'] = 'customer'
        
        response = self.app.post('/customer/checkout', data={
            'buyer_name': 'Budi Santoso'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi stok TIDAK berkurang (tetap 10)
        with app.app_context():
            prod = Product.query.get(1)
            self.assertEqual(prod.stock, 10)
            
            # Verifikasi tidak ada transaksi yang tercatat
            trans_count = Transaction.query.count()
            self.assertEqual(trans_count, 0)

    def test_cancelled_transaction_restores_stock(self):
        # Set status login kasir untuk memproses pembatalan order
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'admin_test'
                sess['user_role'] = 'cashier' # kasir
                
        # Buat transaksi buatan (status: Processed, beli 3 Basreng, sisa stok 7)
        with app.app_context():
            prod = Product.query.get(1)
            prod.stock = 7
            
            trans = Transaction(
                invoice_number='INV/TEST/001',
                customer_name='Budi',
                total_price=45000.0,
                status='Processed'
            )
            db.session.add(trans)
            db.session.flush()
            
            item = TransactionItem(
                transaction_id=trans.id,
                product_id=1,
                quantity=3,
                price_at_transaction=15000.0
            )
            db.session.add(item)
            db.session.commit()
            trans_id = trans.id
            
        # Panggil route kasir untuk membatalkan pesanan (update status jadi Cancelled)
        response = self.app.get(f'/cashier/order/update/{trans_id}/Cancelled', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi stok kembali dipulihkan (dari 7 menjadi 10)
        with app.app_context():
            prod = Product.query.get(1)
            trans = Transaction.query.get(trans_id)
            self.assertEqual(prod.stock, 10)
            self.assertEqual(trans.status, 'Cancelled')

if __name__ == '__main__':
    unittest.main()
