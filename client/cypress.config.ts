import {defineConfig} from "cypress";

export default defineConfig({
  component: {
    devServer: {
      framework: "angular",
      bundler: "webpack",
    },
    specPattern: "**/*.cy.ts",
  },
  env: {
    "coverage": true,
    "language": "en",
    "codeCoverage": {
      "enabled": true
    },
    "pgp": false,
    "init_password": "Password12345#",
    "user_password": "ACollectionOfDiplomaticHistorySince_1966_ToThe_Pr esentDay#",
    "field_types": [
      "Single-line text input",
      "Multi-line text input",
      "Selection box",
      "Multiple choice input",
      "Checkbox",
      "Attachment",
      "Terms of service",
      "Date",
      "Date range",
      "Voice",
      "Group of questions"
    ],
    "takeScreenshots": true
  },
  e2e: {
    setupNodeEvents(on, config) {
      return require("./cypress/plugins/index.ts").default(on, config);
    },
    baseUrl: "https://127.0.0.1:8443",
    viewportWidth: 1920,
    viewportHeight: 1080
  },
  defaultCommandTimeout: 20000,
});
