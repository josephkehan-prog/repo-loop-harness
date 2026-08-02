"use strict";

const byId = (id) => document.getElementById(id);
const refreshButton = byId("refresh");
const toast = byId("toast");
let currentDigest = "";
let toastTimer;

function setText(id, value) {
  byId(id).textContent = value;
}

function textOr(items, fallback = "none detected") {
  return items.length ? items.join(", ") : fallback;
}

function showToast(message, error = false) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.classList.add("visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 1800);
}

function addDefinitionList(targetId, values) {
  const target = byId(targetId);
  target.replaceChildren();
  for (const [label, value] of Object.entries(values)) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label.replaceAll("_", " ");
    description.textContent = String(value);
    row.append(term, description);
    target.append(row);
  }
}

function addLedgerRows(targetId, items, keyName, valueName, emptyMessage) {
  const target = byId(targetId);
  target.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = emptyMessage;
    target.append(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    const key = document.createElement("span");
    const value = document.createElement("code");
    row.className = "ledger-row";
    key.className = "ledger-key";
    value.className = "ledger-value";
    key.textContent = item[keyName];
    value.textContent = item[valueName];
    row.append(key, value);
    target.append(row);
  }
}

function render(payload) {
  const repository = payload.repository;
  const capsule = payload.capsule;
  currentDigest = payload.digest;
  setText("repository-name", repository.name);
  setText("repository-path", repository.path);
  setText("branch", repository.branch || "detached / unversioned");
  setText("revision", repository.head ? repository.head.slice(0, 12) : "unversioned");
  setText(
    "working-tree",
    repository.dirty ? `dirty · ${repository.dirty_paths.length} paths` : "clean",
  );
  setText("runtime-state", payload.runtime.state);
  setText("digest-short", payload.digest.slice(0, 12));
  setText("digest", payload.digest);
  setText("capsule-id", capsule.id);
  setText("trust", capsule.trust);
  setText("languages", textOr(payload.stack.languages));
  setText("package-tools", textOr(payload.stack.package_managers));
  setText("command-count", String(payload.commands.length).padStart(2, "0"));
  setText("evidence-count", String(payload.evidence.length).padStart(2, "0"));

  addLedgerRows("commands", payload.commands, "name", "command", "No executable commands discovered.");
  addLedgerRows("evidence", payload.evidence, "fact", "path", "No stack evidence discovered.");
  addDefinitionList("permissions", capsule.permissions);
  addDefinitionList("loop-limits", capsule.loop);

  const checks = byId("completion-checks");
  checks.replaceChildren();
  const required = capsule.verification.completion_requires;
  for (const check of required.length ? required : ["none discovered"]) {
    const item = document.createElement("li");
    item.textContent = check;
    checks.append(item);
  }
}

async function refresh() {
  refreshButton.disabled = true;
  setText("scan-state", "Scanning repository");
  try {
    const response = await fetch("/api/dashboard", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`scan returned ${response.status}`);
    render(await response.json());
    setText("scan-state", "Repository facts current");
  } catch (error) {
    setText("scan-state", "Scan failed");
    showToast(`Unable to refresh: ${error.message}`, true);
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", refresh);
byId("copy-digest").addEventListener("click", async () => {
  if (!currentDigest) return;
  try {
    await navigator.clipboard.writeText(currentDigest);
    showToast("Digest copied");
  } catch {
    showToast("Clipboard unavailable", true);
  }
});

refresh();
