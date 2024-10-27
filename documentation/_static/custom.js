document.addEventListener("DOMContentLoaded", function() {
    var mainElement = document.querySelector('[role="main"]');

    if (!mainElement) {
      return;
    }

    var banner = document.createElement("div");
    banner.className = 'donation-banner';
    banner.innerHTML = '<img src="https://raw.githubusercontent.com/globaleaks/globaleaks-whistleblowing-software/stable/brand/assets/heart.svg" class="donation-icon" alt="Donate" /> Globaleaks is free and open-source whistleblowing software. <a href="https://github.com/sponsors/globaleaks">Donate here to support its development!</a>';
    mainElement.insertBefore(banner, mainElement.firstChild);
});
