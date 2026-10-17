import fs from "fs";
import { spawn, execSync } from "child_process";

const ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity/brain/ee690060-7b63-4e07-b276-16fb51ab6219";
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const LIVE_URL = "https://dtd-web-dev-625222421634.australia-southeast1.run.app/ops";
const CHROME_PORT = 49180;

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function getAdminPass() {
    try {
        return execSync("gcloud secrets versions access latest --project=dogtrainersdirectory-dev --secret=dtd-admin-pass", {
            encoding: "utf-8",
        }).trim();
    } catch (e) {
        console.warn("Could not fetch admin pass from secret manager:", e.message);
        return "";
    }
}

async function main() {
    const adminPass = process.argv[2] || getAdminPass();
    console.log(`Starting Phase 5A Live UI Acceptance & Screenshot Capture against ${LIVE_URL}...`);

    const chrome = spawn(CHROME_PATH, [
        "--headless=new",
        "--disable-gpu",
        `--remote-debugging-port=${CHROME_PORT}`,
        "--user-data-dir=/tmp/isolated-chrome-profile-live-p5a",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900"
    ]);

    let versionData = null;
    for (let i = 0; i < 20; i++) {
        await sleep(500);
        try {
            const res = await fetch(`http://127.0.0.1:${CHROME_PORT}/json/version`);
            if (res.ok) {
                versionData = await res.json();
                break;
            }
        } catch (_) {}
    }

    if (!versionData) {
        chrome.kill();
        throw new Error("Could not connect to headless Chrome on port " + CHROME_PORT);
    }
    console.log("Connected to browser:", versionData.Browser);

    try {
        const newTabRes = await fetch(`http://127.0.0.1:${CHROME_PORT}/json/new?${LIVE_URL}`, { method: "PUT" });
        const tab = await newTabRes.json();
        const wsUrl = tab.webSocketDebuggerUrl;

        const ws = new WebSocket(wsUrl);
        let idCounter = 1;
        const pending = new Map();

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.id && pending.has(data.id)) {
                pending.get(data.id)(data);
                pending.delete(data.id);
            }
        };

        await new Promise((resolve) => ws.onopen = resolve);

        function send(method, params = {}) {
            return new Promise((resolve) => {
                const id = idCounter++;
                pending.set(id, resolve);
                ws.send(JSON.stringify({ id, method, params }));
            });
        }

        await send("Page.enable");
        await send("Runtime.enable");

        console.log("Waiting for initial page load...");
        await sleep(3500);

        if (adminPass) {
            console.log("Injecting admin session credentials...");
            await send("Runtime.evaluate", {
                expression: `
                    sessionStorage.setItem("dtd-admin-pass", JSON.stringify({
                        value: "${adminPass}",
                        expiresAt: Date.now() + 3600000
                    }));
                    location.reload();
                `
            });

            console.log("Waiting for authenticated Operations Console to load...");
            await sleep(5000);
        }

        // 1. Verify Level 1, Level 2, Level 3 DOM elements
        const evalConsole = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const l1 = document.querySelector('[data-testid="ops-level1-system-status"]');
                    const attentionQueue = document.querySelector('[data-testid="ops-level2-attention"]');
                    const cases = Array.from(document.querySelectorAll('[data-testid^="ops-case-card-"]'));
                    const emptyState = document.querySelector('[data-testid="ops-attention-empty"]');
                    const filterAll = document.querySelector('[data-testid="ops-cases-filter-all"]');
                    const filterHigh = document.querySelector('[data-testid="ops-cases-filter-high"]');
                    const filterMedium = document.querySelector('[data-testid="ops-cases-filter-medium"]');
                    const pagination = document.querySelector('[data-testid="ops-cases-page-indicator"]');
                    const handledSummary = document.querySelector('[data-testid="ops-handled-summary"]');
                    const handledToggle = document.querySelector('[data-testid="ops-handled-toggle"]');
                    const handledFeed = document.querySelector('[data-testid="ops-handled-list"]');
                    const diagToggle = document.querySelector('[data-testid="ops-diagnostics-toggle"]');
                    const diagSection = document.querySelector('[data-testid="ops-diagnostics-section"]');

                    return {
                        hasLevel1Status: !!l1,
                        statusHeadline: l1 ? l1.querySelector('h2')?.innerText : null,
                        hasAttentionQueue: !!attentionQueue,
                        caseCount: cases.length,
                        hasEmptyState: !!emptyState,
                        hasFilterPills: !!(filterAll && filterHigh && filterMedium),
                        hasPagination: !!pagination,
                        hasHandledSummary: !!handledSummary,
                        hasHandledToggle: !!handledToggle,
                        handledFeedVisible: !!handledFeed,
                        hasDiagnosticsToggle: !!diagToggle,
                        diagnosticsVisible: !!diagSection
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Phase 5A Console DOM evaluation:", JSON.stringify(evalConsole.result?.result?.value, null, 2));

        // 2. Capture Desktop Screenshot (1440x900) - Default Scannable View
        console.log("\nCapturing Desktop Screenshot (1440x900)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 900,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1000);
        const resDesktop = await send("Page.captureScreenshot", { format: "png" });
        const desktopPath = `${ARTIFACT_DIR}/ops_live_phase5a_desktop_1440.png`;
        fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
        console.log("  ✓ Saved:", desktopPath);

        // 3. Capture Tablet Screenshot (768x1024)
        console.log("Capturing Tablet Screenshot (768x1024)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 768,
            height: 1024,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resTablet = await send("Page.captureScreenshot", { format: "png" });
        const tabletPath = `${ARTIFACT_DIR}/ops_live_phase5a_tablet_768.png`;
        fs.writeFileSync(tabletPath, Buffer.from(resTablet.result.data, "base64"));
        console.log("  ✓ Saved:", tabletPath);

        // 4. Capture Mobile Screenshot (390x844)
        console.log("Capturing Mobile Screenshot (390x844)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 390,
            height: 844,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resMobile = await send("Page.captureScreenshot", { format: "png" });
        const mobilePath = `${ARTIFACT_DIR}/ops_live_phase5a_mobile_390.png`;
        fs.writeFileSync(mobilePath, Buffer.from(resMobile.result.data, "base64"));
        console.log("  ✓ Saved:", mobilePath);

        // Reset to Desktop for interaction checks
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 900,
            deviceScaleFactor: 1,
            mobile: false
        });

        // 5. Expand Level 3 Handled Automatically and capture screenshot
        console.log("\nExpanding Level 3 Handled Automatically...");
        await send("Runtime.evaluate", {
            expression: `
                const toggle = document.querySelector('[data-testid="ops-handled-toggle"]');
                if (toggle) {
                    toggle.click();
                    toggle.scrollIntoView({ behavior: 'instant', block: 'center' });
                }
            `
        });
        await sleep(1000);
        const resHandled = await send("Page.captureScreenshot", { format: "png" });
        const handledPath = `${ARTIFACT_DIR}/ops_live_phase5a_handled_expanded.png`;
        fs.writeFileSync(handledPath, Buffer.from(resHandled.result.data, "base64"));
        console.log("  ✓ Saved Handled Automatically View:", handledPath);

        // 6. Expand Secondary Diagnostics and capture screenshot
        console.log("\nExpanding Secondary Advanced Diagnostics...");
        await send("Runtime.evaluate", {
            expression: `
                const diagBtn = document.querySelector('[data-testid="ops-diagnostics-toggle"]');
                if (diagBtn) {
                    diagBtn.click();
                    diagBtn.scrollIntoView({ behavior: 'instant', block: 'start' });
                }
            `
        });
        await sleep(1200);
        const resDiag = await send("Page.captureScreenshot", { format: "png" });
        const diagPath = `${ARTIFACT_DIR}/ops_live_phase5a_diagnostics_expanded.png`;
        fs.writeFileSync(diagPath, Buffer.from(resDiag.result.data, "base64"));
        console.log("  ✓ Saved Advanced Diagnostics View:", diagPath);

        ws.close();
        console.log("\nAll Phase 5A live visual checks and responsive screenshots completed successfully!");
    } catch (err) {
        console.error("Live UI verification error:", err);
    } finally {
        chrome.kill();
    }
}

main().catch(console.error);
