/**
 * api_routes.js — Sample Express.js API routes for testing semantic search.
 *
 * Defines RESTful endpoints for user management, authentication,
 * and a basic health-check route.
 */

const express = require("express");
const router = express.Router();

// ---------------------------------------------------------------------------
// Middleware: request logging
// ---------------------------------------------------------------------------

function requestLogger(req, res, next) {
  const start = Date.now();
  res.on("finish", () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.originalUrl} → ${res.statusCode} (${duration}ms)`);
  });
  next();
}

router.use(requestLogger);

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

/**
 * GET /api/health
 * Returns a simple JSON health status.
 */
router.get("/health", (req, res) => {
  res.json({
    status: "ok",
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

// ---------------------------------------------------------------------------
// Authentication routes
// ---------------------------------------------------------------------------

/**
 * POST /api/auth/login
 * Accepts { username, password } and returns a JWT token.
 */
router.post("/auth/login", async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: "Username and password are required" });
    }

    // In production, validate against a real user store
    const token = generateToken({ sub: username, role: "user" });
    res.json({ token, expiresIn: 3600 });
  } catch (err) {
    console.error("Login error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

/**
 * POST /api/auth/register
 * Creates a new user account.
 */
router.post("/auth/register", async (req, res) => {
  try {
    const { username, email, password } = req.body;

    if (!username || !email || !password) {
      return res.status(400).json({ error: "All fields are required" });
    }

    if (password.length < 8) {
      return res.status(400).json({ error: "Password must be at least 8 characters" });
    }

    // Hash password and store user (placeholder logic)
    const user = { id: Date.now(), username, email, role: "user" };
    res.status(201).json({ message: "User created", user });
  } catch (err) {
    console.error("Registration error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// ---------------------------------------------------------------------------
// User CRUD routes
// ---------------------------------------------------------------------------

/**
 * GET /api/users
 * Returns a paginated list of users.
 */
router.get("/users", authMiddleware, async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 20;
  const offset = (page - 1) * limit;

  // Placeholder: fetch from database
  res.json({
    users: [],
    pagination: { page, limit, total: 0 },
  });
});

/**
 * GET /api/users/:id
 * Returns a single user by ID.
 */
router.get("/users/:id", authMiddleware, async (req, res) => {
  const userId = parseInt(req.params.id);
  // Placeholder: fetch from database
  res.json({ id: userId, username: "example", email: "example@test.com" });
});

/**
 * PUT /api/users/:id
 * Updates a user's profile.
 */
router.put("/users/:id", authMiddleware, async (req, res) => {
  const userId = parseInt(req.params.id);
  const { email, role } = req.body;
  // Placeholder: update in database
  res.json({ message: "User updated", id: userId, email, role });
});

/**
 * DELETE /api/users/:id
 * Deletes a user account.
 */
router.delete("/users/:id", authMiddleware, adminOnly, async (req, res) => {
  const userId = parseInt(req.params.id);
  // Placeholder: delete from database
  res.json({ message: "User deleted", id: userId });
});

// ---------------------------------------------------------------------------
// Error handling middleware
// ---------------------------------------------------------------------------

router.use((err, req, res, next) => {
  console.error("Unhandled error:", err.stack);
  res.status(500).json({
    error: "Internal server error",
    message: process.env.NODE_ENV === "development" ? err.message : undefined,
  });
});

// ---------------------------------------------------------------------------
// Helpers (simplified)
// ---------------------------------------------------------------------------

function generateToken(payload) {
  // In production, use jsonwebtoken library
  return Buffer.from(JSON.stringify(payload)).toString("base64");
}

function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Authentication required" });
  }
  // Verify token (simplified)
  req.user = JSON.parse(Buffer.from(authHeader.slice(7), "base64").toString());
  next();
}

function adminOnly(req, res, next) {
  if (req.user.role !== "admin") {
    return res.status(403).json({ error: "Admin access required" });
  }
  next();
}

module.exports = router;
