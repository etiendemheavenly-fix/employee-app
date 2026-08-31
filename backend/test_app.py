import pytest
import os
from io import BytesIO
os.environ["DATABASE_URL"] = "sqlite:///test.db"

from app import app, db, Employee


@pytest.fixture
def client():
    """Create test client with fresh database."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def sample_employee(client):
    """Create a sample employee in the database."""
    with app.app_context():
        emp = Employee(
            name="John Doe",
            email="john@example.com",
            role="Engineer",
            department="Engineering",
        )
        db.session.add(emp)
        db.session.commit()
        return emp.id


class TestHealth:
    def test_health_check(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "healthy"
        assert data["db"] == "connected"


class TestGetEmployees:
    def test_list_empty(self, client):
        res = client.get("/api/employees")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_list_with_employees(self, client, sample_employee):
        res = client.get("/api/employees")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "John Doe"

    def test_get_single_employee(self, client, sample_employee):
        res = client.get(f"/api/employees/{sample_employee}")
        assert res.status_code == 200
        assert res.get_json()["email"] == "john@example.com"

    def test_get_nonexistent_employee(self, client):
        res = client.get("/api/employees/999")
        assert res.status_code == 404


class TestCreateEmployee:
    def test_create_employee(self, client):
        res = client.post("/api/employees", data={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "role": "Designer",
            "department": "Product",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Jane Doe"
        assert data["id"] is not None

    def test_create_missing_fields(self, client):
        res = client.post("/api/employees", data={"name": "Incomplete"})
        assert res.status_code == 400

    def test_create_duplicate_email(self, client, sample_employee):
        res = client.post("/api/employees", data={
            "name": "Duplicate",
            "email": "john@example.com",
            "role": "Test",
            "department": "Test",
        })
        assert res.status_code == 409

    def test_create_with_photo(self, client):
        data = {
            "name": "Photo User",
            "email": "photo@example.com",
            "role": "Tester",
            "department": "QA",
        }
        data["photo"] = (BytesIO(b"fake image"), "photo.jpg")
        res = client.post(
            "/api/employees",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 201
        assert res.get_json()["photo_url"] is not None
        assert "data:image" in res.get_json()["photo_url"]


class TestUpdateEmployee:
    def test_update_employee(self, client, sample_employee):
        res = client.put(f"/api/employees/{sample_employee}", data={
            "name": "John Updated",
            "role": "Senior Engineer",
        })
        assert res.status_code == 200
        assert res.get_json()["name"] == "John Updated"
        assert res.get_json()["role"] == "Senior Engineer"

    def test_update_nonexistent(self, client):
        res = client.put("/api/employees/999", data={"name": "Ghost"})
        assert res.status_code == 404


class TestDeleteEmployee:
    def test_delete_employee(self, client, sample_employee):
        res = client.delete(f"/api/employees/{sample_employee}")
        assert res.status_code == 200
        assert res.get_json()["message"] == "Employee deleted"

        # Verify deleted
        res = client.get(f"/api/employees/{sample_employee}")
        assert res.status_code == 404

    def test_delete_nonexistent(self, client):
        res = client.delete("/api/employees/999")
        assert res.status_code == 404
