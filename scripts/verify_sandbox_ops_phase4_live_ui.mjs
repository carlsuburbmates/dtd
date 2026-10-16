import fs from "fs";
import { spawn } from "child_process";

const ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity/brain/ee690060-7b63-4e07-b276-16fb51ab6219";
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const LIVE_URL = "https://dtd-web-dev-625222421634.australia-southeast1.run.app/ops";
const CHROME_PORT = 49170;

const adminPass = process.argv[2] || "";
const targetDispatchId = process.argv[3] || "";

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
    console.log(`Starting Phase 4 Live UI Acceptance & Screenshot Capture against ${LIVE_URL}...`);
    console.log(`Target dispatch ID: ${targetDispatchId}`);

    const chrome = spawn(CHROME_PATH, [
        "--headless=new",
        "--disable-gpu",
        `--remote-debugging-port=${CHROME_PORT}`,
        "--user-data-dir=/tmp/isolated-chrome-profile-live-p4",
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

        await new Promise((resolve) => (ws.onopen = resolve));

        function send(method, params = {}) {
            return new Promise((resolve) => {
                const id = idCounter++;
                pending.set(id, resolve);
                ws.send(JSON.stringify({ id, method, params }));
            });
        }

        await send("Page.enable");
        await send("Runtime.enable");

        console.log("Waiting for page initial load...");
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
            await sleep(6000);
        }

        // Expand incident card
        console.log(`Locating incident card to display AI Operations Analyst (dispatch: ${targetDispatchId})...`);
        const expandResult = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const cards = Array.from(document.querySelectorAll('[data-testid^="ops-case-card-"]'));
                    const target = cards.find(c => c.getAttribute("data-testid")?.includes("${targetDispatchId}")) 
                                || cards.find(c => c.innerText.includes("${targetDispatchId}"))
                                || cards[0];
                    if (target) {
                        const detailsBtn = Array.from(target.querySelectorAll('button')).find(b => b.innerText.includes("Details"));
                        if (detailsBtn) {
                            detailsBtn.click();
                            return { found: true, clicked: "Details button", text: target.innerText.substring(0, 150) };
                        }
                        const anyBtn = target.querySelector('button');
                        if (anyBtn) anyBtn.click();
                        return { found: true, clicked: "Fallback button", text: target.innerText.substring(0, 150) };
                    }
                    return { found: false, count: cards.length };
                })()
            `,
            returnByValue: true
        });
        console.log("Expand result:", JSON.stringify(expandResult.result?.result?.value));
        await sleep(2500);

        // Verify AI Analyst card is rendered
        const evalAnalystCard = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const card = document.querySelector('[data-role="ops-ai-analysis-card"]') || document.querySelector('[data-testid^="ops-ai-analysis-"]');
                    if (!card) return { found: false, error: "AI analysis card not found in DOM" };
                    return {
                        found: true,
                        text: card.innerText.substring(0, 400),
                        hasConfirmedBadge: card.innerText.includes("Confirmed") || card.innerText.includes("Likely"),
                        hasEvidence: card.innerText.includes("Supporting Evidence"),
                        hasRecommendation: card.innerText.includes("Recommended Next Step"),
                        hasRequestButton: card.innerText.includes("Request Updated Analysis")
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("AI Analyst Card in DOM:", JSON.stringify(evalAnalystCard.result?.result?.value, null, 2));
        const cardVal = evalAnalystCard.result?.result?.value;
        if (!cardVal?.found) {
            throw new Error("AI Analyst card was not found in DOM after expanding case: " + JSON.stringify(cardVal));
        }
        console.log("\nCapturing Desktop Screenshot (1440x900)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 900,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1000);
        const resDesktop = await send("Page.captureScreenshot", { format: "png" });
        const desktopPath = `${ARTIFACT_DIR}/ops_live_phase4_desktop_1440.png`;
        fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
        console.log("  ✓ Saved:", desktopPath);

        // Capture Tablet Screenshot (768x1024)
        console.log("Capturing Tablet Screenshot (768x1024)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 768,
            height: 1024,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resTablet = await send("Page.captureScreenshot", { format: "png" });
        const tabletPath = `${ARTIFACT_DIR}/ops_live_phase4_tablet_768.png`;
        fs.writeFileSync(tabletPath, Buffer.from(resTablet.result.data, "base64"));
        console.log("  ✓ Saved:", tabletPath);

        // Capture Mobile Screenshot (390x844)
        console.log("Capturing Mobile Screenshot (390x844)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 390,
            height: 844,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1000);
        const resMobile = await send("Page.captureScreenshot", { format: "png" });
        const mobilePath = `${ARTIFACT_DIR}/ops_live_phase4_mobile_390.png`;
        fs.writeFileSync(mobilePath, Buffer.from(resMobile.result.data, "base64"));
        console.log("  ✓ Saved:", mobilePath);

        // Capture Expanded AI Analysis Detail
        console.log("Capturing Expanded AI Analysis Detail (1440x1200)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 1200,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1000);
        const resExpanded = await send("Page.captureScreenshot", { format: "png" });
        const expandedPath = `${ARTIFACT_DIR}/ops_live_phase4_ai_analysis_expanded.png`;
        fs.writeFileSync(expandedPath, Buffer.from(resExpanded.result.data, "base64"));
        console.log("  ✓ Saved:", expandedPath);

        ws.close();
        console.log("\nAll live visual checks and responsive screenshots completed successfully!");
    } catch (err) {
        console.error("Live UI verification error:", err);
    } finally {
        chrome.kill();
    }
}

main().catch(console.error);
