from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
from datetime import datetime
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ecommerce.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

# Admin credentials (change these in production)
ADMIN_USERNAME = 'promax'
ADMIN_PASSWORD = 'promax@69'
WHATSAPP_NUMBER = '+916376751010'

# ==================== Helper Functions ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # 'cement' or 'kirana'
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'price': self.price,
            'image_url': self.image_url,
            'stock': self.stock
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(200))
    customer_address = db.Column(db.Text)
    products = db.Column(db.Text)  # JSON string of products
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.Text)

# ==================== Helper Functions ====================

def send_whatsapp_message(phone, message):
    """Send WhatsApp message via Twilio or similar service"""
    # This is a placeholder - you need to integrate with WhatsApp API
    # For now, we'll just log it
    print(f"WhatsApp message to {phone}: {message}")
    return True

def format_whatsapp_message(order_details):
    """Format order details for WhatsApp"""
    message = f"""
🛍️ *New Order Received*

*Customer Details:*
Name: {order_details['name']}
Phone: {order_details['phone']}
Email: {order_details['email']}
Address: {order_details['address']}

*Products:*
{order_details['products']}

*Total Amount:* ₹{order_details['total']:.2f}

*Notes:* {order_details.get('notes', 'N/A')}

---
View order details for fulfillment.
"""
    return message

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_only(f):
    """Decorator to ensure only authenticated admins can access a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            # Redirect to 404 instead of login to hide admin pages
            return render_template('404.html'), 404
        return f(*args, **kwargs)
    return decorated_function

# ==================== Routes ====================

# -------- Frontend Routes --------

@app.route('/')
def home():
    """Home page with product categories"""
    return render_template('home.html')

@app.route('/products/<category>')
def products(category):
    """Display products for a category"""
    if category not in ['cement', 'kirana']:
        return redirect(url_for('home'))
    
    products_list = Product.query.filter_by(category=category).all()
    return render_template('products.html', category=category, products=products_list)

@app.route('/cart')
def cart():
    """Shopping cart page"""
    return render_template('cart.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page"""
    if request.method == 'POST':
        data = request.get_json()
        
        # Create order
        products_text = '\n'.join([f"- {item['name']} x{item['quantity']} @ ₹{item['price']}" 
                                   for item in data.get('items', [])])
        
        order = Order(
            customer_name=data.get('name'),
            customer_phone=data.get('phone'),
            customer_email=data.get('email'),
            customer_address=data.get('address'),
            products=products_text,
            total_amount=data.get('total'),
            notes=data.get('notes', '')
        )
        
        db.session.add(order)
        db.session.commit()
        
        # Send WhatsApp notification
        message = format_whatsapp_message({
            'name': data.get('name'),
            'phone': data.get('phone'),
            'email': data.get('email'),
            'address': data.get('address'),
            'products': products_text,
            'total': data.get('total'),
            'notes': data.get('notes', '')
        })
        
        send_whatsapp_message(WHATSAPP_NUMBER, message)
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'message': 'Order placed successfully! We will contact you on WhatsApp shortly.'
        })
    
    return render_template('checkout.html')

@app.route('/api/products/<category>')
def api_products(category):
    """API endpoint to get products by category"""
    products_list = Product.query.filter_by(category=category).all()
    return jsonify([p.to_dict() for p in products_list])

# -------- Admin Routes --------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@admin_only
def admin_dashboard():
    """Admin dashboard"""
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(10).all()
    
    return render_template('admin_dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders)

@app.route('/admin/products')
@admin_only
def admin_products():
    """Manage products"""
    cement_products = Product.query.filter_by(category='cement').all()
    kirana_products = Product.query.filter_by(category='kirana').all()
    
    return render_template('admin_products.html', 
                         cement_products=cement_products,
                         kirana_products=kirana_products)

@app.route('/admin/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
@admin_only
def admin_api_products():
    """API for managing products"""
    
    if request.method == 'GET':
        category = request.args.get('category')
        if category:
            products_list = Product.query.filter_by(category=category).all()
        else:
            products_list = Product.query.all()
        return jsonify([p.to_dict() for p in products_list])
    
    elif request.method == 'POST':
        # Handle file upload
        image_url = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid conflicts
                filename = f"{datetime.now().timestamp()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename=f'uploads/{filename}', _external=False)
        
        # Get form data
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        price = request.form.get('price')
        stock = request.form.get('stock')
        image_url_form = request.form.get('image_url')
        
        # Use uploaded image or provided URL
        if not image_url and image_url_form:
            image_url = image_url_form
        
        product = Product(
            name=name,
            category=category,
            description=description,
            price=float(price) if price else 0,
            image_url=image_url,
            stock=int(stock) if stock else 0
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True, 'id': product.id})
    
    elif request.method == 'PUT':
        product_id = request.form.get('id')
        product = Product.query.get(product_id)
        if product:
            # Handle file upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{datetime.now().timestamp()}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    product.image_url = url_for('static', filename=f'uploads/{filename}', _external=False)
            
            # Update form fields
            product.name = request.form.get('name', product.name)
            product.description = request.form.get('description', product.description)
            product.price = float(request.form.get('price', product.price))
            product.stock = int(request.form.get('stock', product.stock))
            product.category = request.form.get('category', product.category)
            
            # Update image URL if no file uploaded
            if 'image' not in request.files or not request.files['image'].filename:
                image_url_form = request.form.get('image_url')
                if image_url_form:
                    product.image_url = image_url_form
            
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'})
    
    elif request.method == 'DELETE':
        product_id = request.args.get('id')
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'})

@app.route('/admin/orders')
@admin_only
def admin_orders():
    """View all orders"""
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/api/orders/<int:order_id>', methods=['PUT'])
@admin_only
def admin_update_order(order_id):
    """Update order status"""
    data = request.get_json()
    order = Order.query.get(order_id)
    if order:
        order.status = data.get('status', order.status)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Order not found'})

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ==================== Create Tables ====================

def initialize_app():
    """Initialize the application and database"""
    with app.app_context():
        db.create_all()
        
        # Add sample products if database is empty
        if Product.query.count() == 0:
            print("Adding sample products...")
            
            # Cement Products
            cement_products = [
                Product(
                    name="Portland Cement 50kg",
                    category="cement",
                    description="High-quality Portland cement suitable for construction projects",
                    price=450.00,
                    stock=100
                ),
                Product(
                    name="Fly Ash Cement 50kg",
                    category="cement",
                    description="Eco-friendly fly ash cement with better durability",
                    price=420.00,
                    stock=75
                ),
                Product(
                    name="White Cement 20kg",
                    category="cement",
                    description="Premium white cement for decorative finishes",
                    price=380.00,
                    stock=50
                ),
                Product(
                    name="Plaster Cement 40kg",
                    category="cement",
                    description="Specialized cement for plaster work",
                    price=350.00,
                    stock=60
                ),
            ]
            
            # Kirana Products
            kirana_products = [
                Product(
                    name="Basmati Rice 1kg",
                    category="kirana",
                    description="Premium long-grain basmati rice",
                    price=80.00,
                    stock=200
                ),
                Product(
                    name="Wheat Flour 5kg",
                    category="kirana",
                    description="Pure wheat flour for daily use",
                    price=120.00,
                    stock=150
                ),
                Product(
                    name="Cooking Oil 1L",
                    category="kirana",
                    description="Refined vegetable cooking oil",
                    price=160.00,
                    stock=120
                ),
                Product(
                    name="Dal (Lentils) 1kg",
                    category="kirana",
                    description="Mixed dal assortment",
                    price=140.00,
                    stock=100
                ),
                Product(
                    name="Sugar 1kg",
                    category="kirana",
                    description="White granulated sugar",
                    price=50.00,
                    stock=180
                ),
                Product(
                    name="Salt 1kg",
                    category="kirana",
                    description="Iodized table salt",
                    price=25.00,
                    stock=200
                ),
                Product(
                    name="Spice Mix 500g",
                    category="kirana",
                    description="Mixed spices blend",
                    price=200.00,
                    stock=80
                ),
                Product(
                    name="Tea Leaves 250g",
                    category="kirana",
                    description="Premium tea leaves",
                    price=180.00,
                    stock=120
                ),
            ]
            
            for product in cement_products + kirana_products:
                db.session.add(product)
            
            db.session.commit()
            print(f"✅ Added {len(cement_products) + len(kirana_products)} sample products!")

if __name__ == '__main__':
    initialize_app()
    app.run(debug=True, port=5000)
