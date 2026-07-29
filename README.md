# Sample Store REST API and FAST API

A REST API built with **FastAPI** for the `sample_store` PostgreSQL database
(the one created by `setup_sample_db.py`). Provides full CRUD endpoints for
`customers`, `products`, `orders`, and `order_items`.

## Setup

1. Make sure the database already exists (run `setup_sample_db.py` first if you haven't).
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Open `main.py` and edit the `CONFIG` section near the top (`DB_NAME`, `DB_USER`,
   `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) to match your PostgreSQL credentials.

## Run

```
uvicorn main:app --reload
```

If `uvicorn.exe` gets blocked by a Windows Application Control policy (same
issue as with Streamlit), run it as a module instead:

```
python -m uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Interactive docs

FastAPI auto-generates interactive API docs — open these in your browser to
try every endpoint without writing any code:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Endpoints

| Resource     | Method | Path                          | Description                    |
|--------------|--------|--------------------------------|---------------------------------|
| Customers    | GET    | `/customers`                  | List all customers             |
| Customers    | GET    | `/customers/{id}`             | Get one customer                |
| Customers    | POST   | `/customers`                  | Create a customer               |
| Customers    | PUT    | `/customers/{id}`             | Update a customer (partial ok)  |
| Customers    | DELETE | `/customers/{id}`             | Delete a customer               |
| Products     | GET    | `/products`                   | List all products               |
| Products     | GET    | `/products/{id}`              | Get one product                 |
| Products     | POST   | `/products`                   | Create a product                |
| Products     | PUT    | `/products/{id}`              | Update a product (partial ok)   |
| Products     | DELETE | `/products/{id}`              | Delete a product                |
| Orders       | GET    | `/orders`                     | List all orders                 |
| Orders       | GET    | `/orders/{id}`                | Get one order                   |
| Orders       | GET    | `/orders/{id}/items`          | List items for an order         |
| Orders       | POST   | `/orders`                     | Create an order                 |
| Orders       | PUT    | `/orders/{id}`                | Update an order (partial ok)    |
| Orders       | DELETE | `/orders/{id}`                | Delete an order                 |
| Order Items  | GET    | `/order-items`                | List all order items            |
| Order Items  | GET    | `/order-items/{id}`           | Get one order item              |
| Order Items  | POST   | `/order-items`                | Create an order item            |
| Order Items  | PUT    | `/order-items/{id}`           | Update an order item (partial)  |
| Order Items  | DELETE | `/order-items/{id}`           | Delete an order item            |

`PUT` endpoints accept partial payloads — only send the fields you want to change.

## Example requests

Create a customer:
```bash
curl -X POST http://127.0.0.1:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Dana", "last_name": "Lee", "email": "dana.lee@example.com"}'
```

Create an order for that customer:
```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "status": "pending"}'
```

Update a product's stock:
```bash
curl -X PUT http://127.0.0.1:8000/products/2 \
  -H "Content-Type: application/json" \
  -d '{"stock_qty": 75}'
```

## Notes

- Errors return standard HTTP status codes: `404` (not found), `400`/`409`
  (invalid or conflicting foreign key references), `409` (duplicate email).
- Deleting a customer/product that's referenced by existing orders/order_items
  will be blocked with a `409 Conflict` — delete the dependent records first.
- This is a local development setup (no authentication). Do not expose it to
  the public internet as-is — add an auth layer (e.g. API keys or OAuth2)
  before deploying anywhere reachable outside your machine.
