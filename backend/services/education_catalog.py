from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


CAPABILITIES: List[Dict[str, str]] = [
    {"key": "safe_home_setup", "label": "Safe home setup"},
    {"key": "calm_routine", "label": "Calm routine"},
    {"key": "early_problem_handling", "label": "Early problem handling"},
    {"key": "dog_reading_basics", "label": "Dog-reading basics"},
    {"key": "fear_response", "label": "Fear response"},
    {"key": "reward_timing", "label": "Reward timing"},
    {"key": "public_handling", "label": "Public handling"},
    {"key": "freedom_boundaries", "label": "Freedom boundaries"},
    {"key": "trainer_readiness", "label": "Trainer readiness"},
]


TOOLS: List[Dict[str, Any]] = [
    {
        "slug": "safe-home-checklist",
        "title": "Safe Home Checklist",
        "module_slug": "the-blueprint",
        "type": "checklist",
        "summary": "Set up one safe base area and calm rest zone before giving the dog freedom they cannot handle yet.",
        "items": [
            "Choose one smaller starting area the dog can rest in without constant interruption.",
            "Add soft bedding, fresh water, and one safe chew or food item.",
            "Remove or secure cords, bins, shoes, medicines, cleaning products, and risky foods.",
            "Check for small swallowable objects, toxic plants, batteries, and garden-product access.",
            "Use barriers so the dog starts in one predictable area before earning more house freedom.",
        ],
    },
    {
        "slug": "first-vet-visit-checklist",
        "title": "First Vet Visit Checklist",
        "module_slug": "the-blueprint",
        "type": "checklist",
        "summary": "Bring useful observations and practical questions instead of vague worry or internet guesswork.",
        "items": [
            "Bring feeding, toileting, sleep, vomiting, diarrhoea, energy, and handling observations.",
            "Ask about vaccines, parasite prevention, local disease risks, and microchip or registration status.",
            "Ask how to handle safe early exposure before full vaccination in your local area.",
            "Ask which changes should trigger an urgent vet call and how to make future visits lower-stress.",
        ],
    },
    {
        "slug": "potty-routine-reset",
        "title": "Potty Routine Reset",
        "module_slug": "the-transition-phase",
        "type": "checklist",
        "summary": "Use a calm seven-step reset so accidents become a timing and supervision problem, not a punishment spiral.",
        "items": [
            "Take the dog to the same toilet area each time and keep the trip quiet and boring.",
            "Reward within one or two seconds of the dog toileting in the right place.",
            "Supervise closely after coming back inside so near-misses are caught early.",
            "If you find a mess later, clean it calmly with an odour-removing cleaner and tighten the next cycle.",
        ],
    },
    {
        "slug": "first-week-stabilisation-checklist",
        "title": "First-Week Stabilisation Checklist",
        "module_slug": "the-transition-phase",
        "type": "checklist",
        "summary": "Create a predictable first-week rhythm so the dog stops guessing and the owner stops changing the plan every hour.",
        "items": [
            "Use the same wake, toilet, food, calm interaction, toilet, and rest pattern every day.",
            "Keep the dog's world smaller with one safe rest space, supervised freedom, and fewer novelty spikes.",
            "Keep greetings, departures, and sleep periods calm instead of constantly resetting the setup.",
            "Track when problems happen so you simplify the day before judging the dog.",
        ],
    },
    {
        "slug": "stress-signal-watch-card",
        "title": "Stress Signal Watch Card",
        "module_slug": "the-empathy-engine",
        "type": "reference",
        "summary": "Watch the whole dog so you catch early stress, space-seeking, and shutdown signals before the dog has to escalate.",
        "items": [
            "Check the whole body: eyes, mouth, ears, tail, posture, movement, breathing, and distance from the trigger.",
            "Track early signals such as head turns, lip licking, yawning, panting, tucked tail, freezing, moving away, or refusing food.",
            "If several signals cluster together, pause, create space, and see whether the dog relaxes when pressure drops.",
        ],
    },
    {
        "slug": "illness-red-flag-prompt",
        "title": "Illness Red Flag Prompt",
        "module_slug": "the-empathy-engine",
        "type": "prompt",
        "summary": "Use a vet-first filter when behaviour changes look sudden, physical, painful, or linked to touch, movement, appetite, toileting, or energy.",
        "items": [
            "Ask whether the change is new, sudden, physical, or linked to handling, movement, appetite, water, sleep, or toileting.",
            "Look for pain, limping, stiffness, vomiting, diarrhoea, lethargy, yelping, panting at rest, or sudden handling sensitivity.",
            "If the pattern looks medical, pause the training frame and contact a vet before guessing.",
        ],
    },
    {
        "slug": "safe-exposure-checklist",
        "title": "Safe Exposure Checklist",
        "module_slug": "the-social-filter",
        "type": "checklist",
        "summary": "Use a short before-during-after filter so each exposure stays safe, brief, and easy enough for the dog to cope.",
        "items": [
            "Before exposure, confirm the session is short, rewards are ready, distance can be created, and no forced contact is planned.",
            "During exposure, the dog should still be able to eat, sniff, look away, retreat, and avoid being crowded or frozen.",
            "After exposure, check whether the dog recovered quickly, settled afterward, and whether trigger and distance were recorded.",
            "If recovery was poor, make the next session easier instead of repeating the same pressure.",
        ],
    },
    {
        "slug": "fear-log",
        "title": "Traffic-Light Exposure Log",
        "module_slug": "the-social-filter",
        "type": "log",
        "summary": "Track each exposure as green, yellow, or red so the owner can see which triggers are improving, stuck, or becoming unsafe.",
        "prompts": [
            "What was the exposure type and distance or intensity?",
            "Was the dog's response green, yellow, or red, and what was the first worry sign?",
            "Could the dog take food and move away?",
            "How long did recovery take, what helped, and what should change next time?",
        ],
    },
    {
        "slug": "say-please-routine-card",
        "title": "Say Please Routine Card",
        "module_slug": "the-sync-mechanics",
        "type": "checklist",
        "summary": "Use one daily routine at a time so food, doors, greetings, attention, and play stop tipping into chaos before the dog can think.",
        "items": [
            "Choose one routine and define the smallest calm behaviour you can reward before excitement spikes.",
            "Make the situation easier, reward the tiny calm moment, and do not wait for perfection.",
            "Pause calmly if the dog becomes frantic and repeat the same pattern next time instead of changing the rule.",
            "Review after a few days: is recovery faster, is calm behaviour repeating more often, or does the routine still need to be easier?",
        ],
    },
    {
        "slug": "family-cue-agreement",
        "title": "Family Cue Agreement",
        "module_slug": "the-sync-mechanics",
        "type": "template",
        "summary": "Make the human rule first so every person uses the same cue, the same response, and the same management plan.",
        "items": [
            "Choose one word for the behaviour, one response for unwanted behaviour, and one reward for the desired behaviour.",
            "Agree how doors, jumping, barking, stolen items, food bowls, rest areas, and visitor greetings will be handled.",
            "Define one management plan for moments when the dog cannot cope so the dog is not getting different rules from different people.",
        ],
    },
    {
        "slug": "street-hazard-rules",
        "title": "Street Hazard Rules",
        "module_slug": "the-urban-flow-and-the-shield",
        "type": "reference",
        "summary": "Use a simple walk shield so the owner scans ahead, shortens risk windows, and prevents dangerous access before the dog gets there.",
        "items": [
            "Before the walk, check equipment, bring rewards, choose a route that matches the dog's current ability, and avoid high-risk rubbish zones where possible.",
            "During the walk, scan ahead, shorten the lead near hazards, cross or turn early, reward looking away from ground hazards, and do not chase if the dog grabs something.",
            "After the walk, record hazards, triggers, and whether the route was too hard so the next walk can be made easier.",
        ],
    },
    {
        "slug": "window-barking-environment-checklist",
        "title": "Window Barking Environment Checklist",
        "module_slug": "the-urban-flow-and-the-shield",
        "type": "checklist",
        "summary": "Reduce visual and sound rehearsal before treating barking like a pure obedience problem.",
        "items": [
            "Check whether the dog can see the footpath, street, neighbours, dogs, or fence line and whether outdoor sounds are repeating every day.",
            "Use shields such as blinds, frosted film, furniture moves, gates, background sound, or rest zones away from the trigger.",
            "Offer enrichment before known trigger times and reward quiet moments before barking starts.",
            "Track which shield changes reduce duration and help the dog recover afterward.",
        ],
    },
    {
        "slug": "freedom-expansion-checklist",
        "title": "Freedom Expansion Checklist",
        "module_slug": "the-freedom-framework",
        "type": "checklist",
        "summary": "Use this before adding a new room or more unsupervised time so freedom expands only when the dog can still succeed.",
        "items": [
            "Confirm the dog is toileting, chewing, and resting reliably in the current area before expanding access.",
            "Check the new room for cords, shoes, laundry, bins, food, plants, small objects, rugs, and window or fence triggers.",
            "Keep the trial short, supervised, and easy enough to reverse without punishment if problems appear.",
        ],
    },
    {
        "slug": "room-access-trial-log",
        "title": "Room Access Trial Log",
        "module_slug": "the-freedom-framework",
        "type": "log",
        "summary": "Track whether a new room actually works before increasing access again.",
        "prompts": [
            "Which room or area was added, for how long, and was supervision active?",
            "Did toileting, chewing, and rest stay successful in that space?",
            "What problem appeared, if any, and did it happen only when supervision dropped?",
            "Should access increase, stay the same, or reduce on the next trial?",
        ],
    },
    {
        "slug": "optional-toilet-signal-bell-check",
        "title": "Optional Toilet Signal Bell Check",
        "module_slug": "the-freedom-framework",
        "type": "checklist",
        "summary": "Use a toilet bell only when the routine is already clear and the household can keep the meaning narrow.",
        "items": [
            "Confirm the dog already has a regular toilet routine and the whole household agrees the bell means toilet trip only.",
            "Keep the bell routine calm and boring: bell, straight to toilet area, reward toileting, return inside calmly.",
            "Track whether ringing leads to toileting or turns into play, barking, or door-demanding instead.",
        ],
    },
    {
        "slug": "family-rules-template",
        "title": "Family Rules Template",
        "module_slug": "the-freedom-framework",
        "type": "template",
        "summary": "Write the core household rules down so freedom stays clear instead of changing with each person or day.",
        "items": [
            "Choose the rules that matter most first: rooms, rest area, couch, doors, food, visitors, children, stolen items, outdoor access, and alone time.",
            "Agree what everyone does, what everyone avoids, and how long the rule will be followed before changing it.",
            "Keep the plan realistic. A rule no one follows is not a real rule.",
        ],
    },
    {
        "slug": "trainer-summary-builder",
        "title": "Trainer Summary Builder",
        "module_slug": "the-freedom-framework",
        "type": "trainer_readiness",
        "summary": "Prepare a clean issue summary before contacting a trainer or using future live matching.",
        "prompts": [
            "What is the main concern?",
            "What usually happens before it?",
            "How often does it happen?",
            "What have you already tried?",
            "Is anyone unsafe?",
            "What outcome do you want?",
        ],
    },
]

COURSE_STAGES: List[Dict[str, str]] = [
    {
        "key": "foundations",
        "title": "Foundations",
        "summary": "Set the home up properly and stabilize the first-wave problems before they compound.",
    },
    {
        "key": "reading-and-response",
        "title": "Reading and Response",
        "summary": "Read the dog earlier, reduce pressure faster, and build cleaner owner timing and routines.",
    },
    {
        "key": "real-world-handling",
        "title": "Real-World Handling",
        "summary": "Carry the system into public life, house freedom, and trainer-readiness decisions.",
    },
]


MODULES: List[Dict[str, Any]] = [
    {
        "slug": "the-blueprint",
        "number": 1,
        "title": "The Blueprint",
        "objective": "Set up the environment so the dog can settle before behaviour problems start stacking.",
        "eyebrow": "Guide 1",
        "strapline": "Safe home, rest zone, first vet/cost baseline.",
        "stage_key": "foundations",
        "intro": "Before training problems begin, the home needs a safe setup. This guide helps the owner build one safe base area, create a usable rest zone, remove common hazards, prepare for the first vet visit, and understand the basic cost reality of dog ownership.",
        "outcome": "By the end of this module, the owner should be able to set up one safe base area, create a calm rest zone without using it as punishment, remove common hazards, know when poisoning needs immediate advice, prepare useful vet questions, understand the first-year cost reality, and know what to record before later trainer or vet support.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You have one safe starting area and one calm rest space that the dog can actually use.",
            "The main household, food, medication, and garden hazards have been removed or secured.",
            "You have a first-vet question list and a realistic routine-versus-emergency cost baseline.",
        ],
        "signs_of_progress": [
            "The dog settles faster because the environment is calmer and easier to understand.",
            "The owner changes setup and safety first instead of reacting as if every early problem is training failure.",
        ],
        "capability_keys": ["safe_home_setup", "calm_routine"],
        "teaser_scenario": "The dog has arrived, the house feels chaotic, and every room is becoming a stress rehearsal zone.",
        "teaser_mistake": "Giving the dog full run of the house before there is one quiet, protected rest zone.",
        "teaser_next_step": "Start with one calm home base and one simple setup checklist before chasing behaviour fixes.",
        "trainer_readiness_prompt": "If settling problems persist after the setup reset, record what the dog does, when, and where.",
        "tool_refs": ["safe-home-checklist", "first-vet-visit-checklist"],
        "lessons": [
            {
                "slug": "home-base-first",
                "title": "Build the Home Base",
                "estimated_minutes": 6,
                "scenario": "The new dog arrives home, seems quiet at first, then starts pacing, chewing, following people constantly, and struggling to settle. The house already feels chaotic, and the owner is unsure whether this is a training problem or a setup problem.",
                "notice": [
                    "A new dog needs a smaller, safer starting area before full access to the home.",
                    "The goal is not to trap the dog. The goal is to make the home easier to understand and easier to rest in.",
                ],
                "common_mistake": "Giving the dog full freedom too soon, or only using the crate, pen, or laundry area after something has already gone wrong.",
                "decision_rule": "Start small, calm, and safe. Create one protected base area and rest zone before expanding the dog's world.",
                "do_now": [
                    "Create one safe base area with soft bedding, water, and one safe chew or food item.",
                    "Use barriers, a pen, a gated room, or an open crate setup to reduce chaos and protect rest.",
                ],
                "watch_for": [
                    "Does the dog settle faster when traffic, noise, and access are reduced?",
                    "Does the dog become frantic, chew more, or follow people constantly when they are overtired or cannot switch off?",
                ],
                "when_to_seek_help": "If the dog cannot settle anywhere, panics in the rest area, tries to injure themselves escaping confinement, or suddenly seems unwell or distressed.",
                "trainer_readiness_note": "Record where the dog sleeps, how long they can rest, what happens before they become unsettled, and whether distress starts immediately or after a delay.",
                "media": [
                    {"type": "visual", "title": "Safe-base layout", "description": "A simple home-base sketch showing one safe starting area, low household traffic, soft bedding, water, and barrier use."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Safe-base check", "prompt": "Can your dog rest safely here without getting into trouble, or does the setup still make mistakes too easy?"},
                ],
            },
            {
                "slug": "hazards-before-habits",
                "title": "Remove Household Hazards",
                "estimated_minutes": 5,
                "scenario": "The dog picks something up from the floor, steals food, chews a packet, digs near garden products, or mouths something from the bathroom, garage, laundry, or bin. The owner is not sure whether it is dangerous.",
                "notice": [
                    "Many ordinary household and garden items can seriously harm dogs, including medicines, pest-control products, batteries, xylitol, strings, magnets, and some foods or plants.",
                    "A dog does not need to look sick immediately for the situation to be serious.",
                ],
                "common_mistake": "Waiting to see what happens, trying home remedies first, or throwing away the packet before calling a vet.",
                "decision_rule": "If your dog may have swallowed or contacted a toxin, treat it as a vet question first. Do not guess, and do not improvise treatment.",
                "do_now": [
                    "Move the dog away from the hazard and prevent further access.",
                    "Keep the packet, label, plant sample, or a photo if safe to do so, and call your vet, emergency vet, or the Animal Poisons Helpline.",
                ],
                "watch_for": [
                    "Vomiting, diarrhoea, drooling, wobbliness, unusual tiredness, tremors, seizures, breathing change, or collapse.",
                    "Remember that some poisonings worsen before obvious signs appear.",
                ],
                "when_to_seek_help": "Immediately, if exposure is possible. Suspected poisoning is not a training problem and not a wait-and-see problem.",
                "trainer_readiness_note": "Tell the vet what the dog may have eaten or contacted, the amount, time, product or plant name, the dog's weight, symptoms, and any packaging or photos. A trainer only becomes relevant later if the dog repeatedly scavenges or raids hazards after the medical risk is handled.",
                "media": [
                    {"type": "visual", "title": "Hazard sweep", "description": "A room-by-room hazard audit for medicines, foods, bins, batteries, garden products, plants, and small swallowable objects."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Vet-first check", "prompt": "If this item could seriously harm a dog, what information would you need before calling the vet or poison service?"},
                ],
            },
            {
                "slug": "first-vet-and-cost-baseline",
                "title": "Prepare the First Vet Visit",
                "estimated_minutes": 6,
                "scenario": "The dog is home, the owner has food and bedding, but now needs clarity on vaccines, parasite prevention, microchipping, registration, safe early exposure, desexing questions, and what the first year may actually cost.",
                "notice": [
                    "The first vet visit is not just for vaccines. It is the first professional baseline for general health, local disease risks, behaviour-relevant health questions, and low-stress future care.",
                    "Routine costs and unexpected costs need to be planned separately, because cost stress can quickly become a welfare issue.",
                ],
                "common_mistake": "Waiting until there is a problem, going to the vet without questions, or delaying care because the first-year costs were underestimated.",
                "decision_rule": "Book early and bring notes. Ask what this dog needs in this local area and this household, not only what the internet says puppies need.",
                "do_now": [
                    "Book the first vet visit and bring paperwork, food details, vaccine or microchip details, and notes about appetite, toileting, sleep, vomiting, diarrhoea, fear, handling, or sudden changes.",
                    "Create a simple dog budget with separate routine, setup, and unexpected-cost sections before the first scare or surprise bill.",
                ],
                "watch_for": [
                    "Cost stress becomes a welfare issue when it starts delaying vet visits, prevention, or treatment.",
                    "Speak to a vet first if the dog seems unwell, painful, lethargic, has vomiting or diarrhoea, has eaten something unsafe, or suddenly behaves differently.",
                ],
                "when_to_seek_help": "Vet advice comes before training advice when symptoms look physical, urgent, or unsafe. Be upfront about budget limits so care can be prioritised realistically.",
                "trainer_readiness_note": "Record what changed, when it started, what the dog ate or contacted, vaccine history if known, stool quality, appetite, sleep pattern, and any fear signals during travel or handling.",
                "media": [
                    {"type": "video", "title": "First-vet and budget prep", "description": "A short walkthrough showing what to bring to the first vet visit and how to separate routine costs from emergency costs."},
                    {"type": "visual", "title": "First-week blueprint timeline", "description": "Day 0: prepare one safe living area and one quiet sleep space, Day 3: book the first vet visit and list your questions, Day 5: build the dog budget line and emergency buffer."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Baseline prep", "prompt": "What does this dog need in this local area, and what would become difficult if an emergency cost hit next month?"},
                ],
            },
        ],
    },
    {
        "slug": "the-transition-phase",
        "number": 2,
        "title": "The Transition Phase",
        "objective": "Stabilize the common early problems that overwhelm new owners before those problems harden into chaos.",
        "eyebrow": "Guide 2",
        "strapline": "Toileting, biting, chewing, owner overwhelm.",
        "stage_key": "foundations",
        "intro": "The first days and weeks with a new puppy or dog often feel messy because the dog and household are still adjusting. This guide helps the owner stabilise toileting, biting, chewing, crying, and early overwhelm before those problems harden into daily chaos.",
        "outcome": "By the end of this module, the owner can recognise common transition problems, tighten routine without punishment, redirect biting and chewing safely, reduce over-arousal through rest and supervision, and record useful patterns if vet or trainer help is needed.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You have one predictable first-week rhythm for toileting, food, rest, and supervised freedom.",
            "You can respond to accidents, mouthing, and chewing without punishment, chasing, or panic.",
            "You know which timing, rest, and supervision details to record if the same problem keeps repeating.",
        ],
        "signs_of_progress": [
            "Problems start clustering around clear triggers such as long awake periods, play, meals, or too much freedom.",
            "The owner simplifies the day first instead of changing rules every time a new problem appears.",
        ],
        "capability_keys": ["early_problem_handling", "calm_routine"],
        "teaser_scenario": "Accidents, biting, crying, and owner overwhelm are making the first week feel like a failing system.",
        "teaser_mistake": "Escalating the owner's reaction instead of tightening supervision and routine.",
        "teaser_next_step": "Return to a simpler routine first, then judge whether the issue is normal adjustment or something larger.",
        "trainer_readiness_prompt": "If the same pattern keeps breaking through despite a cleaner routine, prepare a short behaviour log.",
        "tool_refs": ["potty-routine-reset", "first-week-stabilisation-checklist"],
        "lessons": [
            {
                "slug": "accidents-need-routine-not-anger",
                "title": "Accidents Need Routine, Not Anger",
                "estimated_minutes": 6,
                "scenario": "Your puppy goes outside, comes back in, and toilets on the floor a few minutes later, leaving you frustrated and unsure whether the dog is confused, difficult, or doing it on purpose.",
                "notice": [
                    "Toileting is a routine and timing issue before it becomes a behaviour problem.",
                    "Learning happens at the exact moment the dog toilets in the right place, so late rewards weaken the lesson.",
                ],
                "common_mistake": "Punishing after the accident with yelling, scolding, dragging the dog to the mess, or acting angry while cleaning.",
                "decision_rule": "Reward the correct moment. Tighten the routine, use the same toilet area, and reinforce toileting in the right place within one or two seconds.",
                "do_now": [
                    "Take the dog to the same toileting area, stay calm and quiet, wait, and reward immediately after the dog toilets.",
                    "If you catch indoor toileting in progress, interrupt calmly, go straight outside, and reward if the dog finishes there.",
                    "If you find the accident later, clean it calmly, avoid scolding, and tighten supervision on the next cycle.",
                ],
                "watch_for": [
                    "Track the time, location, what happened before it, the last meal, drink, nap, and outdoor toilet chance.",
                    "Notice whether accidents cluster around play, excitement, missed supervision, or too much freedom after coming back inside.",
                ],
                "when_to_seek_help": "Seek vet advice first if a previously reliable dog suddenly starts toileting inside, the dog strains, cries, seems unable to hold urine, or there are health signs such as blood, diarrhoea, vomiting, lethargy, or sudden behaviour change. Seek trainer support if the routine is consistent but accidents continue, supervision keeps breaking down, the dog hides to toilet, or the pattern stays unclear after several days of tracking.",
                "trainer_readiness_note": "Before asking for help, record the dog's age, how long they have been home, how often and where accidents happen, whether they toilet outside when given the chance, whether the dog is punished or interrupted, how accidents are cleaned, and whether any health signs are present.",
                "media": [
                    {"type": "visual", "title": "Potty reset flow", "description": "A simple routine map showing the outside attempt, immediate reward, calm return inside, and supervision reset."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Reward timing check", "prompt": "Did the reward land within one or two seconds of toileting in the right place, or is the timing still too loose?"},
                ],
            },
            {
                "slug": "biting-and-chewing-without-chaos",
                "title": "Biting and Chewing Without Chaos",
                "estimated_minutes": 6,
                "scenario": "Your puppy bites hands, sleeves, ankles, or clothing and chews furniture, shoes, cords, or bedding, making normal interaction feel painful, personal, and exhausting.",
                "notice": [
                    "Puppies explore with their mouths, and biting often spikes when they are tired, overstimulated, teething, bored, under-rested, or given too much freedom.",
                    "Chewing escalates when legal chew options are not ready before the dog needs them or when rough play turns hands and clothing into part of the game.",
                ],
                "common_mistake": "Treating all biting as aggression or making hands, sleeves, pushing, squealing, chasing, or prying items from the mouth part of the game.",
                "decision_rule": "Do not become the toy. Prepare legal chewing options early, redirect calmly, and end the interaction before the dog's arousal spills over.",
                "do_now": [
                    "Prepare safe chew toys, food puzzles, stuffed rubber toys, supervised shredding items if appropriate, and toy-based play before problems start.",
                    "When biting starts, pause, stop moving hands and clothing, offer a toy or chew, and if the dog cannot redirect, end the interaction calmly and move to a rest break.",
                    "If the dog grabs something unsafe, do not chase or pry the mouth open unless it is an emergency. Offer a high-value swap and remove access next time.",
                ],
                "watch_for": [
                    "Track whether biting or chewing happens after long awake periods, rough play, visitors, hunger, overstimulation, alone-time, or wide access to the home.",
                    "Notice whether the dog had safe chew options available and whether the pattern is easier to redirect before tired or frantic periods.",
                ],
                "when_to_seek_help": "Seek trainer or vet guidance if bites are hard, repeated, escalating, or feel defensive rather than playful; if the dog stiffens, freezes, growls, snaps, guards items, or cannot redirect; or if chewing keeps reaching dangerous items despite setup changes. Seek vet guidance first if the dog seems painful, suddenly different, unusually irritable, unwell, or defensive about handling.",
                "trainer_readiness_note": "Before booking help, record what the dog bites or chews, the time of day, what happened immediately before, sleep or rest before the incident, whether chew options were available, whether the dog could redirect, bite intensity, and whether growling, freezing, guarding, or fear showed up.",
                "media": [
                    {"type": "video", "title": "Redirect before frantic", "description": "A short demonstration of pausing, offering a legal chew, and moving the dog into a calmer outlet before the interaction tips over."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "State before story", "prompt": "What changed just before the biting started: sleep, arousal, freedom, visitors, or access to legal chew options?"},
                ],
            },
            {
                "slug": "owner-overwhelm-is-data",
                "title": "Owner Overwhelm Is Data",
                "estimated_minutes": 5,
                "scenario": "The first day felt manageable, but now every hour seems to bring a new problem: toileting, chewing, biting, crying, refusing to settle, or needing constant attention.",
                "notice": [
                    "The first week is a transition period where the dog is learning where to sleep, toilet, chew, rest, and how much freedom they actually have.",
                    "Owner overwhelm usually means the day has too many moving parts, too little rest, or too many changing rules for the current stage.",
                ],
                "common_mistake": "Trying to fix every issue separately by reacting harder to accidents, roughhousing through biting, changing the sleeping setup every night, or searching random advice and changing the plan again.",
                "decision_rule": "Stabilise the day before judging the dog. Simplify the routine first, then solve one repeat problem at a time.",
                "do_now": [
                    "Create a predictable daily rhythm: wake, toilet, food, short calm interaction, toilet, rest, then repeat.",
                    "Keep the dog's world smaller with the same toilet area, predictable meals, one safe rest space, supervised freedom, calm greetings and departures, safe chew options, and uninterrupted sleep.",
                    "Choose one problem to track instead of reacting to all of them at once.",
                ],
                "watch_for": [
                    "Notice whether problems spike after long awake periods, after meals, after play, after visitors, when the owner is distracted, when the dog has too much space, or when household rules change.",
                    "Track which part of the day breaks first and whether the dog knows what happens next or is still guessing.",
                ],
                "when_to_seek_help": "Seek support if the dog cannot rest at all, panics when left briefly, biting is intense, repeated, or frightening, the dog seems unwell or suddenly different, the owner feels unable to cope safely, household conflict is escalating, or the same issue keeps worsening despite a simpler routine.",
                "trainer_readiness_note": "Before asking for help, record what time the problem happens, what happened just before it, how long the dog had been awake, whether the dog had toileted recently, what the dog had access to, what the owner did next, and whether the pattern is improving, staying the same, or worsening.",
                "media": [
                    {"type": "interactive", "title": "First-week stabilizer", "description": "A guided checklist for simplifying the day so the dog stops guessing and the owner can see which pattern actually needs attention first."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Stabilise before solving", "prompt": "What single problem should you track first once the daily rhythm is simple enough to repeat?"},
                ],
            },
        ],
    },
    {
        "slug": "the-empathy-engine",
        "number": 3,
        "title": "The Empathy Engine",
        "objective": "Teach owners to read the dog earlier so they stop mislabelling stress, fear, and illness as attitude.",
        "eyebrow": "Guide 3",
        "strapline": "Dog signals, stress signs, illness red flags.",
        "stage_key": "reading-and-response",
        "intro": "Many early behaviour problems are really communication problems. This guide helps the owner notice stress, fear, over-arousal, discomfort, and possible illness before the dog escalates, so they know when to pause, create space, change the setup, contact a vet, or prepare for trainer support.",
        "outcome": "By the end of this module, the owner can watch the whole dog instead of one body part, notice early stress and distance-seeking signals, stop forcing uncomfortable interactions, treat freezing, growling, and snapping as warning information, and switch to a vet-first lens when behaviour change looks sudden or physical.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You can name the first cluster of body signals the dog shows before a larger reaction in at least one recurring situation.",
            "You respond to warnings by reducing pressure and creating safety instead of forcing the dog through the moment.",
            "You know which sudden or physical behaviour changes should trigger a vet-first response before training advice.",
        ],
        "signs_of_progress": [
            "The owner spots stress earlier because they are reading the whole dog, not waiting for barking or snapping.",
            "Escalations feel more understandable because the trigger, distance, recovery, and body pattern are being recorded clearly.",
        ],
        "capability_keys": ["dog_reading_basics"],
        "teaser_scenario": "The dog is being described as stubborn, but the body is already showing strain and avoidance.",
        "teaser_mistake": "Judging the behaviour before reading the body that produced it.",
        "teaser_next_step": "Slow down long enough to catch the first signal, not just the visible blow-up.",
        "trainer_readiness_prompt": "If you need help later, bring the first signs you saw before the barking, freezing, or refusal.",
        "tool_refs": ["stress-signal-watch-card", "illness-red-flag-prompt"],
        "lessons": [
            {
                "slug": "see-the-first-signal",
                "title": "Read the Whole Dog",
                "estimated_minutes": 6,
                "scenario": "Your dog turns their head away when someone reaches toward them, then licks their lips, lowers their body, moves away, pants, freezes, or avoids eye contact while someone insists they are 'fine'.",
                "notice": [
                    "Dogs communicate with their whole body, not one isolated signal.",
                    "Eyes, mouth, ears, tail, posture, movement, breathing, distance from the trigger, and willingness to take food all matter together.",
                ],
                "common_mistake": "Looking only for obvious signs such as barking, growling, snapping, or biting and missing the quieter discomfort signals that came first.",
                "decision_rule": "Read the cluster, not the single sign. If several signals point to discomfort or distance-seeking, pause.",
                "do_now": [
                    "Stop what is happening, give the dog space, reduce pressure, and move the dog away from the trigger if needed.",
                    "Do not punish the signal or force the dog to get over it. Let the dog recover before trying again.",
                ],
                "watch_for": [
                    "Notice whether the dog relaxes when people stop reaching, whether food works at a distance but not up close, and whether the dog freezes before reacting.",
                    "Track whether one specific person, dog, object, sound, or handling type keeps producing the same body pattern.",
                ],
                "when_to_seek_help": "Seek trainer support if stress signs repeat in the same situations, the dog cannot recover after space is given, the dog freezes, growls, snaps, or bites, or safety is uncertain around children or visitors. Seek vet advice if the signals appear suddenly, the dog reacts to touch, or appetite, movement, toileting, sleep, or energy also change.",
                "trainer_readiness_note": "Before seeking help, record what happened, where it happened, who or what was present, the first body signal noticed, whether the dog could move away, whether the dog accepted food, what changed when distance increased, and whether the issue was sudden or gradual.",
                "media": [
                    {"type": "visual", "title": "Whole-dog scan", "description": "A simple field card showing the body areas and recovery clues owners should check together instead of one signal at a time."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Read the cluster", "prompt": "What is the dog's whole body saying here, and are they trying to create distance?"},
                ],
            },
            {
                "slug": "fear-is-not-defiance",
                "title": "Stress Signals Are Early Information",
                "estimated_minutes": 5,
                "scenario": "Your dog lip-licks during handling, yawns when visitors lean over them, pants in the car when it is not hot, or lowers their body when a stranger reaches out, but people keep going because the dog is not barking or growling.",
                "notice": [
                    "Stress signals are information, not bad behaviour.",
                    "They often mean the dog needs space, slower pacing, lower pressure, or a chance to opt out before escalation.",
                ],
                "common_mistake": "Ignoring polite signals until the dog escalates, or correcting the signal by scolding growling, forcing handling, pulling the dog closer, or punishing barking without asking what caused it.",
                "decision_rule": "Early signals are the cheapest moment to help. Make the situation easier before the dog has to shout louder.",
                "do_now": [
                    "Use the pause-and-distance rule: pause, reduce the trigger, increase distance, lower noise or social pressure, and let the dog choose whether to re-engage.",
                    "Reward calm observation if appropriate and end the situation positively before the dog tips over.",
                ],
                "watch_for": [
                    "Track the earliest signals such as lip licking, yawning, panting, paw lift, head turns, tucked tail, ears back, hiding, sudden stillness, repeated avoidance, or refusing food.",
                    "Then track what happened next so you identify the earliest warning, not only the final reaction.",
                ],
                "when_to_seek_help": "Seek support if stress signs are frequent, the dog's world is shrinking, normal daily activities are being avoided, recovery stays poor after the trigger leaves, the dog escalates to freezing, growling, snapping, lunging, or biting, or the owner is unsure how to keep everyone safe.",
                "trainer_readiness_note": "Tell a trainer which signals appear first, what triggers them, how close the trigger was, how long recovery takes, what makes the dog better or worse, and whether the dog has ever growled, snapped, or bitten. Tell a vet if the stress signs are new, sudden, linked to handling, or happening alongside appetite, sleep, toileting, mobility, or energy changes.",
                "media": [
                    {"type": "video", "title": "Pause-and-distance rule", "description": "A short scenario showing how reducing pressure and adding space changes the dog's ability to cope before escalation."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Help before escalation", "prompt": "What can you make easier right now before the dog needs to escalate beyond these early signals?"},
                ],
            },
            {
                "slug": "freeze-growl-snap-warning",
                "title": "Freeze, Growl, Snap: Do Not Punish the Warning",
                "estimated_minutes": 6,
                "scenario": "Your dog freezes when someone reaches for their collar, growls when a child approaches their bed, or snaps when someone tries to take an item from their mouth while another person says you cannot let the dog 'get away with that.'",
                "notice": [
                    "Freezing, growling, and snapping are serious warning signals that usually mean the dog feels over threshold or unsafe.",
                    "The immediate goal is not to win the moment. It is to prevent a bite, reduce pressure, and understand what caused the warning.",
                ],
                "common_mistake": "Punishing the warning and teaching the dog to stop warning while the underlying fear, pain, guarding, or discomfort remains.",
                "decision_rule": "Thank the warning by making the situation safer. Ask what the dog was trying to stop or avoid, then change the setup.",
                "do_now": [
                    "Stop moving toward the dog, do not yell, do not grab, and do not punish.",
                    "Create space, remove people, children, or other animals if needed, wait until the dog is safer and calmer, record what happened, and seek help if the warning repeats or safety is uncertain.",
                    "If an item is involved, avoid direct confrontation unless there is immediate danger. Use management first and prevent access next time.",
                ],
                "watch_for": [
                    "Identify the trigger category: touch, collar grab, grooming, vet-style handling, food, chew, stolen item, bed, child approach, visitor entry, unfamiliar dog, pain, being cornered, or being woken.",
                    "Notice the first signal, the final signal, whether the dog could escape, and how long recovery took after pressure changed.",
                ],
                "when_to_seek_help": "Trainer or behaviour support is needed if warnings repeat, children are involved, the dog guards food, toys, beds, people, or spaces, the dog snaps or bites, the dog blocks or corners people, or the owner cannot manage safely. Vet advice is needed if the warning is sudden, linked to touch, guarding a body part, or comes with stiffness, limping, yelping, appetite change, lethargy, vomiting, diarrhoea, sleep disruption, or behaviour change after injury, illness, surgery, or medication.",
                "trainer_readiness_note": "Record what triggered the warning, distance from the trigger, who was involved, whether the dog could escape, whether food, bed, toy, touch, or pain may be involved, the first and final signals, whether contact happened, whether anyone was injured, how long recovery took, and what changed afterward.",
                "media": [
                    {"type": "visual", "title": "Warning-response ladder", "description": "A safety-first guide showing how to respond when the dog freezes, growls, snaps, or guards instead of forcing the moment."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Make it safer", "prompt": "What was the dog trying to stop or avoid, and what change would lower pressure fastest right now?"},
                ],
            },
            {
                "slug": "when-behaviour-may-be-health",
                "title": "Behaviour Change May Be Health Information",
                "estimated_minutes": 5,
                "scenario": "Your dog is suddenly different: they avoid touch, sleep more, hide, snap when handled, stop eating normally, toilet differently, move stiffly, limp, pant at rest, vomit, have diarrhoea, or seem unusually flat.",
                "notice": [
                    "Sudden behaviour change can be health information, not attitude.",
                    "Pain, nausea, illness, injury, dental pain, ear problems, skin irritation, digestive upset, toxin exposure, or medication effects can all change behaviour.",
                ],
                "common_mistake": "Trying to train through a health problem by correcting snapping during painful handling, calling the dog lazy when they are lethargic, forcing exercise through stiffness, or ignoring vomiting, diarrhoea, appetite change, or sudden fear.",
                "decision_rule": "Sudden change means vet first. If the pattern is new, sudden, physical, or linked to touch, movement, appetite, toileting, or energy, contact a vet before treating it as a training problem.",
                "do_now": [
                    "Pause training pressure and record appetite, water intake, toileting, vomiting, diarrhoea, sleep, energy, walking, stiffness, limping, panting, coughing, scratching, licking one area, touch sensitivity, yelping, hiding, and sudden fear or aggression.",
                    "If symptoms are urgent, contact a vet immediately. If they are mild but unusual, contact your vet for guidance rather than guessing.",
                ],
                "watch_for": [
                    "Vet-first signs include collapse, seizure, difficulty breathing, repeated vomiting, severe diarrhoea, blood in vomit, stool, or urine, suspected toxin exposure, sudden inability to walk, severe lethargy, painful crying, swollen abdomen, or rapid deterioration.",
                    "Also watch for sudden aggression linked to touch or refusal to eat when other symptoms are present.",
                ],
                "when_to_seek_help": "This lesson does not diagnose or treat illness. Contact a vet when the issue may be medical, and bring a trainer in later only if urgent medical causes are cleared and the behaviour continues as a repeating pattern.",
                "trainer_readiness_note": "Tell the vet what changed, when it started, whether it was sudden or gradual, appetite and water intake, toileting changes, vomiting or diarrhoea, movement changes, pain signs, handling sensitivity, possible toxin access, and recent diet changes.",
                "media": [
                    {"type": "visual", "title": "Vet-first filter", "description": "A fast decision card for sudden changes that may be pain, illness, injury, or another physical issue rather than a training problem."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Health check first", "prompt": "What changed besides the behaviour itself, and does any of it point to touch, movement, appetite, toileting, or energy?"},
                ],
            },
        ],
    },
    {
        "slug": "the-social-filter",
        "number": 4,
        "title": "The Social Filter",
        "objective": "Help owners handle exposure, socialisation, and fear without turning normal learning into accidental flooding.",
        "eyebrow": "Guide 4",
        "strapline": "Fear, socialisation, handling, safe exposure.",
        "stage_key": "reading-and-response",
        "intro": "Socialisation is not about exposing the dog to everything as fast as possible. This guide helps the owner introduce people, places, sounds, surfaces, handling, and everyday experiences without forcing the dog past their coping point.",
        "outcome": "By the end of this module, the owner can use safe positive exposure instead of forced interaction, read whether the dog is coping or overwhelmed, use distance and choice when the dog is worried, plan low-risk early exposure with veterinary guidance, and know when fear or handling stress is outside self-guided education.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You understand that socialisation means safe exposure, not forced contact or crowding.",
            "You can identify green, yellow, and red responses and create more distance when the dog is unsure.",
            "You have tried at least one safe exposure session, started gentle handling practice, and know when fear requires vet or trainer support.",
        ],
        "signs_of_progress": [
            "The owner is measuring success by coping and recovery, not by how close the dog got to the trigger.",
            "The dog can observe, eat, retreat, and settle more easily because exposure sessions stay shorter and lower pressure.",
        ],
        "capability_keys": ["fear_response"],
        "teaser_scenario": "The owner wants the dog to be confident, but every exposure choice risks becoming too much too fast.",
        "teaser_mistake": "Measuring success by how close the dog got, instead of how well the dog coped.",
        "teaser_next_step": "Protect recovery and distance first so exposure stays useful instead of overwhelming.",
        "trainer_readiness_prompt": "If fear repeats, log trigger distance, recovery time, and what made the moment worse.",
        "tool_refs": ["safe-exposure-checklist", "fear-log"],
        "lessons": [
            {
                "slug": "socialisation-is-not-flooding",
                "title": "Socialisation Is Not Forced Interaction",
                "estimated_minutes": 6,
                "scenario": "You take your puppy or new dog to meet friends. People lean over the dog, reach for the head, talk loudly, and encourage the dog to say hello while the dog backs away, hides, freezes, lip-licks, or refuses treats.",
                "notice": [
                    "Socialisation is not the same as contact. Dogs can learn safely by watching, hearing, and exploring from a distance.",
                    "The goal is a positive or neutral experience, not meeting every person or dog.",
                ],
                "common_mistake": "Forcing the dog toward something they are scared of by dragging them closer, holding them still to be touched, passing them around, or treating fear as stubbornness.",
                "decision_rule": "Exposure only counts if the dog is coping. If the dog cannot observe, recover, and stay relaxed enough to learn, increase distance or end the session.",
                "do_now": [
                    "Choose one small exposure such as one person at a distance, one new surface, one quiet sound, one calm object, one short car experience, or one gentle handling moment.",
                    "Keep it short, let the dog decide whether to approach, reward calm observation, and end while the dog is still coping.",
                ],
                "watch_for": [
                    "The dog is probably coping if they can eat, sniff, move normally, approach and retreat, look away and recover, or settle afterward.",
                    "The dog may not be coping if they freeze, hide, pull away, refuse food, tremble, bark repeatedly, growl, snap, try to escape, or cannot recover after distance increases.",
                ],
                "when_to_seek_help": "Seek professional support if fear is intense or escalating, the dog freezes, growls, snaps, or bites, the dog cannot recover after the trigger is removed, panic happens around normal daily experiences, safety is uncertain around children, visitors, or other animals, or the owner feels unsure how to manage exposure safely.",
                "trainer_readiness_note": "Record what the dog saw, heard, touched, or experienced, the distance from the trigger, the first sign of worry, whether the dog could take food, whether the dog could move away, how long recovery took, what helped, and what made it worse.",
                "media": [
                    {"type": "visual", "title": "Safe observation guide", "description": "A simple field card showing how to run one short exposure without forced greetings or crowding."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Coping check", "prompt": "Is the dog relaxed enough to observe and recover here, or has this become forced interaction?"},
                ],
            },
            {
                "slug": "step-back-first",
                "title": "Safe Early Exposure Before the World Gets Too Big",
                "estimated_minutes": 5,
                "scenario": "Your puppy is not fully vaccinated yet, and you are unsure whether to keep them isolated, take them everywhere, attend puppy school, meet vaccinated dogs, or carry them around for exposure.",
                "notice": [
                    "This is a balance question: early positive experience matters, but disease risk matters too.",
                    "The safest decision depends on local risk, vaccination status, puppy health, and veterinary advice, not generic internet rules.",
                ],
                "common_mistake": "Choosing one extreme by either isolating the puppy completely or exposing them everywhere and to every dog without regard for local risk.",
                "decision_rule": "Separate exposure from risky contact. Let the puppy experience the world safely without direct contact with unknown dogs or contaminated areas when vet guidance says that is the better path.",
                "do_now": [
                    "Ask the vet what exposure is safe for this puppy in your local area right now.",
                    "Use low-risk options that fit that advice: carried observation, calm car watching, visitors at a distance, household objects and sounds at home, safe surface walks, reputable indoor puppy class if appropriate, or controlled exposure to healthy vaccinated dogs in private settings if vet-approved.",
                    "Avoid dog parks, busy off-leash areas, heavily used unknown-dog spaces, uncontrolled puppy play, crowded pet events, and any higher-risk contact until the vet says it is suitable.",
                ],
                "watch_for": [
                    "The exposure is too much if the puppy stops eating, hides, trembles, freezes, becomes frantic, cannot disengage, cannot recover, or grows more worried each time.",
                    "The exposure is more appropriate if the puppy notices and recovers, takes food, explores calmly, can retreat, remains playful or relaxed, and settles afterward.",
                ],
                "when_to_seek_help": "Seek vet advice if the puppy is unwell, vaccination or disease risk is unclear, the puppy has had contact with sick or unknown dogs, puppy class safety is uncertain, or local outbreak risk may matter. Seek trainer or behaviour support if the puppy repeatedly panics during low-intensity exposure, fear is increasing, the puppy cannot recover, or the puppy growls, snaps, or attempts to flee.",
                "trainer_readiness_note": "Ask the vet which areas to avoid until vaccination is complete, whether puppy school is appropriate now, what exposure is safe before full vaccination, whether the puppy can meet known vaccinated dogs, and what symptoms after an outing should trigger a call. Tell a trainer what exposure has been tried, what distance the puppy can handle, what triggers fear, whether food is accepted, how long recovery takes, and what the vet has advised.",
                "media": [
                    {"type": "video", "title": "Low-risk early exposure", "description": "A short scenario showing how a puppy can experience the world safely before full vaccination without forced risky contact."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Risk versus exposure", "prompt": "How can this puppy experience the world safely here without direct contact that exceeds the vet's guidance?"},
                ],
            },
            {
                "slug": "traffic-light-rule-for-fear",
                "title": "The Traffic-Light Rule for Fear",
                "estimated_minutes": 6,
                "scenario": "Your dog sees something unfamiliar such as a skateboard, child, umbrella, vacuum, grooming brush, car, statue, or person wearing a hat. Sometimes they seem curious, sometimes hesitant, and sometimes they bark, hide, or panic.",
                "notice": [
                    "The same experience can be safe or unsafe depending on the dog's emotional state in that moment.",
                    "A green-yellow-red filter helps the owner decide whether to continue, make it easier, or stop.",
                ],
                "common_mistake": "Turning yellow into red by pushing a dog that is already unsure because they are almost doing it.",
                "decision_rule": "Stay in green. Respect yellow. Exit red. If the experience is no longer easy enough for the dog, step back.",
                "do_now": [
                    "If the dog is green, reward calm observation, keep the session short, and finish on a good note.",
                    "If the dog is yellow, increase distance, lower intensity, reduce movement or noise, allow retreat, reward recovery, and end soon.",
                    "If the dog is red, stop, move away, do not punish, do not keep exposing, allow recovery, record what happened, and seek help if the pattern is repeated or unsafe.",
                ],
                "watch_for": [
                    "Green usually means calm looking, eating, sniffing, approaching and retreating, loose movement, and quick recovery.",
                    "Yellow often means pausing, leaning away, lowering the body, lip licking, yawning, moving behind the owner, hesitating on food, or needing more distance.",
                    "Red includes freezing, refusing food, trembling, repeated barking, growling, snapping, trying to escape, hiding, panic, or failure to recover.",
                ],
                "when_to_seek_help": "Seek support if the dog regularly goes straight to red, has repeated red reactions to normal life, cannot recover after distance, is becoming more fearful over time, shows growling, snapping, lunging, or biting, or feels unsafe around children, visitors, dogs, or public spaces.",
                "trainer_readiness_note": "Track the exposure type, distance, traffic-light colour, first body signal, whether food was accepted, recovery time, what helped, and what should be avoided next time.",
                "media": [
                    {"type": "visual", "title": "Traffic-light filter", "description": "A quick green-yellow-red guide for deciding whether to continue, back off, or stop the exposure."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Name the colour", "prompt": "Is the dog still in green, edging into yellow, or already in red and needing the session stopped?"},
                ],
            },
            {
                "slug": "handling-with-consent-and-care",
                "title": "Handling, Grooming, and Vet Touch",
                "estimated_minutes": 5,
                "scenario": "You try to touch your dog's paws, ears, mouth, tail, collar, or harness, and the dog pulls away, mouths your hand, stiffens, hides, growls, or becomes frantic.",
                "notice": [
                    "Handling is an experience the dog learns, and it needs to predict safety, choice, and reward.",
                    "This matters for vet checks, grooming, nail care, ear and mouth checks, harness fitting, collar handling, medication, and emergency handling.",
                ],
                "common_mistake": "Doing too much too quickly by grabbing sensitive areas suddenly, forcing grooming, restraining through struggle, ignoring stiffening or growling, or waiting until care is urgent before practising.",
                "decision_rule": "Touch should stay easy enough that the dog can recover. If the dog pulls away, stiffens, or panics, the step is too big.",
                "do_now": [
                    "Practise micro-handling with very short sessions: touch one easy body area briefly, reward, stop, and repeat later.",
                    "Build gradually from easier areas toward more sensitive areas over multiple sessions, and stop before the dog becomes worried.",
                    "Do not force the full sequence in one session, restrain through panic, or continue after growling, snapping, or freezing.",
                ],
                "watch_for": [
                    "Handling is too hard if the dog turns away, stiffens, lip-licks, mouths hands, pulls the body part away, hides, growls, snaps, stops taking food, or becomes frantic.",
                    "Handling is more appropriate if the dog stays loose, can take food, can move away, re-engages willingly, and settles afterward.",
                ],
                "when_to_seek_help": "Seek vet advice if handling discomfort is sudden, one body part seems painful, or the dog yelps, guards, limps, scratches, shakes the head, avoids touch on one side, or has swelling, discharge, bleeding, skin change, ear smell, dental concern, or injury. Seek trainer or behaviour support if the dog panics during normal handling, grooming or vet visits are unsafe, the dog growls, snaps, or bites during handling, or the owner cannot complete basic care safely.",
                "trainer_readiness_note": "Tell the vet or trainer which body areas cause concern, what the dog does first, whether the reaction is sudden or long-standing, whether pain signs are present, what handling is necessary now, what has already been tried, and whether the dog can take food during handling.",
                "media": [
                    {"type": "interactive", "title": "Safe handling practice", "description": "A short prompt set for brief rewarded touch sessions that build toward grooming and vet care without conflict."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Make the step smaller", "prompt": "What is the smallest touch step your dog can accept calmly before you ask for anything more?"},
                ],
            },
        ],
    },
    {
        "slug": "the-sync-mechanics",
        "number": 5,
        "title": "The Sync Mechanics",
        "objective": "Give owners a calm, usable learning system so the dog can understand everyday expectations.",
        "eyebrow": "Guide 5",
        "strapline": "Reward timing, calm routines, household consistency.",
        "stage_key": "reading-and-response",
        "intro": "Dogs learn from what works. This guide helps the owner improve timing, routine, and household consistency so the dog receives clearer information every day without the home becoming an obedience class or a shouting match.",
        "outcome": "By the end of this module, the owner can reward the behaviour they want at the right moment, notice when they are accidentally rewarding the wrong thing, build calm routines around food, doors, greetings, rest, and attention, use short consistent household cues, and reduce mixed signals across the home.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You can describe exactly what behaviour you are rewarding and what behaviour may be getting rewarded by accident.",
            "At least one daily calm routine now happens the same way every time instead of beginning with chaos.",
            "The household has one shared rule for a high-friction behaviour and everyone knows how to respond.",
        ],
        "signs_of_progress": [
            "The dog repeats calm behaviours more often because the feedback is landing at the right moment.",
            "Household conflict drops because fewer repeated commands, mixed cues, and accidental rewards are slipping into daily life.",
        ],
        "capability_keys": ["reward_timing", "calm_routine"],
        "teaser_scenario": "The owner is trying hard, but the timing and household language keep telling the dog different stories.",
        "teaser_mistake": "Repeating cues and rewarding late instead of making the success moment clear.",
        "teaser_next_step": "Build a tiny number of repeatable calm routines and reinforce the exact choice you want.",
        "trainer_readiness_prompt": "If progress stalls, note which routines are clear and which household rules still conflict.",
        "tool_refs": ["say-please-routine-card", "family-cue-agreement"],
        "lessons": [
            {
                "slug": "mark-the-right-second",
                "title": "Reward the Moment You Want",
                "estimated_minutes": 5,
                "scenario": "Your dog briefly sits before jumping, pauses barking for a second before starting again, lies down quietly for a moment, or looks at you instead of grabbing the lead, but by the time you respond the good moment has already disappeared.",
                "notice": [
                    "Timing matters because dogs learn from what happens immediately around their behaviour.",
                    "If the reward lands too late, the dog may connect it to whatever happened after the moment you actually wanted.",
                ],
                "common_mistake": "Rewarding after the moment has passed and accidentally paying for jumping, renewed barking, following, pawing, or another behaviour that came after the calm moment.",
                "decision_rule": "Reward the behaviour while it is happening or immediately after it happens. If it is unclear what got rewarded, make the setup easier.",
                "do_now": [
                    "Choose one behaviour to reward today, not ten: four paws on the floor, a quiet pause, calm sit before food, looking at the owner, calm door movement, lying quietly, taking a toy instead of a hand, returning to the owner, or settling on a mat.",
                    "Prepare the reward before the situation starts and keep the picture simple: behaviour happens, reward happens.",
                    "Use food, calm praise, toy access, distance from pressure, or permission to move forward as the reward, but land it immediately.",
                ],
                "watch_for": [
                    "Notice whether the dog repeats the behaviour more often and whether rewards are accidentally landing after jumping, barking, grabbing, pawing, pushing through doors, stealing items, biting clothing, rushing the bowl, or demanding attention.",
                    "If the unwanted behaviour increases, ask what is still working for the dog in that moment.",
                ],
                "when_to_seek_help": "Seek trainer support if the owner cannot safely manage the situation, the dog is too over-aroused to take food or respond, the behaviour involves guarding, snapping, lunging, or biting, the behaviour is worsening despite clearer timing, or the household cannot agree on one response. Seek vet advice if behaviour changes suddenly or the dog seems painful, unwell, frantic, restless, or unable to settle.",
                "trainer_readiness_note": "Before asking for help, record the behaviour you wanted, the behaviour that actually got rewarded, the reward used, the timing of the reward, whether the dog repeated the behaviour, who was present, what happened before it, and whether the dog could take food or respond.",
                "media": [
                    {"type": "video", "title": "Timing drill", "description": "A short timing exercise showing how one small calm behaviour gets reinforced before the dog shifts into something else."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Exact moment check", "prompt": "What was the dog doing at the exact moment you rewarded them, and was it actually the behaviour you wanted?"},
                ],
            },
            {
                "slug": "stop-paying-for-the-wrong-behaviour",
                "title": "Stop Accidentally Paying for the Wrong Behaviour",
                "estimated_minutes": 5,
                "scenario": "Your dog barks for attention, jumps on visitors, paws, mouths clothing, or steals items while people look, talk, laugh, chase, push, or open the door trying to stop it.",
                "notice": [
                    "Attention can be a reward. For some dogs, eye contact, talking, touching, laughing, chasing, pushing, or opening access is enough to make the behaviour happen again.",
                    "The dog is not being spiteful if the behaviour keeps working.",
                ],
                "common_mistake": "Reacting strongly to behaviour the owner wants to reduce and accidentally rewarding it with attention, access, or movement.",
                "decision_rule": "Reward the replacement, not the chaos. Ask what the dog should do instead, then reward that instead of the old behaviour.",
                "do_now": [
                    "Choose one repeating behaviour and write down what you will stop rewarding, and what you will reward instead.",
                    "Set the dog up to succeed with management such as a lead, baby gate, safe room, food scatter, mat, calm greeting plan, fewer people, or more distance when the situation is too hard.",
                    "Do not rely on willpower in a hard situation; reduce rehearsal while the replacement becomes easier to reward.",
                ],
                "watch_for": [
                    "The unwanted behaviour may briefly increase when it stops working. That does not automatically mean the plan is wrong.",
                    "Track whether the replacement behaviour is staying easy and whether the household is still accidentally rewarding the old behaviour.",
                ],
                "when_to_seek_help": "Seek support if the behaviour is intense or unsafe, the dog becomes frustrated or aggressive, rehearsal cannot be prevented, children, visitors, or other animals are at risk, the behaviour is linked to fear, panic, guarding, or distress, or the household cannot apply the same response.",
                "trainer_readiness_note": "Tell a trainer what the dog gets from the behaviour, whether that is attention, food, play, distance, access, escape, or movement, what replacement you tried, whether the behaviour changed, how the household responded, and whether safety concerns are present.",
                "media": [
                    {"type": "visual", "title": "Replacement map", "description": "A simple worksheet showing the old behaviour, what has been rewarding it, and the replacement behaviour that should get paid instead."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Find the payoff", "prompt": "What is the dog getting from this behaviour right now, and what should they get instead for the calmer replacement?"},
                ],
            },
            {
                "slug": "say-please-in-real-life",
                "title": "Calm Routines Before Big Feelings",
                "estimated_minutes": 6,
                "scenario": "The dog rushes the food bowl, pushes through doors, jumps at greetings, barks when ignored, grabs the lead before walks, or becomes frantic before play, and the owner feels like the dog has no manners.",
                "notice": [
                    "Many manners problems are routine problems. The dog is learning what starts food, doors, play, attention, movement, and waiting every day.",
                    "If every exciting event begins with chaos, the dog may rehearse chaos every day.",
                ],
                "common_mistake": "Waiting until the dog is already overexcited, then asking for too much too late.",
                "decision_rule": "Build the routine before the dog tips over. Start with the calmest version of the moment the dog can manage.",
                "do_now": [
                    "Pick one daily routine and use the same pattern each time: food, door, greeting, or attention.",
                    "For food, prepare calmly, wait for one tiny calm moment, lower the bowl, and pause if the dog rushes.",
                    "For doors, wait for a quiet pause, open slightly, close calmly if the dog surges, and reward calm waiting by opening again.",
                    "For greetings or attention, keep the setup low-key, reward four paws down or a quiet pause, and use gates, distance, or lower intensity if needed.",
                ],
                "watch_for": [
                    "Track whether the dog becomes calmer when the routine becomes predictable: shorter excitement bursts, quicker recovery, more waiting, less jumping, less barking, more checking in, and easier settling after the event.",
                    "Notice which routine still tips over first and whether the step needs to be made easier.",
                ],
                "when_to_seek_help": "Seek support if the dog cannot calm even with easier routines, arousal escalates into biting, snapping, guarding, or lunging, the dog becomes distressed when access is delayed, doors, food, greetings, or visitors cannot be managed safely, or the dog appears frantic, unwell, or unable to rest.",
                "trainer_readiness_note": "Record the routine chosen, what happens before excitement starts, what the dog does, what the owner does, what reward is used, what makes it easier, what makes it worse, and whether the dog recovers afterward.",
                "media": [
                    {"type": "visual", "title": "Calm routine card", "description": "A simple before-during-after routine card for food, doors, greetings, lead-on, play, or attention."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Smallest calm step", "prompt": "What is the smallest calm behaviour your dog can manage in this routine before excitement tips over?"},
                ],
            },
            {
                "slug": "one-household-language",
                "title": "One Household, One Rule",
                "estimated_minutes": 4,
                "scenario": "One person lets the dog jump up, another gets angry about jumping, one feeds from the table, another wants the dog to stop begging, and different people use different words for the same thing.",
                "notice": [
                    "Dogs learn from patterns. If each person responds differently, the dog receives mixed information.",
                    "The problem may not be the dog's attitude. The problem may be the household system.",
                ],
                "common_mistake": "Expecting the dog to understand rules humans have not agreed on.",
                "decision_rule": "Make the human rule first. If humans cannot answer what every person will do, the dog cannot learn the rule reliably.",
                "do_now": [
                    "Create a family cue agreement with one word for the behaviour, one response for unwanted behaviour, one reward for desired behaviour, and one management plan when the dog cannot cope.",
                    "Start with high-friction situations such as jumping, door rushing, food bowl behaviour, biting clothing, stolen items, barking for attention, or leaving the rest area undisturbed.",
                ],
                "watch_for": [
                    "Watch whether repeated commands drop, frustration drops, calm behaviours appear more often, and people stop arguing about what to do.",
                    "Notice which rules still break down because visitors, children, or one household member are following a different script.",
                ],
                "when_to_seek_help": "Seek support if household members cannot safely follow the same plan, children are involved and safety is uncertain, the dog guards food, toys, people, or resting places, the dog snaps, bites, or lunges, the behaviour is fear-based or worsening, or the owner needs a trainer to coach the household rather than only the dog.",
                "trainer_readiness_note": "Bring the family cue agreement to the trainer and explain which rules are inconsistent, who is struggling to follow the plan, what behaviours are rewarded by accident, which situations create conflict, whether visitors or children are involved, and whether safety concerns exist.",
                "media": [
                    {"type": "interactive", "title": "Cue agreement", "description": "A short shared template for household rules, responses, and management plans so the dog is not decoding three different systems."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Human rule first", "prompt": "What will every person do when this behaviour happens, and where is the household still giving mixed information?"},
                ],
            },
        ],
    },
    {
        "slug": "the-urban-flow-and-the-shield",
        "number": 6,
        "title": "The Urban Flow & The Shield",
        "objective": "Help owners carry calm decisions into noisy streets, home trigger zones, and early alone-time stress.",
        "eyebrow": "Guide 6",
        "strapline": "Public stress, street hazards, window barking, alone-time calm.",
        "stage_key": "real-world-handling",
        "intro": "Modern homes and streets are noisy, busy, and full of triggers. This guide helps the owner manage public stress, street hazards, window barking, and early alone-time difficulty without pushing the dog into overwhelm.",
        "outcome": "By the end of this module, the owner can notice when the street is too much, make walks shorter and safer, reduce access to scavenging hazards, use distance and barriers to prevent repeated public stress, lower visual and sound trigger access at home, and start alone-time routines without punishing distress.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "You know how to make walks smaller when the dog is stressed and can name at least three public triggers that matter.",
            "You can scan for street hazards before the dog reaches them and have a plan for dangerous ingestion.",
            "You have reduced at least one window or fence trigger, know not to punish alone-time distress after returning, and can record what happens when the dog is left.",
        ],
        "signs_of_progress": [
            "The owner makes the environment easier earlier instead of pushing through public stress or repeating corrections after the dog is already overwhelmed.",
            "Street, home-trigger, and alone-time patterns are becoming more predictable because trigger access, recovery, and setup are being tracked more clearly.",
        ],
        "capability_keys": ["public_handling", "trainer_readiness"],
        "teaser_scenario": "The dog is fine in one room, then unravels outside or stays hyper-alert at the front window.",
        "teaser_mistake": "Pushing through outside stress or home trigger zones as if the dog just needs more obedience.",
        "teaser_next_step": "Act like the shield first: create space, reduce rehearsal, and let recovery happen before continuing.",
        "trainer_readiness_prompt": "If public stress or alone-time distress keeps repeating, start recording triggers and recovery patterns.",
        "tool_refs": ["street-hazard-rules", "window-barking-environment-checklist"],
        "lessons": [
            {
                "slug": "outside-stress-needs-a-shield",
                "title": "Public Stress: Make the Walk Smaller",
                "estimated_minutes": 6,
                "scenario": "A truck passes, a skateboard rolls by, a child runs past, another dog barks behind a fence, and your planned normal walk turns into pulling, freezing, barking, spinning, panting, or trying to rush home.",
                "notice": [
                    "A walk is not automatically relaxing. For some dogs, the street is a lot of information at once.",
                    "The owner needs to notice when the walk has stopped being useful and has become too difficult for the dog to recover from.",
                ],
                "common_mistake": "Thinking the dog needs a longer walk when the dog actually needs an easier walk, and continuing forward because the owner feels embarrassed or committed to the route.",
                "decision_rule": "A useful walk is one the dog can recover from. If the dog cannot think, sniff, take food, or move normally, make the walk smaller.",
                "do_now": [
                    "Walk at a quieter time, choose a shorter route, cross the road early, turn around before the trigger gets close, or use a wider footpath or visual cover such as a parked car, tree, wall, or driveway opening.",
                    "Give the dog sniffing time, stop before they become frantic, and use the front yard, driveway, hallway, or car park as a mini-exposure area when a full walk is too much.",
                ],
                "watch_for": [
                    "The walk may be too hard if the dog scans constantly, pants when not hot, refuses food, freezes, lunges, barks repeatedly, tries to flee, cannot sniff, or cannot settle after returning home.",
                    "The walk is more appropriate if the dog sniffs, takes food, looks and looks away, turns with the owner, shows looser movement, and settles after the outing.",
                ],
                "when_to_seek_help": "Seek trainer support if barking, lunging, freezing, or panic repeats on walks, the dog cannot recover with distance, people, dogs, children, bikes, or traffic trigger strong reactions, the owner cannot safely manage the lead, the dog has snapped, bitten, redirected onto the lead or owner, escaped, or the dog's world is shrinking because walks feel unsafe. Seek vet advice if public stress appears suddenly or the dog seems painful, unwell, unusually tired, disoriented, sound-sensitive after a health change, or has other changes in mobility, appetite, toileting, sleep, or energy.",
                "trainer_readiness_note": "Record the route, time of day, trigger, distance from trigger, first body signal, final reaction, whether the dog could eat or sniff, whether distance helped, recovery time after the walk, equipment used, and whether the owner could safely manage the situation.",
                "media": [
                    {"type": "video", "title": "Smaller-walk reset", "description": "A short demonstration of how route choice, distance, and visual cover reduce public overwhelm before the dog tips over."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Useful or too hard?", "prompt": "Is the dog still able to sniff, take food, and recover here, or has the walk already become too difficult to continue usefully?"},
                ],
            },
            {
                "slug": "street-rubbish-and-public-chaos",
                "title": "Street Hazards: The Shield",
                "estimated_minutes": 5,
                "scenario": "Your dog grabs food scraps, bones, gum, bait, rubbish, animal faeces, a dead bird, medication, glass, or another unknown object from the ground before you can react.",
                "notice": [
                    "The street contains hazards the dog does not understand, and risk rises when the owner is distracted, the lead is too loose near rubbish, or the route repeats the same high-risk zones.",
                    "The owner's job is to shield the dog from access before the mouth gets there.",
                ],
                "common_mistake": "Reacting only after the dog has the object by chasing, shouting, prying the mouth open, repeating cues the dog has not learned under pressure, or walking straight through high-risk rubbish areas.",
                "decision_rule": "Prevent access before the mouth gets there. Scan ahead and move early instead of reacting late.",
                "do_now": [
                    "Use the shield pattern: scan five to ten steps ahead, shorten the lead before hazard zones, move the dog to the safe side of the footpath, cross the road or arc around rubbish, and reward the dog for looking away from the item.",
                    "Use a cheerful swap if the dog has a safe but unwanted item, and contact a vet or poison service if the item may be toxic, sharp, dangerous, or unknown.",
                ],
                "watch_for": [
                    "Track hazard patterns such as the same street corner, takeaway strip, bin night, picnic area, building site, train stop, or garden bed.",
                    "Track dog patterns such as fast sniffing, sudden head dips, grabbing and moving away, swallowing quickly, stiffening over items, growling when approached, or refusing to swap.",
                ],
                "when_to_seek_help": "Contact a vet or Animal Poisons Helpline immediately if the dog may have eaten bait, unknown medication, chocolate, grapes or raisins, xylitol, sharp objects, cooked bones, mouldy food, toxic plants, chemicals, or anything unknown that causes concern. Seek trainer support if scavenging is repeated, the dog guards found items, runs away with them, the owner cannot safely manage walks, or the dog is unsafe around rubbish, food, or dropped objects.",
                "trainer_readiness_note": "Tell the vet the suspected item, amount, time, location, the dog's weight, symptoms, and provide a photo if possible. Tell the trainer where scavenging happens, what the dog grabs, lead length and route, whether the dog swaps, whether guarding occurs, and what management has already been tried.",
                "media": [
                    {"type": "visual", "title": "Shield pattern", "description": "A practical route-scanning visual for bins, food litter, dropped objects, and safe side changes before the dog reaches the hazard."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "Scan ahead", "prompt": "What is the hazard before your dog reaches it, and what early route or lead change would prevent access?"},
                ],
            },
            {
                "slug": "window-barking-and-alone-time-foundations",
                "title": "Window Barking: Build the Shield",
                "estimated_minutes": 6,
                "scenario": "Your dog rushes to the window every time someone walks past and barks at neighbours, delivery drivers, school children, dogs, bikes, possums, cats, or cars while people keep shouting for the barking to stop.",
                "notice": [
                    "Window barking is often a repeated pattern where barking appears to work because the trigger eventually moves away.",
                    "The better question is not how to stop the bark, but why the dog keeps getting access to the same trigger again and again.",
                ],
                "common_mistake": "Letting the dog practise the same window or fence routine every day and only reacting after the barking starts.",
                "decision_rule": "Block rehearsal before training harder. Reduce what the dog can see, hear, or practise before the next trigger appears.",
                "do_now": [
                    "Close blinds during peak trigger times, use frosted film, move furniture away from front windows, block access to the front room or fence line, use background sound, and create a rest area away from the trigger.",
                    "Offer food puzzles or chews during known trigger times and reward quiet moments before barking starts.",
                ],
                "watch_for": [
                    "Track the time of barking, location, trigger, whether it is window, fence, door, or balcony based, whether the trigger is visual or sound based, barking duration, what blocks the trigger, and whether the dog can settle elsewhere.",
                    "Notice whether blocking the view or softening sound changes recovery time.",
                ],
                "when_to_seek_help": "Seek trainer support if barking persists despite environmental changes, escalates into lunging, snapping, or redirected biting, the dog cannot settle away from the window, neighbours are affected, the owner cannot safely interrupt or redirect, the dog reacts to many everyday sights or sounds, or the behaviour appears fear-based or highly distressed. Seek vet advice if noise sensitivity appears suddenly or barking is paired with panic, trembling, pacing, drooling, or inability to recover after a health or sensory change.",
                "trainer_readiness_note": "Record the trigger, time of day, window or fence location, whether the trigger is visual, sound-based, or both, what blocks it, what does not help, barking duration, recovery time, and whether the dog can eat or settle afterward.",
                "media": [
                    {"type": "interactive", "title": "Window shield audit", "description": "A quick home audit for visual access, sound exposure, fence rehearsal, and rest spaces away from the trigger."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "Block rehearsal first", "prompt": "What is allowing this barking routine to practise itself every day, and which shield would reduce access before the next trigger appears?"},
                ],
            },
            {
                "slug": "alone-time-starts-below-threshold",
                "title": "Alone-Time Calm Without Punishing Distress",
                "estimated_minutes": 6,
                "scenario": "You leave the room or house and your dog barks, cries, scratches, paces, follows, chews, toilets, drools, or waits by the door, while other people suggest letting the dog cry it out.",
                "notice": [
                    "Alone-time difficulty is not spite. The dog may be underprepared, bored, overtired, confused by routine changes, worried about separation, distressed by confinement, reacting to outside sounds, or not yet comfortable in the home.",
                    "The owner needs to notice whether the dog is settling or panicking.",
                ],
                "common_mistake": "Punishing the dog after returning or forcing longer absences too quickly when the dog is already distressed.",
                "decision_rule": "Practise absence below panic level. If the dog cannot stay calm for this amount of alone time, make the step smaller and safer.",
                "do_now": [
                    "Start with tiny separations: step behind a gate for a few seconds, walk to another room and return calmly, close a door briefly and reopen before panic, or sit outside the room while the dog has a chew.",
                    "Meet toileting needs first, provide a safe rest space, use safe enrichment, keep departures and returns boring and predictable, return before panic where possible, and build slowly.",
                    "Do not punish barking after returning, leave the dog to panic repeatedly, push duration because you are impatient, or rely on food toys if the dog is too distressed to eat.",
                ],
                "watch_for": [
                    "The dog is coping better if they eat, rest, chew calmly, move around normally, settle after the owner leaves, and recover quickly when the owner returns.",
                    "The dog may be distressed if they bark or howl repeatedly, scratch doors or windows, pace, drool, tremble, toilet only when left, destroy exit points, refuse food, injure themselves, or panic as soon as departure cues appear.",
                ],
                "when_to_seek_help": "Seek trainer or veterinary behaviour support if the dog panics when alone, injures themselves or damages exits, repeated barking, howling, pacing, drooling, toileting, or destruction keeps happening, the dog cannot eat when left, distress starts before the owner leaves, progress stalls or worsens, or the owner must leave for longer than the dog can handle. Seek vet advice if toileting, vomiting, drooling, lethargy, pain, confusion, or sudden behaviour change may be medical, the dog is older and the behaviour is new, the dog is injuring themselves, or medication or referral may be needed.",
                "trainer_readiness_note": "Record one short video if safe and practical, plus how long after departure distress starts, what the dog does first, whether barking, pacing, drooling, scratching, chewing, toileting, or escape attempts occur, whether food is eaten, whether the dog settles, recovery time after return, confinement setup, daily routine, exercise or rest before departure, and whether the behaviour is new or long-standing.",
                "media": [
                    {"type": "visual", "title": "Tiny-separation ladder", "description": "A simple step ladder for building calm absence in very short, boring increments before the dog tips into panic."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Below panic or too hard?", "prompt": "Can your dog stay calm for this amount of alone time, or is this already above their current threshold?"},
                ],
            },
        ],
    },
    {
        "slug": "the-freedom-framework",
        "number": 7,
        "title": "The Freedom Framework",
        "objective": "Expand freedom carefully so the dog gains access without losing clarity, structure, or safety.",
        "eyebrow": "Guide 7",
        "strapline": "Boundaries, room access, signal bell, family rules.",
        "stage_key": "real-world-handling",
        "intro": "Freedom should expand only when the dog is ready for it. This guide helps the owner gradually increase room access, prevent regression, use simple household rules, and understand optional signals such as a toilet bell without turning them into a magic fix.",
        "outcome": "By the end of this module, the owner can expand the dog's access gradually, notice when freedom is too much too soon, prevent hidden toileting and unsafe chewing, keep the safe base area available, use household rules consistently, and know when regression, guarding, distress, or unsafe behaviour needs trainer or vet support.",
        "checkpoint_title": "Before you move on",
        "checkpoint_items": [
            "Freedom is being expanded one area at a time and the safe base area remains available.",
            "Regression is treated as information, not defiance, and the owner knows when to reduce difficulty.",
            "The household has agreed on core rules and, if using a toilet bell, its purpose is narrow and consistent.",
        ],
        "signs_of_progress": [
            "New spaces stay safer and calmer because access is expanding in smaller, supervised steps.",
            "Household responses become more predictable, so freedom can expand without major setbacks.",
        ],
        "capability_keys": ["freedom_boundaries"],
        "teaser_scenario": "The dog improves, then regresses as soon as the house relaxes the rules too quickly.",
        "teaser_mistake": "Giving more freedom as a reward before the current space is stable.",
        "teaser_next_step": "Add freedom in small earned layers, and tighten the plan quickly when the dog loses the thread.",
        "trainer_readiness_prompt": "If regression, guarding, distress, or repeating failures keep showing up, record the access pattern, recent changes, and family rules before asking for help.",
        "tool_refs": [
            "freedom-expansion-checklist",
            "room-access-trial-log",
            "optional-toilet-signal-bell-check",
            "family-rules-template",
        ],
        "lessons": [
            {
                "slug": "freedom-expands-slowly",
                "title": "Freedom Expands Slowly",
                "estimated_minutes": 5,
                "scenario": "Your dog is doing well in their safe area, toileting more reliably, chewing safer items, resting better, and following the household rhythm, so you wonder whether it is time to let them roam the whole house.",
                "notice": [
                    "Success in one small area does not automatically mean the dog is ready for the entire home.",
                    "Freedom is not just a reward. It is a skill the dog grows into as space, temptation, and distance from supervision increase.",
                ],
                "common_mistake": "Expanding access too quickly by opening the whole house after a few good days, removing the safe area too early, or treating regression as defiance instead of a setup warning.",
                "decision_rule": "Add one space at a time. If the dog cannot succeed in the new area while you can still supervise, the step is too big.",
                "do_now": [
                    "Start with the safe base area, then one supervised room, then one short supervised trial in a second room, and expand only if toileting, chewing, and settling stay reliable.",
                    "Before adding a room, puppy-proof it, close doors, remove hazards, lift cords, move shoes, bags, laundry, bins, plants, and food, check rugs and soft surfaces, and keep the rest area available.",
                    "If accidents or unsafe chewing appear, return to the smaller space without turning that reset into punishment.",
                ],
                "watch_for": [
                    "Freedom may be too much if the dog disappears into other rooms, toilets where you cannot see, chews unsafe items, becomes more unsettled, patrols, barks at windows, guards access, or becomes harder to redirect.",
                    "Freedom is more appropriate if the dog stays relaxed, returns to the owner, rests normally, toilets in the expected place, chews legal items, and settles after exploration.",
                ],
                "when_to_seek_help": "Seek trainer support if the dog repeatedly toilets or chews despite a clear setup, guards rooms, beds, people, food, or stolen items, becomes distressed when access is limited, the owner cannot supervise safely, expansion causes barking, panic, snapping, or destructive behaviour, or the household cannot agree on boundaries. Seek vet advice if toileting suddenly changes, the dog cannot hold urine or stool, seems painful, restless, confused, unusually distressed, or behaviour changes suddenly without a clear setup reason.",
                "trainer_readiness_note": "Record which areas the dog can access, when access was expanded, where accidents or chewing happen, what supervision was in place, what the dog did before the problem, how long the dog was unsupervised, whether the dog had toileted recently, and what changed when access was reduced again.",
                "media": [
                    {"type": "visual", "title": "Freedom ladder", "description": "A stepwise progression map from safe base area to wider household access without skipping supervision layers."},
                ],
                "interactive_blocks": [
                    {"type": "decision", "title": "Too big a step?", "prompt": "Can your dog actually succeed in this new space while you can still supervise, or is the next room only tempting, not truly earned?"},
                ],
            },
            {
                "slug": "regression-is-information",
                "title": "Regression Is Information",
                "estimated_minutes": 5,
                "scenario": "Your dog was doing well, then suddenly there is a toileting accident, chewed furniture, barking at the window, stolen items, or restless pacing, and the owner thinks the dog knows better.",
                "notice": [
                    "Regression usually means something changed, such as access level, supervision, rest, routine, visitors, new sounds, stress, illness, or tempting items.",
                    "The setup may no longer match the dog's current ability.",
                ],
                "common_mistake": "Responding with punishment instead of investigation by yelling, scolding, forcing confinement angrily, changing the whole routine again, or ignoring possible health changes.",
                "decision_rule": "When regression appears, reduce difficulty and look for the pattern before blaming the dog.",
                "do_now": [
                    "Use a 48-hour regression reset: reduce access by one level, increase supervision, add more toilet opportunities, restore planned rest, remove tempting items, use safe chews and enrichment, and track when the issue happens.",
                    "Contact the vet if the change is sudden, physical, or illness-related, and do not treat the smaller setup as punishment.",
                ],
                "watch_for": [
                    "Look for changes in routine, sleep, appetite, toileting, visitors, home layout, new rooms, outdoor stress, weather, construction noise, household conflict, work schedule, and health signs.",
                    "Notice what improves when freedom is reduced again and what remains unstable.",
                ],
                "when_to_seek_help": "Seek vet advice if regression is sudden or paired with increased urination, diarrhoea, vomiting, lethargy, pain signs, limping, confusion, appetite change, sleep disruption, sudden irritability, or defensive handling reactions. Seek trainer support if regression continues despite reducing difficulty, the dog becomes unsafe, guarding, biting, or panic appears, the owner cannot identify the pattern, or the household cannot maintain one plan.",
                "trainer_readiness_note": "Record what was going well before, what changed, when regression started, location, time of day, supervision level, rest pattern, toileting pattern, health signs, and what improved when freedom was reduced.",
                "media": [
                    {"type": "interactive", "title": "Regression reset", "description": "A short reset guide for lowering difficulty and finding the pattern before reacting emotionally."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "What changed?", "prompt": "What became harder for your dog recently: access, routine, supervision, rest, stress, or something physical?"},
                ],
            },
            {
                "slug": "signals-and-the-optional-toilet-bell",
                "title": "Signals and the Optional Toilet Bell",
                "estimated_minutes": 6,
                "scenario": "Your dog stands near the door, scratches, whines, barks, paces, or stares at you, and you wonder whether they need to toilet, want attention, want outside time, or are just restless. You have heard about using a bell.",
                "notice": [
                    "A signal is useful only if it has a clear meaning.",
                    "A toilet bell can help some dogs communicate a calm toilet need, but it becomes confusing if it also means play, attention, barking outside, or general door access.",
                ],
                "common_mistake": "Using a bell before the toilet routine is clear or opening the door every time the dog rings without checking the purpose.",
                "decision_rule": "A signal should support the routine, not replace it. The bell is optional, and the routine matters more than the tool.",
                "do_now": [
                    "Only use a bell if the household can stay consistent and keep the meaning narrow: calm toilet trip only.",
                    "If using one, place it near the toilet exit, prompt or wait for a light touch before a planned toilet trip, go straight to the toilet area, keep the trip boring and focused, reward toileting immediately, and return inside calmly.",
                    "If the dog rings repeatedly after just toileting, wait briefly, check whether they truly need to go, avoid turning it into a game, and review whether boredom, rest, or attention seeking are muddying the signal.",
                ],
                "watch_for": [
                    "The bell may be useful if the dog already understands the toilet area, the household responds consistently, ringing usually leads to toileting, the dog is not becoming frantic, and accidents reduce.",
                    "The bell may be causing confusion if the dog rings constantly, rings to play, rings to bark outside, becomes frustrated when the door does not open, accidents continue, or household responses differ.",
                ],
                "when_to_seek_help": "Seek trainer support if the dog cannot develop a clear toileting routine, signalling becomes frantic or demanding, the dog guards doorways or outdoor access, barks, scratches, or panics around exits, or the household cannot use the signal consistently. Seek vet advice if toilet frequency suddenly changes or the dog strains, cries, leaks urine, has diarrhoea, vomits, seems lethargic, or cannot hold urine or stool.",
                "trainer_readiness_note": "Record how often the dog signals, what signal they use, whether toileting happens afterward, whether the signal is being used for attention or play, who responds, what happens after the signal, whether accidents are improving, and whether any health signs exist.",
                "media": [
                    {"type": "visual", "title": "Signal meaning check", "description": "A simple guide for keeping a toilet signal narrow enough that it supports the routine instead of replacing it."},
                ],
                "interactive_blocks": [
                    {"type": "reflection", "title": "One meaning only", "prompt": "What happens after the signal every single time right now, and is that meaning still narrow enough to stay clear?"},
                ],
            },
            {
                "slug": "family-rules-make-freedom-clearer",
                "title": "Family Rules Make Freedom Clearer",
                "estimated_minutes": 5,
                "scenario": "One person lets the dog on the couch, another removes them, one feeds from the table, another wants begging to stop, one opens the door when the dog barks, and another wants quiet waiting.",
                "notice": [
                    "Freedom becomes confusing when the rules change from person to person.",
                    "The dog does not need harsh rules. They need predictable ones around rooms, couches, doors, food, visitors, children, rest, and access.",
                ],
                "common_mistake": "Expecting the dog to follow rules that humans have not agreed on.",
                "decision_rule": "One rule, one response, one week. If the rule changes daily, the dog cannot learn it clearly.",
                "do_now": [
                    "Write a simple family rules template for the most important areas first: rest area, rooms, couch, door, food, visitors, children, stolen items, outdoor access, and alone time.",
                    "Keep the rules realistic and choose what everyone will do the same way for the next seven days.",
                ],
                "watch_for": [
                    "Rules are working if household arguments reduce, calm behaviours repeat more often, responses become quicker and clearer, visitors understand the plan, the dog rests without interruption, and freedom can expand without major setbacks.",
                    "Rules need adjustment if they are too complicated, children or visitors cannot follow them, one person keeps changing the plan, the dog becomes frustrated or unsafe, or the rule creates more conflict than clarity.",
                ],
                "when_to_seek_help": "Seek trainer support if the household cannot agree on safe handling, children are involved and safety is uncertain, the dog guards food, toys, beds, people, or spaces, snaps, bites, lunges, or blocks access, becomes distressed when rules are applied, or the owner needs coaching to make a realistic household plan. Seek vet advice if rule problems appear after sudden behaviour change or the dog reacts to being touched, moved, or woken with possible pain, illness, sleep disruption, or confusion involved.",
                "trainer_readiness_note": "Bring the family rules template to the trainer and record which rules are unclear, who responds differently, which behaviours are being rewarded by accident, whether children or visitors are involved, whether guarding or fear is present, whether the dog has safe rest areas, and whether the behaviour changed suddenly.",
                "media": [
                    {"type": "interactive", "title": "Family rules template", "description": "A shared structure for rooms, doors, rest, visitors, and access rules so freedom stops changing by convenience."},
                ],
                "interactive_blocks": [
                    {"type": "prompt", "title": "One week, one rule", "prompt": "What will everyone in the home do the same way for the next seven days, and where is the current rule still drifting?"},
                ],
            },
        ],
    },
]


def capability_keys() -> List[str]:
    return [cap["key"] for cap in CAPABILITIES]


def capability_labels() -> Dict[str, str]:
    return {cap["key"]: cap["label"] for cap in CAPABILITIES}


def _tool_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    for tool in TOOLS:
        if tool["slug"] == slug:
            return deepcopy(tool)
    return None


def _stage_by_key(stage_key: str) -> Dict[str, str]:
    return next((stage for stage in COURSE_STAGES if stage["key"] == stage_key), COURSE_STAGES[0])


def _lesson_summary(lesson: Dict[str, Any], module_slug: str) -> Dict[str, Any]:
    return {
        "slug": lesson["slug"],
        "title": lesson["title"],
        "estimated_minutes": int(lesson.get("estimated_minutes") or 0),
        "scenario": lesson["scenario"],
        "path": f"/education/modules/{module_slug}/lessons/{lesson['slug']}",
        "preview_path": f"/education/modules/{module_slug}/lessons/{lesson['slug']}/preview",
    }


def _module_summary(module: Dict[str, Any]) -> Dict[str, Any]:
    lesson_summaries = [_lesson_summary(lesson, module["slug"]) for lesson in module["lessons"]]
    tool_refs = []
    stage = _stage_by_key(str(module.get("stage_key") or "foundations"))
    for raw_tool in module.get("tool_refs", []):
        if isinstance(raw_tool, dict):
            tool_refs.append(deepcopy(raw_tool))
            continue
        tool = _tool_by_slug(str(raw_tool))
        if tool:
            tool_refs.append(tool)
    return {
        "slug": module["slug"],
        "number": module["number"],
        "eyebrow": module["eyebrow"],
        "title": module["title"],
        "strapline": module["strapline"],
        "stage_key": stage["key"],
        "stage_title": stage["title"],
        "stage_summary": stage["summary"],
        "intro": module.get("intro", ""),
        "outcome": module.get("outcome", ""),
        "checkpoint_title": module.get("checkpoint_title", ""),
        "checkpoint_items": deepcopy(module.get("checkpoint_items") or []),
        "signs_of_progress": deepcopy(module.get("signs_of_progress") or []),
        "objective": module["objective"],
        "teaser_scenario": module["teaser_scenario"],
        "teaser_mistake": module["teaser_mistake"],
        "teaser_next_step": module["teaser_next_step"],
        "trainer_readiness_prompt": module["trainer_readiness_prompt"],
        "capability_keys": list(module["capability_keys"]),
        "estimated_minutes": sum(int(lesson.get("estimated_minutes") or 0) for lesson in module["lessons"]),
        "lesson_count": len(module["lessons"]),
        "lesson_summaries": lesson_summaries,
        "tool_refs": tool_refs,
        "teaser_path": f"/education/modules/{module['slug']}",
        "guide_path": f"/education/modules/{module['slug']}/guide",
        "first_lesson_path": f"/education/modules/{module['slug']}/lessons/{module['lessons'][0]['slug']}",
        "dashboard_path": f"/education/modules/{module['slug']}/guide",
    }


def get_catalog() -> Dict[str, Any]:
    modules = [_module_summary(module) for module in MODULES]
    total_lessons = sum(module["lesson_count"] for module in modules)
    total_minutes = sum(module["estimated_minutes"] for module in modules)
    return {
        "course": {
            "title": "The First Leash",
            "eyebrow": "Free starter guide",
            "subtitle": "A calm, practical start for life with a new dog.",
            "support_line": "Seven simple guides for the early weeks at home.",
            "list_intro": "From first setup to everyday confidence.",
            "promise": "A calm, practical start for life with a new dog.",
            "primary_cta": "Start the guide",
            "continue_cta": "Continue guide",
            "view_cta": "View guide",
            "checklist_cta": "Open checklist",
            "resume_cta": "Continue where you left off",
            "total_modules": len(modules),
            "total_lessons": total_lessons,
            "estimated_minutes": total_minutes,
        },
        "capabilities": deepcopy(CAPABILITIES),
        "modules": modules,
        "roadmap": [
            {
                **stage,
                "modules": [module for module in modules if module["stage_key"] == stage["key"]],
            }
            for stage in COURSE_STAGES
        ],
        "problem_routes": [
            {
                "label": "Settle the home first",
                "copy": "Start with home setup, hazards, and rest-zone basics.",
                "href": "/education/modules/the-blueprint",
            },
            {
                "label": "Toileting, biting, chewing",
                "copy": "Stabilize the first-week problems before they spiral.",
                "href": "/education/modules/the-transition-phase",
            },
            {
                "label": "Stress signals or illness?",
                "copy": "Read the body before you judge the behaviour.",
                "href": "/education/modules/the-empathy-engine",
            },
            {
                "label": "Fear and social pressure",
                "copy": "Lower pressure and protect recovery before pushing exposure.",
                "href": "/education/modules/the-social-filter",
            },
            {
                "label": "Timing and family consistency",
                "copy": "Fix reward timing and household cue drift.",
                "href": "/education/modules/the-sync-mechanics",
            },
            {
                "label": "Outside stress or barking",
                "copy": "Use the shield model for trigger-rich environments.",
                "href": "/education/modules/the-urban-flow-and-the-shield",
            },
            {
                "label": "Freedom and house rules",
                "copy": "Expand access carefully and lock in family rules.",
                "href": "/education/modules/the-freedom-framework",
            },
        ],
        "tool_summaries": [
            {
                "slug": tool["slug"],
                "title": tool["title"],
                "module_slug": tool["module_slug"],
                "type": tool["type"],
                "summary": tool["summary"],
                "path": f"/education/tools/{tool['slug']}",
            }
            for tool in TOOLS
        ],
    }


def get_module(slug: str) -> Optional[Dict[str, Any]]:
    for module in MODULES:
        if module["slug"] == slug:
            out = deepcopy(module)
            tool_refs = []
            for raw_tool in module.get("tool_refs", []):
                if isinstance(raw_tool, dict):
                    tool_refs.append(deepcopy(raw_tool))
                    continue
                tool = _tool_by_slug(str(raw_tool))
                if tool:
                    tool_refs.append(tool)
            out["tool_refs"] = tool_refs
            out["lesson_summaries"] = [_lesson_summary(lesson, module["slug"]) for lesson in module["lessons"]]
            out["teaser_path"] = f"/education/modules/{module['slug']}"
            out["guide_path"] = f"/education/modules/{module['slug']}/guide"
            return out
    return None


def get_public_module(slug: str) -> Optional[Dict[str, Any]]:
    module = get_module(slug)
    if not module:
        return None
    representative = deepcopy(module["lessons"][0])
    return {
        **_module_summary(module),
        "lesson_previews": [
            {
                "slug": lesson["slug"],
                "title": lesson["title"],
                "scenario": lesson["scenario"],
                "preview_path": f"/education/modules/{module['slug']}/lessons/{lesson['slug']}/preview",
            }
            for lesson in module["lessons"]
        ],
        "representative_lesson": {
            "title": representative["title"],
            "scenario": representative["scenario"],
            "common_mistake": representative["common_mistake"],
            "decision_rule": representative["decision_rule"],
        },
    }


def get_public_lesson_preview(module_slug: str, lesson_slug: str) -> Optional[Dict[str, Any]]:
    module = get_module(module_slug)
    if not module:
        return None
    for lesson in module["lessons"]:
        if lesson["slug"] != lesson_slug:
            continue
        tool_refs = []
        for raw_tool in module.get("tool_refs", []):
            if isinstance(raw_tool, dict):
                tool_refs.append(deepcopy(raw_tool))
                continue
            tool = _tool_by_slug(str(raw_tool))
            if tool:
                tool_refs.append(tool)
        return {
            "module": _module_summary(module),
            "lesson": {
                "slug": lesson["slug"],
                "title": lesson["title"],
                "scenario": lesson["scenario"],
                "notice": deepcopy(lesson.get("notice") or [])[:2],
                "common_mistake": lesson["common_mistake"],
                "decision_rule": lesson["decision_rule"],
                "watch_for": deepcopy(lesson.get("watch_for") or [])[:1],
                "trainer_readiness_note": lesson["trainer_readiness_note"],
                "estimated_minutes": int(lesson.get("estimated_minutes") or 0),
            },
            "tool_refs": tool_refs,
            "unlock_path": f"/education/sign-in?next=/education/modules/{module_slug}/lessons/{lesson_slug}",
        }
    return None


def get_lesson(module_slug: str, lesson_slug: str) -> Optional[Dict[str, Any]]:
    module = get_module(module_slug)
    if not module:
        return None
    for lesson in module["lessons"]:
        if lesson["slug"] == lesson_slug:
            tool_refs = []
            for raw_tool in module.get("tool_refs", []):
                if isinstance(raw_tool, dict):
                    tool_refs.append(deepcopy(raw_tool))
                    continue
                tool = _tool_by_slug(str(raw_tool))
                if tool:
                    tool_refs.append(tool)
            return {
                "module": _module_summary(module),
                "lesson": deepcopy(lesson),
                "tool_refs": tool_refs,
            }
    return None


def get_module_guide(slug: str, completed_lesson_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    module = get_module(slug)
    if not module:
        return None
    completed = set(str(item) for item in (completed_lesson_keys or []))
    lesson_rows: List[Dict[str, Any]] = []
    current_found = False
    continue_path = ""
    continue_label = "Start module"
    completed_count = 0

    for lesson in module["lessons"]:
        lesson_key = f"{module['slug']}:{lesson['slug']}"
        is_completed = lesson_key in completed
        if is_completed:
            completed_count += 1
        if is_completed:
            status = "completed"
        elif not current_found:
            status = "current"
            current_found = True
            continue_path = f"/education/modules/{module['slug']}/lessons/{lesson['slug']}"
            continue_label = "Continue guide" if completed_count else "Start the guide"
        else:
            status = "up_next"
        lesson_rows.append(
            {
                "slug": lesson["slug"],
                "title": lesson["title"],
                "status": status,
                "estimated_minutes": int(lesson.get("estimated_minutes") or 0),
                "path": f"/education/modules/{module['slug']}/lessons/{lesson['slug']}",
                "summary": lesson["scenario"],
                "decision_rule": lesson["decision_rule"],
            }
        )

    if not continue_path and lesson_rows:
        continue_path = lesson_rows[-1]["path"]
        continue_label = "Revisit final lesson"

    return {
        "module": _module_summary(module),
        "progress": {
            "completed_lessons_count": completed_count,
            "total_lessons": len(module["lessons"]),
            "percent_complete": int(round((completed_count / max(len(module["lessons"]), 1)) * 100)),
        },
        "lesson_rows": lesson_rows,
        "continue_path": continue_path,
        "continue_label": continue_label,
        "checkpoint": {
            "title": str(module.get("checkpoint_title") or ""),
            "items": deepcopy(module.get("checkpoint_items") or []),
        },
        "signs_of_progress": deepcopy(module.get("signs_of_progress") or []),
        "trainer_readiness_prompt": str(module.get("trainer_readiness_prompt") or ""),
    }


def get_tool(slug: str) -> Optional[Dict[str, Any]]:
    tool = _tool_by_slug(slug)
    if not tool:
        return None
    module = get_module(tool["module_slug"])
    return {
        "tool": tool,
        "module": _module_summary(module) if module else None,
    }
