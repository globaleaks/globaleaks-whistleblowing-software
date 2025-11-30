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

      on("after:screenshot", (details) => {
        if (details.path.includes("failed")) return;

        const language = config.env.language;
        const destPath = path.resolve(
          __dirname,
          "../documentation/images",
          details.path.replace(".png", "").split("/").slice(-2).join("/") +
            "." +
            language +
            ".png"
        );
        const destDir = path.dirname(destPath);
        if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
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
