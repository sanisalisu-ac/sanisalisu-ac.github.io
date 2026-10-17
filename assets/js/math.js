/* Renders $...$ and \(...\) / \[...\] with the self-hosted KaTeX. */
window.addEventListener("load", function () {
  if (typeof renderMathInElement !== "function") return;
  renderMathInElement(document.getElementById("main"), {
    delimiters: [
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false }
    ],
    throwOnError: false
  });
});
