import fs from "fs";
import { chromium } from "playwright";

const SESSION_FILE_PATH =
  "./data/sessions/igrsup-session.json";

export async function launchBrowser() {
  console.log("Launching browser...");

  const browser = await chromium.launch({
    headless: false,
  });

  let context;

  if (fs.existsSync(SESSION_FILE_PATH)) {
    console.log(
      "[SESSION] Loading saved session..."
    );

    try {
      context = await browser.newContext({
        storageState: SESSION_FILE_PATH,
        viewport: {
          width: 1280,
          height: 900,
        },
      });

      console.log(
        "[SESSION] Session restored successfully"
      );
    } catch (error) {
      console.warn(
        "[SESSION] Saved session could not be restored"
      );
      console.warn(error.message);
    }
  }

  if (!context) {
    console.warn(
      "[SESSION] No valid saved session found, continuing without session restore"
    );

    context = await browser.newContext({
      viewport: {
        width: 1280,
        height: 900,
      },
    });
  }

  const page = await context.newPage();

  return {
    browser,
    context,
    page,
  };
}
