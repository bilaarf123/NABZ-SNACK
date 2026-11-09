import json
import datetime
import random
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from config import Config
from models import db, User, Product, Transaction, TransactionItem, Cart, CartItem

app = Flask(__name__)
app.config.from_object(Config)

# Inisialisasi Database
db.init_app(app)

# Pastikan tabel selalu ada saat aplikasi pertama dijalankan
with app.app_context():
    db.create_all()

# Helper Indonesian Month Name
MONTHS_ID = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus', 
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

# ==========================================
# CONTEXT PROCESSORS & HELPERS
# ==========================================
@app.context_processor
def inject_cart_count():
    if 'user_id' in session:
        cart = Cart.query.filter_by(user_id=session['user_id']).first()
        if cart:
            total_items = sum(item.quantity for item in cart.items)
            return {'cart_count': total_items}
    return {'cart_count': 0}

# ==========================================
# DECORATORS & AUTH UTILITIES
# ==========================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'error')
                return redirect(url_for('login'))
            if session.get('user_role') not in allowed_roles and session.get('user_role') != 'admin':
                flash('Anda tidak memiliki izin (hak akses) untuk halaman ini!', 'error')
                # Redirect ke halaman beranda
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==========================================
# PUBLIC ROUTES
# ==========================================

@app.route('/')
def index():
    # Tampilkan semua produk di Landing Page agar pengunjung bisa melihat katalog
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/catalog')
def catalog():
    products = Product.query.all()
    return render_template('catalog.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/profile')
@login_required
def profile():
    user = User.query.get_or_404(session['user_id'])
    transactions = Transaction.query.filter_by(customer_id=user.id).all()
    total_spent = sum(t.total_price for t in transactions if t.status == 'Completed')
    return render_template('profile.html', user=user, transaction_count=len(transactions), total_spent=total_spent)


# ==========================================
# AUTH CONTROLLERS
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        # Redirect ke dashboard masing-masing jika sudah login
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'cashier':
            return redirect(url_for('cashier_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.role == 'admin':
                flash('Harap gunakan halaman Login Admin untuk masuk sebagai administrator.', 'error')
                return redirect(url_for('login'))
                
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            flash(f'Selamat datang kembali, {user.username}!', 'success')
            
            if user.role == 'cashier':
                return redirect(url_for('cashier_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            flash('Username atau kata sandi Anda salah!', 'error')
            
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Anda sudah login sebagai pengguna biasa.', 'error')
            return redirect(url_for('index'))
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.role != 'admin':
                flash('Akses ditolak. Halaman ini hanya untuk Administrator.', 'error')
                return redirect(url_for('admin_login'))
                
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            flash(f'Selamat datang kembali Administrator {user.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau kata sandi Admin salah!', 'error')
            
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = 'customer' # Paksa role customer untuk keamanan
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Kata sandi dan konfirmasi kata sandi tidak cocok!', 'error')
            return render_template('register.html')
            
        # Cek jika email atau username sudah terdaftar
        existing_email = User.query.filter_by(email=email).first()
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_email:
            flash('Alamat email sudah terdaftar!', 'error')
        elif existing_user:
            flash('Nama pengguna (username) sudah digunakan!', 'error')
        else:
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Pendaftaran akun berhasil! Silakan masuk.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda berhasil keluar dari sistem.', 'success')
    return redirect(url_for('index'))

def get_user_cart():
    if 'user_id' not in session:
        return None
    cart = Cart.query.filter_by(user_id=session['user_id']).first()
    if not cart:
        cart = Cart(user_id=session['user_id'])
        db.session.add(cart)
        db.session.commit()
    return cart

@app.route('/cart')
@login_required
def cart_page():
    cart = get_user_cart()
    return render_template('cart.html', cart=cart)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    if quantity > product.stock:
        flash(f'Stok tidak cukup! Hanya tersedia {product.stock} item.', 'error')
        return redirect(request.referrer or url_for('index'))

    cart = get_user_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    
    if item:
        if item.quantity + quantity > product.stock:
            flash(f'Stok tidak cukup! Hanya tersedia {product.stock} item.', 'error')
        else:
            item.quantity += quantity
            db.session.commit()
            flash(f'{product.name} berhasil ditambahkan ke keranjang.', 'success')
    else:
        new_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(new_item)
        db.session.commit()
        flash(f'{product.name} berhasil ditambahkan ke keranjang.', 'success')
        
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != session['user_id']:
        return "Unauthorized", 403
        
    quantity = int(request.form.get('quantity', 1))
    if quantity <= 0:
        db.session.delete(item)
        db.session.commit()
        flash('Produk dihapus dari keranjang.', 'success')
    elif quantity > item.product.stock:
        flash(f'Stok tidak cukup! Hanya tersedia {item.product.stock} item.', 'error')
    else:
        item.quantity = quantity
        db.session.commit()
        flash('Kuantitas berhasil diperbarui.', 'success')
        
    return redirect(url_for('cart_page'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != session['user_id']:
        return "Unauthorized", 403
        
    db.session.delete(item)
    db.session.commit()
    flash('Produk dihapus dari keranjang.', 'success')
    return redirect(url_for('cart_page'))


@app.route('/customer/dashboard')
@role_required(['customer'])
def customer_dashboard():
    products = Product.query.all()
    # Ambil riwayat pesanan milik pelanggan ini sendiri
    transactions = Transaction.query.filter_by(customer_id=session['user_id'])\
                                     .order_by(Transaction.created_at.desc()).all()
    return render_template('customer_dashboard.html', products=products, transactions=transactions)

@app.route('/customer/invoice/<int:trans_id>/download')
@login_required
def download_invoice(trans_id):
    transaction = Transaction.query.get_or_404(trans_id)
    # Verifikasi hak akses: Hanya pemilik transaksi, admin, atau kasir yang bisa download
    if session.get('user_role') not in ['admin', 'cashier'] and transaction.customer_id != session.get('user_id'):
        flash('Anda tidak memiliki akses ke invoice ini.', 'error')
        return redirect(url_for('customer_dashboard'))
    
    # Generate PDF using ReportLab
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )
    
    header_right_style = ParagraphStyle(
        'HeaderRight',
        parent=normal_style,
        alignment=2 # Right align
    )
    
    # Header Table
    header_data = [
        [
            Paragraph("<b>NABZ SNACK</b><br/>Cemilan Pilihan Alami", normal_style),
            Paragraph("<b>INVOICE</b><br/>No: {}<br/>Tanggal: {}".format(
                transaction.invoice_number,
                transaction.created_at.strftime('%d %B %Y %H:%M')
            ), header_right_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[250, 250])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # Customer Info Table
    info_data = [
        [
            Paragraph("<b>Ditagihkan Kepada:</b><br/>{}".format(transaction.customer_name), normal_style),
            Paragraph("<b>Catatan Pesanan:</b><br/>{}".format(transaction.notes or '-'), header_right_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Items Table
    table_data = [
        ["Deskripsi Produk", "Harga Satuan", "Qty", "Subtotal"]
    ]
    for item in transaction.items:
        prod_name = item.product.name if item.product else 'Produk tidak tersedia'
        price = "Rp {:,.0f}".format(item.price_at_transaction).replace(',', '.')
        qty = str(item.quantity)
        subtotal = "Rp {:,.0f}".format(item.price_at_transaction * item.quantity).replace(',', '.')
        table_data.append([prod_name, price, qty, subtotal])
        
    total_val = "Rp {:,.0f}".format(transaction.total_price).replace(',', '.')
    table_data.append(["Total Keseluruhan", "", "", total_val])
    
    items_table = Table(table_data, colWidths=[240, 100, 50, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ff4500')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'LEFT'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#cccccc')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8f9fa')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#ff4500')),
        ('TOPPADDING', (0,-1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 8),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))
    
    # Footer
    footer_text = Paragraph(
        "<center>Terima kasih atas pesanan Anda di Nabz Snack!<br/>"
        "Apabila ada pertanyaan mengenai invoice ini, silakan hubungi kami.</center>",
        normal_style
    )
    story.append(footer_text)
    
    doc.build(story)
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="Invoice_{transaction.invoice_number.replace("/", "_")}.pdf"'
    return response
@app.route('/customer/checkout', methods=['POST'])
@login_required
def customer_checkout():
    buyer_name = request.form.get('buyer_name') or session.get('username')
    notes = request.form.get('notes')
    
    cart = get_user_cart()
    if not cart or not cart.items:
        flash('Keranjang belanja Anda kosong!', 'error')
        return redirect(url_for('cart_page'))
        
    # 1. Validasi Stok
    total_price = 0
    validated_items = []
    
    for item in cart.items:
        prod = item.product
        if not prod:
            flash(f"Produk dalam keranjang tidak ditemukan!", 'error')
            return redirect(url_for('cart_page'))
            
        qty = item.quantity
        if qty > prod.stock:
            flash(f"Gagal Checkout! Stok '{prod.name}' tidak mencukupi (Tersedia: {prod.stock}, Diminta: {qty}).", 'error')
            return redirect(url_for('cart_page'))
            
        total_price += prod.price * qty
        validated_items.append((prod, qty))
        
    # 2. Kurangi Stok & Buat Transaksi
    now = datetime.datetime.now()
    invoice = f"INV/{now.strftime('%Y%m%d')}/{random.randint(100, 999)}"
    
    transaction = Transaction(
        invoice_number=invoice,
        customer_name=buyer_name,
        customer_id=session.get('user_id'),
        total_price=total_price,
        status='Completed',
        notes=notes,
        created_at=now
    )
    db.session.add(transaction)
    db.session.flush() # Mengisi transaction.id
    
    for prod, qty in validated_items:
        # Kurangi stok
        prod.stock -= qty
        # Buat detail item transaksi
        item_detail = TransactionItem(
            transaction_id=transaction.id,
            product_id=prod.id,
            quantity=qty,
            price_at_transaction=prod.price
        )
        db.session.add(item_detail)
        
    # 3. Kosongkan Keranjang
    for item in cart.items:
        db.session.delete(item)
        
    db.session.commit()
    flash('Checkout berhasil! Invoice Anda: {}. Silakan tunggu konfirmasi kasir.'.format(invoice), 'success')
    
    # Redirect ke halaman konfirmasi checkout
    return redirect(url_for('checkout_success', trans_id=transaction.id))

@app.route('/checkout/success/<int:trans_id>')
@login_required
def checkout_success(trans_id):
    transaction = Transaction.query.get_or_404(trans_id)
    # Pastikan hanya pemilik transaksi atau admin/kasir yang bisa lihat
    if session.get('user_role') not in ['admin', 'cashier'] and transaction.customer_id != session.get('user_id'):
        flash('Anda tidak memiliki akses ke halaman ini.', 'error')
        return redirect(url_for('index'))
    return render_template('checkout_success.html', transaction=transaction)

# ==========================================
# CASHIER CONTROLLERS
# ==========================================

@app.route('/cashier/dashboard')
@role_required(['cashier'])
def cashier_dashboard():
    products = Product.query.all()
    # Tampilkan seluruh transaksi yang terdaftar di sistem untuk dipantau
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    
    # Hitung jumlah order online yang masuk (status Pending)
    pending_orders_count = Transaction.query.filter_by(status='Pending').count()
    
    return render_template('cashier_dashboard.html', 
                           products=products, 
                           transactions=transactions,
                           pending_orders_count=pending_orders_count)

@app.route('/cashier/pos/checkout', methods=['POST'])
@role_required(['cashier'])
def cashier_pos_checkout():
    pos_items_json = request.form.get('pos_items')
    customer_name = request.form.get('pos_customer_name', 'Pelanggan Umum')
    
    if not pos_items_json:
        flash('Bukti pembelian POS kosong!', 'error')
        return redirect(url_for('cashier_dashboard'))
        
    try:
        pos_items = json.loads(pos_items_json)
    except Exception:
        flash('Data transaksi POS tidak valid!', 'error')
        return redirect(url_for('cashier_dashboard'))
        
    if not pos_items:
        flash('Tidak ada produk yang dipilih!', 'error')
        return redirect(url_for('cashier_dashboard'))
        
    # 1. Validasi Stok
    total_price = 0
    validated_items = []
    
    for item in pos_items:
        prod = Product.query.get(item['id'])
        if not prod:
            flash(f"Produk '{item['name']}' tidak ditemukan!", 'error')
            return redirect(url_for('cashier_dashboard'))
            
        qty = int(item['quantity'])
        if qty > prod.stock:
            flash(f"Gagal Transaksi POS! Stok '{prod.name}' tidak mencukupi.", 'error')
            return redirect(url_for('cashier_dashboard'))
            
        total_price += prod.price * qty
        validated_items.append((prod, qty))
        
    # 2. Buat Invoice POS & Kurangi Stok
    now = datetime.datetime.now()
    invoice = f"INV/POS/{now.strftime('%Y%m%d')}/{random.randint(100, 999)}"
    
    transaction = Transaction(
        invoice_number=invoice,
        customer_name=customer_name,
        cashier_id=session['user_id'],
        total_price=total_price,
        status='Completed', # Pembelian offline langsung selesai di tempat
        notes='Transaksi POS Offline langsung di kasir toko.',
        created_at=now
    )
    db.session.add(transaction)
    db.session.flush()
    
    for prod, qty in validated_items:
        prod.stock -= qty
        item_detail = TransactionItem(
            transaction_id=transaction.id,
            product_id=prod.id,
            quantity=qty,
            price_at_transaction=prod.price
        )
        db.session.add(item_detail)
        
    db.session.commit()
    flash(f"Transaksi POS offline berhasil! Cetak Struk: {invoice}.", 'success')
    return redirect(url_for('cashier_dashboard'))

@app.route('/cashier/order/update/<int:trans_id>/<string:new_status>')
@role_required(['cashier'])
def update_order_status(trans_id, new_status):
    transaction = Transaction.query.get_or_404(trans_id)
    
    # Validasi perubahan status yang valid
    if new_status not in ['Processed', 'Completed', 'Cancelled']:
        flash('Perubahan status tidak valid!', 'error')
        return redirect(url_for('cashier_dashboard'))
        
    old_status = transaction.status
    
    # Jika dibatalkan (Cancelled), kembalikan stok produk ke semula
    if new_status == 'Cancelled' and old_status != 'Cancelled':
        for item in transaction.items:
            if item.product:
                item.product.stock += item.quantity
                
    # Jika dari Cancelled dikembalikan menjadi aktif lagi (opsional, tapi sebagai pengaman)
    elif old_status == 'Cancelled' and new_status != 'Cancelled':
        # Kurangi lagi stoknya
        for item in transaction.items:
            if item.product:
                if item.quantity > item.product.stock:
                    flash(f"Gagal mengaktifkan kembali! Stok '{item.product.name}' tidak mencukupi.", 'error')
                    return redirect(url_for('cashier_dashboard'))
                item.product.stock -= item.quantity
                
    transaction.status = new_status
    db.session.commit()
    
    flash(f"Status pesanan {transaction.invoice_number} berhasil diperbarui menjadi '{new_status}'!", 'success')
    return redirect(url_for('cashier_dashboard'))

# ==========================================
# ADMIN CONTROLLERS
# ==========================================

@app.route('/admin/dashboard')
@role_required(['admin'])
def admin_dashboard():
    products = Product.query.all()
    users = User.query.all()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    
    # 1. Hitung Statistik Ringkasan
    total_revenue = sum(t.total_price for t in transactions if t.status == 'Completed')
    total_transactions = sum(1 for t in transactions if t.status == 'Completed')
    
    # 2. Grafik 1: Tren Penjualan Bulanan (Omset)
    # Kelompokkan omset Completed transaksi berdasarkan bulan
    trend_dict = {}
    for t in transactions:
        if t.status == 'Completed':
            m_name = MONTHS_ID[t.created_at.month]
            trend_dict[m_name] = trend_dict.get(m_name, 0.0) + t.total_price
            
    # Urutkan berdasarkan urutan bulan yang logis (Maret -> April -> Mei, dsb.)
    # Untuk demo, kita urutkan berdasarkan urutan bulan natural
    month_order = {v: k for k, v in MONTHS_ID.items()}
    sorted_trend = sorted(trend_dict.items(), key=lambda x: month_order.get(x[0], 99))
    
    trend_chart_data = {
        'labels': [x[0] for x in sorted_trend] if sorted_trend else ['Maret', 'April', 'Mei'],
        'data': [x[1] for x in sorted_trend] if sorted_trend else [40000, 57000, 41000]
    }
    
    # 3. Grafik 2: Penjualan Kategori
    # Hitung jumlah item terjual per kategori snack
    category_dict = {}
    for t in transactions:
        if t.status == 'Completed':
            for item in t.items:
                cat = item.product.category if item.product else 'Lainnya'
                category_dict[cat] = category_dict.get(cat, 0) + item.quantity
                
    category_chart_data = {
        'labels': list(category_dict.keys()) if category_dict else ['Basreng', 'Makaroni', 'Keripik', 'Seblak'],
        'data': list(category_dict.values()) if category_dict else [3, 4, 3, 2]
    }
    
    # 4. Grafik 3: Menu Terlaris (Top Selling)
    # Jumlah kuantitas terjual per produk snack
    top_dict = {}
    for t in transactions:
        if t.status == 'Completed':
            for item in t.items:
                name = item.product.name if item.product else 'Produk Dihapus'
                # Potong nama yang kepanjangan
                short_name = name.split(' (')[0]
                top_dict[short_name] = top_dict.get(short_name, 0) + item.quantity
                
    # Urutkan descending dan ambil 5 teratas
    sorted_top = sorted(top_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    
    top_products_chart_data = {
        'labels': [x[0] for x in sorted_top] if sorted_top else ['Basreng Pedas', 'Makaroni Pedas', 'Keripik Setan'],
        'data': [x[1] for x in sorted_top] if sorted_top else [3, 4, 3]
    }
    
    return render_template('admin_dashboard.html',
                           products=products,
                           users=users,
                           total_revenue=total_revenue,
                           total_transactions=total_transactions,
                           trend_chart_data=trend_chart_data,
                           category_chart_data=category_chart_data,
                           top_products_chart_data=top_products_chart_data)

@app.route('/admin/product/add', methods=['POST'])
@role_required(['admin'])
def add_product():
    name = request.form.get('name')
    price = float(request.form.get('price'))
    stock = int(request.form.get('stock'))
    category = request.form.get('category')
    spicy_level = int(request.form.get('spicy_level'))
    image_url = request.form.get('image_url')
    description = request.form.get('description')
    
    if not image_url or not image_url.strip():
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        image_url = f'/static/images/{slug}.png'

    new_product = Product(
        name=name, price=price, stock=stock, 
        category=category, spicy_level=spicy_level,
        image_url=image_url, description=description
    )
    db.session.add(new_product)
    db.session.commit()
    flash(f"Snack '{name}' berhasil ditambahkan ke database!", 'success')
    return redirect(url_for('admin_dashboard') + '#products-pane')

@app.route('/admin/product/edit', methods=['POST'])
@role_required(['admin'])
def edit_product():
    prod_id = int(request.form.get('id'))
    prod = Product.query.get_or_404(prod_id)
    
    prod.name = request.form.get('name')
    prod.price = float(request.form.get('price'))
    prod.stock = int(request.form.get('stock'))
    prod.category = request.form.get('category')
    prod.spicy_level = int(request.form.get('spicy_level'))
    image_url = request.form.get('image_url')
    if not image_url or not image_url.strip():
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', prod.name.lower()).strip('_')
        image_url = f'/static/images/{slug}.png'
    prod.image_url = image_url
    prod.description = request.form.get('description')
    
    db.session.commit()
    flash(f"Data produk '{prod.name}' berhasil diperbarui!", 'success')
    return redirect(url_for('admin_dashboard') + '#products-pane')

@app.route('/admin/product/delete/<int:prod_id>')
@role_required(['admin'])
def delete_product(prod_id):
    prod = Product.query.get_or_404(prod_id)
    name = prod.name
    db.session.delete(prod)
    db.session.commit()
    flash(f"Produk '{name}' berhasil dihapus dari sistem.", 'success')
    return redirect(url_for('admin_dashboard') + '#products-pane')

@app.route('/admin/user/edit', methods=['POST'])
@role_required(['admin'])
def edit_user():
    user_id = int(request.form.get('id'))
    user = User.query.get_or_404(user_id)

    new_username = request.form.get('username', '').strip()
    new_email    = request.form.get('email', '').strip()
    new_role     = request.form.get('role', 'customer')
    new_password = request.form.get('new_password', '').strip()

    # Cek duplikasi username (kecuali milik user ini sendiri)
    existing_user = User.query.filter(User.username == new_username, User.id != user_id).first()
    if existing_user:
        flash(f"Username '{new_username}' sudah digunakan oleh pengguna lain!", 'error')
        return redirect(url_for('admin_dashboard') + '#users-pane')

    # Cek duplikasi email (kecuali milik user ini sendiri)
    existing_email = User.query.filter(User.email == new_email, User.id != user_id).first()
    if existing_email:
        flash(f"Email '{new_email}' sudah terdaftar pada akun lain!", 'error')
        return redirect(url_for('admin_dashboard') + '#users-pane')

    user.username = new_username
    user.email    = new_email
    user.role     = new_role

    if new_password:
        user.set_password(new_password)

    db.session.commit()
    flash(f"Data akun '{user.username}' berhasil diperbarui!", 'success')
    return redirect(url_for('admin_dashboard') + '#users-pane')

@app.route('/admin/user/delete/<int:user_id>')
@role_required(['admin'])
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash("Anda tidak dapat menghapus akun Anda sendiri yang sedang aktif!", "error")
        return redirect(url_for('admin_dashboard') + '#users-pane')
        
    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Akun pengguna '{username}' berhasil dihapus.", 'success')
    return redirect(url_for('admin_dashboard') + '#users-pane')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
