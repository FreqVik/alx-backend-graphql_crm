import requests
from datetime import datetime, timedelta

GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"

def fetch_recent_orders():
    """Query GraphQL endpoint for orders from the last 7 days."""
    query = """
    query GetRecentOrders($startDate: DateTime!) {
        orders(orderDate_Gte: $startDate, status: "PENDING") {
            id
            customer {
                email
            }
        }
    }
    """
    start_date = (datetime.now() - timedelta(days=7)).isoformat()
    response = requests.post(
        GRAPHQL_ENDPOINT,
        json={"query": query, "variables": {"startDate": start_date}},
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise Exception(f"GraphQL query failed: {response.text}")

    data = response.json()
    return data.get("data", {}).get("orders", [])


def log_orders(orders):
    """Log each order’s ID and customer email with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        for order in orders:
            email = order["customer"]["email"]
            order_id = order["id"]
            f.write(f"[{timestamp}] Reminder for Order {order_id} - {email}\n")


if __name__ == "__main__":
    try:
        orders = fetch_recent_orders()
        if orders:
            log_orders(orders)
        print("Order reminders processed!")
    except Exception as e:
        print(f"Error: {e}")
