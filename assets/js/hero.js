/* Hero: Krasnoselskii–Mann iterations x_{n+1} = (1-λ)x_n + λ T x_n spiralling into the
   fixed point of a rotation T. The dashed circle is the Picard orbit, which never converges. */
(function () {
  "use strict";
  var canvas = document.getElementById("hero-canvas");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var W = 0, H = 0, P = { x: 0, y: 0 }, colors = {}, trails = [], last = 0, raf = 0;
  var THETA = 80 * Math.PI / 180, COS = Math.cos(THETA), SIN = Math.sin(THETA);

  function readColors() {
    var s = getComputedStyle(document.documentElement);
    colors.ink = s.getPropertyValue("--indigo").trim() || "#2d3e8c";
    colors.fix = s.getPropertyValue("--ochre").trim() || "#a6741f";
    colors.faint = s.getPropertyValue("--ink-3").trim() || "#6b7383";
  }
  function T(x, y) { // rotation about P
    var dx = x - P.x, dy = y - P.y;
    return { x: P.x + COS * dx - SIN * dy, y: P.y + SIN * dx + COS * dy };
  }
  function resize() {
    var r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var img = document.querySelector(".hero .portrait");
    if (img) { // keep the fixed point in the open space beside the portrait, clear of the text
      var q = img.getBoundingClientRect();
      var L = q.left - r.left, Tp = q.top - r.top;
      P = W > 720 ? { x: L + q.width / 2, y: Math.max(60, Tp * 0.5) }
                  : { x: L + q.width + (W - L - q.width) / 2, y: Tp + q.height / 2 };
    } else P = { x: W * 0.75, y: H * 0.3 };
  }
  function edgePoint() {
    var side = Math.floor(Math.random() * 4), t = Math.random();
    return [{ x: t * W, y: -10 }, { x: W + 10, y: t * H }, { x: t * W, y: H + 10 }, { x: -10, y: t * H }][side];
  }
  function addTrail(start) {
    var s = start || edgePoint();
    trails.push({ pts: [s], lambda: 0.08 + Math.random() * 0.1, done: false, fade: 1 });
    if (trails.length > 7) trails.shift();
  }
  function step(tr) {
    var x = tr.pts[tr.pts.length - 1], tx = T(x.x, x.y), l = tr.lambda;
    var n = { x: (1 - l) * x.x + l * tx.x, y: (1 - l) * x.y + l * tx.y };
    tr.pts.push(n);
    if (Math.hypot(n.x - P.x, n.y - P.y) < 0.6 || tr.pts.length > 400) tr.done = true;
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    // Picard orbit of the newest trail's start: a circle it never leaves
    if (trails.length) {
      var s = trails[trails.length - 1].pts[0];
      ctx.save(); ctx.setLineDash([3, 6]); ctx.strokeStyle = colors.faint; ctx.globalAlpha = 0.28; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(P.x, P.y, Math.hypot(s.x - P.x, s.y - P.y), 0, 2 * Math.PI); ctx.stroke(); ctx.restore();
    }
    trails.forEach(function (tr) {
      ctx.save(); ctx.globalAlpha = 0.55 * tr.fade; ctx.strokeStyle = colors.ink; ctx.fillStyle = colors.ink; ctx.lineWidth = 1.1;
      ctx.beginPath();
      tr.pts.forEach(function (p, i) { if (i) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); });
      ctx.stroke();
      tr.pts.forEach(function (p, i) {
        ctx.beginPath(); ctx.arc(p.x, p.y, i === tr.pts.length - 1 && !tr.done ? 3 : 1.4, 0, 2 * Math.PI); ctx.fill();
      });
      ctx.restore();
    });
    ctx.save(); ctx.strokeStyle = colors.fix; ctx.fillStyle = colors.fix; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(P.x, P.y, 7, 0, 2 * Math.PI); ctx.stroke();
    ctx.beginPath(); ctx.arc(P.x, P.y, 2.5, 0, 2 * Math.PI); ctx.fill(); ctx.restore();
  }
  function tick(t) {
    if (t - last > 70) {
      last = t;
      trails.forEach(function (tr) { if (!tr.done) step(tr); else tr.fade = Math.max(0.25, tr.fade - 0.01); });
      if (trails.filter(function (tr) { return !tr.done; }).length < 2 && Math.random() < 0.04) addTrail();
      draw();
    }
    raf = requestAnimationFrame(tick);
  }
  function staticScene() {
    trails = [];
    for (var i = 0; i < 5; i++) { addTrail(); while (!trails[i].done) step(trails[i]); }
    draw();
  }

  readColors(); resize();
  if (reduce) staticScene(); else { addTrail(); addTrail(); raf = requestAnimationFrame(tick); }

  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { resize(); trails = []; if (reduce) staticScene(); else addTrail(); }, 150);
  });
  document.addEventListener("themechange", function () { readColors(); draw(); });
  canvas.parentElement.addEventListener("click", function (e) {
    if (e.target.closest("a, button")) return;
    var r = canvas.getBoundingClientRect();
    addTrail({ x: e.clientX - r.left, y: e.clientY - r.top });
    if (reduce) { var tr = trails[trails.length - 1]; while (!tr.done) step(tr); draw(); }
  });
  document.addEventListener("visibilitychange", function () {
    if (reduce) return;
    if (document.hidden) cancelAnimationFrame(raf); else raf = requestAnimationFrame(tick);
  });
})();
