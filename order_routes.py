import sqlite3, json
from flask import request, jsonify, Blueprint
from server_settings import token_valid, get_user_id_from_token, is_admin

# blue print
order_bp = Blueprint("order", __name__)


@order_bp.route('/create_order', methods=['POST'])
def create_order():
    try:
        token = request.form.get('token')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        items_json = request.form.get('items', '[]')

        items = json.loads(items_json)

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        # Validate token
        if not token_valid(conn, token):
            conn.close()
            return jsonify(error="not authorized")

        user_id = get_user_id_from_token(token, conn)

        # calculate total price
        total_price = 0
        for item in items:
            cursor.execute("SELECT price FROM products WHERE product_id = ?", (item["product_id"],))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return jsonify(error=f"Product {item['product_id']} does not exist")

            price = row[0]
            total_price += price * item["quantity"]

        # insert into orders tabee
        cursor.execute("""
            INSERT INTO orders (user_id, phone_number, address, total_price, order_date, order_status)
            VALUES (?, ?, ?, ?, datetime('now'), 'pending')
        """, (user_id, phone_number, address, total_price))

        order_id = cursor.lastrowid

        # insert items into order_items table
        for item in items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price_at_time) VALUES (?, ?, ?, ?)",
                (order_id, item["product_id"], item["quantity"], price)
            )

        conn.commit()
        conn.close()

        return jsonify(success=True, order_id=order_id)

    except Exception as e:
        return jsonify(error=str(e))


@order_bp.route('/get_orders', methods=['POST'])
def get_orders():
    try:
        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()
        if not is_admin(token, conn):
            raise Exception('not authorized')

        cursor.execute("SELECT user_id, phone_number, address, total_price, order_date, order_status, created_at, order_id FROM orders ORDER BY order_id DESC")
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            orders.append({
                "user_id": row[0],
                "phone_number": row[1],
                "address": row[2],
                "total_price": row[3],
                "order_date": row[4],
                "order_status": row[5],
                "created_at": row[6],
                "order_id": row[7]
            })

        conn.close()
        return jsonify(success=True, orders=orders)

    except Exception as e:
        return jsonify(error=str(e))

@order_bp.route('/get_order_details', methods=['POST'])
def get_order_details():
    try:
        order_id = request.form.get('order_id')

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        if not is_admin(token, conn):
            raise Exception('not authorized')
        cursor.execute(
            "SELECT user_id, phone_number, address, total_price, order_date, "
            "order_status, created_at, order_id "
            "FROM orders WHERE order_id = ?", 
            (order_id,)
        )
        order = cursor.fetchone()

        if not order:
            return jsonify(error="Order does not exist")

        cursor.execute("""
            SELECT product_id, quantity, price_at_time
            FROM order_items
            WHERE order_id = ?
        """, (order_id,))
        items_rows = cursor.fetchall()

        items = []
        for r in items_rows:
            items.append({
                "product_id": r[0],
                "quantity": r[1],
                "price_at_time": r[2]
            })

        result = {
            "user_id": order[0],
            "phone_number": order[1],
            "address": order[2],
            "total_price": order[3],
            "order_date": order[4],
            "order_status": order[5],
            "created_at": order[6],
            "order_id": order[7],
            "items": items
        }

        conn.close()
        return jsonify(success=True, order=result)

    except Exception as e:
        return jsonify(error=str(e))

