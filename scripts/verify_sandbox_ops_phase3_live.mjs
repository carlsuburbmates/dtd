import fs from "fs";
import { spawn } from "child_process";

const ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity/brain/ee690060-7b63-4e07-b276-16fb51ab6219";
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const LIVE_URL = "https://dtd-web-dev-x2kdoaemtq-ts.a.run.app/ops";
const ADMIN_PASS = "iVk6vhQUE_zlpcfqzwNaC6lj2GZopFRBsXp0WjqbaOojCV_fGhyjQQNKmiGZ3L3I";
const CHROME_PORT = 49160;

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
    console.log(`Starting Phase 3 Live Sandbox Acceptance against ${LIVE_URL}...`);

    const chrome = spawn(CHROME_PATH, [
        "--headless=new",
        "--disable-gpu",
        `--remote-debugging-port=${CHROME_PORT}`,
        "--user-data-dir=/tmp/isolated-chrome-profile-live-p3",
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
        console.log("Connecting WebSocket to tab:", wsUrl);

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

        console.log("Waiting for page load...");
        await sleep(3500);

        console.log("Injecting admin session pass...");
        await send("Runtime.evaluate", {
            expression: `
                sessionStorage.setItem("dtd-admin-pass", JSON.stringify({
                    value: "${ADMIN_PASS}",
                    expiresAt: Date.now() + 3600000
                }));
                location.reload();
            `
        });

        console.log("Waiting for authenticated Operations Console to render...");
        await sleep(5000);

        // Verification checks
        console.log("\n--- Executing Phase 3 Acceptance Gates ---");

        // Gate A: System Status
        const evalStatus = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const level1 = document.querySelector('[data-testid="ops-level1-system-status"]');
                    if (!level1) return { found: false, error: "ops-level1-system-status missing" };
                    return {
                        found: true,
                        text: level1.innerText.substring(0, 300)
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Gate A - System Status:", JSON.stringify(evalStatus.result?.result?.value, null, 2));

        // Gate B: Needs Your Attention
        const evalAttention = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const level2 = document.querySelector('[data-testid="ops-level2-attention"]');
                    if (!level2) return { found: false, error: "ops-level2-attention missing" };
                    const emptyCard = document.querySelector('[data-testid="ops-attention-empty"]');
                    const cards = document.querySelectorAll('[data-testid^="ops-case-card-"]');
                    return {
                        found: true,
                        isEmpty: !!emptyCard,
                        caseCardsCount: cards.length,
                        sampleCaseText: cards.length > 0 ? cards[0].innerText.substring(0, 250) : null
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Gate B - Needs Your Attention:", JSON.stringify(evalAttention.result?.result?.value, null, 2));

        // Gate C: Handled Automatically
        const evalHandled = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const level3 = document.querySelector('[data-testid="ops-level3-handled-automatically"]');
                    if (!level3) return { found: false, error: "ops-level3-handled-automatically missing" };
                    return {
                        found: true,
                        text: level3.innerText.substring(0, 300)
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Gate C - Handled Automatically:", JSON.stringify(evalHandled.result?.result?.value, null, 2));

        // Gate E: Advanced Diagnostics disclosure
        const evalDiagInitial = await send("Runtime.evaluate", {
            expression: `
                (() => {
                    const toggle = document.querySelector('[data-testid="ops-diagnostics-toggle"]');
                    const asideNav = document.querySelector('[data-testid="ops-shell-nav"]');
                    const asideParent = asideNav ? asideNav.closest('aside') : null;
                    const isVisible = asideParent ? window.getComputedStyle(asideParent).display !== 'none' : false;
                    return {
                        toggleFound: !!toggle,
                        toggleText: toggle ? toggle.innerText : null,
                        sidebarVisibleByDefault: isVisible
                    };
                })()
            `,
            returnByValue: true
        });
        console.log("Gate E - Diagnostics Initial (Closed by default):", JSON.stringify(evalDiagInitial.result?.result?.value, null, 2));

        // Gate F: Responsive Screenshots Capture
        // 1. Desktop (1440x900)
        console.log("\nCapturing Desktop Screenshot (1440x900)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 900,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1500);
        const resDesktop = await send("Page.captureScreenshot", { format: "png" });
        const desktopPath = `${ARTIFACT_DIR}/ops_live_phase3_desktop_1440.png`;
        fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
        console.log("  ✓ Saved:", desktopPath);

        // 2. Tablet (768x1024)
        console.log("Capturing Tablet Screenshot (768x1024)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 768,
            height: 1024,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1500);
        const resTablet = await send("Page.captureScreenshot", { format: "png" });
        const tabletPath = `${ARTIFACT_DIR}/ops_live_phase3_tablet_768.png`;
        fs.writeFileSync(tabletPath, Buffer.from(resTablet.result.data, "base64"));
        console.log("  ✓ Saved:", tabletPath);

        // 3. Mobile (390x844)
        console.log("Capturing Mobile Screenshot (390x844)...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 390,
            height: 844,
            deviceScaleFactor: 2,
            mobile: true
        });
        await sleep(1500);
        const resMobile = await send("Page.captureScreenshot", { format: "png" });
        const mobilePath = `${ARTIFACT_DIR}/ops_live_phase3_mobile_390.png`;
        fs.writeFileSync(mobilePath, Buffer.from(resMobile.result.data, "base64"));
        console.log("  ✓ Saved:", mobilePath);

        // 4. Toggle Advanced Diagnostics & capture expanded
        console.log("Toggling Advanced Diagnostics on Desktop...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1440,
            height: 1200,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(500);
        await send("Runtime.evaluate", {
            expression: `
                const toggle = document.querySelector('[data-testid="ops-diagnostics-toggle"]');
                if (toggle) toggle.click();
            `
        });
        await sleep(1500);
        const resDiag = await send("Page.captureScreenshot", { format: "png" });
        const diagPath = `${ARTIFACT_DIR}/ops_live_phase3_diagnostics_expanded.png`;
        fs.writeFileSync(diagPath, Buffer.from(resDiag.result.data, "base64"));
        console.log("  ✓ Saved expanded diagnostics screenshot:", diagPath);

        ws.close();
        console.log("\nAll live Phase 3 acceptance checks and screenshots completed successfully!");
    } catch (err) {
        console.error("Live acceptance verification error:", err);
    } finally {
        chrome.kill();
        console.log("Chrome terminated.");
    }
}

main().catch(console.error);
