import { clientsApi } from "../core/api.js";
import { createAvatar, createElement, createStatusBadge } from "../core/dom.js";
import { formatDate, percentage } from "../core/utils.js";
import { onClientsChanged } from "../features/client-events.js";
import { showToast } from "../ui/toast.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const COUNT_UP_MS = 800;
const STATUSES = [
  { key: "client", label: "Clientes" },
  { key: "prospect", label: "Prospectos" },
  { key: "inactive", label: "Inactivos" },
];

const prefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

function animateNumber(element, target) {
  const start = Number(element.textContent) || 0;
  if (prefersReducedMotion || start === target) {
    element.textContent = target;
    return;
  }

  const startedAt = performance.now();
  const step = (now) => {
    const progress = Math.min((now - startedAt) / COUNT_UP_MS, 1);
    const eased = 1 - (1 - progress) ** 3;
    element.textContent = Math.round(start + (target - start) * eased);
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderKpis({ total, by_status: byStatus }) {
  animateNumber(document.querySelector('[data-kpi="total"]'), total);
  document.querySelector('[data-kpi-hint="total"]').textContent = "En toda la cartera";

  STATUSES.forEach(({ key }) => {
    animateNumber(document.querySelector(`[data-kpi="${key}"]`), byStatus[key]);
    document.querySelector(`[data-kpi-hint="${key}"]`).textContent =
      `${percentage(byStatus[key], total)}% de la cartera`;
  });
}

/** Cada segmento es un círculo con trazo parcial; r=15.915 da una circunferencia de 100. */
function createRingSegment(key, share, offset) {
  const segment = document.createElementNS(SVG_NAMESPACE, "circle");
  segment.setAttribute("class", `orbit-chart__segment orbit-chart__segment--${key}`);
  segment.setAttribute("cx", "21");
  segment.setAttribute("cy", "21");
  segment.setAttribute("r", "15.915");
  segment.setAttribute("stroke-dasharray", `${share} ${100 - share}`);
  segment.setAttribute("stroke-dashoffset", String(25 - offset));
  return segment;
}

function renderRing({ total, by_status: byStatus }) {
  let offset = 0;
  const segments = STATUSES.map(({ key }) => {
    const share = total === 0 ? 0 : (byStatus[key] / total) * 100;
    const segment = createRingSegment(key, share, offset);
    offset += share;
    return segment;
  });

  document.querySelector("#ring-segments").replaceChildren(...segments);
  document.querySelector("#conversion-rate").textContent = `${percentage(byStatus.client, total)}%`;
  document.querySelector("#ring-legend").replaceChildren(
    ...STATUSES.map(({ key, label }) =>
      createElement(
        "li",
        { class: `legend__item legend__item--${key}` },
        createElement("span", {}, label),
        createElement("strong", {}, String(byStatus[key])),
      ),
    ),
  );
}

function renderBars(weeklySignups) {
  const highest = Math.max(...weeklySignups.map(({ total }) => total), 1);
  document.querySelector("#signup-bars").replaceChildren(
    ...weeklySignups.map(({ week, total }, index) =>
      createElement(
        "li",
        {
          class: "bars__item",
          style: `--bar-height: ${(total / highest) * 100}%; --order: ${index}`,
          "aria-label": `Semana del ${formatDate(`${week}T12:00:00`)}: ${total}`,
        },
        createElement("span", { class: "bars__value" }, String(total)),
        createElement("span", { class: "bars__track" }, createElement("span", { class: "bars__fill" })),
        createElement("span", { class: "bars__label" }, formatDate(`${week}T12:00:00`)),
      ),
    ),
  );
}

function createRecentItem(client) {
  return createElement(
    "li",
    { class: "recent__item" },
    createAvatar(client.name),
    createElement(
      "div",
      { class: "recent__identity" },
      createElement("strong", {}, client.name),
      createElement("span", {}, client.company || client.email),
    ),
    createElement("time", { class: "recent__date", datetime: client.created_at }, formatDate(client.created_at)),
    createStatusBadge(client),
  );
}

function renderRecent(clients) {
  const list = document.querySelector("#recent-clients");
  if (clients.length === 0) {
    list.replaceChildren(
      createElement("li", { class: "recent__empty" }, "Todavía no hay clientes registrados."),
    );
    return;
  }
  list.replaceChildren(...clients.map(createRecentItem));
}

async function loadDashboard() {
  try {
    const stats = await clientsApi.stats();
    renderKpis(stats);
    renderRing(stats);
    renderBars(stats.weekly_signups);
    renderRecent(stats.recent);
  } catch (error) {
    showToast(error.message, "error");
  }
}

onClientsChanged(loadDashboard);
loadDashboard();
