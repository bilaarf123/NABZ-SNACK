from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # 'admin', 'cashier', 'customer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer_transactions = db.relationship('Transaction', foreign_keys='Transaction.customer_id', backref='customer', lazy=True)
    cashier_transactions = db.relationship('Transaction', foreign_keys='Transaction.cashier_id', backref='cashier', lazy=True)
    cart = db.relationship('Cart', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(50), nullable=False) # e.g. Makaroni, Keripik, Basreng, Seblak
    spicy_level = db.Column(db.Integer, nullable=False, default=1) # 1 - 5
    image_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    transaction_items = db.relationship('TransactionItem', backref='product', lazy=True)

    @property
    def display_image(self):
        if self.image_url:
            return self.image_url
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', self.name.lower()).strip('_')
        return f'/static/images/{slug}.png'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'category': self.category,
            'spicy_level': self.spicy_level,
            'image_url': self.display_image,
            'description': self.description
        }



class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending') # 'Pending', 'Processed', 'Completed', 'Cancelled'
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('TransactionItem', backref='transaction', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_id': self.customer_id,
            'cashier_id': self.cashier_id,
            'total_price': self.total_price,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': [item.to_dict() for item in self.items]
        }


class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_transaction = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else 'Produk Dihapus',
            'quantity': self.quantity,
            'price_at_transaction': self.price_at_transaction,
            'subtotal': self.quantity * self.price_at_transaction
        }


class Cart(db.Model):
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', cascade='all, delete-orphan', lazy=True)

    def total_price(self):
        return sum(item.subtotal() for item in self.items)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    product = db.relationship('Product')

    def subtotal(self):
        return self.quantity * (self.product.price if self.product else 0)

