// API Configuration
const API_BASE = "/api";

const STAT_META = {
  strength:     { icon: "⚔️", label: "STR", color: "#ef4444" },
  stamina:      { icon: "🛡️", label: "STA", color: "#f97316" },
  intelligence: { icon: "🧠", label: "INT", color: "#3b82f6" },
  agility:      { icon: "💨", label: "AGI", color: "#22d3ee" },
  vitality:     { icon: "❤️", label: "VIT", color: "#10b981" },
  dexterity:    { icon: "🎯", label: "DEX", color: "#a855f7" },
  faith:        { icon: "✨", label: "FTH", color: "#f59e0b" },
  luck:         { icon: "🍀", label: "LCK", color: "#84cc16" },
};

const SCALING_FACTORS = { S: 0.03, A: 0.02, B: 0.015, C: 0.01 };

function computeMultiplier(statLevel, requirement, grade) {
  if (statLevel < requirement) return 0.5;
  return 1.0 + (statLevel - requirement) * (SCALING_FACTORS[grade] || 0.01);
}

// State
let player = { level: 1, current_xp: 0, gold: 0, xp_current_level: 0, xp_next_level: 100 };
let tasks = [];
let rewards = [];
let items = [];

// --- DOM ELEMENTS ---
const elements = {
  levelBadge: document.getElementById("level-badge"),
  goldAmount: document.getElementById("gold-amount"),
  xpProgress: document.getElementById("xp-progress"),
  xpText: document.getElementById("xp-text"),
  tasksList: document.getElementById("tasks-list"),
  rewardsList: document.getElementById("rewards-list"),
  
  // Tab Elements
  tabTasks: document.getElementById("tab-tasks"),
  tabStats: document.getElementById("tab-stats"),
  tabJourney: document.getElementById("tab-journey"),
  tabCharacter: document.getElementById("tab-character"),
  tabShop: document.getElementById("tab-shop"),
  panelTasks: document.getElementById("panel-tasks"),
  panelStats: document.getElementById("panel-stats"),
  panelJourney: document.getElementById("panel-journey"),
  panelCharacter: document.getElementById("panel-character"),
  panelShop: document.getElementById("panel-shop"),
  weaponIndicator: document.getElementById("weapon-indicator"),
  modalItemPicker: document.getElementById("modal-item-picker"),
  closeItemPicker: document.getElementById("close-item-picker"),
  itemPickerTitle: document.getElementById("item-picker-title"),
  itemPickerList: document.getElementById("item-picker-list"),

  // Stats view fields
  statLevel: document.getElementById("stat-level"),
  statGold: document.getElementById("stat-gold"),
  statXp: document.getElementById("stat-xp"),
  statTotalTasks: document.getElementById("stat-total-tasks"),

  // Modals
  modalTask: document.getElementById("modal-task"),
  modalReward: document.getElementById("modal-reward"),
  btnAddTask: document.getElementById("btn-add-task"),
  btnAddReward: document.getElementById("btn-add-reward"),
  closeTaskModal: document.getElementById("close-task-modal"),
  closeRewardModal: document.getElementById("close-reward-modal"),
  formTask: document.getElementById("form-task"),
  formReward: document.getElementById("form-reward")
};

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupModals();
  fetchInitialData();
  registerServiceWorker();
});

// --- SERVICE WORKER REGISTRATION ---
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js?v=3")
        .then(reg => {
          reg.update();
          console.log("Service Worker registered:", reg.scope);
        })
        .catch(err => console.error("Service Worker registration failed:", err));
    });
  }
}

// --- NAVIGATION & TABS ---
function setupNavigation() {
  const allTabs = [elements.tabTasks, elements.tabStats, elements.tabJourney, elements.tabCharacter, elements.tabShop];
  const allPanels = [elements.panelTasks, elements.panelStats, elements.panelJourney, elements.panelCharacter, elements.panelShop];

  const switchTab = (tabName) => {
    allTabs.forEach(t => t.classList.remove("active"));
    allPanels.forEach(p => p.classList.remove("active"));
    elements.btnAddTask.style.display = "none";
    elements.btnAddReward.style.display = "none";

    if (tabName === "tasks") {
      elements.tabTasks.classList.add("active");
      elements.panelTasks.classList.add("active");
      elements.btnAddTask.style.display = "flex";
      renderTasks();
    } else if (tabName === "stats") {
      elements.tabStats.classList.add("active");
      elements.panelStats.classList.add("active");
      renderStats();
    } else if (tabName === "journey") {
      elements.tabJourney.classList.add("active");
      elements.panelJourney.classList.add("active");
      renderJourney();
    } else if (tabName === "character") {
      elements.tabCharacter.classList.add("active");
      elements.panelCharacter.classList.add("active");
      renderCharacter();
    } else if (tabName === "shop") {
      elements.tabShop.classList.add("active");
      elements.panelShop.classList.add("active");
      elements.btnAddReward.style.display = "flex";
      renderRewards();
    }
  };

  elements.tabTasks.addEventListener("click", () => switchTab("tasks"));
  elements.tabStats.addEventListener("click", () => switchTab("stats"));
  elements.tabJourney.addEventListener("click", () => switchTab("journey"));
  elements.tabCharacter.addEventListener("click", () => switchTab("character"));
  elements.tabShop.addEventListener("click", () => switchTab("shop"));
  
  // Default to tasks tab
  switchTab("tasks");
}

// --- MODALS ---
function setupModals() {
  // Open Task Modal
  elements.btnAddTask.addEventListener("click", () => elements.modalTask.classList.add("active"));
  // Close Task Modal
  elements.closeTaskModal.addEventListener("click", () => elements.modalTask.classList.remove("active"));
  
  // Open Reward Modal
  elements.btnAddReward.addEventListener("click", () => elements.modalReward.classList.add("active"));
  // Close Reward Modal
  elements.closeRewardModal.addEventListener("click", () => elements.modalReward.classList.remove("active"));

  // Close Item Picker Modal
  elements.closeItemPicker.addEventListener("click", () => elements.modalItemPicker.classList.remove("active"));

  // Submit Task Form
  elements.formTask.addEventListener("submit", async (e) => {
    e.preventDefault();
    const statVal = document.getElementById("task-stat").value;
    const taskData = {
      title: document.getElementById("task-title").value,
      task_type: document.getElementById("task-type").value,
      xp_reward: parseInt(document.getElementById("task-xp").value) || 10,
      gold_reward: parseInt(document.getElementById("task-gold").value) || 5,
      stat_reward_type: statVal || null,
      stat_xp_reward: parseInt(document.getElementById("task-stat-xp").value) || 10,
    };

    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(taskData)
      });
      if (response.ok) {
        const newTask = await response.json();
        tasks.push(newTask);
        renderTasks();
        elements.modalTask.classList.remove("active");
        elements.formTask.reset();
      }
    } catch (err) {
      console.error("Error creating task:", err);
    }
  });

  // Submit Reward Form
  elements.formReward.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rewardData = {
      name: document.getElementById("reward-name").value,
      gold_cost: parseInt(document.getElementById("reward-gold-cost").value) || 10
    };

    try {
      const response = await fetch(`${API_BASE}/rewards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rewardData)
      });
      if (response.ok) {
        const newReward = await response.json();
        rewards.push(newReward);
        renderRewards();
        elements.modalReward.classList.remove("active");
        elements.formReward.reset();
      }
    } catch (err) {
      console.error("Error creating reward:", err);
    }
  });
}

// --- DATA FETCHING ---
async function fetchInitialData() {
  try {
    const [pRes, tRes, rRes, iRes] = await Promise.all([
      fetch(`${API_BASE}/player`),
      fetch(`${API_BASE}/tasks`),
      fetch(`${API_BASE}/rewards`),
      fetch(`${API_BASE}/items`),
    ]);

    if (pRes.ok) player = await pRes.json();
    if (tRes.ok) tasks = await tRes.json();
    if (rRes.ok) rewards = await rRes.json();
    if (iRes.ok) items = await iRes.json();

    updatePlayerHeader();
    renderTasks();
  } catch (err) {
    console.error("Error loading app data:", err);
  }
}

// --- HEADER RENDERING ---
function updatePlayerHeader() {
  elements.levelBadge.textContent = `Lvl ${player.level}`;
  elements.goldAmount.textContent = player.gold;

  const xpInLevel = player.current_xp - player.xp_current_level;
  const xpSpan = player.xp_next_level - player.xp_current_level;
  elements.xpProgress.max = xpSpan;
  elements.xpProgress.value = xpInLevel;
  elements.xpText.textContent = `${xpInLevel} / ${xpSpan} XP`;
}

// --- CORE UI RENDERING ---

// Render Tasks
function renderWeaponIndicator() {
  const el = elements.weaponIndicator;
  const w = player.loadout ? player.loadout.weapon : null;
  if (!w) {
    el.innerHTML = `<span class="wi-empty">No weapon equipped</span>`;
    return;
  }
  const meta = STAT_META[w.governing_stat];
  const statLevel = (player.stats && player.stats[w.governing_stat]) ? player.stats[w.governing_stat].level : 1;
  const mult = computeMultiplier(statLevel, w.stat_requirement, w.scaling_grade);
  const multClass = mult < 1 ? "wi-penalty" : mult > 1 ? "wi-bonus" : "";
  el.innerHTML = `
    <span class="wi-name">${meta ? meta.icon : "🗡️"} ${w.name}</span>
    <span class="wi-mult ${multClass}">${mult.toFixed(2)}x</span>
  `;
}

function renderTasks() {
  renderWeaponIndicator();
  elements.tasksList.innerHTML = "";
  const activeTasks = tasks.filter(t => !t.is_completed);

  if (activeTasks.length === 0) {
    elements.tasksList.innerHTML = `
      <div style="text-align: center; color: var(--color-text-secondary); padding: 40px 20px;">
        <p style="font-size: 1.1rem; margin-bottom: 8px; font-weight: 600;">All clear!</p>
        <p style="font-size: 0.85rem; color: var(--color-text-muted);">Create a daily task or quest to begin gamifying your life.</p>
      </div>
    `;
    return;
  }

  activeTasks.forEach(task => {
    const card = document.createElement("div");
    card.className = "card";
    const meta = task.stat_reward_type ? STAT_META[task.stat_reward_type] : null;
    const statBadge = meta
      ? `<span class="badge badge-stat" style="background-color: ${meta.color}20; color: ${meta.color};">${meta.icon} +${task.stat_xp_reward} ${meta.label}</span>`
      : "";
    card.innerHTML = `
      <div class="card-info">
        <div class="card-title">${task.title}</div>
        <div class="card-metadata">
          <span class="badge badge-${task.task_type}">${task.task_type}</span>
          ${statBadge}
          <span class="xp-preview">+${task.xp_reward} XP</span>
          <span class="gold-preview">+${task.gold_reward} G</span>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-complete" data-id="${task.id}">✓</button>
        <button class="btn btn-delete" data-id="${task.id}">×</button>
      </div>
    `;

    // Event listener for completion
    card.querySelector(".btn-complete").addEventListener("click", async (e) => {
      e.stopPropagation();
      await completeTask(task.id);
    });

    // Event listener for deletion
    card.querySelector(".btn-delete").addEventListener("click", async (e) => {
      e.stopPropagation();
      await deleteTask(task.id);
    });

    elements.tasksList.appendChild(card);
  });
}

// Complete Task Handler
async function completeTask(id) {
  try {
    const response = await fetch(`${API_BASE}/tasks/${id}/complete`, { method: "POST" });
    if (response.ok) {
      const data = await response.json();
      player = data.player;
      updatePlayerHeader();

      const taskIndex = tasks.findIndex(t => t.id === id);
      if (taskIndex !== -1) {
        tasks[taskIndex].is_completed = true;
      }
      renderTasks();

      if (data.level_ups && data.level_ups.length > 0) {
        showLevelUps(data.level_ups);
      }

      if (elements.panelStats.classList.contains("active")) {
        renderStats();
      }
    }
  } catch (err) {
    console.error("Error completing task:", err);
  }
}

function showLevelUps(levelUps) {
  levelUps.forEach((lu, i) => {
    const meta = STAT_META[lu.name];
    const label = meta ? `${meta.icon} ${lu.name}` : "⬆ Character";
    const color = meta ? meta.color : "var(--accent-primary)";
    const toast = document.createElement("div");
    toast.className = "level-up-toast";
    toast.style.borderColor = color;
    toast.style.top = `${16 + i * 52}px`;
    toast.innerHTML = `<span class="toast-label">${label}</span> leveled up! <span style="color: ${color};">Lvl ${lu.old_level} → ${lu.new_level}</span>`;
    document.getElementById("app-container").appendChild(toast);
    setTimeout(() => toast.classList.add("visible"), i * 150);
    setTimeout(() => {
      toast.classList.remove("visible");
      setTimeout(() => toast.remove(), 300);
    }, 2800 + i * 150);
  });
}

// Delete Task Handler
async function deleteTask(id) {
  try {
    const response = await fetch(`${API_BASE}/tasks/${id}`, { method: "DELETE" });
    if (response.ok) {
      tasks = tasks.filter(t => t.id !== id);
      renderTasks();
    }
  } catch (err) {
    console.error("Error deleting task:", err);
  }
}

// Render Shop Rewards
function renderRewards() {
  elements.rewardsList.innerHTML = "";
  
  if (rewards.length === 0) {
    elements.rewardsList.innerHTML = `
      <div style="text-align: center; color: var(--color-text-secondary); padding: 40px 20px;">
        <p style="font-size: 1.1rem; margin-bottom: 8px; font-weight: 600;">No items available</p>
        <p style="font-size: 0.85rem; color: var(--color-text-muted);">Create customized rewards to spend your gold on.</p>
      </div>
    `;
    return;
  }

  rewards.forEach(reward => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-info">
        <div class="card-title">${reward.name}</div>
        <div class="card-metadata">
          <span class="gold-preview">${reward.gold_cost} Gold</span>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-purchase" data-id="${reward.id}">Buy</button>
        <button class="btn btn-delete" data-id="${reward.id}">×</button>
      </div>
    `;

    // Event listener for purchase
    card.querySelector(".btn-purchase").addEventListener("click", async (e) => {
      e.stopPropagation();
      await purchaseReward(reward.id);
    });

    // Event listener for deletion
    card.querySelector(".btn-delete").addEventListener("click", async (e) => {
      e.stopPropagation();
      await deleteReward(reward.id);
    });

    elements.rewardsList.appendChild(card);
  });
}

// Purchase Reward Handler
async function purchaseReward(id) {
  try {
    const response = await fetch(`${API_BASE}/rewards/${id}/purchase`, { method: "POST" });
    if (response.ok) {
      player = await response.json();
      updatePlayerHeader();
      alert("Reward Purchased!");
    } else {
      const errData = await response.json();
      alert(errData.detail || "Unable to purchase reward.");
    }
  } catch (err) {
    console.error("Error purchasing reward:", err);
  }
}

// Delete Reward Handler
async function deleteReward(id) {
  try {
    const response = await fetch(`${API_BASE}/rewards/${id}`, { method: "DELETE" });
    if (response.ok) {
      rewards = rewards.filter(r => r.id !== id);
      renderRewards();
    }
  } catch (err) {
    console.error("Error deleting reward:", err);
  }
}

// --- CHARACTER / PAPER DOLL ---
const SLOT_ICONS = { Weapon: "🗡️", Armor: "🛡️", Artifact: "💎", Accessory: "💍" };

function renderCharacter() {
  const loadout = player.loadout || {};
  const stats = player.stats || {};
  const slots = ["Weapon", "Armor", "Artifact", "Accessory"];

  slots.forEach(slot => {
    const item = loadout[slot.toLowerCase()];
    const slotEl = document.getElementById(`doll-slot-${slot.toLowerCase()}`);
    const nameEl = document.getElementById(`slot-${slot.toLowerCase()}-name`);
    const statsEl = document.getElementById(`slot-${slot.toLowerCase()}-stats`);

    if (item) {
      nameEl.textContent = item.name;
      slotEl.classList.add("slot-filled");

      const meta = STAT_META[item.governing_stat];
      const label = meta ? meta.label : item.governing_stat;
      const grade = item.scaling_grade;
      const req = item.stat_requirement;
      const effect = item.passive_effect || "";

      statsEl.innerHTML = `
        <span class="inv-stat"><span class="inv-stat-val">${grade}</span> Grade</span>
        <span class="inv-stat"><span class="inv-stat-val">${req}</span> ${label}</span>
        ${effect ? `<span class="inv-stat" style="grid-column:1/-1;font-style:italic;opacity:0.7;">${effect}</span>` : ""}
      `;
    } else {
      nameEl.textContent = "Empty";
      slotEl.classList.remove("slot-filled");
      statsEl.innerHTML = `
        <span class="inv-stat">-- Grade</span>
        <span class="inv-stat">-- Stat</span>
      `;
    }
  });

  let totalPower = 0;
  for (const key of Object.keys(STAT_META)) {
    totalPower += (stats[key] ? stats[key].level : 1);
  }
  document.getElementById("total-power").textContent = totalPower;

  document.querySelectorAll(".inv-slot").forEach(slotEl => {
    slotEl.onclick = () => openItemPicker(slotEl.dataset.slot);
  });
}

function openItemPicker(slotType) {
  elements.itemPickerTitle.textContent = `Select ${slotType}`;
  elements.itemPickerList.innerHTML = "";

  const loadout = player.loadout || {};
  const equippedItem = loadout[slotType.toLowerCase()];
  const slotItems = items.filter(i => i.slot_type === slotType);

  if (equippedItem) {
    const unequipCard = document.createElement("div");
    unequipCard.className = "card item-picker-card";
    unequipCard.innerHTML = `
      <div class="card-info"><div class="card-title">Remove current ${slotType.toLowerCase()}</div></div>
      <div class="actions"><button class="btn btn-unequip">Remove</button></div>
    `;
    unequipCard.querySelector(".btn-unequip").addEventListener("click", async () => {
      await unequipSlot(slotType);
    });
    elements.itemPickerList.appendChild(unequipCard);
  }

  if (slotItems.length === 0 && !equippedItem) {
    elements.itemPickerList.innerHTML = `<div style="text-align:center;color:var(--color-text-muted);padding:30px;">No ${slotType.toLowerCase()} items available</div>`;
  }

  slotItems.forEach(item => {
    const meta = STAT_META[item.governing_stat];
    const statColor = meta ? meta.color : "var(--color-text-secondary)";
    const statIcon = meta ? meta.icon : "";
    const statLabel = meta ? meta.label : item.governing_stat;
    const statLevel = (player.stats && player.stats[item.governing_stat]) ? player.stats[item.governing_stat].level : 1;
    const meetsReq = statLevel >= item.stat_requirement;
    const isEquipped = equippedItem && equippedItem.id === item.id;

    const card = document.createElement("div");
    card.className = `card item-picker-card${isEquipped ? " weapon-equipped" : ""}${!meetsReq ? " item-locked" : ""}`;
    card.innerHTML = `
      <div class="card-info">
        <div class="card-title">${item.name}${isEquipped ? ' <span class="equipped-tag">EQUIPPED</span>' : ""}</div>
        <div class="card-metadata">
          <span class="badge badge-stat" style="background-color:${statColor}20;color:${statColor};">${statIcon} ${statLabel}</span>
          <span class="weapon-grade grade-${item.scaling_grade}">Grade ${item.scaling_grade}</span>
          <span style="color:var(--color-text-muted);">Req ${item.stat_requirement}</span>
        </div>
        ${item.passive_effect ? `<div class="item-passive">${item.passive_effect}</div>` : ""}
        ${!meetsReq ? `<div class="item-req-warning">🔒 Requires ${statLabel} Lvl ${item.stat_requirement} (you have ${statLevel})</div>` : ""}
      </div>
      <div class="actions">
        ${isEquipped
          ? ""
          : `<button class="btn btn-equip${meetsReq ? "" : " btn-locked"}">${meetsReq ? "Equip" : "Locked"}</button>`
        }
      </div>
    `;

    if (!isEquipped && meetsReq) {
      card.querySelector(".btn-equip").addEventListener("click", async () => {
        await equipItem(slotType, item.id);
      });
    }

    elements.itemPickerList.appendChild(card);
  });

  elements.modalItemPicker.classList.add("active");
}

async function equipItem(slotType, itemId) {
  try {
    const res = await fetch(`${API_BASE}/loadout/${slotType}?item_id=${itemId}`, { method: "PATCH" });
    if (res.ok) {
      player = await res.json();
      updatePlayerHeader();
      renderCharacter();
      elements.modalItemPicker.classList.remove("active");
    } else {
      const err = await res.json();
      alert(err.detail || "Cannot equip item.");
    }
  } catch (err) {
    console.error("Error equipping item:", err);
  }
}

async function unequipSlot(slotType) {
  try {
    const res = await fetch(`${API_BASE}/loadout/${slotType}`, { method: "DELETE" });
    if (res.ok) {
      player = await res.json();
      updatePlayerHeader();
      renderCharacter();
      elements.modalItemPicker.classList.remove("active");
    }
  } catch (err) {
    console.error("Error unequipping slot:", err);
  }
}

// Render Stats Panel
function renderStats() {
  elements.statLevel.textContent = player.level;
  elements.statGold.textContent = player.gold;

  const xpInLevel = player.current_xp - player.xp_current_level;
  const xpSpan = player.xp_next_level - player.xp_current_level;
  elements.statXp.textContent = `${xpInLevel} / ${xpSpan} XP`;

  const completedCount = tasks.filter(t => t.is_completed).length;
  elements.statTotalTasks.textContent = completedCount;

  const grid = document.getElementById("rpg-stats-grid");
  grid.innerHTML = "";
  const stats = player.stats || {};
  for (const [key, meta] of Object.entries(STAT_META)) {
    const s = stats[key] || { level: 1, xp: 0, xp_current_level: 0, xp_next_level: 100 };
    const inLevel = s.xp - s.xp_current_level;
    const span = s.xp_next_level - s.xp_current_level;
    const row = document.createElement("div");
    row.className = "rpg-stat-row";
    row.style.setProperty("--stat-color", meta.color);
    row.innerHTML = `
      <span class="rpg-stat-icon">${meta.icon}</span>
      <div class="rpg-stat-info">
        <div class="rpg-stat-header">
          <span class="rpg-stat-name">${key}</span>
          <span class="rpg-stat-lvl" style="color: ${meta.color};">Lvl ${s.level}</span>
        </div>
        <progress class="rpg-xp-bar" value="${inLevel}" max="${span}"></progress>
        <span class="rpg-xp-text">${inLevel} / ${span} XP</span>
      </div>
    `;
    grid.appendChild(row);
  }
}

// --- JOURNEY CHART ---
let journeyChart = null;
let journeyData = [];
let enabledStats = new Set();

async function renderJourney() {
  try {
    const res = await fetch(`${API_BASE}/analytics/history`);
    if (res.ok) journeyData = await res.json();
  } catch (err) {
    console.error("Error fetching history:", err);
  }
  renderJourneyToggles();
  renderJourneyChart();
}

function renderJourneyToggles() {
  const container = document.getElementById("journey-toggles");
  container.innerHTML = "";
  for (const [key, meta] of Object.entries(STAT_META)) {
    const active = enabledStats.has(key);
    const btn = document.createElement("button");
    btn.className = `toggle-chip${active ? " toggle-active" : ""}`;
    btn.style.setProperty("--chip-color", meta.color);
    btn.textContent = `${meta.icon} ${meta.label}`;
    btn.addEventListener("click", () => {
      if (enabledStats.has(key)) enabledStats.delete(key);
      else enabledStats.add(key);
      renderJourneyToggles();
      renderJourneyChart();
    });
    container.appendChild(btn);
  }
}

function renderJourneyChart() {
  const ctx = document.getElementById("journey-chart");
  if (journeyChart) journeyChart.destroy();

  const labels = journeyData.map(d => d.date.slice(5));

  const datasets = [
    {
      label: "General XP",
      data: journeyData.map(d => d.general_xp),
      borderColor: "#8b5cf6",
      backgroundColor: "rgba(139, 92, 246, 0.1)",
      tension: 0.3,
      fill: true,
      pointRadius: 3,
    },
  ];

  for (const key of enabledStats) {
    const meta = STAT_META[key];
    datasets.push({
      label: `${meta.label} XP`,
      data: journeyData.map(d => d[key] || 0),
      borderColor: meta.color,
      backgroundColor: "transparent",
      tension: 0.3,
      borderDash: [5, 3],
      pointRadius: 2,
    });
  }

  journeyChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          ticks: { color: "#6b7280", font: { size: 10 } },
          grid: { color: "rgba(37, 37, 48, 0.5)" },
        },
        y: {
          beginAtZero: true,
          ticks: { color: "#6b7280", font: { size: 10 } },
          grid: { color: "rgba(37, 37, 48, 0.5)" },
        },
      },
      plugins: {
        legend: {
          labels: { color: "#9ca3af", font: { size: 11 }, boxWidth: 12, padding: 10 },
        },
        tooltip: {
          backgroundColor: "#1a1a22",
          titleColor: "#f3f4f6",
          bodyColor: "#9ca3af",
          borderColor: "#252530",
          borderWidth: 1,
        },
      },
    },
  });
}
