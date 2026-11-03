(() => {
  const FAV_KEY = "agent-skills-favs";
  const RECENT_KEY = "agent-skills-recents";

  const els = {
    search: document.getElementById("search"),
    category: document.getElementById("category"),
    list: document.getElementById("skill-list"),
    visibleCount: document.getElementById("visible-count"),
    empty: document.getElementById("empty-state"),
    view: document.getElementById("skill-view"),
    title: document.getElementById("skill-title"),
    desc: document.getElementById("skill-desc"),
    cat: document.getElementById("skill-cat"),
    body: document.getElementById("skill-body"),
    install: document.getElementById("install-cmd"),
    github: document.getElementById("github-link"),
    favBtn: document.getElementById("fav-btn"),
    toast: document.getElementById("toast"),
    heroCount: document.getElementById("hero-count"),
    statCount: document.getElementById("stat-count"),
    statCats: document.getElementById("stat-cats"),
    quickFilters: document.getElementById("quick-filters"),
    finder: document.getElementById("finder"),
    finderInput: document.getElementById("finder-input"),
    finderResults: document.getElementById("finder-results"),
    findBtn: document.getElementById("find-skill-btn"),
    finderRun: document.getElementById("finder-run"),
    finderClose: document.getElementById("finder-close"),
    copyInstallAll: document.getElementById("copy-install-all"),
  };

  let skills = [];
  let activeId = null;
  let favs = readStore(FAV_KEY, []);
  let recents = readStore(RECENT_KEY, []);
  let quickFilter = "all";

  function readStore(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key)) || fallback;
    } catch {
      return fallback;
    }
  }

  function writeStore(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* ignore quota / private mode */
    }
  }

  function toast(message) {
    els.toast.textContent = message;
    els.toast.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      els.toast.hidden = true;
    }, 2200);
  }

  async function copyText(text) {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard");
  }

  function tokens(text) {
    return String(text || "")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length > 2);
  }

  function scoreSkill(skill, query) {
    const q = query.toLowerCase().trim();
    if (!q) return 1;
    const hay = `${skill.id} ${skill.name} ${skill.description} ${skill.category} ${skill.body}`.toLowerCase();
    if (hay.includes(q)) return 100;
    const parts = tokens(q);
    let score = 0;
    for (const part of parts) {
      if (skill.id.includes(part)) score += 12;
      if (skill.name.toLowerCase().includes(part)) score += 10;
      if (skill.description.toLowerCase().includes(part)) score += 6;
      if (skill.category.toLowerCase().includes(part)) score += 4;
      if (skill.body.toLowerCase().includes(part)) score += 1;
    }
    return score;
  }

  function filteredSkills() {
    const query = els.search.value.trim();
    const category = els.category.value;
    return skills
      .map((skill) => ({ skill, score: scoreSkill(skill, query) }))
      .filter(({ skill, score }) => {
        if (category && skill.category !== category) return false;
        if (quickFilter === "favorites" && !favs.includes(skill.id)) return false;
        if (quickFilter === "recent" && !recents.includes(skill.id)) return false;
        if (query && score <= 0) return false;
        return true;
      })
      .sort((a, b) => {
        if (quickFilter === "recent") {
          return recents.indexOf(a.skill.id) - recents.indexOf(b.skill.id);
        }
        if (b.score !== a.score) return b.score - a.score;
        return a.skill.name.localeCompare(b.skill.name);
      })
      .map(({ skill }) => skill);
  }

  function renderList() {
    const visible = filteredSkills();
    els.visibleCount.textContent = String(visible.length);
    els.list.innerHTML = "";
    for (const skill of visible) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `skill-item${skill.id === activeId ? " active" : ""}`;
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-selected", skill.id === activeId ? "true" : "false");
      btn.innerHTML = `
        <span class="name">${escapeHtml(skill.name)}</span>
        <span class="desc">${escapeHtml(skill.description || "No description")}</span>
        <span class="meta">${escapeHtml(skill.category)}${favs.includes(skill.id) ? " · ★" : ""}</span>
      `;
      btn.addEventListener("click", () => selectSkill(skill.id));
      els.list.appendChild(btn);
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderMarkdown(md) {
    const html = window.marked.parse(md || "");
    return window.DOMPurify.sanitize(html);
  }

  function promptFor(skill, tool) {
    const opener =
      tool === "chatgpt"
        ? "You are ChatGPT acting as a specialist agent."
        : tool === "gemini"
          ? "You are Gemini acting as a specialist agent."
          : "You are Claude acting as a specialist agent.";
    return `${opener}

Use the following Agent Skill named "${skill.name}".

${skill.description}

Follow these instructions carefully:

${skill.body}

When I give you a task, apply this skill and produce a concise, actionable result.`;
  }

  function selectSkill(id) {
    const skill = skills.find((item) => item.id === id);
    if (!skill) return;
    activeId = id;
    recents = [id, ...recents.filter((item) => item !== id)].slice(0, 12);
    writeStore(RECENT_KEY, recents);

    els.empty.hidden = true;
    els.view.hidden = false;
    els.cat.textContent = skill.category;
    els.title.textContent = skill.name;
    els.desc.textContent = skill.description || "No description provided.";
    els.install.textContent = skill.install;
    els.github.href = skill.github;
    els.body.innerHTML = renderMarkdown(skill.body);
    els.favBtn.setAttribute("aria-pressed", favs.includes(id) ? "true" : "false");
    els.favBtn.textContent = favs.includes(id) ? "★ Favorited" : "☆ Favorite";
    renderList();
    history.replaceState(null, "", `#${encodeURIComponent(id)}`);
  }

  function toggleFavorite() {
    if (!activeId) return;
    if (favs.includes(activeId)) {
      favs = favs.filter((id) => id !== activeId);
    } else {
      favs = [activeId, ...favs];
    }
    writeStore(FAV_KEY, favs);
    selectSkill(activeId);
  }

  function fillCategories() {
    const categories = [...new Set(skills.map((skill) => skill.category))].sort();
    for (const category of categories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      els.category.appendChild(option);
    }
    els.statCats.textContent = String(categories.length);

    const chips = [
      ["all", "All"],
      ["favorites", "Favorites"],
      ["recent", "Recent"],
    ];
    els.quickFilters.innerHTML = "";
    for (const [id, label] of chips) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `chip${quickFilter === id ? " active" : ""}`;
      btn.textContent = label;
      btn.addEventListener("click", () => {
        quickFilter = id;
        [...els.quickFilters.children].forEach((child) => child.classList.remove("active"));
        btn.classList.add("active");
        renderList();
      });
      els.quickFilters.appendChild(btn);
    }
  }

  function runFinder() {
    const query = els.finderInput.value.trim();
    const matches = skills
      .map((skill) => ({ skill, score: scoreSkill(skill, query) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8);
    els.finderResults.innerHTML = "";
    if (!matches.length) {
      els.finderResults.innerHTML = `<p class="skill-desc">No strong matches. Try fewer words or a different task description.</p>`;
      return;
    }
    for (const { skill, score } of matches) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "finder-card";
      btn.innerHTML = `<strong>${escapeHtml(skill.name)}</strong><span>${escapeHtml(skill.description)}</span><span>${escapeHtml(skill.category)} · score ${score}</span>`;
      btn.addEventListener("click", () => {
        els.finder.hidden = true;
        selectSkill(skill.id);
        document.getElementById("playground").scrollIntoView({ behavior: "smooth" });
      });
      els.finderResults.appendChild(btn);
    }
  }

  function bindCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", async () => {
        const skill = skills.find((item) => item.id === activeId);
        if (!skill) return;
        const mode = button.getAttribute("data-copy");
        if (mode === "install") {
          await copyText(skill.install);
          return;
        }
        if (mode === "raw") {
          await copyText(`# ${skill.name}\n\n${skill.description}\n\n${skill.body}`);
          return;
        }
        await copyText(promptFor(skill, mode));
      });
    });
  }

  async function init() {
    const response = await fetch("./skills.json");
    if (!response.ok) throw new Error("Failed to load skills.json");
    const payload = await response.json();
    skills = payload.skills || [];
    els.heroCount.textContent = String(skills.length);
    els.statCount.textContent = String(skills.length);
    fillCategories();
    renderList();
    bindCopyButtons();

    const hash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
    if (hash && skills.some((skill) => skill.id === hash)) {
      selectSkill(hash);
    } else if (skills[0]) {
      /* keep empty state until user picks */
    }

    els.search.addEventListener("input", renderList);
    els.category.addEventListener("change", renderList);
    els.favBtn.addEventListener("click", toggleFavorite);
    els.findBtn.addEventListener("click", () => {
      els.finder.hidden = false;
      els.finderInput.focus();
    });
    els.finderClose.addEventListener("click", () => {
      els.finder.hidden = true;
    });
    els.finderRun.addEventListener("click", runFinder);
    els.finderInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runFinder();
    });
    els.copyInstallAll.addEventListener("click", () =>
      copyText("npx skills add sisodiabhumca/agent-skills")
    );
    document.querySelector(".install-chip")?.addEventListener("click", () =>
      copyText("npx skills add sisodiabhumca/agent-skills")
    );
  }

  init().catch((error) => {
    console.error(error);
    els.list.innerHTML = `<p class="skill-desc">Could not load skills.json. If you are opening the file locally, serve the docs folder over HTTP.</p>`;
  });
})();
