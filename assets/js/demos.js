/* Interactive examples on the Code page. */
(function () {
  "use strict";
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  function Plot(canvas, range) {
    var ctx = canvas.getContext("2d");
    var api = {
      ctx: ctx,
      size: function () {
        var r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.width * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0); api.w = r.width;
      },
      X: function (x) { return (x + range) / (2 * range) * api.w; },
      Y: function (y) { return (range - y) / (2 * range) * api.w; },
      inv: function (px, py) { return [px / api.w * 2 * range - range, range - py / api.w * 2 * range]; },
      axes: function () {
        ctx.clearRect(0, 0, api.w, api.w);
        ctx.strokeStyle = css("--rule"); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(api.X(-range), api.Y(0)); ctx.lineTo(api.X(range), api.Y(0));
        ctx.moveTo(api.X(0), api.Y(-range)); ctx.lineTo(api.X(0), api.Y(range)); ctx.stroke();
      },
      path: function (pts, color, width, dots) {
        ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width;
        ctx.beginPath(); pts.forEach(function (p, i) { if (i) ctx.lineTo(api.X(p[0]), api.Y(p[1])); else ctx.moveTo(api.X(p[0]), api.Y(p[1])); });
        ctx.stroke();
        if (dots) pts.forEach(function (p) { ctx.beginPath(); ctx.arc(api.X(p[0]), api.Y(p[1]), 2.2, 0, 7); ctx.fill(); });
      },
      mark: function (p) {
        ctx.strokeStyle = css("--ochre"); ctx.fillStyle = css("--ochre"); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(api.X(p[0]), api.Y(p[1]), 8, 0, 7); ctx.stroke();
        ctx.beginPath(); ctx.arc(api.X(p[0]), api.Y(p[1]), 3, 0, 7); ctx.fill();
      }
    };
    return api;
  }
  function bind(ids, fmt, redraw) {
    ids.forEach(function (id) {
      var input = document.getElementById(id), out = document.getElementById(id + "-out");
      var upd = function () { out.textContent = fmt[id](+input.value); redraw(); };
      input.addEventListener("input", upd);
      out.textContent = fmt[id](+input.value);
    });
  }
  var val = function (id) { return +document.getElementById(id).value; };
  var norm = function (p, q) { return Math.hypot(p[0] - q[0], p[1] - q[1]); };

  // ---- Example 1: Picard vs Krasnoselskii–Mann for a rotation ----
  var c1 = document.getElementById("demo-km");
  if (c1) {
    var p1 = Plot(c1, 1.2), x0 = [0.9, 0.5];
    var draw1 = function () {
      p1.size(); p1.axes();
      var th = val("km-theta") * Math.PI / 180, lam = val("km-lambda") / 100, n = val("km-n");
      var rot = function (x) { return [Math.cos(th) * x[0] - Math.sin(th) * x[1], Math.sin(th) * x[0] + Math.cos(th) * x[1]]; };
      var pic = [x0], km = [x0];
      for (var i = 0; i < n; i++) {
        pic.push(rot(pic[i]));
        var t = rot(km[i]); km.push([(1 - lam) * km[i][0] + lam * t[0], (1 - lam) * km[i][1] + lam * t[1]]);
      }
      p1.ctx.globalAlpha = 0.55; p1.path(pic, css("--ink-3"), 1, true); p1.ctx.globalAlpha = 1;
      p1.path(km, css("--indigo"), 1.6, true); p1.mark([0, 0]);
      document.getElementById("km-report").textContent = "After " + n + " steps the distance to the fixed point is " +
        norm(pic[n], [0, 0]).toFixed(3) + " for Picard and " + norm(km[n], [0, 0]).toExponential(2) + " for Krasnoselskii–Mann.";
    };
    bind(["km-theta", "km-lambda", "km-n"], {
      "km-theta": function (v) { return v + "°"; }, "km-lambda": function (v) { return (v / 100).toFixed(2); },
      "km-n": function (v) { return String(v); } }, draw1);
    c1.addEventListener("click", function (e) { var r = c1.getBoundingClientRect(); x0 = p1.inv(e.clientX - r.left, e.clientY - r.top); draw1(); });
    draw1();
    window.addEventListener("resize", draw1);
    document.addEventListener("themechange", draw1);
  }

  // ---- Example 2: projected gradient vs extragradient for a monotone VI on a box ----
  var c2 = document.getElementById("demo-eg");
  if (c2) {
    var p2 = Plot(c2, 1.25), xs = [0.3, -0.2], y0 = [-0.8, 0.7];
    var proj = function (x) { return [Math.max(-1, Math.min(1, x[0])), Math.max(-1, Math.min(1, x[1]))]; };
    var draw2 = function () {
      p2.size(); p2.axes();
      var eps = val("eg-eps") / 100, tau = val("eg-tau") / 100, n = val("eg-n");
      var M = [[eps, 1], [-1, eps]];
      var q = [-(M[0][0] * xs[0] + M[0][1] * xs[1]), -(M[1][0] * xs[0] + M[1][1] * xs[1])];
      var F = function (x) { return [M[0][0] * x[0] + M[0][1] * x[1] + q[0], M[1][0] * x[0] + M[1][1] * x[1] + q[1]]; };
      var pg = [y0], eg = [y0];
      for (var i = 0; i < n; i++) {
        var a = pg[i], fa = F(a); pg.push(proj([a[0] - tau * fa[0], a[1] - tau * fa[1]]));
        var b = eg[i], fb = F(b), y = proj([b[0] - tau * fb[0], b[1] - tau * fb[1]]), fy = F(y);
        eg.push(proj([b[0] - tau * fy[0], b[1] - tau * fy[1]]));
      }
      var ctx = p2.ctx; ctx.strokeStyle = css("--ink-2"); ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
      ctx.strokeRect(p2.X(-1), p2.Y(1), p2.X(1) - p2.X(-1), p2.Y(-1) - p2.Y(1)); ctx.setLineDash([]);
      ctx.globalAlpha = 0.6; p2.path(pg, css("--ink-3"), 1, true); ctx.globalAlpha = 1;
      p2.path(eg, css("--indigo"), 1.6, true); p2.mark(xs);
      var L = Math.hypot(1, eps);
      document.getElementById("eg-report").textContent = "After " + n + " steps: projected gradient is " + norm(pg[n], xs).toFixed(3) +
        " from the solution, extragradient " + norm(eg[n], xs).toExponential(2) + ". Extragradient is guaranteed to converge when τ < 1/L = " + (1 / L).toFixed(2) + ".";
    };
    bind(["eg-eps", "eg-tau", "eg-n"], {
      "eg-eps": function (v) { return (v / 100).toFixed(2); }, "eg-tau": function (v) { return (v / 100).toFixed(2); },
      "eg-n": function (v) { return String(v); } }, draw2);
    c2.addEventListener("click", function (e) { var r = c2.getBoundingClientRect(); y0 = proj(p2.inv(e.clientX - r.left, e.clientY - r.top)); draw2(); });
    draw2();
    window.addEventListener("resize", draw2);
    document.addEventListener("themechange", draw2);
  }
})();
