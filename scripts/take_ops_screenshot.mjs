import { spawn } from "child_process";
import fs from "fs";

const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const ARTIFACT_DIR = "/Users/carlg/.gemini/antigravity/brain/ee690060-7b63-4e07-b276-16fb51ab6219";
const PORT = 9333;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    console.log("Launching headless Chrome on port", PORT);
    const chrome = spawn(CHROME_PATH, [
        "--headless=new",
        "--disable-gpu",
        `--remote-debugging-port=${PORT}`,
        "--user-data-dir=/tmp/isolated-chrome-profile-ops",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900"
    ]);

    await sleep(2500);

    try {
        const versionRes = await fetch(`http://127.0.0.1:${PORT}/json/version`);
        const versionData = await versionRes.json();
        console.log("Connected to browser:", versionData.Browser);

        const newTabRes = await fetch(`http://127.0.0.1:${PORT}/json/new?https://dogtrainersdirectory.com.au/ops`, { method: "PUT" });
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

        await new Promise(resolve => ws.onopen = resolve);

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
        await sleep(3000);

        // Inject session storage with correct key and JSON structure
        console.log("Injecting passcode...");
        await send("Runtime.evaluate", {
            expression: `
                sessionStorage.setItem("dtd-admin-pass", JSON.stringify({
                    value: "7cBAJEinvqf9R_ha1mgowOW5rWfn8_2heNxflmXHj7SPljas",
                    expiresAt: Date.now() + 3600000
                }));
                location.reload();
            `
        });

        console.log("Waiting for dashboard to render...");
        await sleep(4000);

        // Capture Desktop Screenshot (1440x900)
        console.log("Capturing Desktop screenshot...");
        const resDesktop = await send("Page.captureScreenshot", { format: "png" });
        const desktopPath = `${ARTIFACT_DIR}/ops_redesign_desktop.png`;
        fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
        console.log("Saved desktop screenshot:", desktopPath);

        // Click on Messages tab
        console.log("Navigating to Messages view...");
        await send("Runtime.evaluate", {
            expression: `
                const msgBtn = document.querySelector('[data-testid="ops-nav-messages"]');
                if (msgBtn) msgBtn.click();
            `
        });
        await sleep(2000);

        console.log("Capturing Messages view screenshot...");
        const resMsg = await send("Page.captureScreenshot", { format: "png" });
        const msgPath = `${ARTIFACT_DIR}/ops_messages_view.png`;
        fs.writeFileSync(msgPath, Buffer.from(resMsg.result.data, "base64"));
        console.log("Saved messages view screenshot:", msgPath);

        // Switch back to overview for laptop resize
        await send("Runtime.evaluate", {
            expression: `
                const ovBtn = document.querySelector('[data-testid="ops-nav-overview"]');
                if (ovBtn) ovBtn.click();
            `
        });
        await sleep(1000);

        // Resize to 1200x800 and capture
        console.log("Capturing Laptop (1200x800) screenshot...");
        await send("Emulation.setDeviceMetricsOverride", {
            width: 1200,
            height: 800,
            deviceScaleFactor: 1,
            mobile: false
        });
        await sleep(1500);
        const resLaptop = await send("Page.captureScreenshot", { format: "png" });
        const laptopPath = `${ARTIFACT_DIR}/ops_redesign_laptop.png`;
        fs.writeFileSync(laptopPath, Buffer.from(resLaptop.result.data, "base64"));
        console.log("Saved laptop screenshot:", laptopPath);

        ws.close();
    } catch (err) {
        console.error("Error during screenshot:", err);
    } finally {
        chrome.kill();
        console.log("Chrome terminated.");
    }
}

main().catch(console.error);
