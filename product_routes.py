from main import app
from PIL import Image
import os
from flask import request, jsonify, send_from_directory
import sqlite3, json, uuid
from server_settings import UPLOAD_FOLDER, THUMBS_FOLDER, ALLOWED_EXT, is_admin

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBS_FOLDER, exist_ok=True)

def is_allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_image(file):
    """Save an uploaded image and return (success, original, thumbnail, error_msg)."""

    if not file:
        return False, None, None, "No image file"

    if file.filename == "":
        return False, None, None, "No file selected"

    if not is_allowed(file.filename):
        return False, None, None, "Only JPG, JPEG, PNG allowed"

    try:
        # generate unique name
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # save original
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        # create thumbnail
        thumb_name = f"thumb_{filename}"
        thumb_path = os.path.join(THUMBS_FOLDER, thumb_name)

        img = Image.open(path)
        img.thumbnail((300, 300))
        img.save(thumb_path)

        return True, filename, thumb_name, None

    except Exception as e:
        return False, None, None, str(e)

@app.route('/add_product', methods=['POST'])
def add_product():
    try:
        token = request.form.get('token')
        name = request.form.get('name')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        description = request.form.get('description')
        tags_json = request.form.get('tags', '[]')
        tags = json.loads(tags_json)

        image_files = request.files.getlist('images')

        # db connection
        conn = sqlite3.connect("emap.db")
        # admin check
        cursor = conn.cursor()
        if not is_admin(conn, token):
            return jsonify(error="not authorized")


        cursor.execute("""
            INSERT INTO products (name, description, price,quantity, created_at, updated_at)
            VALUES (?, ?, ?,?, datetime('now'), datetime('now'))
        """, (name, description, price, quantity))

        product_id = cursor.lastrowid


        for file in image_files:
            ok, original, thumb, error = save_image(file)
            if ok:
                cursor.execute("""
                    INSERT INTO images (product_id, file_name, uploaded_at)
                    VALUES (?, ?, datetime('now'))
                """, (product_id, original))


        for tag_name in tags:

            cursor.execute("SELECT tag_id FROM tags WHERE tag_name = ?", (tag_name,))
            row = cursor.fetchone()

            if row:
                tag_id = row[0]
            else:
                cursor.execute("INSERT INTO tags (tag_name) VALUES (?)", (tag_name,))
                tag_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO product_tags (product_id, tag_id)
                VALUES (?, ?)
            """, (product_id, tag_id))


        conn.commit()
        conn.close()

        return jsonify(success=True, product_id=product_id)

    except Exception as e:
        return jsonify(error=str(e))
@app.route('/delete_product', methods=['POST'])
def delete_product():
    try:
        token = request.form.get('token')
        product_id = request.form.get('product_id')

        # db connection
        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()
        # check admin
        if not is_admin(conn, token):
            return jsonify(error="Not authorized")


        # check if product exists
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        if cursor.fetchone() is None:
            return jsonify(error="Product does not exist")

        # eelete the product
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))

        conn.commit()
        conn.close()

        return jsonify(success=True)

    except Exception as e:
        return jsonify(error=str(e))

def get_images(cursor, product_id):
    cursor.execute("SELECT file_name FROM images WHERE product_id = ?", (product_id,))
    rows = cursor.fetchall()
    return [row[0] for row in rows] # a list of image names
def get_products_dict(cursor, rows):
    products = []
    for row in rows:
        product_id = row[0]
        products.append({
            "product_id": product_id,
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "quantity": row[4],
            "created_at": row[5],
            "updated_at": row[6],

            "images": get_images(cursor, product_id),
        })

    return products

@app.route('/products', methods=['POST'])
def get_all_products():
    try:
        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM products ORDER BY product_id DESC")
        rows = cursor.fetchall()

        products = get_products_dict(cursor, rows)

        conn.close()
        return jsonify(success=True, products=products)

    except Exception as e:
        return jsonify(error=str(e))


@app.route('/uploads/<filename>')
def serve_uploaded_img(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/uploads/thumbs/<filename>')
def serve_uploaded_thumbnail(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
