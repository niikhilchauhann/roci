import fs from "fs";

import { launchBrowser }
from "../modules/igrsup/browser/browser.js";

import { parsePropertyHTML }
from "../modules/igrsup/property/parser.js";

import {
  exportTransactions,
  createExportBaseName,
}
from "../modules/igrsup/property/exporter.js";

import {
  PROPERTY_SELECTORS,
}
from "../modules/igrsup/property/selectors.js";

import {
  SEARCH_CONFIG,
}
from "../modules/igrsup/property/search-config.js";

function cleanText(text) {
  return text
    ?.replace(/\s+/g, " ")
    ?.replace(/\n/g, " ")
    ?.trim();
}

async function waitForOptionValue(locator, value) {
  await locator.waitFor({ state: "visible", timeout: 0 });

  await locator.page().waitForFunction(
    ({ selector, optionValue }) => {
      const element = document.querySelector(selector);
      if (!element) return false;
      return Array.from(element.options || []).some(
        option => option.value === optionValue
      );
    },
    {
      selector: await locator.evaluate(element => {
        if (element.id) return `#${element.id}`;
        if (element.name)
          return `${element.tagName.toLowerCase()}[name="${element.name}"]`;
        return "";
      }),
      optionValue: value,
    },
    { timeout: 0 }
  );
}

async function pauseForManualLogin() {
  console.log("");
  console.log("=================================");
  console.log("LOGIN MANUALLY IN BROWSER");
  console.log("AFTER LOGIN PRESS ENTER");
  console.log("=================================");
  console.log("");

  process.stdin.resume();
  await new Promise(resolve => {
    process.stdin.once("data", () => resolve());
  });
}

async function main() {

  const { browser, context, page } = await launchBrowser();

  try {

    console.log("[SESSION] Loaded");

    await page.goto(PROPERTY_SELECTORS.searchPage, {
      waitUntil: "networkidle",
      timeout: 0,
    });

    await pauseForManualLogin();

    // ── Save session immediately after manual login ──
    fs.mkdirSync("./data/sessions", { recursive: true });
    await context.storageState({
      path: "./data/sessions/igrsup-session.json",
    });
    console.log("[SESSION] Session saved");

    await page.goto(PROPERTY_SELECTORS.searchPage, {
      waitUntil: "networkidle",
      timeout: 0,
    });

    console.log("[PAGE] Property page loaded");

    // ── Use corrected select selectors ──
    const districtSelect =
      page.locator(
        PROPERTY_SELECTORS.districtSelect
      );
    const sroLocator      = page.locator(PROPERTY_SELECTORS.sroSelect);
    const villageLocator  = page.locator(PROPERTY_SELECTORS.villageSelect);
    const submitLocator   = page.locator(PROPERTY_SELECTORS.submitButton).first();

    // ── District ──
    console.log(
      "[AUTO] Waiting district select"
    );

    await districtSelect.waitFor({
      state: "attached",
      timeout: 60000,
    });

    await page.waitForTimeout(5000);

    console.log(
      "[AUTO] District select ready"
    );
    console.log("[AUTO] Selecting district");
    await districtSelect.selectOption({
      value: SEARCH_CONFIG.districtCode,
    });
    await page.waitForTimeout(3000);
    console.log("[AUTO] District selected");

    // ── SRO ──
    console.log("[AUTO] Selecting SRO");
    await waitForOptionValue(sroLocator, SEARCH_CONFIG.sroCode);
    await sroLocator.selectOption({ value: SEARCH_CONFIG.sroCode });
    await page.waitForTimeout(3000);
    console.log("[AUTO] SRO selected");

    // ── Village ──
    console.log("[AUTO] Selecting village");
    await waitForOptionValue(villageLocator, SEARCH_CONFIG.villageCode);
    await villageLocator.selectOption({ value: SEARCH_CONFIG.villageCode });
    await page.waitForTimeout(3000);
    console.log("[AUTO] Village selected");

    console.log(
      "[AUTO] Waiting for property field activation"
    );

    console.log(
      "[AUTO] Checking property field state"
    );

    await page.waitForFunction(() => {
      const el =
        document.querySelector("#propertyId");

      if (!el) return false;

      const style =
        window.getComputedStyle(el);

      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        !el.disabled
      );
    }, {
      timeout: 60000,
    });

    await page.waitForTimeout(2000);

    console.log(
      "[AUTO] Property field activated"
    );

    // ── Property ID ──
    const inputDiagnostics =
      await page.evaluate(() => {
        const inputs = [
          ...document.querySelectorAll(
            "input, textarea"
          ),
        ];

        return {
          iframeCount:
            document.querySelectorAll("iframe")
              .length,
          inputs: inputs.map(el => ({
            tagName: el.tagName,
            id: el.id,
            name: el.name,
            className: el.className,
            type: el.type,
            placeholder: el.placeholder,
            value: el.value,
            visible:
              !!(
                el.offsetWidth ||
                el.offsetHeight ||
                el.getClientRects().length
              ),
            disabled: !!el.disabled,
            readOnly: !!el.readOnly,
            outerHTML: el.outerHTML,
          })),
        };
      });

    console.log(
      "[AUTO] Input diagnostics:",
      JSON.stringify(
        inputDiagnostics,
        null,
        2
      )
    );

    console.log(
      "[AUTO] Filling property ID"
    );

    const selectedPropertyField =
      await page.evaluate(() => {
        const isVisible = el =>
          !!(
            el.offsetWidth ||
            el.offsetHeight ||
            el.getClientRects().length
          );

        const getContextText = el =>
          (
            el.closest("tr, td, div, li, p")
              ?.innerText || ""
          ).toLowerCase();

        const candidates = [
          ...document.querySelectorAll(
            "input[type='text'], textarea"
          ),
        ]
          .filter(el =>
            isVisible(el) &&
            !el.disabled &&
            !el.readOnly
          )
          .map((el, index) => {
            const contextText =
              getContextText(el);
            const idText =
              `${el.id} ${el.name}`.toLowerCase();

            let score = 0;

            if (
              /खसरा|गाटा|plot|khasra|property/i.test(
                contextText
              )
            ) {
              score += 50;
            }

            if (
              /propertyid|propertynum|khasra|plot/i.test(
                idText
              )
            ) {
              score += 40;
            }

            if (
              /address|पता|propnewaddress/i.test(
                contextText + " " + idText
              )
            ) {
              score -= 100;
            }

            return {
              index,
              score,
              tagName: el.tagName,
              id: el.id,
              name: el.name,
              className: el.className,
              outerHTML: el.outerHTML,
              visible: isVisible(el),
              boundingBox: {
                x: el.getBoundingClientRect().x,
                y: el.getBoundingClientRect().y,
                width:
                  el.getBoundingClientRect().width,
                height:
                  el.getBoundingClientRect().height,
              },
            };
          })
          .sort((a, b) => b.score - a.score);

        const selected =
          candidates[0];

        if (!selected) {
          throw new Error(
            "No visible editable property candidate found"
          );
        }

        const target =
          [
            ...document.querySelectorAll(
              "input[type='text'], textarea"
            ),
          ].filter(el =>
            isVisible(el) &&
            !el.disabled &&
            !el.readOnly
          )[selected.index];

        if (!target) {
          throw new Error(
            "Selected property element no longer available"
          );
        }

        target.setAttribute(
          "data-igrsup-property-target",
          "true"
        );

        return selected;
      });

    console.log(
      "[AUTO] Selected property element outerHTML:",
      selectedPropertyField.outerHTML
    );
    console.log(
      "[AUTO] Selected property element bounding box:",
      selectedPropertyField.boundingBox
    );
    console.log(
      "[AUTO] Selected property element visibility:",
      selectedPropertyField.visible
    );

    await page.evaluate((value) => {
      const input = document.querySelector(
        '[data-igrsup-property-target="true"]'
      );

      if (!input) {
        throw new Error(
          "Active property field not found"
        );
      }

      input.removeAttribute("readonly");
      input.disabled = false;

      input.focus();
      input.value = value;

      input.dispatchEvent(
        new Event("input", { bubbles: true })
      );

      input.dispatchEvent(
        new Event("change", { bubbles: true })
      );

      input.dispatchEvent(
        new KeyboardEvent("keyup", {
          bubbles: true,
        })
      );

      input.blur();
    }, SEARCH_CONFIG.propertyId);

    await page.waitForTimeout(2000);

    console.log(
      "[AUTO] Re-reading property value"
    );

    const finalValue = await page.evaluate(() => {
      const input = document.querySelector(
        '[data-igrsup-property-target="true"]'
      );
      return input ? input.value : null;
    });

    console.log(
      "[AUTO] Final property value:",
      finalValue
    );

    if (!finalValue?.trim()) {
      throw new Error(
        "Property value still empty after DOM injection"
      );
    }

    console.log(
      "[AUTO] Property ID filled"
    );

    // ── Capture village name before submit ──
    const exportMeta = {
      villageName: cleanText(
        await villageLocator.evaluate(element => {
          const opt = element.options[element.selectedIndex];
          return opt ? opt.text : element.value;
        })
      ),
      plotValue: cleanText(SEARCH_CONFIG.propertyId),
    };

    // ── Submit ──
    console.log("[AUTO] Clicking submit");

    await submitLocator.waitFor({ state: "visible", timeout: 0 });
    await submitLocator.scrollIntoViewIfNeeded();

    // Set up new-tab listener BEFORE clicking
    const reportPagePromise = context.waitForEvent("page", { timeout: 0 });

    // force:true bypasses overlay/intercept issues that caused the recurring error
    await submitLocator.click({ force: true });

    console.log(
      "[AUTO] Submit clicked"
    );

    await page.waitForTimeout(5000);

    const popupPromise = page.waitForEvent("popup");

    await page
      .locator('input[name="action:getPropertyDeedSearchDetail"]')
      .click();

    const reportPage =
      await popupPromise;

    await reportPage.waitForLoadState("domcontentloaded");
    await reportPage.waitForTimeout(5000);

    console.log("[POPUP URL]", reportPage.url());

    const reportHtml =
      await reportPage.content();

    console.log(
      "[HAS REGISTRATION DATA]",
      reportHtml.includes("7771")
    );

    console.log(
      "[REPORT TABLE COUNT]",
      await reportPage.locator("table").count()
    );

    fs.writeFileSync(
      "./debug-report.html",
      reportHtml,
      "utf-8"
    );

    await reportPage.screenshot({
      path: "./debug-report-page.png",
      fullPage: true
    });

    const tables = await reportPage
      .locator("table")
      .evaluateAll((tables) =>
        tables.map((t, i) => ({
          index: i,
          rows: t.rows.length,
          id: t.id || "",
          className: t.className || "",
          text: t.innerText.slice(0, 300)
        }))
      );

    console.log(
      JSON.stringify(tables, null, 2)
    );

    const popupRows = await reportPage
      .locator("table tr")
      .evaluateAll(rows =>
        rows.map((row, index) => ({
          index,
          text: row.innerText,
          html: row.outerHTML
        }))
      );

    fs.writeFileSync(
      "./debug-popup-rows.json",
      JSON.stringify(popupRows, null, 2),
      "utf-8"
    );

    fs.mkdirSync("./data/raw", { recursive: true });
    fs.writeFileSync(
      "./data/raw/property-search-result.html",
      reportHtml,
      "utf-8"
    );

    const rows =
      parsePropertyHTML(reportHtml);
    console.log(`[PARSER] Rows extracted: ${rows.length}`);

    const fileBaseName = createExportBaseName({
      villageName:     cleanText(exportMeta.villageName),
      propertyId:      cleanText(exportMeta.plotValue),
      propertyAddress: cleanText(exportMeta.plotValue),
    });

    fs.mkdirSync("./data/exports", { recursive: true });

    const exportResult = exportTransactions(
      `./data/exports/${fileBaseName}`,
      rows
    );

    console.log("[EXPORT] JSON saved:", exportResult.jsonPath);
    console.log("[EXPORT] CSV saved:",  exportResult.csvPath);
    console.log("[COMPLETE] Export finished");

  } catch (error) {

    console.error(error);
    console.log("");
    console.log("=================================");
    console.log("SCRIPT FAILED");
    console.log("BROWSER KEPT OPEN FOR DEBUGGING");
    console.log("=================================");

    await new Promise(() => {});
  }
}

main();
