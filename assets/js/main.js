/* Site-wide behaviour: menu, theme toggle, protected email links, contact form. */
(function () {
  "use strict";

  // Mobile menu
  var menuBtn = document.getElementById("menu-toggle");
  var nav = document.getElementById("nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
      menuBtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }

  // Theme toggle (remembered on this device only)
  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
      document.dispatchEvent(new CustomEvent("themechange"));
    });
  }

  // Email addresses are assembled in the browser so that harvesters do not find them in the HTML.
  document.querySelectorAll(".js-email").forEach(function (a) {
    var addr = a.dataset.u + "@" + a.dataset.d;
    a.textContent = addr;
    a.href = "mailto:" + addr;
  });

  // Shared helpers for the request and contact forms
  window.SiteConfig = fetch("data/site.json").then(function (r) { return r.json(); }).catch(function () { return {}; });

  window.sendForm = function (form, subject, bodyLines, statusEl) {
    return window.SiteConfig.then(function (cfg) {
      var fd = new FormData(form);
      if (fd.get("_gotcha")) return true; // silently drop bot submissions
      var email = String(fd.get("email") || "").trim();
      var name = String(fd.get("name") || "").trim();
      if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        statusEl.className = "form-status err";
        statusEl.textContent = "Enter your name and a valid email address.";
        return false;
      }
      if (cfg.formspree_id) {
        fd.append("_subject", subject);
        statusEl.className = "form-status";
        statusEl.textContent = "Sending…";
        return fetch("https://formspree.io/f/" + encodeURIComponent(cfg.formspree_id), {
          method: "POST", body: fd, headers: { Accept: "application/json" }
        }).then(function (r) {
          if (!r.ok) throw new Error("status " + r.status);
          statusEl.className = "form-status ok";
          statusEl.textContent = "Sent. You will receive a reply by email.";
          form.reset();
          return true;
        }).catch(function () {
          statusEl.className = "form-status err";
          statusEl.textContent = "The message could not be sent. Try again, or use the email address on the contact page.";
          return false;
        });
      }
      // No form service configured: open the visitor's email program with everything filled in.
      var to = (cfg.email_user || "") + "@" + (cfg.email_domain || "");
      var body = bodyLines.concat(["", "Name: " + name, "Email: " + email]).join("\n");
      window.location.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      statusEl.className = "form-status ok";
      statusEl.textContent = "Your email program should now open with the message ready to send.";
      return true;
    });
  };

  var contact = document.getElementById("contact-form");
  if (contact) {
    contact.addEventListener("submit", function (e) {
      e.preventDefault();
      var fd = new FormData(contact);
      window.sendForm(contact, "Website: " + fd.get("topic"),
        [String(fd.get("message") || "")], document.getElementById("contact-status"));
    });
  }

  // Dialog close buttons and backdrop clicks
  document.querySelectorAll("dialog").forEach(function (d) {
    d.addEventListener("click", function (e) { if (e.target === d && !d.classList.contains("lightbox")) d.close(); });
    d.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", function () { d.close(); }); });
  });
})();
