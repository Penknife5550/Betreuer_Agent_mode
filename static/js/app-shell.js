// App-Shell: setzt data-stuck="true" auf den Header, sobald der
// Sentinel oberhalb davon aus dem Viewport scrollt. CSS reagiert
// mit dem Shadow. IntersectionObserver statt scroll-Listener,
// damit kein Reaktivitaets-Overhead auf jedem Scroll-Tick anfaellt.
//
// Re-Init nach htmx:afterSettle: wird der DOM durch htmx ausgetauscht,
// haengt der alte Observer auf einem detached node und Sticky-Shadow
// funktioniert nicht mehr.
(function () {
  let io = null;

  function init() {
    if (io) {
      io.disconnect();
      io = null;
    }
    const sentinel = document.getElementById("header-sentinel");
    const header = document.querySelector("[data-app-header]");
    if (!sentinel || !header || !("IntersectionObserver" in window)) return;

    io = new IntersectionObserver(
      ([entry]) => {
        header.dataset.stuck = entry.isIntersecting ? "false" : "true";
      },
      { rootMargin: "0px", threshold: 0 }
    );
    io.observe(sentinel);
  }

  init();
  document.body.addEventListener("htmx:afterSettle", init);
})();
