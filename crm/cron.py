from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"

def log_crm_heartbeat():
    """Logs CRM health every 5 minutes and verifies GraphQL connectivity."""
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    status = "Unknown"

    try:
        # Configure gql transport
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=3,
        )

        client = Client(transport=transport, fetch_schema_from_transport=False)

        # Simple GraphQL query to check health
        query = gql("{ hello }")
        response = client.execute(query)
        status = f"GraphQL OK - Response: {response.get('hello', 'No reply')}"

    except Exception as e:
        status = f"GraphQL Error - {e}"

    # Append heartbeat message to log file
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} CRM is alive - {status}\n")
