"""Load testing with Locust (H5.1).

Usage: locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between


class POSUser(HttpUser):
    """Simulates a restaurant POS user."""

    wait_time = between(1, 3)

    def on_start(self):
        """Login and get auth token."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "admin123",
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    @task(5)
    def get_menu(self):
        self.client.get("/api/v1/menu/items", headers=self.headers)

    @task(3)
    def get_orders(self):
        self.client.get("/api/v1/orders", headers=self.headers)

    @task(2)
    def get_stock(self):
        self.client.get("/api/v1/stock/items", headers=self.headers)

    @task(1)
    def get_analytics_dashboard(self):
        self.client.get("/api/v1/analytics/dashboard", headers=self.headers)

    @task(3)
    def create_guest_order(self):
        self.client.post("/api/v1/orders/guest", json={
            "items": [{"menu_item_id": 1, "quantity": 1}],
            "table_number": 1,
        })

    @task(2)
    def get_kitchen_orders(self):
        self.client.get("/api/v1/kitchen/orders", headers=self.headers)

    @task(1)
    def get_customers(self):
        self.client.get("/api/v1/customers", headers=self.headers)

    @task(1)
    def health_check(self):
        self.client.get("/health/ready")
