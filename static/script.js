const API = "/api/items";
const form = document.getElementById("itemForm");
const list = document.getElementById("items");
const filters = document.querySelectorAll(".filter");
const search = document.getElementById("search");

let items = [];
let currentFilter = "all";
let searchText = "";

async function fetchItems() {
  const res = await fetch(API);
  items = await res.json();
  render();
}

function filterItems() {
  return items.filter(i => {
    const catOk = currentFilter === "all" ? true : i.category === currentFilter;
    const txt = (i.title + " " + i.description).toLowerCase();
    const searchOk = !searchText || txt.includes(searchText);
    return catOk && searchOk;
  });
}

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString();
}

function itemHTML(i) {
  return `
    <li class="item">
      <div class="meta">
        <span class="badge ${i.category}">${i.category.toUpperCase()}</span>
        <span class="title">${escapeHTML(i.title)}</span>
      </div>
      <div class="desc">${escapeHTML(i.description)}</div>
      <div class="foot">
        <span>Location: ${i.location ? escapeHTML(i.location) : "—"} • Contact: ${escapeHTML(i.contact)}</span>
        <span>${fmtDate(i.created_at)}</span>
      </div>
      <div style="margin-top:8px;">
        <button class="delete" onclick="deleteItem(${i.id})">Delete</button>
      </div>
    </li>
  `;
}

function render() {
  const filtered = filterItems();
  list.innerHTML = filtered.map(itemHTML).join("") || "<p style='color:#9ca3af'>No items yet.</p>";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: form.title.value.trim(),
    category: form.category.value.trim(),
    location: form.location.value.trim(),
    description: form.description.value.trim(),
    contact: form.contact.value.trim()
  };
  if (!payload.title || !payload.category || !payload.description || !payload.contact) {
    alert("Please fill in all required fields.");
    return;
  }
  const res = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const msg = await res.json().catch(() => ({}));
    alert(msg.error || "Failed to add item.");
    return;
  }
  form.reset();
  await fetchItems();
});

filters.forEach(btn => {
  btn.addEventListener("click", () => {
    filters.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    render();
  });
});

search.addEventListener("input", () => {
  searchText = search.value.trim().toLowerCase();
  render();
});

async function deleteItem(id) {
  if (!confirm("Delete this item?")) return;
  const res = await fetch(`${API}/${id}`, { method: "DELETE" });
  if (res.ok) {
    items = items.filter(i => i.id !== id);
    render();
  } else {
    alert("Failed to delete item.");
  }
}

// Simple HTML escaper to prevent XSS in the demo
function escapeHTML(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

fetchItems();
