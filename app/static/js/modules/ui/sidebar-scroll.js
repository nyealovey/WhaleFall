(function (global) {
  "use strict";

  const SIDEBAR_SELECTOR = "[data-sidebar-scroll-root]";
  const ACTIVE_LINK_SELECTOR = ".app-sidebar__link.is-active";
  const LINK_SELECTOR = ".app-sidebar__link";
  const STORAGE_KEY = "wf.sidebar.scrollTop";
  const VIEWPORT_PADDING = 10;

  function getStorage() {
    try {
      return global.sessionStorage || null;
    } catch {
      return null;
    }
  }

  function readSavedScroll() {
    const storage = getStorage();
    if (!storage) {
      return null;
    }

    const rawValue = storage.getItem(STORAGE_KEY);
    if (rawValue === null) {
      return null;
    }

    const parsedValue = Number.parseInt(rawValue, 10);
    return Number.isFinite(parsedValue) && parsedValue >= 0 ? parsedValue : null;
  }

  function saveSidebarScroll(sidebar) {
    const storage = getStorage();
    if (!storage || !sidebar) {
      return;
    }

    const scrollTop = Math.max(0, Math.round(sidebar.scrollTop || 0));
    storage.setItem(STORAGE_KEY, String(scrollTop));
  }

  function revealActiveLink(sidebar) {
    const activeLink = sidebar.querySelector(ACTIVE_LINK_SELECTOR);
    if (!activeLink) {
      return;
    }

    const sidebarRect = sidebar.getBoundingClientRect();
    const linkRect = activeLink.getBoundingClientRect();
    const viewportTop = sidebarRect.top + VIEWPORT_PADDING;
    const viewportBottom = sidebarRect.bottom - VIEWPORT_PADDING;

    if (linkRect.top >= viewportTop && linkRect.bottom <= viewportBottom) {
      return;
    }

    if (linkRect.top < viewportTop) {
      sidebar.scrollTop -= viewportTop - linkRect.top;
      return;
    }

    sidebar.scrollTop += linkRect.bottom - viewportBottom;
  }

  function restoreSidebarScroll(sidebar) {
    const savedScroll = readSavedScroll();
    if (savedScroll === null) {
      return;
    }

    sidebar.scrollTop = savedScroll;
  }

  function bindSidebarLinks(sidebar) {
    sidebar.querySelectorAll(LINK_SELECTOR).forEach((link) => {
      link.addEventListener("click", () => {
        saveSidebarScroll(sidebar);
      });
    });
  }

  function initSidebarScroll() {
    const sidebar = document.querySelector(SIDEBAR_SELECTOR);
    if (!sidebar) {
      return;
    }

    restoreSidebarScroll(sidebar);
    revealActiveLink(sidebar);
    saveSidebarScroll(sidebar);
    bindSidebarLinks(sidebar);

    sidebar.addEventListener(
      "scroll",
      () => {
        saveSidebarScroll(sidebar);
      },
      { passive: true },
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSidebarScroll, { once: true });
  } else {
    initSidebarScroll();
  }
})(window);
