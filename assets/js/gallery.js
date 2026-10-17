/* Gallery lightbox with keyboard and swipe navigation. */
(function () {
  "use strict";
  var dlg = document.getElementById("lightbox");
  if (!dlg) return;
  var img = document.getElementById("lb-img"), cap = document.getElementById("lb-cap"), count = document.getElementById("lb-count");
  var items = [], idx = 0, opener = null;

  function show(i) {
    idx = (i + items.length) % items.length;
    var b = items[idx], album = document.getElementById(b.dataset.album);
    img.src = b.dataset.full;
    img.alt = b.querySelector("img").alt;
    cap.textContent = album.querySelector("h2").textContent + ", " + album.querySelector(".when").textContent.replace(/\s+/g, " ").trim();
    count.textContent = (idx + 1) + " of " + items.length;
  }
  document.querySelectorAll(".grid button").forEach(function (b) {
    b.addEventListener("click", function () {
      opener = b;
      items = Array.prototype.slice.call(document.querySelectorAll('.grid button[data-album="' + b.dataset.album + '"]'));
      show(+b.dataset.index);
      dlg.showModal();
    });
  });
  document.getElementById("lb-prev").addEventListener("click", function () { show(idx - 1); });
  document.getElementById("lb-next").addEventListener("click", function () { show(idx + 1); });
  dlg.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") { e.preventDefault(); show(idx - 1); }
    if (e.key === "ArrowRight") { e.preventDefault(); show(idx + 1); }
  });
  dlg.addEventListener("close", function () { img.removeAttribute("src"); if (opener) opener.focus(); });
  dlg.addEventListener("click", function (e) { if (e.target === dlg || e.target.tagName === "FIGURE") dlg.close(); });
  var x0 = null;
  dlg.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  dlg.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
    x0 = null;
  });
})();
