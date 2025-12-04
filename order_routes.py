import sqlite3, json
from flask import request, jsonify
from main import app
from server_settings import token_valid

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        token = request.form.get('token')
        user_id = request.form.get('user_id')
        phone_number = request.form.get('phone_number')
        items_json = request.form.get('items', '[]')

        items = json.loads(items_json)

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        if not token_valid(conn, token):
            return jsonify(error="not authorized")

        total_price = 0
        for item in items:
            cursor.execute("SELECT price FROM products WHERE product_id = ?", (item["product_id"],))
            row = cursor.fetchone()
            if not row:
                return jsonify(error=f"Product {item['product_id']} does not exist")

            price = row[0]  # correct
            total_price += price * item["quantity"]

        cursor.execute("""
                       INSERT INTO orders
                           (user_id, phone_number, total_price, order_date, order_status)
                       VALUES (?, ?, ?, datetime('now'), 'pending')
                       """, (user_id, phone_number, total_price))

        order_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                           INSERT INTO order_items
                               (order_id, product_id, quantity, price_at_time)
                           VALUES (?, ?, ?, (SELECT price
                                             FROM products
                                             WHERE product_id = ?))
                           """, (order_id, item["product_id"], item["quantity"], item["product_id"]))

        conn.commit()
        conn.close()

        return jsonify(success=True, order_id=order_id)

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/get_orders', methods=['POST'])
def get_orders():
    try:
        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            # row index mapping verified from UML
            orders.append({
                "user_id": row[0],
                "phone_number": row[1],
                "total_price": row[2],
                "order_date": row[3],
                "order_status": row[4],
                "created_at": row[5],  # if present
                "order_id": row[6]
            })

        conn.close()
        return jsonify(success=True, orders=orders)

    except Exception as e:
        return jsonify(error=str(e))
@app.route('/get_order_details', methods=['POST'])
def get_order_details():
    try:
        order_id = request.form.get('order_id')

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()

        if not order:
            return jsonify(error="Order does not exist")

        cursor.execute("""
                       SELECT product_id, quantity, price_at_time
                       FROM order_items
                       WHERE order_id = ?
                       """, (order_id,))

        items_rows = cursor.fetchall()

        items = [{
            "product_id": r[0],
            "quantity": r[1],
            "price_at_time": r[2]
        } for r in items_rows]

        result = {
            "user_id": order[0],
            "phone_number": order[1],
            "total_price": order[2],
            "order_date": order[3],
            "order_status": order[4],
            "created_at": order[5],  # if exists
            "order_id": order[6],
            "items": items
        }

        conn.close()
        return jsonify(success=True, order=result)

    except Exception as e:
        return jsonify(error=str(e))
