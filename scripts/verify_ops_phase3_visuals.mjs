import http from "http";
import fs from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const BUILD_DIR = path.join(REPO_ROOT, "frontend", "build");
const ARTIFACT_DIR = process.env.DTD_VISUAL_ARTIFACT_DIR || path.join("/tmp", "dtd-ops-phase3-visuals");
const ADMIN_PASS = process.env.DTD_OPS_TEST_ADMIN_PASS;
if (!ADMIN_PASS) {
    throw new Error("Set DTD_OPS_TEST_ADMIN_PASS in the local environment to run this authenticated visual check.");
}
fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
const CHROME_PROFILE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), "dtd-ops-phase3-chrome-"));
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const SERVER_PORT = 49152;
const CHROME_PORT = 49153;

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

// Sample Phase 3 Oversight Snapshot
const mockOversightData = {
    generated_at: new Date().toISOString(),
    retention_cutoff: new Date(Date.now() - 30 * 86400000).toISOString(),
    system_status: {
        commercial_posture: {
            mode: "zero_risk_fail_closed",
            stripe_live_enabled: false,
            active_subscriptions: 0,
            description: "Zero financial risk · Live billing blocked"
        },
        readiness: {
            database: "connected",
            database_read_only: false,
            gemini_configured: true,
            postmark_configured: true,
            resend_configured: false,
            twilio_configured: true,
            stripe_webhook_secret_configured: false
        },
        engine_tick: {
            execution_owner: "cloud_scheduler",
            last_run: new Date(Date.now() - 120000).toISOString(),
            last_status: "ok",
            duration_ms: 2150,
            loops: {
                ranking: { status: "ok" },
                inference: { status: "ok" },
                health: { status: "ok" },
                sponsor_inventory: { status: "ok" },
                nurture: { status: "ok" },
                reactivation_route: { status: "ok" }
            }
        }
    },
    live_counts: {
        total_trainers: 42,
        published_trainers: 38,
        unclaimed_trainers: 4
    },
    alerts: [
        {
            key: "notif_delivery_failure",
            severity: "high",
            tone: "rose",
            title: "Notification Delivery Failures Detected",
            summary: "3 consecutive transactional notification failures in the last hour."
        }
    ],
    ops_cases: [
        {
            case_id: "inc-notif-resend-001",
            incident_id: "inc-notif-resend-001",
            queue: "needs_review",
            severity: "high",
            state: "reopened",
            title: "Resend Provider API Connection Refused",
            summary: "Transactional notification delivery failed across 3 retry attempts.",
            affected_entity: "notif-resend-postmark",
            impact_explanation: "Owner welcome emails and trainer match notifications cannot be dispatched until connectivity is restored.",
            recommended_action: "Inspect provider credentials and retry dispatch from queue.",
            first_seen_at: new Date(Date.now() - 3600000).toISOString(),
            last_seen_at: new Date(Date.now() - 300000).toISOString(),
            occurrences: 3,
            operational_state: "reopened",
            recurrence_count: 1,
            constituent_event_ids: ["evt-001", "evt-002", "evt-003"]
        },
        {
            case_id: "inc-supply-richmond-002",
            incident_id: "inc-supply-richmond-002",
            queue: "blocked_supply",
            severity: "medium",
            state: "detected",
            title: "Supply Shortage in Richmond / Burnley Catchment",
            summary: "Zero verified active trainers available for incoming puppy training inquiries.",
            affected_entity: "catchment:richmond-3121",
            impact_explanation: "Client match requests in 3121 are holding in deferred matching queue.",
            recommended_action: "Review pending trainer intake queue or widen search radius.",
            first_seen_at: new Date(Date.now() - 7200000).toISOString(),
            last_seen_at: new Date(Date.now() - 600000).toISOString(),
            occurrences: 1,
            operational_state: "detected",
            recurrence_count: 0
        }
    ],
    work_queue: {
        total_active_cases: 2,
        by_queue: {
            needs_review: 1,
            intro_ready: 0,
            blocked_supply: 1,
            health_watch: 0
        },
        cases: []
    },
    handled_automatically: {
        total_handled_24h: 148,
        summary: "148 background tasks executed successfully with 0 required manual steps.",
        items: [
            {
                task: "Serverless Engine Tick",
                count: 144,
                details: "Cloud Scheduler runs completed normally (ranking, health, nurture, inventory)",
                last_occurred: new Date(Date.now() - 120000).toISOString()
            },
            {
                task: "Guardian Audit",
                count: 2,
                details: "Verified invariant compliance across all active profiles with zero violations",
                last_occurred: new Date(Date.now() - 1800000).toISOString()
            },
            {
                task: "Fraud Suppression",
                count: 1,
                details: "Suspicious duplicate lead submission throttled without operator friction",
                last_occurred: new Date(Date.now() - 14400000).toISOString()
            },
            {
                task: "Delivery Recovery",
                count: 1,
                details: "Postmark transient timeout recovered automatically on secondary attempt",
                last_occurred: new Date(Date.now() - 28800000).toISOString()
            }
        ]
    },
    message_log: {
        total_events: 5,
        events: []
    },
    diagnostic_views: {
        pipeline_flow: { steps: [] },
        matching: { summary: {} },
        guardian: { status: "healthy" }
    }
};

function getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
        case ".html": return "text/html";
        case ".js": return "application/javascript";
        case ".css": return "text/css";
        case ".json": return "application/json";
        case ".png": return "image/png";
        case ".svg": return "image/svg+xml";
        default: return "application/octet-stream";
    }
}

// Start Static/API Mock Server
const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://localhost:${SERVER_PORT}`);

    if (url.pathname === "/api/oversight") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify(mockOversightData));
    }

    if (url.pathname.startsWith("/api/oversight/actions")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ success: true, message: "Action accepted" }));
    }

    // Serve static files from build
    let filePath = path.join(BUILD_DIR, url.pathname === "/" ? "index.html" : url.pathname);
    if (!fs.existsSync(filePath)) {
        filePath = path.join(BUILD_DIR, "index.html");
    }

    try {
        const content = fs.readFileSync(filePath);
        res.writeHead(200, { "Content-Type": getMimeType(filePath) });
        res.end(content);
    } catch (err) {
        res.writeHead(500);
        res.end(String(err));
    }
});

await new Promise((resolve) => server.listen(SERVER_PORT, "127.0.0.1", resolve));
console.log(`Local test server listening on port ${SERVER_PORT}`);

// Launch Chrome
console.log(`Launching Chrome headless on port ${CHROME_PORT}...`);
let chrome;
try {
chrome = spawn(CHROME_PATH, [
    "--headless=new",
    "--disable-gpu",
    `--remote-debugging-port=${CHROME_PORT}`,
    `--user-data-dir=${CHROME_PROFILE_DIR}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--window-size=1440,900"
], { stdio: ["ignore", "pipe", "pipe"] });

chrome.stdout.on("data", (d) => console.log("[Chrome stdout]", d.toString()));
chrome.stderr.on("data", (d) => console.log("[Chrome stderr]", d.toString()));

let versionData = null;
for (let i = 0; i < 15; i++) {
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

    const newTabRes = await fetch(`http://127.0.0.1:${CHROME_PORT}/json/new?http://127.0.0.1:${SERVER_PORT}/ops`, { method: "PUT" });
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

    console.log("Injecting admin session storage...");
    await send("Runtime.evaluate", {
        expression: `
            sessionStorage.setItem("dtd-admin-pass", ${JSON.stringify(JSON.stringify({ value: ADMIN_PASS, expiresAt: Date.now() + 3600000 }))});
            location.reload();
        `
    });

    console.log("Waiting for dashboard to render...");
    await sleep(4000);

    // 1. Desktop Screenshot (1440x900)
    console.log("Capturing Desktop screenshot (1440x900)...");
    await send("Emulation.setDeviceMetricsOverride", {
        width: 1440,
        height: 900,
        deviceScaleFactor: 1,
        mobile: false
    });
    await sleep(1000);
    const resDesktop = await send("Page.captureScreenshot", { format: "png" });
    const desktopPath = `${ARTIFACT_DIR}/ops_phase3_desktop_1440.png`;
    fs.writeFileSync(desktopPath, Buffer.from(resDesktop.result.data, "base64"));
    console.log("Saved desktop screenshot:", desktopPath);

    // 2. Tablet Screenshot (768x1024)
    console.log("Capturing Tablet screenshot (768x1024)...");
    await send("Emulation.setDeviceMetricsOverride", {
        width: 768,
        height: 1024,
        deviceScaleFactor: 2,
        mobile: true
    });
    await sleep(1000);
    const resTablet = await send("Page.captureScreenshot", { format: "png" });
    const tabletPath = `${ARTIFACT_DIR}/ops_phase3_tablet_768.png`;
    fs.writeFileSync(tabletPath, Buffer.from(resTablet.result.data, "base64"));
    console.log("Saved tablet screenshot:", tabletPath);

    // 3. Mobile Screenshot (390x844)
    console.log("Capturing Mobile screenshot (390x844)...");
    await send("Emulation.setDeviceMetricsOverride", {
        width: 390,
        height: 844,
        deviceScaleFactor: 2,
        mobile: true
    });
    await sleep(1000);
    const resMobile = await send("Page.captureScreenshot", { format: "png" });
    const mobilePath = `${ARTIFACT_DIR}/ops_phase3_mobile_390.png`;
    fs.writeFileSync(mobilePath, Buffer.from(resMobile.result.data, "base64"));
    console.log("Saved mobile screenshot:", mobilePath);

    // 4. Toggle Advanced Diagnostics on Desktop
    console.log("Switching back to Desktop and toggling Advanced Diagnostics...");
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
    const diagPath = `${ARTIFACT_DIR}/ops_phase3_diagnostics_expanded.png`;
    fs.writeFileSync(diagPath, Buffer.from(resDiag.result.data, "base64"));
    console.log("Saved diagnostics expanded screenshot:", diagPath);

    ws.close();
    console.log("All screenshots captured successfully!");
} catch (err) {
    console.error("Screenshot capture error:", err);
} finally {
    chrome?.kill();
    server.close();
    fs.rmSync(CHROME_PROFILE_DIR, { recursive: true, force: true });
    console.log("Chrome and test server terminated.");
}
