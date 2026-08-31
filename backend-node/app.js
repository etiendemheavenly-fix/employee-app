const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");
const multer = require("multer");
const upload = multer({ storage: multer.memoryStorage() });

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://postgres:postgres@localhost:5432/employees",
});

// Create table on startup
async function init() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS employees (
      id SERIAL PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      email VARCHAR(100) UNIQUE NOT NULL,
      role VARCHAR(100) NOT NULL,
      department VARCHAR(100) NOT NULL,
      dob VARCHAR(10),
      photo_data BYTEA,
      photo_filename VARCHAR(255)
    )
  `);
  console.log("Database tables initialized");
}

// Helper: Convert photo data to base64 data URL
function convertPhotoToUrl(photoData) {
  if (!photoData) return null;
  return `data:image/jpeg;base64,${photoData.toString("base64")}`;
}

// Helper: Convert employee row to DTO
function employeeToDto(emp) {
  return {
    id: emp.id,
    name: emp.name,
    email: emp.email,
    role: emp.role,
    department: emp.department,
    dob: emp.dob,
    photo_url: convertPhotoToUrl(emp.photo_data),
  };
}

// GET /api/health
app.get("/api/health", async (req, res) => {
  try {
    await pool.query("SELECT 1");
    res.json({ status: "healthy", db: "connected" });
  } catch (e) {
    res.status(503).json({ status: "unhealthy", db: "disconnected" });
  }
});

// GET /api/employees
app.get("/api/employees", async (req, res) => {
  const result = await pool.query("SELECT * FROM employees ORDER BY name");
  res.json(result.rows.map(employeeToDto));
});

// GET /api/employees/:id
app.get("/api/employees/:id", async (req, res) => {
  const result = await pool.query("SELECT * FROM employees WHERE id = $1", [req.params.id]);
  if (result.rows.length === 0) return res.status(404).json({ error: "Not found" });
  res.json(employeeToDto(result.rows[0]));
});

// POST /api/employees
app.post("/api/employees", upload.single("photo"), async (req, res) => {
  const { name, email, role, department, dob } = req.body;
  if (!name || !email || !role || !department) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  try {
    const existing = await pool.query("SELECT id FROM employees WHERE email = $1", [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: "Email already exists" });
    }
    
    const photoData = req.file ? req.file.buffer : null;
    const photoFilename = req.file ? req.file.originalname : null;
    
    const result = await pool.query(
      "INSERT INTO employees (name, email, role, department, dob, photo_data, photo_filename) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *",
      [name, email, role, department, dob || null, photoData, photoFilename]
    );
    res.status(201).json(employeeToDto(result.rows[0]));
  } catch (e) {
    if (e.code === "23505") return res.status(409).json({ error: "Email already exists" });
    throw e;
  }
});

// PUT /api/employees/:id
app.put("/api/employees/:id", upload.single("photo"), async (req, res) => {
  const existing = await pool.query("SELECT * FROM employees WHERE id = $1", [req.params.id]);
  if (existing.rows.length === 0) return res.status(404).json({ error: "Not found" });
  const emp = existing.rows[0];
  const { name, email, role, department, dob } = req.body;
  
  const photoData = req.file ? req.file.buffer : emp.photo_data;
  const photoFilename = req.file ? req.file.originalname : emp.photo_filename;
  
  const result = await pool.query(
    "UPDATE employees SET name=$1, email=$2, role=$3, department=$4, dob=$5, photo_data=$6, photo_filename=$7 WHERE id=$8 RETURNING *",
    [name || emp.name, email || emp.email, role || emp.role, department || emp.department,
     dob || emp.dob, photoData, photoFilename, req.params.id]
  );
  res.json(employeeToDto(result.rows[0]));
});

// DELETE /api/employees/:id
app.delete("/api/employees/:id", async (req, res) => {
  const result = await pool.query("DELETE FROM employees WHERE id = $1 RETURNING *", [req.params.id]);
  if (result.rows.length === 0) return res.status(404).json({ error: "Not found" });
  res.json({ message: "Employee deleted" });
});

// GET /api/stats
app.get("/api/stats", async (req, res) => {
  const total = await pool.query("SELECT COUNT(*) FROM employees");
  const depts = await pool.query("SELECT department, COUNT(id) FROM employees GROUP BY department");
  const latest = await pool.query("SELECT * FROM employees ORDER BY id DESC LIMIT 1");
  const departments = {};
  depts.rows.forEach(r => { departments[r.department] = parseInt(r.count); });
  res.json({
    total_employees: parseInt(total.rows[0].count),
    departments,
    latest_hire: latest.rows[0] ? employeeToDto(latest.rows[0]) : null,
    version: "2.0.0",
  });
});

const PORT = process.env.PORT || 5000;

if (require.main === module) {
  init().then(() => {
    app.listen(PORT, () => console.log(`Backend running on http://localhost:${PORT}`));
  });
}

module.exports = { app, pool, init };
