import 'cypress-axe';
import "@cypress/code-coverage/support";

import "./commands";

Cypress.on("uncaught:exception", (err) => {
  return false;
});
