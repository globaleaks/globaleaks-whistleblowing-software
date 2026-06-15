import 'cypress-axe';
import "@cypress/code-coverage/support";

import "./commands";

// Test-only stylesheet: stabilizes rendering for screenshots and reduces
// flakiness by killing animations/transitions and hiding transient overlays.
// Injected at window:before:load so it is present on every document load.
// Rules use !important so they win over Angular component styles, which are
// injected into <head> at runtime (after this <style>) by emulated view
// encapsulation.
const TEST_CSS = `
*, *::before, *::after {
  animation: none !important;
  transition: none !important;
}

.reveal {
  opacity: 1 !important;
}

#PageOverlay,
#Loader,
.tooltip {
  display: none !important;
}

.modal-content,
.dropdown-menu {
  border: unset !important;
  border-radius: unset !important;
}

table {
  font-size: 0.8125rem !important;
}
`;

Cypress.on("window:before:load", (win) => {
  const style = win.document.createElement("style");
  style.id = "cypress-test-css";
  style.innerHTML = TEST_CSS;
  win.document.documentElement.appendChild(style);
});

Cypress.on("uncaught:exception", (err) => {
  return false;
});
