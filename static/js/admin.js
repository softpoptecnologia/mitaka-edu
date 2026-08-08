(function () {
  const shell = document.getElementById("adminShell");
  const toggle = document.getElementById("sidebarToggle");
  const overlay = document.getElementById("adminOverlay");
  if (!shell || !toggle) return;

  const KEY = "mitaka-sidebar-collapsed";
  const mq = window.matchMedia("(max-width: 991.98px)");

  function isMobile() {
    return mq.matches;
  }

  function applyDesktopPref() {
    if (!isMobile() && localStorage.getItem(KEY) === "1") {
      shell.classList.add("sidebar-collapsed");
    }
  }

  function closeMobile() {
    shell.classList.remove("sidebar-open");
    document.body.classList.remove("admin-nav-open");
  }

  function syncToggleLabel() {
    const open = isMobile() ? shell.classList.contains("sidebar-open") : !shell.classList.contains("sidebar-collapsed");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Recolher menu" : "Abrir menu");
  }

  toggle.addEventListener("click", function () {
    if (isMobile()) {
      shell.classList.toggle("sidebar-open");
      document.body.classList.toggle("admin-nav-open", shell.classList.contains("sidebar-open"));
    } else {
      shell.classList.toggle("sidebar-collapsed");
      localStorage.setItem(KEY, shell.classList.contains("sidebar-collapsed") ? "1" : "0");
    }
    syncToggleLabel();
  });

  if (overlay) {
    overlay.addEventListener("click", function () {
      closeMobile();
      syncToggleLabel();
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && shell.classList.contains("sidebar-open")) {
      closeMobile();
      syncToggleLabel();
    }
  });

  mq.addEventListener("change", function () {
    closeMobile();
    shell.classList.remove("sidebar-collapsed");
    applyDesktopPref();
    syncToggleLabel();
  });

  applyDesktopPref();
  syncToggleLabel();
})();
