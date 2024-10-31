/**
 * @type {Cypress.PluginConfig}
 */
import * as fs from 'fs';
import * as path from 'path';
import * as registerCodeCoverageTasks from "@cypress/code-coverage/task";

export default (on, config) => {
  on('before:browser:launch', (browser: Cypress.Browser, launchOptions: Cypress.BrowserLaunchOptions) => {
    if (browser.family === 'chromium') {
      launchOptions.args.push('--window-size=1920,1080')
      launchOptions.args.push('--force-device-scale-factor=1');
      launchOptions.args.push('--force-color-profile=srgb');
      launchOptions.args.push('--disable-low-res-tiling');
      launchOptions.args.push('--disable-smooth-scrolling');
    }
    return launchOptions;
  });

  on('after:screenshot', (details) => {
    if (details.path.includes('failed')) {
      return;
    }

    return new Promise((resolve, reject) => {
      const language = config.env.language;

      const destPath = __dirname + "/../../../documentation/images/" + details.path.replace(".png", "").split('/').slice(-2).join('/') + "." + language + ".png";

      const destDir = path.dirname(destPath);

      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }

      fs.copyFile(details.path, destPath, (err) => {
        if (err) return reject(err)

        resolve({ path: destPath })
      })
    })
  })

  return registerCodeCoverageTasks(on, config);
};
