const request = require("supertest");
const { app, pool, init } = require("./app");

beforeAll(async () => {
  await init();
  await pool.query("DELETE FROM employees");
});

afterAll(async () => {
  await pool.query("DELETE FROM employees");
  await pool.end();
});

beforeEach(async () => {
  await pool.query("DELETE FROM employees");
});

describe("GET /api/health", () => {
  test("returns healthy", async () => {
    const res = await request(app).get("/api/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("healthy");
    expect(res.body.db).toBe("connected");
  });
});

describe("GET /api/employees", () => {
  test("returns empty list", async () => {
    const res = await request(app).get("/api/employees");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  test("returns employees after insert", async () => {
    await pool.query(
      "INSERT INTO employees (name, email, role, department) VALUES ($1,$2,$3,$4)",
      ["John Doe", "john@example.com", "Engineer", "Engineering"]
    );
    const res = await request(app).get("/api/employees");
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(1);
    expect(res.body[0].name).toBe("John Doe");
  });
});

describe("GET /api/employees/:id", () => {
  test("returns 404 for missing employee", async () => {
    const res = await request(app).get("/api/employees/9999");
    expect(res.status).toBe(404);
  });

  test("returns employee by id", async () => {
    const insert = await pool.query(
      "INSERT INTO employees (name, email, role, department) VALUES ($1,$2,$3,$4) RETURNING id",
      ["Jane Doe", "jane@example.com", "Designer", "Product"]
    );
    const res = await request(app).get(`/api/employees/${insert.rows[0].id}`);
    expect(res.status).toBe(200);
    expect(res.body.email).toBe("jane@example.com");
  });
});

describe("POST /api/employees", () => {
  test("creates employee", async () => {
    const res = await request(app)
      .post("/api/employees")
      .field("name", "Alice")
      .field("email", "alice@example.com")
      .field("role", "Lead")
      .field("department", "Engineering");
    expect(res.status).toBe(201);
    expect(res.body.id).toBeDefined();
    expect(res.body.name).toBe("Alice");
  });

  test("returns 400 for missing fields", async () => {
    const res = await request(app)
      .post("/api/employees")
      .field("name", "Incomplete");
    expect(res.status).toBe(400);
  });

  test("returns 409 for duplicate email", async () => {
    await pool.query(
      "INSERT INTO employees (name, email, role, department) VALUES ($1,$2,$3,$4)",
      ["Bob", "bob@example.com", "Manager", "Sales"]
    );
    const res = await request(app)
      .post("/api/employees")
      .field("name", "Bob2")
      .field("email", "bob@example.com")
      .field("role", "Manager")
      .field("department", "Sales");
    expect(res.status).toBe(409);
  });

  test("creates employee with photo", async () => {
    const res = await request(app)
      .post("/api/employees")
      .field("name", "Photo User")
      .field("email", "photo@example.com")
      .field("role", "Tester")
      .field("department", "QA")
      .attach("photo", Buffer.from("fake image data"), "photo.jpg");
    expect(res.status).toBe(201);
    expect(res.body.photo_url).toMatch(/^data:image\/jpeg;base64,/);
  });
});

describe("PUT /api/employees/:id", () => {
  test("updates employee", async () => {
    const insert = await pool.query(
      "INSERT INTO employees (name, email, role, department) VALUES ($1,$2,$3,$4) RETURNING id",
      ["Charlie", "charlie@example.com", "Junior", "Engineering"]
    );
    const res = await request(app)
      .put(`/api/employees/${insert.rows[0].id}`)
      .field("name", "Charlie Updated")
      .field("role", "Senior");
    expect(res.status).toBe(200);
    expect(res.body.name).toBe("Charlie Updated");
    expect(res.body.role).toBe("Senior");
  });

  test("returns 404 for missing employee", async () => {
    const res = await request(app)
      .put("/api/employees/9999")
      .field("name", "Ghost");
    expect(res.status).toBe(404);
  });
});

describe("DELETE /api/employees/:id", () => {
  test("deletes employee", async () => {
    const insert = await pool.query(
      "INSERT INTO employees (name, email, role, department) VALUES ($1,$2,$3,$4) RETURNING id",
      ["Dave", "dave@example.com", "VP", "Finance"]
    );
    const res = await request(app).delete(`/api/employees/${insert.rows[0].id}`);
    expect(res.status).toBe(200);
    expect(res.body.message).toBe("Employee deleted");
  });

  test("returns 404 for missing employee", async () => {
    const res = await request(app).delete("/api/employees/9999");
    expect(res.status).toBe(404);
  });
});
