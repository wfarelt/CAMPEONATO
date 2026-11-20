function showTeamLogoFallback(image) {
  image.classList.add("d-none");
  const fallback = image.parentElement.querySelector("[data-team-logo-fallback]");
  if (fallback) {
    fallback.classList.remove("d-none");
  }
}

function checkTeamLogos() {
  document.querySelectorAll("img[data-team-logo]").forEach(function (image) {
    if (image.complete && image.naturalWidth === 0) {
      showTeamLogoFallback(image);
    }
  });
}

checkTeamLogos();
window.addEventListener("load", checkTeamLogos);

document.addEventListener("error", function (event) {
  const image = event.target;
  if (image instanceof HTMLImageElement && image.matches("[data-team-logo]")) {
    showTeamLogoFallback(image);
  }
}, true);