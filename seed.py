import datetime
from flask import Flask
from models import db, User, Product, Transaction, TransactionItem
from config import Config

def seed_database():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        # Drop all tables and recreate them to ensure a fresh start
        db.drop_all()
        db.create_all()
        print("Tabel basis data berhasil dibuat!")
        
        # 1. Tambah Akun Pengguna
        users = [
            {'username': 'admin', 'email': 'admin@nabzsnack.com', 'role': 'admin', 'password': 'admin123'},
            {'username': 'kasir', 'email': 'kasir@nabzsnack.com', 'role': 'cashier', 'password': 'kasir123'},
            {'username': 'pelanggan', 'email': 'pelanggan@nabzsnack.com', 'role': 'customer', 'password': 'pelanggan123'}
        ]
        
        seeded_users = {}
        for u_data in users:
            user = User(
                username=u_data['username'],
                email=u_data['email'],
                role=u_data['role']
            )
            user.set_password(u_data['password'])
            db.session.add(user)
            seeded_users[u_data['role']] = user
            
        # Simpan user agar ID digenerate
        db.session.commit()
        print("Pengguna default berhasil dimasukkan!")

        # 2. Tambah Produk Snack Pedas
        products_data = [
            {
                'name': 'Basreng Pedas Gila (Level 5)',
                'price': 15000.0,
                'stock': 45,
                'category': 'Basreng',
                'spicy_level': 5,
                'image_url': '/static/images/basreng_pedas.png',
                'description': 'Bakso goreng renyah yang diiris tipis dengan taburan cabai rawit kering asli melimpah. Pedasnya nendang banget!'
            },
            {
                'name': 'Makaroni Pedas Manis (Level 3)',
                'price': 10000.0,
                'stock': 60,
                'category': 'Makaroni',
                'spicy_level': 3,
                'image_url': '/static/images/makaroni_pedas.png',
                'description': 'Makaroni goreng renyah bumbu cabai merah pedas berpadu dengan manis gurih gula karamel alami.'
            },
            {
                'name': 'Keripik Singkong Setan (Level 4)',
                'price': 12000.0,
                'stock': 35,
                'category': 'Keripik',
                'spicy_level': 4,
                'image_url': '/static/images/keripik_singkong.png',
                'description': 'Keripik singkong tipis renyah dibalut dengan ulekan bumbu cabai rawit setan basah khas Bandung.'
            },
            {
                'name': 'Seblak Kering Daun Jeruk (Level 3)',
                'price': 13000.0,
                'stock': 40,
                'category': 'Seblak',
                'spicy_level': 3,
                'image_url': '/static/images/seblak_kering.png',
                'description': 'Kerupuk seblak bantat gurih pedas dengan aroma wangi kencur dan kesegaran daun jeruk purut pilihan.'
            },
            {
                'name': 'Pilus Cikur Pedas (Level 1)',
                'price': 8000.0,
                'stock': 75,
                'category': 'Pilus',
                'spicy_level': 1,
                'image_url': '/static/images/pilus_pedas.png',
                'description': 'Pilus bulat renyah rasa kencur gurih dengan taburan bubuk cabai tipis yang ramah di lambung.'
            },
            {
                'name': 'Usus Goreng Pedas Daun Jeruk (Level 4)',
                'price': 16000.0,
                'stock': 25,
                'category': 'Usus',
                'spicy_level': 4,
                'image_url': '/static/images/usus_pedas.png',
                'description': 'Usus ayam bersih digoreng garing renyah tidak berminyak, dibalut bumbu cabai pedas harum daun jeruk.'
            },
            {
                'name': 'Mie Lidi Bumbu Balado (Level 2)',
                'price': 8000.0,
                'stock': 80,
                'category': 'Lainnya',
                'spicy_level': 2,
                'image_url': '/static/images/mie_lidi_balado.png',
                'description': 'Mie lidi renyah nostalgia dengan bumbu balado gurih manis dan tingkat kepedasan sedang.'
            },
            {
                'name': 'Cimol Kering Pedas (Level 3)',
                'price': 14000.0,
                'stock': 30,
                'category': 'Lainnya',
                'spicy_level': 3,
                'image_url': '/static/images/cimol_pedas.png',
                'description': 'Cimol digoreng kering hingga bantat renyah, dibalur dengan cabai bubuk asli dan rempah gurih khas Bandung.'
            },
            {
                'name': 'Kripik Kaca Cabe Merah (Level 5)',
                'price': 11000.0,
                'stock': 50,
                'category': 'Keripik',
                'spicy_level': 5,
                'image_url': '/static/images/kripik_kaca.png',
                'description': 'Keripik singkong super tipis sebening kaca dengan bumbu cabe merah basah super pedas.'
            },
            {
                'name': 'Pilus Cikur Ekstra Pedas (Level 4)',
                'price': 9000.0,
                'stock': 65,
                'category': 'Pilus',
                'spicy_level': 4,
                'image_url': '/static/images/pilus_ekstra_pedas.png',
                'description': 'Versi pedas nendang dari Pilus Cikur biasa. Renyah, wangi kencur, dan cabainya sangat menyengat!'
            }
        ]
        
        seeded_products = []
        for p_data in products_data:
            prod = Product(
                name=p_data['name'],
                price=p_data['price'],
                stock=p_data['stock'],
                category=p_data['category'],
                spicy_level=p_data['spicy_level'],
                image_url=p_data['image_url'],
                description=p_data['description']
            )
            db.session.add(prod)
            seeded_products.append(prod)
            
        db.session.commit()
        print("Produk default berhasil dimasukkan!")

        # 3. Tambah Riwayat Transaksi Sampel (Untuk visualisasi grafik)
        # Kita buat transaksi sampel di 3 bulan terakhir (Maret, April, Mei 2026)
        today = datetime.datetime.now()
        
        # Transaksi 1: Maret 2026 (Completed)
        t1 = Transaction(
            invoice_number='INV/20260315/001',
            customer_name='Budi Santoso',
            customer_id=seeded_users['customer'].id,
            total_price=40000.0,
            status='Completed',
            notes='Kirim sore hari ya.',
            created_at=datetime.datetime(2026, 3, 15, 14, 30)
        )
        db.session.add(t1)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=t1.id, product_id=seeded_products[0].id, quantity=2, price_at_transaction=15000.0)) # Basreng
        db.session.add(TransactionItem(transaction_id=t1.id, product_id=seeded_products[1].id, quantity=1, price_at_transaction=10000.0)) # Makaroni
        
        # Transaksi 2: April 2026 (Completed)
        t2 = Transaction(
            invoice_number='INV/20260410/002',
            customer_name='Siti Rahmawati',
            total_price=57000.0,
            status='Completed',
            notes='Beli langsung di toko (POS Kasir)',
            cashier_id=seeded_users['cashier'].id,
            created_at=datetime.datetime(2026, 4, 10, 11, 15)
        )
        db.session.add(t2)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=t2.id, product_id=seeded_products[2].id, quantity=3, price_at_transaction=12000.0)) # Keripik Singkong
        db.session.add(TransactionItem(transaction_id=t2.id, product_id=seeded_products[5].id, quantity=1, price_at_transaction=16000.0)) # Usus
        db.session.add(TransactionItem(transaction_id=t2.id, product_id=seeded_products[4].id, quantity=1, price_at_transaction=5000.0)) # Pilus (diskon promo)

        # Transaksi 3: Mei 2026 (Completed)
        t3 = Transaction(
            invoice_number='INV/20260520/003',
            customer_name='Rian Hidayat',
            customer_id=seeded_users['customer'].id,
            total_price=41000.0,
            status='Completed',
            created_at=datetime.datetime(2026, 5, 20, 19, 45)
        )
        db.session.add(t3)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=t3.id, product_id=seeded_products[0].id, quantity=1, price_at_transaction=15000.0)) # Basreng
        db.session.add(TransactionItem(transaction_id=t3.id, product_id=seeded_products[3].id, quantity=2, price_at_transaction=13000.0)) # Seblak
        
        # Transaksi 4: Hari Ini (Completed - dari customer)
        t4 = Transaction(
            invoice_number='INV/20260529/004',
            customer_name='Ahmad Dahlan',
            customer_id=seeded_users['customer'].id,
            total_price=26000.0,
            status='Completed',
            created_at=today - datetime.timedelta(hours=3)
        )
        db.session.add(t4)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=t4.id, product_id=seeded_products[3].id, quantity=2, price_at_transaction=13000.0)) # Seblak
        
        # Transaksi 5: Hari Ini (Completed - Kasir)
        t5 = Transaction(
            invoice_number='INV/20260529/005',
            customer_name='Pelanggan Umum',
            total_price=30000.0,
            status='Completed',
            cashier_id=seeded_users['cashier'].id,
            created_at=today - datetime.timedelta(minutes=45)
        )
        db.session.add(t5)
        db.session.flush()
        db.session.add(TransactionItem(transaction_id=t5.id, product_id=seeded_products[1].id, quantity=3, price_at_transaction=10000.0)) # Makaroni
        
        db.session.commit()
        print("Transaksi sampel berhasil dimasukkan!")
        print("Database Seeding Selesai dengan Sukses!")

if __name__ == '__main__':
    seed_database()
