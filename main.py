"""
main.py

REST API for the sample_store PostgreSQL database
(created by setup_sample_db.py), built with FastAPI.

Provides full CRUD (Create, Read, Update, Delete) endpoints for:
    - customers
    - products
    - orders
    - order_items

Requirements:
    pip install fastapi "uvicorn[standard]" psycopg2-binary pydantic

Usage:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs for interactive Swagger UI.
"""

from contextlib import contextmanager
from typing import List, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

# ----------------------------------------------------------------------
# CONFIG - adjust to match your local PostgreSQL setup
# ----------------------------------------------------------------------
DB_NAME = "sample_store"
DB_USER = "postgres"
DB_PASSWORD = "Ameena12"   # change to your actual password
DB_HOST = "localhost"
DB_PORT = "5432"


@contextmanager
def get_cursor(commit: bool = False):
    """Context manager that yields a dict-cursor and handles commit/close."""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def fk_violation_message(e: Exception) -> str:
    return (
        "Operation blocked: this record is referenced by another table, "
        "or references a record that does not exist."
    )


# ----------------------------------------------------------------------
# Pydantic schemas
# ----------------------------------------------------------------------
class CustomerBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: EmailStr


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None


class Customer(CustomerBase):
    customer_id: int


class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    stock_qty: int = Field(0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    stock_qty: Optional[int] = Field(None, ge=0)


class Product(ProductBase):
    product_id: int


class OrderBase(BaseModel):
    customer_id: int
    status: str = Field("pending", max_length=20)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=20)


class Order(OrderBase):
    order_id: int


class OrderItemBase(BaseModel):
    order_id: int
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)


class OrderItem(OrderItemBase):
    order_item_id: int


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
app = FastAPI(
    title="Sample Store API",
    description="REST API for the sample_store PostgreSQL database",
    version="1.0.0",
)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Sample Store API is running"}


# ========================================================================
# CUSTOMERS
# ========================================================================
@app.get("/customers", response_model=List[Customer], tags=["Customers"])
def list_customers():
    with get_cursor() as cur:
        cur.execute("SELECT customer_id, first_name, last_name, email FROM customers ORDER BY customer_id")
        return cur.fetchall()


@app.get("/customers/{customer_id}", response_model=Customer, tags=["Customers"])
def get_customer(customer_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT customer_id, first_name, last_name, email FROM customers WHERE customer_id = %s", (customer_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return row


@app.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED, tags=["Customers"])
def create_customer(customer: CustomerCreate):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO customers (first_name, last_name, email)
                   VALUES (%s, %s, %s)
                   RETURNING customer_id, first_name, last_name, email""",
                (customer.first_name, customer.last_name, customer.email),
            )
            return cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status.HTTP_409_CONFLICT, "A customer with this email already exists")


@app.put("/customers/{customer_id}", response_model=Customer, tags=["Customers"])
def update_customer(customer_id: int, customer: CustomerUpdate):
    fields = customer.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [customer_id]

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""UPDATE customers SET {set_clause} WHERE customer_id = %s
                    RETURNING customer_id, first_name, last_name, email""",
                values,
            )
            row = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status.HTTP_409_CONFLICT, "A customer with this email already exists")

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return row


@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Customers"])
def delete_customer(customer_id: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM customers WHERE customer_id = %s RETURNING customer_id", (customer_id,))
            row = cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation as e:
        raise HTTPException(status.HTTP_409_CONFLICT, fk_violation_message(e))

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")


# ========================================================================
# PRODUCTS
# ========================================================================
@app.get("/products", response_model=List[Product], tags=["Products"])
def list_products():
    with get_cursor() as cur:
        cur.execute("SELECT product_id, name, description, price, stock_qty FROM products ORDER BY product_id")
        return cur.fetchall()


@app.get("/products/{product_id}", response_model=Product, tags=["Products"])
def get_product(product_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT product_id, name, description, price, stock_qty FROM products WHERE product_id = %s", (product_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return row


@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_product(product: ProductCreate):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO products (name, description, price, stock_qty)
               VALUES (%s, %s, %s, %s)
               RETURNING product_id, name, description, price, stock_qty""",
            (product.name, product.description, product.price, product.stock_qty),
        )
        return cur.fetchone()


@app.put("/products/{product_id}", response_model=Product, tags=["Products"])
def update_product(product_id: int, product: ProductUpdate):
    fields = product.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [product_id]

    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""UPDATE products SET {set_clause} WHERE product_id = %s
                RETURNING product_id, name, description, price, stock_qty""",
            values,
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return row


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
def delete_product(product_id: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM products WHERE product_id = %s RETURNING product_id", (product_id,))
            row = cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation as e:
        raise HTTPException(status.HTTP_409_CONFLICT, fk_violation_message(e))

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")


# ========================================================================
# ORDERS
# ========================================================================
@app.get("/orders", response_model=List[Order], tags=["Orders"])
def list_orders():
    with get_cursor() as cur:
        cur.execute("SELECT order_id, customer_id, status FROM orders ORDER BY order_id")
        return cur.fetchall()


@app.get("/orders/{order_id}", response_model=Order, tags=["Orders"])
def get_order(order_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT order_id, customer_id, status FROM orders WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return row


@app.get("/orders/{order_id}/items", response_model=List[OrderItem], tags=["Orders"])
def get_order_items(order_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT order_id, customer_id, status FROM orders WHERE order_id = %s", (order_id,))
        if not cur.fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
        cur.execute(
            """SELECT order_item_id, order_id, product_id, quantity, unit_price
               FROM order_items WHERE order_id = %s ORDER BY order_item_id""",
            (order_id,),
        )
        return cur.fetchall()


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(order: OrderCreate):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO orders (customer_id, status)
                   VALUES (%s, %s)
                   RETURNING order_id, customer_id, status""",
                (order.customer_id, order.status),
            )
            return cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "customer_id does not reference an existing customer")


@app.put("/orders/{order_id}", response_model=Order, tags=["Orders"])
def update_order(order_id: int, order: OrderUpdate):
    fields = order.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [order_id]

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""UPDATE orders SET {set_clause} WHERE order_id = %s
                    RETURNING order_id, customer_id, status""",
                values,
            )
            row = cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "customer_id does not reference an existing customer")

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return row


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Orders"])
def delete_order(order_id: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM orders WHERE order_id = %s RETURNING order_id", (order_id,))
            row = cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot delete order: it still has order_items. Delete those first.")

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")


# ========================================================================
# ORDER ITEMS
# ========================================================================
@app.get("/order-items", response_model=List[OrderItem], tags=["Order Items"])
def list_order_items():
    with get_cursor() as cur:
        cur.execute("SELECT order_item_id, order_id, product_id, quantity, unit_price FROM order_items ORDER BY order_item_id")
        return cur.fetchall()


@app.get("/order-items/{order_item_id}", response_model=OrderItem, tags=["Order Items"])
def get_order_item(order_item_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT order_item_id, order_id, product_id, quantity, unit_price FROM order_items WHERE order_item_id = %s",
            (order_item_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
    return row


@app.post("/order-items", response_model=OrderItem, status_code=status.HTTP_201_CREATED, tags=["Order Items"])
def create_order_item(item: OrderItemCreate):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                   VALUES (%s, %s, %s, %s)
                   RETURNING order_item_id, order_id, product_id, quantity, unit_price""",
                (item.order_id, item.product_id, item.quantity, item.unit_price),
            )
            return cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "order_id or product_id does not reference an existing record")


@app.put("/order-items/{order_item_id}", response_model=OrderItem, tags=["Order Items"])
def update_order_item(order_item_id: int, item: OrderItemUpdate):
    fields = item.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [order_item_id]

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""UPDATE order_items SET {set_clause} WHERE order_item_id = %s
                    RETURNING order_item_id, order_id, product_id, quantity, unit_price""",
                values,
            )
            row = cur.fetchone()
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "order_id or product_id does not reference an existing record")

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
    return row


@app.delete("/order-items/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Order Items"])
def delete_order_item(order_item_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM order_items WHERE order_item_id = %s RETURNING order_item_id", (order_item_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order item not found")
