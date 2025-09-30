require("dotenv").config();
const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const Item = require("./models/Item");  // <-- add this

const app = express();
app.use(cors());
app.use(express.json());

// Connect to MongoDB (already in your file)
mongoose.connect(process.env.MONGO_URI)
  .then(async () => {
    console.log("MongoDB connected");
    // ensure indexes (runs fast; safe to call at startup)
    await Item.syncIndexes();
  })
  .catch((err) => {
    console.error("MongoDB connection error:", err.message);
    process.exit(1);
  });

// Health check
app.get("/", (_req, res) => res.send("Lost & Found backend running"));

// Create an item (LOST or FOUND)
app.post("/api/items", async (req, res) => {
  try {
    const item = await Item.create(req.body);
    res.status(201).json(item);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// List items with filters: status, category, search, date range, active
app.get("/api/items", async (req, res) => {
  const { status, category, search, from, to, active } = req.query;
  const q = {};
  if (status) q.status = status;
  if (category) q.category = category;
  if (active !== undefined) q.active = active === "true";
  if (from || to) {
    q.dateLostOrFound = {};
    if (from) q.dateLostOrFound.$gte = new Date(from);
    if (to) q.dateLostOrFound.$lte = new Date(to);
  }

  let query = Item.find(q).sort({ createdAt: -1 }).limit(100);
  if (search) query = query.find({ $text: { $search: search } });

  const items = await query.exec();
  res.json(items);
});

// Read one
app.get("/api/items/:id", async (req, res) => {
  const item = await Item.findById(req.params.id);
  if (!item) return res.status(404).json({ error: "Not found" });
  res.json(item);
});

// Update (partial)
app.patch("/api/items/:id", async (req, res) => {
  try {
    const item = await Item.findByIdAndUpdate(req.params.id, req.body, {
      new: true,
      runValidators: true,
    });
    if (!item) return res.status(404).json({ error: "Not found" });
    res.json(item);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Soft delete (mark inactive)
app.delete("/api/items/:id", async (req, res) => {
  const item = await Item.findByIdAndUpdate(req.params.id, { active: false }, { new: true });
  if (!item) return res.status(404).json({ error: "Not found" });
  res.json({ ok: true, item });
});

// Convenience endpoints
app.get("/api/lost", async (_req, res) => {
  const items = await Item.find({ status: "lost", active: true }).sort({ createdAt: -1 }).limit(100);
  res.json(items);
});
app.get("/api/found", async (_req, res) => {
  const items = await Item.find({ status: "found", active: true }).sort({ createdAt: -1 }).limit(100);
  res.json(items);
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
