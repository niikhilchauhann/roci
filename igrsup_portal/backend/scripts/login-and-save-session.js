import fs from "fs";

import { chromium }
from "playwright";

const SESSION_FILE_PATH =
  "./data/sessions/igrsup-session.json";

async function main() {

  // LAUNCH
  const browser =
    await chromium.launch({
      headless: false,
    });

  // CONTEXT
  const context =
    await browser.newContext();

  // PAGE
  const page =
    await context.newPage();

  // OPEN LOGIN PAGE
  await page.goto(
    "https://igrsup.gov.in/igrsup/userServicesHomeAction"
  );

  console.log(
    "Fill captcha + OTP manually"
  );

  // WAIT FOR DASHBOARD
  await page.waitForURL(
    "**/userServicesDashboardAction",
    {
      timeout: 300000,
    }
  );

  console.log(
    "Dashboard loaded"
  );

  fs.mkdirSync(
    "./data/sessions",
    { recursive: true }
  );

  await context.storageState({
    path: SESSION_FILE_PATH,
  });

  console.log(
    "[SESSION] Loaded"
  );

  console.log(
    "Session saved successfully"
  );

}

main();
