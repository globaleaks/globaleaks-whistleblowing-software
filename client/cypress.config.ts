import * as fs from 'fs';
import * as path from 'path';

import {defineConfig} from "cypress";
import registerCodeCoverageTasks from "@cypress/code-coverage/task";


export default defineConfig({
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
      // All your plugin logic goes here
      registerCodeCoverageTasks(on, config);

      on("before:browser:launch", (browser, launchOptions) => {
        if (browser.family === "chromium") {
          launchOptions.args.push("--window-size=1920,1080");
          launchOptions.args.push("--force-device-scale-factor=1");
        }
        return launchOptions;
      });

      on("after:screenshot", (details) => {
         if (details.path.includes("failed")) return;

         const language = config.env.language;

         // Get path relative to Cypress screenshots folder
         const relativePath = path.relative(config.screenshotsFolder, details.path);

         // Split path into segments
         const parts = relativePath.split(path.sep);

         // Remove the first segment (spec folder)
         const strippedParts = parts.slice(1); // removes "02-test-admin-perform-wizard.cy.ts"

         // Get folder and base name
         const folder = path.dirname(strippedParts.join(path.sep));   // e.g., "wizard" or "mobile/wizard"
         const baseName = path.basename(strippedParts.join(path.sep), ".png"); // e.g., "1"

         // Build destination path
         const destPath = path.resolve(
           __dirname,
           "../documentation/images",
           folder,
           `${baseName}.${language}.png`
         );

         // Ensure folder exists
         const destDir = path.dirname(destPath);
         if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });

         // Copy the file
         fs.copyFileSync(details.path, destPath);

        return { path: destPath };
      });

      on("task", {
        log(message) {
          console.log(message);
          return null;
        },
        table(message) {
          console.table(message);
          return null;
        },
      });

      return config;
    },
    baseUrl: "https://127.0.0.1:8443",
    viewportWidth: 1280,
    viewportHeight: 720
  },
  defaultCommandTimeout: 20000,
});
