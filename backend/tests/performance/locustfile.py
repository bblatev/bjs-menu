"""Load testing with Locust (H5.1).

Usage: locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, tag


class POSUser(HttpUser):
    """Simulates a restaurant POS user (highest traffic)."""

    wait_time = between(1, 3)
    weight = 5

    def on_start(self):
        """Login and get auth session."""
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

    @tag("menu")
    @task(5)
    def get_menu(self):
        self.client.get("/api/v1/menu/items", headers=self.headers)

    @tag("menu")
    @task(2)
    def get_menu_categories(self):
        self.client.get("/api/v1/menu/categories", headers=self.headers)

    @tag("orders")
    @task(3)
    def get_orders(self):
        self.client.get("/api/v1/orders", headers=self.headers)

    @tag("orders")
    @task(3)
    def create_guest_order(self):
        self.client.post("/api/v1/orders/guest", json={
            "items": [{"menu_item_id": 1, "quantity": 1}],
            "table_number": 1,
        })

    @tag("inventory")
    @task(2)
    def get_stock(self):
        self.client.get("/api/v1/stock/items", headers=self.headers)

    @tag("inventory")
    @task(1)
    def get_inventory_levels(self):
        self.client.get("/api/v1/inventory", headers=self.headers)

    @tag("kitchen")
    @task(2)
    def get_kitchen_orders(self):
        self.client.get("/api/v1/kitchen/orders", headers=self.headers)

    @tag("pos")
    @task(2)
    def get_pos_status(self):
        self.client.get("/api/v1/pos/status", headers=self.headers)

    @tag("analytics")
    @task(1)
    def get_analytics_dashboard(self):
        self.client.get("/api/v1/analytics/dashboard", headers=self.headers)

    @tag("reports")
    @task(1)
    def get_daily_report(self):
        self.client.get("/api/v1/reports/daily", headers=self.headers)

    @tag("customers")
    @task(1)
    def get_customers(self):
        self.client.get("/api/v1/customers", headers=self.headers)

    @tag("health")
    @task(1)
    def health_check(self):
        self.client.get("/health/ready")


class ManagerUser(HttpUser):
    """Simulates a manager reviewing analytics, reports, and settings."""

    wait_time = between(3, 8)
    weight = 2

    def on_start(self):
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

    @tag("analytics")
    @task(3)
    def get_analytics(self):
        self.client.get("/api/v1/analytics/dashboard", headers=self.headers)

    @tag("reports")
    @task(2)
    def get_sales_report(self):
        self.client.get("/api/v1/reports/daily", headers=self.headers)

    @tag("staff")
    @task(2)
    def get_staff_list(self):
        self.client.get("/api/v1/staff", headers=self.headers)

    @tag("audit")
    @task(1)
    def get_audit_logs(self):
        self.client.get("/api/v1/audit-logs", headers=self.headers)

    @tag("settings")
    @task(1)
    def get_settings(self):
        self.client.get("/api/v1/settings", headers=self.headers)

    @tag("financial")
    @task(2)
    def get_financial_summary(self):
        self.client.get("/api/v1/financial/summary", headers=self.headers)

    @tag("inventory")
    @task(1)
    def get_inventory_intelligence(self):
        self.client.get("/api/v1/inventory-intelligence/abc-analysis", headers=self.headers)


class GuestUser(HttpUser):
    """Simulates guest/public traffic (menu browsing, ordering)."""

    wait_time = between(2, 5)
    weight = 3

    @tag("menu", "guest")
    @task(5)
    def browse_menu(self):
        self.client.get("/api/v1/menu/items")

    @tag("menu", "guest")
    @task(3)
    def browse_categories(self):
        self.client.get("/api/v1/menu/categories")

    @tag("orders", "guest")
    @task(2)
    def place_guest_order(self):
        self.client.post("/api/v1/orders/guest", json={
            "items": [{"menu_item_id": 1, "quantity": 2}],
            "table_number": 5,
        })

    @tag("health")
    @task(1)
    def health_check(self):
        self.client.get("/health/ready")
