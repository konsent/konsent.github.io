const DATA_URL = "./data/Spruance_Leader_Card_Guide_KR.json";
const STORAGE_KEY = "spruance-leader-guide-state-v1";

const $ = (selector) => document.querySelector(selector);
const elements = {
  app: $(".app-shell"),
  scroll: $("#card-scroll"),
  section: $("#section-label"),
  kind: $("#kind-label"),
  number: $("#card-number"),
  key: $("#card-key"),
  title: $("#card-title"),
  image: $("#card-image"),
  imagePlaceholder: $("#media-placeholder"),
  imagePath: $("#image-path"),
  steps: $("#steps"),
  notesPanel: $("#notes-panel"),
  notes: $("#notes"),
  flowActions: $("#flow-actions"),
  historyBack: $("#history-back"),
  previous: $("#previous-card"),
  next: $("#next-card"),
  toc: $("#toc-dialog"),
  tocContent: $("#toc-content"),
  search: $("#search-input"),
  confirm: $("#confirm-dialog"),
};

let cards = [];
let cardsByNumber = new Map();
let state = { currentNumber: 1, history: [] };
let swipeStart = null;

function shortcutFor(index) {
  if (index < 9) return String(index + 1);
  if (index === 9) return "0";
  return `Shift+${index - 9}`;
}

function shortcutIndex(event) {
  if (event.altKey || event.ctrlKey || event.metaKey) return null;
  if (event.code.startsWith("Numpad") && !event.shiftKey) {
    const digit = Number(event.code.slice(-1));
    return digit === 0 ? 9 : digit - 1;
  }
  if (!event.code.startsWith("Digit")) return null;
  const digit = Number(event.code.slice(-1));
  if (event.shiftKey) return digit >= 1 && digit <= 3 ? digit + 9 : null;
  return digit === 0 ? 9 : digit - 1;
}

function normaliseState(saved) {
  if (!saved || !Number.isInteger(saved.currentNumber) || !cardsByNumber.has(saved.currentNumber)) return { currentNumber: 1, history: [] };
  const history = Array.isArray(saved.history)
    ? saved.history.filter((number) => Number.isInteger(number) && cardsByNumber.has(number)).slice(-100)
    : [];
  return { currentNumber: saved.currentNumber, history };
}

function loadState() {
  try {
    return normaliseState(JSON.parse(localStorage.getItem(STORAGE_KEY)));
  } catch {
    return { currentNumber: 1, history: [] };
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function changeCard(number, { remember = true } = {}) {
  if (!cardsByNumber.has(number) || number === state.currentNumber) return;
  if (remember) state.history.push(state.currentNumber);
  state.currentNumber = number;
  saveState();
  renderCard();
}

function browse(offset) {
  const index = cards.findIndex((card) => card.number === state.currentNumber);
  const target = cards[index + offset];
  if (target) changeCard(target.number);
}

function goBack() {
  const previous = state.history.pop();
  if (!cardsByNumber.has(previous)) return;
  state.currentNumber = previous;
  saveState();
  renderCard();
}

function renderList(element, values) {
  element.replaceChildren(...values.map((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    return item;
  }));
}

function renderCard() {
  const card = cardsByNumber.get(state.currentNumber) ?? cards[0];
  const index = cards.indexOf(card);
  elements.section.textContent = card.section;
  elements.kind.textContent = card.kind;
  elements.number.textContent = `카드 ${card.number}`;
  elements.key.textContent = card.key;
  elements.title.textContent = card.title;
  const imagePath = (card.image ?? "").normalize("NFC");
  elements.image.hidden = true;
  elements.imagePlaceholder.hidden = false;
  elements.imagePath.textContent = imagePath || "사진 경로를 지정하세요";
  elements.image.alt = `${card.title} 관련 사진`;
  elements.image.onload = () => {
    if (elements.image.getAttribute("src") === imagePath) {
      elements.image.hidden = false;
      elements.imagePlaceholder.hidden = true;
    }
  };
  elements.image.onerror = () => {
    if (elements.image.getAttribute("src") === imagePath) {
      elements.image.hidden = true;
      elements.imagePlaceholder.hidden = false;
    }
  };
  elements.image.src = imagePath;
  renderList(elements.steps, card.steps);
  elements.notesPanel.hidden = !card.notes.length;
  renderList(elements.notes, card.notes);
  elements.flowActions.replaceChildren(...card.buttons.map((button, index) => {
    const action = document.createElement("button");
    action.type = "button";
    action.className = "flow-button";
    action.dataset.shortcutIndex = String(index);
    action.setAttribute("aria-label", `${shortcutFor(index)}번 단축키: ${button.text}`);
    const label = document.createElement("span");
    label.className = "flow-label";
    label.textContent = button.text;
    const shortcut = document.createElement("kbd");
    shortcut.className = "shortcut-key";
    shortcut.textContent = shortcutFor(index);
    const arrow = document.createElement("span");
    arrow.className = "flow-arrow";
    arrow.textContent = "→";
    action.append(label, shortcut, arrow);
    action.addEventListener("click", () => changeCard(button.target));
    return action;
  }));
  elements.historyBack.disabled = state.history.length === 0;
  elements.previous.disabled = index === 0;
  elements.next.disabled = index === cards.length - 1;
  elements.scroll.scrollTop = 0;
  elements.scroll.focus({ preventScroll: true });
  renderToc();
}

function matchingCards(query) {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return cards;
  if (/^\d+$/.test(needle)) {
    const directMatch = cardsByNumber.get(Number(needle));
    if (directMatch) return [directMatch];
  }
  return cards.filter((card) => [card.number, card.title, card.section, ...card.steps].join(" ").toLocaleLowerCase().includes(needle));
}

function renderToc() {
  const visibleCards = matchingCards(elements.search.value);
  const grouped = new Map();
  for (const card of visibleCards) {
    const sectionCards = grouped.get(card.section) ?? [];
    sectionCards.push(card);
    grouped.set(card.section, sectionCards);
  }
  const fragments = [];
  if (!visibleCards.length) {
    const empty = document.createElement("p");
    empty.className = "toc-empty";
    empty.textContent = "일치하는 카드가 없습니다.";
    fragments.push(empty);
  }
  for (const [section, sectionCards] of grouped) {
    const group = document.createElement("section");
    group.className = "toc-section";
    const heading = document.createElement("h3");
    heading.textContent = section;
    const list = document.createElement("ul");
    list.className = "toc-list";
    for (const card of sectionCards) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "toc-item";
      button.setAttribute("aria-current", String(card.number === state.currentNumber));
      button.innerHTML = `<span>${card.number}</span>${card.title}`;
      button.addEventListener("click", () => {
        elements.toc.close();
        changeCard(card.number);
      });
      item.append(button);
      list.append(item);
    }
    group.append(heading, list);
    fragments.push(group);
  }
  elements.tocContent.replaceChildren(...fragments);
}

function validateData(data) {
  if (!Array.isArray(data.cards) || !data.cards.length) throw new Error("cards가 없습니다.");
  const byNumber = new Map(data.cards.map((card) => [card.number, card]));
  if (byNumber.size !== data.cards.length) throw new Error("카드 번호가 중복되었습니다.");
  for (const card of data.cards) {
    if (!Number.isInteger(card.number) || !Array.isArray(card.buttons) || !Array.isArray(card.steps)) throw new Error(`카드 ${card.number}의 형식이 올바르지 않습니다.`);
    if (card.buttons.some((button) => !byNumber.has(button.target))) throw new Error(`카드 ${card.number}에 존재하지 않는 목적지가 있습니다.`);
  }
  return byNumber;
}

function showError() {
  elements.app.replaceChildren($("#error-template").content.cloneNode(true));
}

function installEvents() {
  $("#toc-button").addEventListener("click", () => elements.toc.showModal());
  $("#close-toc").addEventListener("click", () => elements.toc.close());
  $("#open-reset").addEventListener("click", () => {
    elements.toc.close();
    elements.confirm.showModal();
  });
  elements.search.addEventListener("input", renderToc);
  elements.historyBack.addEventListener("click", goBack);
  elements.previous.addEventListener("click", () => browse(-1));
  elements.next.addEventListener("click", () => browse(1));
  $("#cancel-reset").addEventListener("click", () => elements.confirm.close());
  $("#confirm-reset").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    state = { currentNumber: 1, history: [] };
    elements.confirm.close();
    renderCard();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") return;
    if (event.target.matches("input, textarea, button") || elements.toc.open || elements.confirm.open) return;
    const index = shortcutIndex(event);
    const shortcutButton = index === null ? null : elements.flowActions.querySelector(`[data-shortcut-index="${index}"]`);
    if (shortcutButton) {
      event.preventDefault();
      shortcutButton.click();
      return;
    }
    if (event.key === "ArrowLeft") browse(-1);
    if (event.key === "ArrowRight") browse(1);
    if (event.key.toLocaleLowerCase() === "r") elements.confirm.showModal();
  });
  elements.scroll.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    swipeStart = { x: event.clientX, y: event.clientY, target: event.target };
  });
  elements.scroll.addEventListener("pointerup", (event) => {
    if (!swipeStart || swipeStart.target.closest("button, summary, a")) return;
    const dx = event.clientX - swipeStart.x;
    const dy = event.clientY - swipeStart.y;
    swipeStart = null;
    if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    browse(dx < 0 ? 1 : -1);
  });
  elements.scroll.addEventListener("pointercancel", () => { swipeStart = null; });
}

async function start() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    cardsByNumber = validateData(data);
    cards = [...data.cards].sort((a, b) => a.number - b.number);
    state = loadState();
    installEvents();
    renderCard();
  } catch (error) {
    console.error(error);
    showError();
  }
}

start();
