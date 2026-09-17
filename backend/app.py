from http.server import BaseHTTPRequestHandler, HTTPServer
import boto3
import json
import os
import psycopg2


DB_HOST = os.getenv(
    "DB_HOST",
    "postgres.database-ns.svc.cluster.local"
)
DB_PORT = os.getenv("DB_PORT", "5432")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SECRET_NAME = os.getenv(
    "DB_SECRET_NAME",
    "devops-store/postgres"
)

def get_db_credentials():
    client = boto3.client(
        "secretsmanager",
        region_name=AWS_REGION
    )

    response = client.get_secret_value(
        SecretId=SECRET_NAME
    )

    secret = json.loads(response["SecretString"])

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


server = HTTPServer(("0.0.0.0", 8080), Handler)

print("Backend running on port 8080")

server.serve_forever()