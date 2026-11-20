function showMatchLogoFallback(image) {
  image.classList.add("d-none");
  const fallback = image.parentElement.querySelector("[data-match-logo-fallback]");
  if (fallback) {
    fallback.classList.remove("d-none");
  }
}

function checkMatchLogos() {
  document.querySelectorAll("img[data-match-logo]").forEach(function (image) {
    if (image.complete && image.naturalWidth === 0) {
      showMatchLogoFallback(image);
    }
  });
}

checkMatchLogos();
window.addEventListener("load", checkMatchLogos);

document.addEventListener("error", function (event) {
  const image = event.target;
  if (image instanceof HTMLImageElement && image.matches("[data-match-logo]")) {
    showMatchLogoFallback(image);
  }
}, true);