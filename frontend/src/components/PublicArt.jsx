import React from "react";

function NetworkArtwork() {
    return (
        <>
            <defs>
                <linearGradient id="network-wash" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#F7F1E7" />
                    <stop offset="45%" stopColor="#E7E1D5" />
                    <stop offset="100%" stopColor="#D6C9B5" />
                </linearGradient>
                <linearGradient id="network-line" x1="10%" y1="10%" x2="90%" y2="90%">
                    <stop offset="0%" stopColor="#D06D4F" />
                    <stop offset="50%" stopColor="#9D8C66" />
                    <stop offset="100%" stopColor="#27473E" />
                </linearGradient>
            </defs>
            <rect x="16" y="16" width="608" height="688" rx="28" fill="url(#network-wash)" />
            <circle cx="154" cy="188" r="52" fill="#F3E6D8" opacity="0.8" />
            <circle cx="476" cy="520" r="94" fill="#EBDBC7" opacity="0.9" />
            <path d="M118 472C192 378 262 324 334 308C424 288 500 318 546 392" stroke="url(#network-line)" strokeWidth="4" fill="none" strokeLinecap="round" />
            <path d="M132 514C208 458 282 430 356 432C424 434 478 462 514 512" stroke="#27473E" strokeWidth="1.5" fill="none" opacity="0.5" />
            <path d="M154 210C196 258 234 290 286 318C338 346 406 370 464 366" stroke="#D06D4F" strokeWidth="2.5" fill="none" opacity="0.75" strokeLinecap="round" />
            <circle cx="152" cy="186" r="8" fill="#27473E" />
            <circle cx="282" cy="318" r="6" fill="#D06D4F" />
            <circle cx="466" cy="366" r="8" fill="#27473E" />
            <circle cx="544" cy="392" r="10" fill="#D06D4F" />
            <rect x="124" y="114" width="164" height="92" rx="22" fill="#FCF9F4" stroke="#D8CBB8" />
            <rect x="332" y="460" width="156" height="110" rx="24" fill="#FCF9F4" stroke="#D8CBB8" />
            <path d="M164 164C194 138 224 138 248 158C270 176 276 206 258 228C238 252 202 260 170 242C146 228 146 190 164 164Z" fill="#27473E" opacity="0.9" />
            <path d="M364 518C394 496 430 498 454 522C478 548 472 584 442 600C406 620 360 608 342 578C328 554 338 534 364 518Z" fill="#D06D4F" opacity="0.85" />
        </>
    );
}

function TrainerArtwork() {
    return (
        <>
            <defs>
                <linearGradient id="trainer-wash" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#F8F3EA" />
                    <stop offset="55%" stopColor="#E6DED1" />
                    <stop offset="100%" stopColor="#CEC1AD" />
                </linearGradient>
            </defs>
            <rect x="16" y="16" width="608" height="688" rx="28" fill="url(#trainer-wash)" />
            <rect x="102" y="122" width="420" height="470" rx="36" fill="#FAF6F0" stroke="#D9CDBA" />
            <path d="M186 248C220 214 262 204 298 226C326 244 344 276 344 312C344 358 314 394 266 402C228 408 198 394 176 364C154 334 156 284 186 248Z" fill="#27473E" opacity="0.94" />
            <path d="M314 250C354 224 396 220 430 238C470 258 492 300 488 344C484 392 448 430 394 438C356 444 324 434 298 408C322 386 336 352 336 314C336 292 328 268 314 250Z" fill="#E8D5BF" />
            <path d="M204 494C248 468 298 456 358 458C418 460 460 476 492 504" stroke="#D06D4F" strokeWidth="4" fill="none" strokeLinecap="round" />
            <path d="M182 538C234 514 296 502 370 504C430 506 474 520 506 542" stroke="#27473E" strokeWidth="1.6" fill="none" opacity="0.55" />
            <rect x="156" y="518" width="136" height="44" rx="18" fill="#F6ECE0" stroke="#D9CDBA" />
            <rect x="316" y="518" width="168" height="44" rx="18" fill="#F6ECE0" stroke="#D9CDBA" />
        </>
    );
}

function TrustArtwork() {
    return (
        <>
            <defs>
                <linearGradient id="trust-wash" x1="10%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#F7F3EC" />
                    <stop offset="50%" stopColor="#E9E3D8" />
                    <stop offset="100%" stopColor="#D6CCBF" />
                </linearGradient>
            </defs>
            <rect x="16" y="16" width="608" height="688" rx="28" fill="url(#trust-wash)" />
            <circle cx="320" cy="316" r="164" fill="#FBF8F2" stroke="#D9CCB8" strokeWidth="2" />
            <path d="M320 210L410 246V322C410 408 350 458 320 474C290 458 230 408 230 322V246L320 210Z" fill="#27473E" />
            <path d="M320 248L378 272V320C378 382 338 420 320 432C302 420 262 382 262 320V272L320 248Z" fill="#F7EFE3" />
            <path d="M296 332L316 352L352 308" stroke="#D06D4F" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M146 500C204 456 262 434 320 434C378 434 438 456 494 500" stroke="#27473E" strokeWidth="2" fill="none" opacity="0.35" />
            <path d="M134 532C198 494 260 476 320 476C380 476 444 494 506 532" stroke="#D06D4F" strokeWidth="3.5" fill="none" opacity="0.75" strokeLinecap="round" />
        </>
    );
}

function PricingArtwork() {
    return (
        <>
            <defs>
                <linearGradient id="pricing-wash" x1="0%" y1="10%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#F7F3EC" />
                    <stop offset="52%" stopColor="#E7DFD3" />
                    <stop offset="100%" stopColor="#D7CBBA" />
                </linearGradient>
            </defs>
            <rect x="16" y="16" width="608" height="688" rx="28" fill="url(#pricing-wash)" />
            <rect x="120" y="144" width="400" height="400" rx="40" fill="#FBF8F4" stroke="#D9CDBA" />
            <rect x="168" y="204" width="304" height="74" rx="24" fill="#27473E" opacity="0.96" />
            <rect x="168" y="302" width="304" height="50" rx="18" fill="#EEE6DA" />
            <rect x="168" y="372" width="204" height="50" rx="18" fill="#EEE6DA" />
            <rect x="386" y="372" width="86" height="50" rx="18" fill="#D06D4F" opacity="0.88" />
            <path d="M150 556C210 522 266 506 320 506C374 506 430 522 490 556" stroke="#27473E" strokeWidth="2" fill="none" opacity="0.35" />
            <path d="M144 590C214 552 274 536 320 536C366 536 426 552 496 590" stroke="#D06D4F" strokeWidth="3.5" fill="none" opacity="0.75" strokeLinecap="round" />
        </>
    );
}

const VARIANT_COPY = {
    network: {
        eyebrow: "Verified rollout",
        title: "Real local coverage over generic listings",
        detail: "A quieter, more selective public surface for owners and trainers in Greater Melbourne.",
        artwork: <NetworkArtwork />,
    },
    trainer: {
        eyebrow: "Trainer standards",
        title: "Prepared for quality, not volume",
        detail: "A sharper trainer-facing presence with calmer proof, clearer structure, and stronger early signals.",
        artwork: <TrainerArtwork />,
    },
    trust: {
        eyebrow: "Consent and care",
        title: "Trust shown with structure",
        detail: "Boundaries, consent, and contact expectations made visible without sounding bureaucratic.",
        artwork: <TrustArtwork />,
    },
    pricing: {
        eyebrow: "Commercial clarity",
        title: "Simple model with clear expectations",
        detail: "Pricing and billing surfaces should feel composed, exact, and easy to understand.",
        artwork: <PricingArtwork />,
    },
};

export default function PublicArt({ variant = "network", className = "", compact = false }) {
    const copy = VARIANT_COPY[variant] || VARIANT_COPY.network;

    return (
        <div className={`art-panel ${compact ? "art-panel-compact" : ""} ${className}`.trim()}>
            <div className="art-panel__frame">
                <svg
                    viewBox="0 0 640 720"
                    className="art-panel__svg"
                    aria-hidden="true"
                    focusable="false"
                    role="presentation"
                >
                    {copy.artwork}
                </svg>
            </div>
            <div className="art-panel__copy">
                <div className="small-caps">{copy.eyebrow}</div>
                <h2 className="font-serif text-[2rem] leading-[0.95] text-[#203D35] mt-3">
                    {copy.title}
                </h2>
                <p className="text-sm sm:text-base text-[#52645F] mt-3 max-w-md">
                    {copy.detail}
                </p>
            </div>
        </div>
    );
}
