from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/low_stock_updates_log.txt"

def update_low_stock():
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    try:
        transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=True, retries=3)
        client = Client(transport=transport, fetch_schema_from_transport=False)

        mutation = gql("""
            mutation {
                updateLowStockProducts {
                    message
                    updatedProducts {
                        name
                        stock
                    }
                }
            }
        """)

        response = client.execute(mutation)
        data = response["updateLowStockProducts"]

        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {data['message']}\n")
            for p in data.get("updatedProducts", []):
                f.write(f" - {p['name']}: new stock = {p['stock']}\n")

    except Exception as e:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] Error: {e}\n")
