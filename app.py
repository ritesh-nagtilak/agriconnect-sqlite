from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Database initialization
def init_db():
    conn = sqlite3.connect('agriconnect.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT NOT NULL,
            stock_quantity INTEGER NOT NULL,
            description TEXT,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buyer_id) REFERENCES users (id),
            FOREIGN KEY (farmer_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (buyer_id) REFERENCES users (id),
            FOREIGN KEY (farmer_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('agriconnect.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT p.*, u.full_name as farmer_name, u.address as farmer_location
        FROM products p 
        JOIN users u ON p.farmer_id = u.id 
        WHERE p.stock_quantity > 0 
        ORDER BY p.created_at DESC 
        LIMIT 6
    ''').fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/register/<user_type>')
def register_form(user_type):
    if user_type not in ['farmer', 'buyer']:
        return redirect(url_for('index'))
    return render_template(f'{user_type}_register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    user_type = request.form['user_type']
    full_name = request.form['full_name']
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')

    if not all([username, email, password, user_type, full_name]):
        flash('Please fill in all required fields')
        return redirect(url_for('register_form', user_type=user_type))

    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO users (username, email, password_hash, user_type, full_name, phone, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, user_type, full_name, phone, address))
        conn.commit()
        conn.close()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    except sqlite3.IntegrityError:
        flash('Username or email already exists')
        return redirect(url_for('register_form', user_type=user_type))

@app.route('/login')
def login_form():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['user_type'] = user['user_type']

        if user['user_type'] == 'farmer':
            return redirect(url_for('farmer_dashboard'))
        else:
            return redirect(url_for('buyer_dashboard'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('login_form'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/farmer/dashboard')
def farmer_dashboard():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products WHERE farmer_id = ?', (session['user_id'],)).fetchall()
    orders = conn.execute('''
        SELECT o.*, p.name as product_name, u.full_name as buyer_name,u.phone as buyer_phone
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.buyer_id = u.id
        WHERE o.farmer_id = ?
        ORDER BY o.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('farmer_dashboard.html', products=products, orders=orders)

@app.route('/buyer/dashboard')
def buyer_dashboard():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    orders = conn.execute('''
        SELECT o.*, p.name as product_name, u.full_name as farmer_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.farmer_id = u.id
        WHERE o.buyer_id = ?
        ORDER BY o.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('buyer_dashboard.html', orders=orders)

@app.route('/products')
def product_list():
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    conn = get_db_connection()
    query = '''
        SELECT p.*, u.full_name as farmer_name, u.address as farmer_location
        FROM products p 
        JOIN users u ON p.farmer_id = u.id 
        WHERE p.stock_quantity > 0
    '''
    params = []

    if category:
        query += ' AND p.category = ?'
        params.append(category)

    if search:
        query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    query += ' ORDER BY p.created_at DESC'

    products = conn.execute(query, params).fetchall()

    categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()
    conn.close()

    return render_template('product_list.html', products=products, categories=categories, 
                         current_category=category, search_term=search)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT p.*, u.full_name as farmer_name, u.phone as farmer_phone, u.address as farmer_location
        FROM products p 
        JOIN users u ON p.farmer_id = u.id 
        WHERE p.id = ?
    ''', (product_id,)).fetchone()

    if not product:
        flash('Product not found')
        return redirect(url_for('product_list'))

    reviews = conn.execute('''
        SELECT r.*, u.full_name as buyer_name
        FROM reviews r
        JOIN users u ON r.buyer_id = u.id
        WHERE r.product_id = ?
        ORDER BY r.created_at DESC
    ''', (product_id,)).fetchall()

    conn.close()
    return render_template('product_detail.html', product=product, reviews=reviews)

@app.route('/add_product')
def add_product_form():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))
    return render_template('add_product.html')

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))

    name = request.form['name']
    category = request.form['category']
    price = float(request.form['price'])
    unit = request.form['unit']
    stock_quantity = int(request.form['stock_quantity'])
    description = request.form['description']

    image_filename = None
    if 'image' in request.files:
        image = request.files['image']
        if image.filename:
            filename = secure_filename(image.filename)
            image_filename = f"{uuid.uuid4().hex}_{filename}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO products (farmer_id, name, category, price, unit, stock_quantity, description, image_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], name, category, price, unit, stock_quantity, description, image_filename))
    conn.commit()
    conn.close()

    flash('Product added successfully!')
    return redirect(url_for('farmer_dashboard'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return jsonify({'success': False, 'message': 'Please login as buyer'})

    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])

    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    if not product or product['stock_quantity'] < quantity:
        conn.close()
        return jsonify({'success': False, 'message': 'Insufficient stock'})

    total_amount = product['price'] * quantity

    conn.execute('''
        INSERT INTO orders (buyer_id, farmer_id, product_id, quantity, total_amount)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], product['farmer_id'], product_id, quantity, total_amount))

    conn.execute('''
        UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?
    ''', (quantity, product_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Order placed successfully!'})

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return jsonify({'success': False, 'message': 'Unauthorized'})

    order_id = int(request.form['order_id'])
    status = request.form['status']

    conn = get_db_connection()
    conn.execute('''
        UPDATE orders SET status = ? WHERE id = ? AND farmer_id = ?
    ''', (status, order_id, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Order status updated!'})

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return jsonify({'success': False, 'message': 'Please login as buyer'})
    
    order_id = int(request.form['order_id'])
    rating = int(request.form['rating'])
    comment = request.form.get('comment', '')
    
    conn = get_db_connection()
    
    order = conn.execute('''
        SELECT o.*, p.id as product_id, p.farmer_id
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.id = ? AND o.buyer_id = ? AND o.status = 'completed'
    ''', (order_id, session['user_id'])).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'success': False, 'message': 'Order not found or not eligible for review'})
    
    existing_review = conn.execute('''
        SELECT id FROM reviews WHERE order_id = ? AND buyer_id = ?
    ''', (order_id, session['user_id'])).fetchone()
    
    if existing_review:
        conn.close()
        return jsonify({'success': False, 'message': 'You have already reviewed this order'})
    
    conn.execute('''
        INSERT INTO reviews (order_id, buyer_id, farmer_id, product_id, rating, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (order_id, session['user_id'], order['farmer_id'], order['product_id'], rating, comment))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Review submitted successfully!'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
