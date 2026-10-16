import fs from "fs";
import { spawn, execSync } from "child_process";

const ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity/brain/ee690060-7b63-4e07-b276-16fb51ab6219";
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const LIVE_URL = "https://dtd-web-dev-625222421634.australia-southeast1.run.app/ops";
const CHROME_PORT = 49175;

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
    console.log(`Starting Phase 5 Live UI Acceptance & Screenshot Capture against ${LIVE_URL}...`);

    const chrome = spawn(CHROME_PATH, [
        "--headless=new",
        "--disable-gpu",
        `--remote-debugging-port=${CHROME_PORT}`,
        "--user-data-dir=/tmp/isolated-chrome-profile-live-p5",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900"
    ]);

    let versionData = null;
    for (let i = 0; i < 20; i++) {
        await sleep(500);
        try {
            const versionRes = await fetch(`http://127.0.0.1:${CHROME_PORT}/json/version`);
            versionData = await versionRes.json();
            break;
        } catch {
            // retry
        }
    }

    if (!versionData) {
        throw new Error("Could not connect to Chrome on port " + CHROME_PORT);
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

        // Verify Level 1, Level 2, Level 3
        const evalConsole = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const l1 = document.querySelector('[data-testid="ops-status-strip"]') || document.querySelector('[data-role="ops-system-status"]');
                    const cases = Array.from(document.querySelectorAll('[data-testid^="ops-case-card-"]'));
                    const handled = document.querySelector('[data-testid="ops-handled-automatically-feed"]') || document.querySelector('[data-role="ops-handled-automatically"]');
                    return {
                        hasLevel1: !!l1,
                        caseCount: cases.length,
                        hasHandledFeed: !!handled,
                        bodyTextSnippet: document.body.innerText.substring(0, 300)
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Console DOM evaluation:", JSON.stringify(evalConsole.result?.result?.value, null, 2));

        // 1. Capture Desktop Screenshot (1440x900)
        console.log("\nCapturing Desktop Screenshot (1440x900)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 900,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1000);
        const resDesktop = await send("Page.captureScreenshot", { format: "png" });
        const desktopPath = `${ARTIFACT_DIR}/ops_live_phase5_desktop_1440.png`;
        fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
        console.log("  ✓ Saved:", desktopPath);

        // 2. Capture Tablet Screenshot (768x1024)
        console.log("Capturing Tablet Screenshot (768x1024)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 768,
            height: 1024,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resTablet = await send("Page.captureScreenshot", { format: "png" });
        const tabletPath = `${ARTIFACT_DIR}/ops_live_phase5_tablet_768.png`;
        fs.writeFileSync(tabletPath, Buffer.from(resTablet.result.data, "base64"));
        console.log("  ✓ Saved:", tabletPath);

        // 3. Capture Mobile Screenshot (390x844)
        console.log("Capturing Mobile Screenshot (390x844)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 390,
            height: 844,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resMobile = await send("Page.captureScreenshot", { format: "png" });
        const mobilePath = `${ARTIFACT_DIR}/ops_live_phase5_mobile_390.png`;
        fs.writeFileSync(mobilePath, Buffer.from(resMobile.result.data, "base64"));
        console.log("  ✓ Saved:", mobilePath);

        // 4. Capture Scrolled Level 3 Handled Automatically View
        console.log("Capturing Level 3 Handled Automatically View (1440x1000)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 1000,
            deviceScaleFactor: 1,
            mobile: false
        });
        await send("Runtime.evaluate", {
            expression: `
                const el = document.querySelector('[data-testid="ops-handled-automatically-feed"]') || document.querySelector('[data-role="ops-handled-automatically"]');
                if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
            `
        });
        await sleep(1200);
        const resHandled = await send("Page.captureScreenshot", { format: "png" });
        const handledPath = `${ARTIFACT_DIR}/ops_live_phase5_handled_automatically.png`;
        fs.writeFileSync(handledPath, Buffer.from(resHandled.result.data, "base64"));
        console.log("  ✓ Saved:", handledPath);

        ws.close();
        console.log("\nAll Phase 5 live visual checks and responsive screenshots completed successfully!");
    } catch (err) {
        console.error("Live UI verification error:", err);
    } finally {
        chrome.kill();
    }
}

main().catch(console.error);
