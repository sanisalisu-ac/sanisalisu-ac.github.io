/* Publication list: filtering, search, BibTeX and PDF requests. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Bar chart heights (set here because the security policy forbids inline styles)
  $$(".yearbars .bar").forEach(function (b) { b.style.height = Math.max(2, +b.dataset.h) + "%"; });

  // ---- filtering (publications page only) ----
  var list = $("#pub-list");
  if (list) {
    var state = { topic: "", q1: false, lead: false, q: "" };
    var params = new URLSearchParams(location.search);
    if (params.get("topic")) state.topic = params.get("topic");
    if (params.get("q")) state.q = params.get("q");
    var search = $("#pub-search");
    if (state.q) search.value = state.q;

    var apply = function () {
      var terms = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      var shown = 0;
      $$(".pub", list).forEach(function (li) {
        var ok = (!state.topic || (" " + li.dataset.topics + " ").indexOf(" " + state.topic + " ") > -1) &&
          (!state.q1 || li.dataset.q1 === "1") &&
          (!state.lead || li.dataset.role !== "") &&
          terms.every(function (t) { return li.dataset.search.indexOf(t) > -1; });
        li.hidden = !ok;
        if (ok) shown++;
      });
      $$(".year-group", list).forEach(function (g) { g.hidden = !$(".pub:not([hidden])", g); });
      var total = $$(".pub", list).length;
      $("#result-count").textContent = shown === total ? "Showing all " + total + " publications" :
        "Showing " + shown + " of " + total + " publications";
      $("#pub-empty").hidden = shown !== 0;
      $$("[data-filter='topic']").forEach(function (c) { c.setAttribute("aria-pressed", String(c.dataset.value === state.topic)); });
      $$("[data-toggle]").forEach(function (c) { c.setAttribute("aria-pressed", String(state[c.dataset.toggle])); });
      var p = new URLSearchParams();
      if (state.topic) p.set("topic", state.topic);
      if (state.q) p.set("q", state.q);
      history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p : "") + location.hash);
    };
    $$("[data-filter='topic']").forEach(function (c) {
      c.addEventListener("click", function () { state.topic = c.dataset.value; apply(); });
    });
    $$("[data-toggle]").forEach(function (c) {
      c.addEventListener("click", function () { state[c.dataset.toggle] = !state[c.dataset.toggle]; apply(); });
    });
    var timer;
    search.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { state.q = search.value.trim(); apply(); }, 120);
    });
    apply();
  }

  // ---- dialogs ----
  var titleOf = function (id) {
    var li = document.getElementById(id);
    return li ? $(".pub-title", li).textContent.trim() : "";
  };
  var bibs = null;
  var getBibs = function () {
    if (!bibs) bibs = fetch("data/bibtex.json").then(function (r) { return r.json(); });
    return bibs;
  };

  var citeDlg = $("#cite-dialog");
  document.addEventListener("click", function (e) {
    var c = e.target.closest("[data-cite]");
    if (c && citeDlg) {
      var id = c.dataset.cite;
      $("#cite-paper").textContent = titleOf(id);
      $("#cite-status").textContent = "";
      $("#cite-bib").textContent = "Loading…";
      citeDlg.showModal();
      getBibs().then(function (b) { $("#cite-bib").textContent = b[id] || "BibTeX is not available for this entry."; })
        .catch(function () { $("#cite-bib").textContent = "BibTeX could not be loaded. Download the full file instead."; });
    }
    var r = e.target.closest("[data-request]");
    if (r && reqDlg) {
      var rid = r.dataset.request;
      var li = document.getElementById(rid);
      var link = li && $(".pub-actions a[href^='https://doi.org/']", li);
      $("#req-paper").textContent = titleOf(rid);
      $("#req-paper-field").value = titleOf(rid);
      $("#req-doi-field").value = link ? link.getAttribute("href") : "";
      $("#req-status").textContent = "";
      reqDlg.showModal();
      $("#req-name").focus();
    }
  });
  var copyBtn = $("#cite-copy");
  if (copyBtn) copyBtn.addEventListener("click", function () {
    var text = $("#cite-bib").textContent;
    var done = function () { $("#cite-status").className = "form-status ok"; $("#cite-status").textContent = "BibTeX copied to the clipboard."; };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { $("#cite-status").textContent = "Select the text above and copy it."; });
  });

  var reqDlg = $("#request-dialog");
  var reqForm = $("#request-form");
  if (reqForm) reqForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var fd = new FormData(reqForm);
    window.sendForm(reqForm, "PDF request: " + fd.get("paper"), [
      "I would be grateful for a copy of the following paper:", "", String(fd.get("paper")), String(fd.get("doi") || ""), "",
      "Institution: " + (fd.get("institution") || "not given"), "Purpose: " + (fd.get("message") || "not given")
    ], $("#req-status"));
  });

  // ---- maths in titles ----
  window.addEventListener("load", function () {
    if (typeof renderMathInElement === "function") renderMathInElement(document.getElementById("main"),
      { delimiters: [{ left: "$", right: "$", display: false }], throwOnError: false });
  });
})();
