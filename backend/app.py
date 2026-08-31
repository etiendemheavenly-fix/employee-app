import os
import logging
import time
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import watchtower
from werkzeug.utils import secure_filename
from prometheus_flask_exporter import PrometheusMetrics

# --- Configuration ---
LOG_GROUP = os.environ.get("LOG_GROUP", "/landmark/employee-app")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# --- App Setup ---
app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/employees"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db = SQLAlchemy(app)

# --- Logging Setup (stdout + CloudWatch) ---
logger = logging.getLogger("employee-app")
logger.setLevel(logging.INFO)

# Stdout handler - JSON format for container logs
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
))
logger.addHandler(stdout_handler)

# CloudWatch handler - streams to /landmark/employee-app log group (optional)
# Disabled for local development - boto3 not required


# --- Models ---
class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(10))
    photo_data = db.Column(db.LargeBinary)  # Store image as binary data
    photo_filename = db.Column(db.String(255))  # Store original filename

    def to_dict(self):
        import base64
        photo_url = None
        if self.photo_data:
            photo_url = f"data:image/jpeg;base64,{base64.b64encode(self.photo_data).decode()}"
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "dob": self.dob,
            "photo_url": photo_url,
        }


# Prometheus metrics
PrometheusMetrics(app)

# Create tables on startup
with app.app_context():
    try:
        db.create_all()
    except Exception:
        # Clean up orphaned sequences/tables left by a previous partial run
        db.session.rollback()
        db.session.execute(db.text("DROP TABLE IF EXISTS employees CASCADE"))
        db.session.execute(db.text("DROP SEQUENCE IF EXISTS employees_id_seq CASCADE"))
        db.session.commit()
        db.create_all()
    logger.info("Database tables initialized")


# --- Middleware ---
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    duration = round((time.time() - g.start_time) * 1000, 2)
    logger.info(
        f"{request.method} {request.path} - {response.status_code} - {duration}ms"
    )
    return response


# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(e):
    logger.warning(f"Bad request: {request.path} - {e}")
    return jsonify({"error": "Bad request", "message": str(e)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {request.path} - {e}")
    return jsonify({"error": "Internal server error"}), 500


# --- Helper ---
def store_photo(file):
    """Store a photo file in the database. Returns tuple of (photo_data, photo_filename)."""
    try:
        photo_data = file.read()
        photo_filename = secure_filename(file.filename)
        logger.info(f"Photo stored in database: {photo_filename} ({len(photo_data)} bytes)")
        return photo_data, photo_filename
    except Exception as e:
        logger.warning(f"Photo storage failed: {e}")
        return None, None


# --- Routes ---
@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "db": "connected"})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "db": "disconnected"}), 503


@app.route("/employees", methods=["GET"])
@app.route("/api/employees", methods=["GET"])
def get_employees():
    employees = Employee.query.order_by(Employee.name).all()
    logger.info(f"Listed {len(employees)} employees")
    return jsonify([e.to_dict() for e in employees])


@app.route("/employees/<int:id>", methods=["GET"])
@app.route("/api/employees/<int:id>", methods=["GET"])
def get_employee(id):
    employee = Employee.query.get_or_404(id)
    return jsonify(employee.to_dict())


@app.route("/employees", methods=["POST"])
@app.route("/api/employees", methods=["POST"])
def create_employee():
    data = request.form
    if not all(k in data for k in ("name", "email", "role", "department")):
        return jsonify({"error": "Missing required fields"}), 400

    # Check for duplicate email
    if Employee.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    photo_data, photo_filename = None, None
    if "photo" in request.files and request.files["photo"].filename:
        photo_data, photo_filename = store_photo(request.files["photo"])

    employee = Employee(
        name=data["name"],
        email=data["email"],
        role=data["role"],
        department=data["department"],
        dob=data.get("dob"),
        photo_data=photo_data,
        photo_filename=photo_filename,
    )
    db.session.add(employee)
    db.session.commit()
    logger.info(f"Employee created: id={employee.id} email={employee.email}")
    return jsonify(employee.to_dict()), 201


@app.route("/employees/<int:id>", methods=["PUT"])
@app.route("/api/employees/<int:id>", methods=["PUT"])
def update_employee(id):
    employee = Employee.query.get_or_404(id)
    data = request.form

    employee.name = data.get("name") or employee.name
    employee.email = data.get("email") or employee.email
    employee.role = data.get("role") or employee.role
    employee.department = data.get("department") or employee.department
    employee.dob = data.get("dob") or employee.dob

    if "photo" in request.files and request.files["photo"].filename:
        photo_data, photo_filename = store_photo(request.files["photo"])
        if photo_data:
            employee.photo_data = photo_data
            employee.photo_filename = photo_filename

    db.session.commit()
    logger.info(f"Employee updated: id={employee.id}")
    return jsonify(employee.to_dict())


@app.route("/employees/<int:id>", methods=["DELETE"])
@app.route("/api/employees/<int:id>", methods=["DELETE"])
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    logger.info(f"Employee deleted: id={id} email={employee.email}")
    return jsonify({"message": "Employee deleted"})


@app.route("/stats", methods=["GET"])
@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns employee stats: total count, department breakdown, latest hire."""
    total = Employee.query.count()
    departments = db.session.query(
        Employee.department, db.func.count(Employee.id)
    ).group_by(Employee.department).all()
    latest = Employee.query.order_by(Employee.id.desc()).first()

    stats = {
        "total_employees": total,
        "departments": {dept: count for dept, count in departments},
        "latest_hire": latest.to_dict() if latest else None,
        "version": "2.0.0",
    }
    logger.info(f"Stats requested: {total} employees across {len(departments)} departments")
    return jsonify(stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
