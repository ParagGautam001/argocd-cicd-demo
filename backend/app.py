from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import psycopg2
from openai import OpenAI



DB_HOST = os.getenv(
    "DB_HOST",
    "postgres.database-ns.svc.cluster.local"
)
DB_PORT = os.getenv("DB_PORT", "5432")


SECRET_FILE = "/mnt/secrets/devops-store_postgres"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=30.0
) if OPENROUTER_API_KEY else None

def get_db_credentials():
    with open(SECRET_FILE, "r") as f:
        secret = json.load(f)

    return (
        secret["username"],
        secret["password"],
        secret["database"]
    )


def get_connection():
    username, password, database = get_db_credentials()

    return psycopg2.connect(
        host=os.getenv(
            "DB_HOST",
            "postgres.database-ns.svc.cluster.local"
        ),
        database=database,
        user=username,
        password=password,
        port=os.getenv("DB_PORT", "5432")
    )

class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        response = json.dumps(data).encode()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

    def do_GET(self):

        if self.path == "/live":
            self.send_json({
                "status": "alive",
                "service": "backend",
                "version": "v3"
            })
            return

        if self.path == "/health":
            try:
                conn = get_connection()
                conn.close()

                self.send_json({
                    "status": "healthy",
                    "service": "backend",
                    "database": "connected",
                    "version": "v3"
                })

            except Exception as e:
                self.send_json({
                    "status": "unhealthy",
                    "service": "backend",
                    "database": "disconnected"
                }, 503)

            return

        if self.path == "/api/products":
            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, name, price, category, description
                    FROM products
                    ORDER BY id
                """)

                rows = cursor.fetchall()

                products = []

                for row in rows:
                    products.append({
                        "id": row[0],
                        "name": row[1],
                        "price": row[2],
                        "category": row[3],
                        "description": row[4]
                    })

                cursor.close()
                conn.close()

                self.send_json({
                    "products": products,
                    "count": len(products)
                })

            except Exception as e:
                self.send_json({
                    "error": "Database connection failed"
                }, 500)

            return

        if self.path == "/api/info":
            self.send_json({
                "application": "DevOps Store",
                "service": "backend",
                "version": "v3",
                "database": "PostgreSQL"
            })
            return

        self.send_json({
            "error": "Endpoint not found"
        }, 404)

    def do_POST(self):

        if self.path != "/api/ai/chat":
            self.send_json({
                "error": "Endpoint not found"
            }, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            data = json.loads(body)
            message = data.get("message", "").strip()

            if not message:
                self.send_json({
                    "error": "Message is required"
                }, 400)
                return

            if client is None:
                self.send_json({
                    "error": "AI service is not configured"
                }, 503)
                return

            # Get current products from PostgreSQL
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, price, category, description
                FROM products
                ORDER BY id
            """)
 
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

            products = []

            for row in rows:
                products.append({
                    "id": row[0],
                    "name": row[1],
                    "price": float(row[2]),
                    "category": row[3],
                    "description": row[4]
                })

            product_context = json.dumps(products, indent=2)

            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the AI shopping assistant for DevOps Store. "
                            "Answer questions using ONLY the product inventory "
                            "provided below. Do not invent products, prices, or availability. "
                            "Be concise, friendly and practical.\n\n"
                            "CURRENT PRODUCT INVENTORY:\n"
                            + product_context
                        )
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=300
            )

            reply = response.choices[0].message.content

            self.send_json({
                "reply": reply
            })

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.send_json({
                "error": str(e)
            }, 500)

server = HTTPServer(("0.0.0.0", 8080), Handler)

print("Backend running on port 8080")

server.serve_forever()