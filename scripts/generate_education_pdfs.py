"""
Generate visually rich, publication-grade PDFs for The First Leash education modules.
Uses ReportLab with high-res photography, custom callouts, badges, and the Organic Earthy Luxe palette.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = REPO_ROOT / "frontend" / "public" / "images"
FILES_DIR = REPO_ROOT / "frontend" / "public" / "files"
DOCS_EDU_DIR = REPO_ROOT / "docs" / "education"

# DTD Color Palette
COLOR_INK = colors.HexColor("#1A3A32")
COLOR_INK_LIGHT = colors.HexColor("#4A615A")
COLOR_MOSS = colors.HexColor("#5C6D59")
COLOR_TERRACOTTA = colors.HexColor("#9B4F31")
COLOR_CREAM = colors.HexColor("#F5F2EB")
COLOR_CARD_BG = colors.HexColor("#FAFAF7")
COLOR_BORDER = colors.HexColor("#E5DFD3")
COLOR_WARN_BG = colors.HexColor("#FBF5F0")
COLOR_DECISION_BG = colors.HexColor("#F0F4F2")
COLOR_WHITE = colors.HexColor("#FFFFFF")
COLOR_TEXT = colors.HexColor("#2B3330")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to compute dynamic total page numbers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Skip header and footer on cover page
            return

        self.saveState()
        page_width, page_height = A4

        # Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_MOSS)
        self.drawString(40, page_height - 30, "THE FIRST LEASH • DOG OWNERS GUIDE")
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_INK_LIGHT)
        self.drawRightString(page_width - 40, page_height - 30, "DOG TRAINERS DIRECTORY")

        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(40, page_height - 35, page_width - 40, page_height - 35)

        # Running Footer
        self.line(40, 40, page_width - 40, 40)
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_INK_LIGHT)
        self.drawString(40, 26, "Evidence-based dog training foundations • dogtrainersdirectory.com.au")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_width - 40, 26, page_str)

        self.restoreState()


def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=36,
        textColor=COLOR_INK,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=COLOR_INK_LIGHT,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="GuideHeading",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=COLOR_INK,
        spaceBefore=14,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="GuideStrapline",
        fontName="Helvetica-Oblique",
        fontSize=12,
        leading=16,
        textColor=COLOR_TERRACOTTA,
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="LessonHeading",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=COLOR_INK,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Badge",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=COLOR_WHITE,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=COLOR_INK,
        spaceBefore=8,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BodyCustom",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=COLOR_TEXT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BulletText",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="DecisionText",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=COLOR_INK,
    ))
    styles.add(ParagraphStyle(
        name="CautionText",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_TERRACOTTA,
    ))
    styles.add(ParagraphStyle(
        name="EscalationText",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_INK,
    ))
    return styles


def build_callout(content_paragraph: Paragraph, bg_color, border_color, title_text=""):
    elements = []
    if title_text:
        title_style = ParagraphStyle(
            name=f"CalloutTitle_{title_text}",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=border_color,
            spaceAfter=3,
        )
        elements.append(Paragraph(title_text, title_style))
    elements.append(content_paragraph)

    table = Table([[elements]], colWidths=[515])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('PADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return table


# Complete Solidified Curriculum Data
CURRICULUM = [
    {
        "number": 1,
        "title": "The Blueprint",
        "strapline": "Home Architecture & Environmental Safety",
        "cover_img": "mod_01_cover.jpg",
        "puppy_img": "mod_01_puppy.jpg",
        "intro": "Before obedience training begins, the home environment must be configured so unwanted behaviors are physically impossible to rehearse. This guide establishes the safe base zone, audits toxic household risks, and builds a realistic healthcare baseline.",
        "lessons": [
            {
                "num": "1.1",
                "title": "The 2-Door Buffer Zone & Base Setup",
                "tag": "Environment & Rest",
                "time": "5 min read",
                "scenario": "A newly arrived puppy or rescue dog explores frantically, paces continuously, and chews baseboards out of sensory overwhelm.",
                "science": "Canine nervous systems require bounded, low-stimulus territory to down-regulate sympathetic arousal. Open floor plans overstimulate vigilance circuits.",
                "protocol": [
                    "Construct a 2-Door Buffer: Exercise pen attached to an open crate in a low-traffic corner (never in entryways or busy hallways).",
                    "Substrate layering: Waterproof rubber mat -> washable absorbent pad -> high-density orthopedic bed -> 1 safe natural chew.",
                    "The Open Den Rule: Crate doors stay open during waking hours. The pen provides 4-6 square meters of safe containment."
                ],
                "caution": "Using confinement solely as punishment after a mistake occurs. Confinement must always be a proactive sanctuary.",
                "decision": "Until house reliability is proven, freedom is earned room by room, never granted by default.",
                "escalation": "Persistent panic, self-harm bar-biting, or distress vocalization lasting >20 minutes indicates separation or confinement anxiety requiring professional care."
            },
            {
                "num": "1.2",
                "title": "The Toxic Sweep & Poison Triage",
                "tag": "Safety & Vet Prep",
                "time": "4 min read",
                "scenario": "Your dog grabs a dropped pill, chews an unfamiliar indoor plant, or raids the laundry detergent shelf.",
                "science": "Xylitol (birch sugar), human NSAIDs, dark chocolate, lilies, and snail bait exhibit variable absorption windows (15m to 12h). Symptoms often appear long after organ damage begins.",
                "protocol": [
                    "Immediate extraction: Remove remaining material safely without engaging in a chase game.",
                    "Evidence capture: Retain packaging, label, plant clipping, or photograph immediately.",
                    "Direct Emergency Contact: Call the Australian Animal Poisons Helpline (1300 869 738) or emergency vet with dog's weight (kg), product name, and time elapsed.",
                    "NEVER induce vomiting with salt (fatal hypernatremia risk)."
                ],
                "caution": "Waiting for vomiting or lethargy before seeking clinical advice. Absorption happens rapidly.",
                "decision": "Toxin ingestion is a medical triage emergency, never a behavioral wait-and-see situation.",
                "escalation": "Suspected ingestion of human pharmaceuticals, rat bait, batteries, or lilies requires immediate physical clinic presentation."
            },
            {
                "num": "1.3",
                "title": "First-Year Healthcare & Financial Baseline",
                "tag": "Healthcare & Budget",
                "time": "5 min read",
                "scenario": "New owners are caught off-guard by preventative care, council registrations, and surprise emergency vet bills.",
                "science": "Routine core vaccines (C3/C5), heartworm macrocyclic lactones, and isoxazoline tick control prevent catastrophic clinical crises.",
                "protocol": [
                    "Initial Consultation: Book health check within 72 hours of arrival. Verify microchip on Central Animal Records / Petsafe.",
                    "Council Registration: Mandatory in Victoria by 3 months of age under the Domestic Animals Act 1994.",
                    "Financial Architecture: Maintain $100-$150 AUD/mo routine budget plus a dedicated $2,000 AUD liquidity buffer or >=80% insurance policy."
                ],
                "caution": "Skipping tick prevention due to perceived low suburban risk. Paralysis ticks exist across Victorian coastal and bushland corridors.",
                "decision": "Emergency healthcare financial buffers must be established before bringing the dog home.",
                "escalation": "If sudden behavioral shifts accompany physical signs (stiffness, whimpering, appetite loss), rule out medical causes with a vet first."
            }
        ]
    },
    {
        "number": 2,
        "title": "The Transition Phase",
        "strapline": "Early Friction & Biological De-Escalation",
        "cover_img": "mod_02_cover.jpg",
        "puppy_img": "mod_02_puppy.jpg",
        "intro": "The first 30 days are when routines harden. This guide replaces frustration with biological predictability, solving house-training delays, needle-sharp arousal biting, and puppy blues.",
        "lessons": [
            {
                "num": "2.1",
                "title": "The Biological Window: Potty Mastery",
                "tag": "House Training",
                "time": "5 min read",
                "scenario": "Your puppy eliminates outside, walks back in, and deposits a puddle on the living room rug 3 minutes later.",
                "science": "Puppies lack complete urinary sphincter muscle control before 16 weeks. Movement, waking, and eating trigger the gastrocolic reflex within 10-20 minutes.",
                "protocol": [
                    "The Bladder Formula: Age in Months + 1 = Maximum Holding Time in Hours (e.g. 2 months = 3h max while asleep; active intervals are 30-45m).",
                    "The 3 Biological Triggers: Take the dog outside immediately upon waking, 10-15m post-meal, and after 10m of physical play.",
                    "The 2-Second Pay Window: Deliver high-value meat reward within 1 to 2 seconds of squat completion while still outdoors.",
                    "Enzymatic Cleanup: Clean accidents with enzymatic bio-cleaners to destroy uric acid crystals (never use ammonia)."
                ],
                "caution": "Rubbing the dog's nose in accidents or scolding. This teaches the dog that eliminating in human presence is dangerous, driving them to hide behind furniture to toilet.",
                "decision": "Indoor accidents reflect human supervision and timing gaps, not canine defiance.",
                "escalation": "Frequent straining, blood in urine, or acute regression in a previously clean dog requires immediate veterinary urinalysis for UTIs."
            },
            {
                "num": "2.2",
                "title": "The Reverse Timeout: Arousal Biting",
                "tag": "Play & Biting",
                "time": "4 min read",
                "scenario": "During evening playtime, the puppy clamps down on hands, jeans, or ankles, biting harder when pushed away.",
                "science": "Pushing, squealing, and wrestling stimulate predatory play drive. Human reaction functions as an active reinforcer.",
                "protocol": [
                    "The 3-Second Disengagement: The instant teeth touch skin, say a neutral marker ('Too bad') in a flat voice.",
                    "The Reverse Timeout (RTO): Stand up, cross arms, step over the baby gate or leave the room for exactly 15 seconds.",
                    "Calm Re-entry: Return without speaking. Offer a tactile replacement (frozen KONG, yak chew, or rope toy).",
                    "Rule: Teeth on human = social attention instantly terminates."
                ],
                "caution": "Physical scolding or muzzle-pinning ('alpha roll'). This triggers defensive fear and escalates arousal biting.",
                "decision": "Remove the human reward (attention) the exact millisecond teeth touch human skin.",
                "escalation": "Biting accompanied by frozen posture, hard staring, snarling, or resource guarding is clinical aggression requiring trainer intervention."
            },
            {
                "num": "2.3",
                "title": "Decompressing Owner Overwhelm & 3-3-3 Rule",
                "tag": "Mindset & Routine",
                "time": "4 min read",
                "scenario": "At day 5, the owner feels profound exhaustion, crying spells, and deep anxiety over having made a mistake.",
                "science": "Sleep deprivation and vigilance elevate human cortisol, while the canine cortisol reset curve requires 72+ hours post-rehoming.",
                "protocol": [
                    "The 3-3-3 Milestone Filter: Day 3 (Overwhelmed/Shut-down) -> Week 3 (Learning routine) -> Month 3 (Attachment & true personality).",
                    "Enforced Nap Cadence: 1 hour awake -> 2 hours quiet rest in the Base Zone. Puppies require 18-20 hours of daily sleep.",
                    "Radical Simplification: Drop complex obedience tricks. Focus solely on sleep, potty timing, and calm supervision."
                ],
                "caution": "Treating normal puppy overstimulation as a permanent behavioral defect.",
                "decision": "A well-rested puppy and a calm owner solve 80% of early friction before formal training begins.",
                "escalation": "If severe owner anxiety persists after routine stabilization, consult a professional trainer to establish an in-home structure plan."
            }
        ]
    },
    {
        "number": 3,
        "title": "The Empathy Engine",
        "strapline": "Canine Body Language & Clinical Observation",
        "cover_img": "mod_03_cover.jpg",
        "puppy_img": "mod_03_puppy.jpg",
        "intro": "Dogs communicate through subtle physiological micro-signals long before they growl or bark. This guide teaches owners how to read the whole dog and never punish vital communication signals.",
        "lessons": [
            {
                "num": "3.1",
                "title": "Canine Micro-Signals & Distance Seeking",
                "tag": "Body Language",
                "time": "5 min read",
                "scenario": "A dog turns its head away, licks its nose, or yawns when approached by a stranger, but the owner thinks it is just tired or cute.",
                "science": "Canine stress cascades through subtle displacement behaviors before escalating to active flight or fight responses.",
                "protocol": [
                    "Level 1 Signals (Early Worry): Nose licks (in absence of food), yawning (when not tired), blinking, head turns away from trigger.",
                    "Level 2 Signals (Active Stress): Whale eye (sclera visible), furrowed brow, ears pinned back, panting with tight commissures.",
                    "Level 3 Signals (Imminent Freeze): Body stiffness, tail rigid/vibrating, mouth clamped shut, complete stillness.",
                    "The 3-Foot Buffer: The instant Level 1-2 signals cluster, create 1 meter of space from the trigger."
                ],
                "caution": "Forcing a dog to endure handling or greetings when displaying displacement signals.",
                "decision": "Listen to the whisper (head turn) so your dog never has to scream (bite).",
                "escalation": "Inability to settle or persistent whale eye in everyday household settings requires professional behavioral assessment."
            },
            {
                "num": "3.2",
                "title": "The Warning Ladder: Never Punish the Growl",
                "tag": "De-escalation",
                "time": "5 min read",
                "scenario": "Your dog growls when someone approaches their food bowl or sofa spot, and the owner scolds the dog to show 'dominance'.",
                "science": "Growling is a vital communication alarm on the Ladder of Aggression. Suppressing the growl produces a dog that bites without warning.",
                "protocol": [
                    "The Escalation Ladder: Calming signals -> Stiffening -> Low Growl -> Snarl -> Air Snap -> Contact Bite.",
                    "De-escalation Procedure: Freeze immediately. Avoid direct eye contact. Slowly step back 2 paces to relieve spatial pressure.",
                    "Never Scold: Treat the growl as vital data about discomfort. Identify and manage the environmental trigger.",
                    "Manage the Trigger: If food-related, feed in an isolated, secure room without human traffic."
                ],
                "caution": "Punishing warning vocalizations removes the smoke alarm while the fire continues to burn.",
                "decision": "Thank your dog for growling; it is the boundary signal that prevents a bite.",
                "escalation": "Any growling, snapping, or stiffening over food, toys, or sleeping locations is clinical Resource Guarding requiring certified trainer triage."
            },
            {
                "num": "3.3",
                "title": "The Medical Baseline Filter",
                "tag": "Clinical Health",
                "time": "4 min read",
                "scenario": "A previously friendly dog suddenly begins snapping when touched near the hips, refusing stairs, or barking at night.",
                "science": "Over 30% of acute behavioral changes are directly linked to underlying medical discomfort (osteoarthritis, otitis, dental pain, gut distress).",
                "protocol": [
                    "The 48-Hour Somatic Check: Audit gait stiffness, hesitation on stairs, ear-touch sensitivity, and appetite changes.",
                    "Veterinary Rule: Before hiring a behaviorist for sudden fear or aggression, obtain a thorough veterinary pain examination.",
                    "Trial Therapy: Discuss diagnostic pain relief trials with your veterinarian if physical examination is inconclusive."
                ],
                "caution": "Attempting behavioral modification on a dog suffering from untreated physical pain.",
                "decision": "Rule out medical and physiological discomfort before classifying any sudden shift as a behavioral problem.",
                "escalation": "Acute behavioral changes paired with lethargy, limping, or yelping require veterinary diagnostics before training."
            }
        ]
    },
    {
        "number": 4,
        "title": "The Social Filter",
        "strapline": "Safe Exposure & Urban Resilience",
        "cover_img": "mod_04_cover.jpg",
        "puppy_img": "mod_04_puppy.jpg",
        "intro": "Real socialization is not about forcing your dog to greet every dog and human. This guide builds environmental neutrality, distance management, and cooperative handling confidence.",
        "lessons": [
            {
                "num": "4.1",
                "title": "Quality Over Quantity: Socialisation ≠ Contact",
                "tag": "Socialisation",
                "time": "5 min read",
                "scenario": "An owner takes a 12-week puppy to a crowded off-leash dog park, allowing chaotic dogs to overwhelm the puppy.",
                "science": "The primary developmental window closes between 12-16 weeks. Traumatic single-event learning during fear periods can cause permanent reactivity.",
                "protocol": [
                    "The Neutrality Protocol: Sit on a quiet park bench 30m away from paths. Reward calm observation of cyclists, prams, and dogs.",
                    "The 3-Second Greeting Rule: If greeting on-leash, allow max 3 seconds (sniff, sniff, call away with praise) before arousal turns into tension.",
                    "Avoid Chaotic Dog Parks: Off-leash dog parks encourage bullying, defensive aggression, and uncontrolled greetings."
                ],
                "caution": "Believing your dog needs to physically interact with every person and dog it encounters.",
                "decision": "We train our dogs to be neutral to the world, not desperate to engage with it.",
                "escalation": "If your puppy panics, hides, or screams during mild exposure at distance, halt sessions and consult a trainer."
            },
            {
                "num": "4.2",
                "title": "The 3-Zone Threshold Bubble",
                "tag": "Reactivity",
                "time": "5 min read",
                "scenario": "Your dog spots another dog across the street, freezes, whines, and lunges at the end of the lead.",
                "science": "When a dog crosses their threshold distance, amygdala activation suppresses cognitive learning and appetite.",
                "protocol": [
                    "Green Zone (Sub-Threshold): Loose body, glances at trigger, takes treats easily. (This is where counter-conditioning works).",
                    "Yellow Zone (Threshold Edge): Stiffens, fixes gaze, slow treat taking. (Action: Increase distance by 5-10m immediately).",
                    "Red Zone (Over-Threshold): Lunging, barking, spinning, refusing food. (Action: Turn around, jog away, evacuate without scolding).",
                    "Arcing Maneuver: Never approach head-on. Step into driveways or arc widely across the road."
                ],
                "caution": "Standing in the Red Zone repeatedly commanding the dog to 'Sit' while they are in a physiological panic state.",
                "decision": "Distance is your primary safety tool. When in doubt, add 10 meters of space.",
                "escalation": "Inability to maintain a Green Zone at >30m distance indicates moderate-to-severe reactivity requiring structured desensitization."
            },
            {
                "num": "4.3",
                "title": "Cooperative Care & Low-Stress Handling",
                "tag": "Husbandry & Grooming",
                "time": "4 min read",
                "scenario": "Nail trimming or ear cleaning requires three adults pinning the dog down while the dog thrashes in terror.",
                "science": "Restraint-based force generates learned helplessness or active defensive biting. Cooperative care gives the dog a predictable consent mechanism.",
                "protocol": [
                    "The Chin Rest Consent Cue: Train the dog to rest their chin on your open hand for high-value rewards.",
                    "The Consent Contract: As long as the chin stays down, gentle handling proceeds. If chin lifts, handling stops immediately.",
                    "Desensitization Ladder: Day 1-3 (touch paw with clipper handle) -> Day 4-7 (tap nail) -> Day 8+ (trim 1 nail tip -> jackpot treat)."
                ],
                "caution": "Forcing grooming procedures through restraint, which intensifies fear and escalates to defensive snapping.",
                "decision": "Consent and predictable agency eliminate terror in healthcare and grooming.",
                "escalation": "Extreme fear, growling, or snapping during routine veterinary touch requires an accredited fear-free trainer."
            }
        ]
    },
    {
        "number": 5,
        "title": "The Sync Mechanics",
        "strapline": "Reward Timing, Cues & Household Consistency",
        "cover_img": "mod_05_cover.jpg",
        "puppy_img": "mod_05_puppy.jpg",
        "intro": "Dogs learn through precise temporal association. This guide tightens marker timing, eliminates accidental rewards for bad behavior, and aligns the whole family on one clear cue set.",
        "lessons": [
            {
                "num": "5.1",
                "title": "The 1-Second Pay Window & Precision Markers",
                "tag": "Marker Training",
                "time": "4 min read",
                "scenario": "The dog sits, the owner says 'good boy,' fumbles in their pocket for 8 seconds, and delivers a treat after the dog has already stood up.",
                "science": "Associative learning requires reinforcer delivery within a 0.5-1.5 second window. Late rewards reinforce the movement occurring at delivery.",
                "protocol": [
                    "Charge the Marker: Select a crisp, short syllable ('Yes!') or clicker. Pair: Click -> Treat immediately 20 times.",
                    "The 3-Step Sequence: Behavior Occurs -> Marker Fired -> Treat Delivered to mouth within 2 seconds.",
                    "Treat Accessibility: Wear a treat pouch or keep pea-sized rewards ready in hand, not buried in pockets."
                ],
                "caution": "Using the marker word as an attention-getter ('Yes! Yes! Look here!'). Markers are camera shutters capturing completed behaviors.",
                "decision": "The marker captures the exact millisecond; the hand delivers the reward.",
                "escalation": "If a dog shows zero food motivation in a calm home, assess diet, health, or overfeeding before training."
            },
            {
                "num": "5.2",
                "title": "Extinguishing Accidental Payoffs",
                "tag": "Extinction & Habits",
                "time": "5 min read",
                "scenario": "The dog jumps on guests, steals kitchen towels, or barks at the dinner table, and family members alternate between scolding and laughing.",
                "science": "Intermittent variable reinforcement schedules create the most durable, hard-to-extinguish habits in behavioral psychology.",
                "protocol": [
                    "Audit Accidental Payoffs: Jumping (guests pet dog) -> Counter-surfing (roast beef left on edge) -> Stealing items (chase game).",
                    "Management Fixes: Clean benches completely. Put dog on leash with guest arrival so jumping is physically prevented.",
                    "Extinction Burst Awareness: When reinforcement stops, the behavior temporarily spikes in intensity before dying out. Stay consistent."
                ],
                "caution": "Giving in 'just this once' after 10 minutes of barking. This directly trains the dog to bark longer next time.",
                "decision": "Control the environment so unwanted behaviors never receive an accidental payoff.",
                "escalation": "If resource guarding accompanies stolen items (growling over socks), do not chase; begin professional trade protocols."
            },
            {
                "num": "5.3",
                "title": "The Household Cue Constitution",
                "tag": "Household Consistency",
                "time": "4 min read",
                "scenario": "Mom says 'Down' (lie on floor), Dad says 'Down' (get off couch), and the kids yell 'Off', leaving the dog completely bewildered.",
                "science": "Canines discriminate specific auditory phonemes paired with body postures, not general semantic concepts.",
                "protocol": [
                    "Define the Vocabulary: 'Sit' (bottom down), 'Drop' (chest on floor), 'Off' (paws off furniture/humans), 'Wait' (pause at thresholds).",
                    "Release Cue: Establish an explicit release word ('Free' or 'Break') so the dog knows when a position ends.",
                    "The Single Cue Rule: Say the verbal cue once. If ignored, do not repeat it 5 times. Guide with a physical hand lure."
                ],
                "caution": "Chanting verbal commands like background noise until the dog learns to filter them out.",
                "decision": "One cue, one word, one criteria, agreed upon by every member of the household.",
                "escalation": "If multiple family members have conflicting training philosophies causing behavioral regression, book a family trainer consultation."
            }
        ]
    },
    {
        "number": 6,
        "title": "The Urban Flow & The Shield",
        "strapline": "Public Life & Distraction Management",
        "cover_img": "mod_06_cover.jpg",
        "puppy_img": "mod_06_puppy.jpg",
        "intro": "Urban streets are sensory obstacle courses. This guide establishes structured walking games, eliminates window barking triggers, and builds sub-panic independence.",
        "lessons": [
            {
                "num": "6.1",
                "title": "The 1-2-3 Engagement Walk",
                "tag": "Leash Manners",
                "time": "5 min read",
                "scenario": "Your dog pulls forcefully on the leash, zig-zagging erratically between smells and dragging you down the footpath.",
                "science": "Rhythmic, predictable verbal count patterns engage the parasympathetic nervous system and restore handler focus.",
                "protocol": [
                    "Split the Walk: 70% slow sniffing on a 2-3m fixed lead (sniffing lowers heart rate), 30% structured focus walking.",
                    "The 1-2-3 Pattern Game: Count out loud '1, 2, 3'. On '3', deliver a treat at your trouser seam. Practice 20 times in driveway.",
                    "Deploy on Street: When approaching a distracting dog, start counting '1, 2, 3'. On '1', the dog turns toward you in anticipation."
                ],
                "caution": "Using retractable flexi-leashes. They maintain continuous pressure, actively conditioning the dog to pull against tension.",
                "decision": "Sniffing is decompression; counting is connection. Balance both on every street walk.",
                "escalation": "Dogs that lunge forcefully and cannot disengage with pattern games need an in-person leash manners specialist."
            },
            {
                "num": "6.2",
                "title": "The Environmental Shield: Window Barking",
                "tag": "Territorial Barking",
                "time": "4 min read",
                "scenario": "The dog perches on the back of the sofa, barking frantically at mail carriers and pedestrians through the front window.",
                "science": "When a dog barks at a pedestrian who walks away, the dog believes their barking chased the threat off, cementing a self-reinforcing loop.",
                "protocol": [
                    "The Physical Shield: Apply static frosted window film to the lower 60cm of front windows. Blocks visual stimuli without losing light.",
                    "Acoustic Masking: Position a brown noise machine or radio near front hallways to mask sudden street sounds.",
                    "Spatial Setup: Move couches and chairs away from window sills to eliminate elevated watchtower perches."
                ],
                "caution": "Yelling 'Quiet!' from across the room. The dog interprets human shouting as vocal participation in their barking.",
                "decision": "You cannot out-train a visual trigger that is rehearsed 30 times a day while you are at work.",
                "escalation": "Compulsive fence-running or barrier frustration causing fence-biting requires environmental containment triage."
            },
            {
                "num": "6.3",
                "title": "Independence Micro-Dosing: Alone Time",
                "tag": "Separation Confidence",
                "time": "5 min read",
                "scenario": "The dog whines, scratches doors, drools, or paces frantically whenever you pick up keys or step out of sight.",
                "science": "Separation distress is a neurological panic state. Desensitization must occur entirely below the threshold of anxiety.",
                "protocol": [
                    "De-Weaponize Departure Cues: Pick up keys -> sit on couch. Put on coat -> make tea. Repeat 10 times daily until cues evoke zero arousal.",
                    "Micro-Dosing Alone Time: Step outside front door for 5 seconds -> return calmly before whining begins.",
                    "Gradual Progression: Advance to 15s -> 30s -> 1m -> 2m -> 5m. If vocalization occurs, cut duration in half on the next trial."
                ],
                "caution": "Leaving a panicked dog with a frozen peanut butter KONG thinking food cures panic (distressed dogs refuse food).",
                "decision": "Build independence second by second, never allowing the panic circuit to activate.",
                "escalation": "Destructive clawing at doorframes, vocalization lasting >15 minutes, or puddles of drool indicates clinical Separation Anxiety requiring a certified specialist."
            }
        ]
    },
    {
        "number": 7,
        "title": "The Freedom Framework",
        "strapline": "Expanding Independence & Professional Escalation",
        "cover_img": "mod_07_cover.jpg",
        "puppy_img": "mod_07_puppy.jpg",
        "intro": "Freedom is earned through proven reliability. This guide structures room-by-room expansion, manages adolescent brain remodeling, and prepares a clinical intake brief when professional help is needed.",
        "lessons": [
            {
                "num": "7.1",
                "title": "The Single-Room Expansion Trial",
                "tag": "House Freedom",
                "time": "4 min read",
                "scenario": "After two good weeks in the kitchen, the owner opens the whole house, and the dog immediately pees in the spare bedroom and chews a rug.",
                "science": "Canine behavioral reliability is spatially bounded and does not automatically generalize to unmapped rooms.",
                "protocol": [
                    "The 3 Milestones: 14 consecutive days zero accidents + 5s chew redirection + 30m independent rest in Base Zone.",
                    "The Room Trial: Open 1 adjacent room (living room). Supervise for 30-45m while humans are actively present.",
                    "Unsupervised Access: Only after 7 consecutive accident-free days under supervision do you allow short unsupervised access."
                ],
                "caution": "Granting full-house freedom before spatial mapping is established.",
                "decision": "Freedom is a privilege awarded for proven reliability, not a biological default.",
                "escalation": "Persistent house soiling despite strict management requires an in-home assessment."
            },
            {
                "num": "7.2",
                "title": "Adolescent Regression Triage",
                "tag": "Adolescence (6-14 Mo)",
                "time": "5 min read",
                "scenario": "At 8 months of age, your previously obedient puppy suddenly forgets recalls, tests boundaries, and barks at fire hydrants.",
                "science": "Adolescence brings massive hormonal surges (testosterone/estrogen) and synaptic pruning in the prefrontal cortex, reducing impulse control.",
                "protocol": [
                    "Temporarily Lower Criteria: Treat the adolescent dog like an older puppy. Re-attach a 10m long line for outdoor recalls.",
                    "Secondary Fear Period Care: If the dog is terrified of a novel object, do not force confrontation. Arc away, feed treats at distance, move on.",
                    "Scent Enrichment: Replace physical fetch with nose-work search games to exhaust cognitive energy without spiking adrenaline."
                ],
                "caution": "Becoming punitive, believing the adolescent dog is deliberately trying to 'dominate' or 'defy' you.",
                "decision": "Adolescence is brain remodeling; manage the environment and tighten criteria until the brain matures.",
                "escalation": "Sudden resource guarding or dog-directed aggression during adolescence requires professional behavior modification."
            },
            {
                "num": "7.3",
                "title": "Clinical Escalation & Trainer Intake Prep",
                "tag": "Professional Handoff",
                "time": "5 min read",
                "scenario": "Despite consistent management, your dog exhibits persistent resource guarding, stranger fear, or severe reactivity.",
                "science": "Complex behavioral pathologies require clinical functional assessments, systematic desensitization plans, and expert trainer oversight.",
                "protocol": [
                    "Synthesize the 6-Point Dossier: (1) Primary Concern, (2) Antecedent trigger, (3) Frequency, (4) Threshold distance, (5) What has been tried, (6) Dunbar Bite Scale level (1-6).",
                    "Directory Matching: Match with verified, accredited trainers on DTD who hold transparent method credentials and local suburb reviews.",
                    "Handoff Readiness: Bring your 48-hour behavior logs and video footage to your initial trainer consultation."
                ],
                "caution": "Waiting until a bite occurs before seeking professional intervention.",
                "decision": "Knowing when to engage a qualified professional is the ultimate hallmark of responsible dog ownership.",
                "escalation": "Connect with verified local Melbourne specialists via the DTD Directory at dogtrainersdirectory.com.au/match."
            }
        ]
    }
]


def render_pdf(output_path: Path, modules_to_render, doc_title: str, doc_subtitle: str, cover_image_name: str):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )
    styles = create_styles()
    story = []

    # Cover Page
    cover_path = IMAGES_DIR / cover_image_name
    if cover_path.exists():
        # Clean rounded cover image
        img = Image(str(cover_path), width=515, height=270)
        story.append(img)
        story.append(Spacer(1, 20))

    story.append(Paragraph(doc_title, styles["DocTitle"]))
    story.append(Paragraph(doc_subtitle, styles["DocSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_TERRACOTTA, spaceAfter=18))

    # Handbook Meta Box
    meta_text = (
        "<b>Publisher:</b> Dog Trainers Directory (Melbourne, Victoria)<br/>"
        "<b>Standard:</b> Evidence-Based Positive Reinforcement & Clinical De-Escalation<br/>"
        "<b>Access:</b> 100% Free Public Guide • dogtrainersdirectory.com.au"
    )
    story.append(build_callout(Paragraph(meta_text, styles["BodyCustom"]), COLOR_CREAM, COLOR_MOSS, "CANONICAL OWNER HANDBOOK"))
    story.append(Spacer(1, 25))
    story.append(PageBreak())

    # Render Modules
    for mod_idx, mod in enumerate(modules_to_render):
        # Module Banner
        mod_cover = IMAGES_DIR / mod["cover_img"]
        if mod_cover.exists():
            banner = Image(str(mod_cover), width=515, height=180)
            story.append(banner)
            story.append(Spacer(1, 14))

        # Guide Title
        badge_p = Paragraph(f"GUIDE {mod['number']} OF 7", styles["Badge"])
        badge_table = Table([[badge_p]], colWidths=[95], rowHeights=[18])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_INK),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(badge_table)
        story.append(Spacer(1, 6))

        story.append(Paragraph(f"Guide {mod['number']} — {mod['title']}", styles["GuideHeading"]))
        story.append(Paragraph(mod["strapline"], styles["GuideStrapline"]))
        story.append(Paragraph(mod["intro"], styles["BodyCustom"]))
        story.append(Spacer(1, 14))

        # Puppy Illustration for Module
        puppy_img = IMAGES_DIR / mod["puppy_img"]
        if puppy_img.exists():
            p_img = Image(str(puppy_img), width=515, height=200)
            story.append(p_img)
            story.append(Spacer(1, 14))

        # Render Lessons for this Module
        for lesson in mod["lessons"]:
            lesson_elements = []

            # Lesson Header
            header_text = f"Section {lesson['num']} • {lesson['title']}"
            lesson_elements.append(Paragraph(header_text, styles["LessonHeading"]))

            sub_badge = f"<b>Focus:</b> {lesson['tag']} &nbsp;|&nbsp; <b>Time:</b> {lesson['time']}"
            lesson_elements.append(Paragraph(sub_badge, styles["BodyCustom"]))
            lesson_elements.append(Spacer(1, 4))

            # Scenario
            lesson_elements.append(Paragraph("<b>The Situation:</b>", styles["SectionHeading"]))
            lesson_elements.append(Paragraph(lesson["scenario"], styles["BodyCustom"]))

            # Biological Science
            lesson_elements.append(Paragraph("<b>The Science & Mechanics:</b>", styles["SectionHeading"]))
            lesson_elements.append(Paragraph(lesson["science"], styles["BodyCustom"]))

            # Protocol
            lesson_elements.append(Paragraph("<b>Action Protocol:</b>", styles["SectionHeading"]))
            for step in lesson["protocol"]:
                bullet = f"• {step}"
                lesson_elements.append(Paragraph(bullet, styles["BulletText"]))

            # Caution Trap
            caution_p = Paragraph(f"<b>Common Trap:</b> {lesson['caution']}", styles["CautionText"])
            lesson_elements.append(Spacer(1, 4))
            lesson_elements.append(build_callout(caution_p, COLOR_WARN_BG, COLOR_TERRACOTTA, "⚠️ CAUTION"))

            # Decision Rule
            decision_p = Paragraph(f"<b>Immutable Rule:</b> {lesson['decision']}", styles["DecisionText"])
            lesson_elements.append(Spacer(1, 4))
            lesson_elements.append(build_callout(decision_p, COLOR_DECISION_BG, COLOR_INK, "⚖️ DECISION RULE"))

            # Escalation
            escalation_p = Paragraph(f"<b>When to Get Professional Help:</b> {lesson['escalation']}", styles["EscalationText"])
            lesson_elements.append(Spacer(1, 4))
            lesson_elements.append(build_callout(escalation_p, COLOR_CREAM, COLOR_MOSS, "🚩 CLINICAL ESCALATION"))

            lesson_elements.append(Spacer(1, 16))
            story.append(KeepTogether(lesson_elements))

        if mod_idx < len(modules_to_render) - 1:
            story.append(PageBreak())

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {output_path} ({output_path.stat().st_size} bytes)")


def main():
    print("Generating Complete Master Handbook...")
    master_pdf_path = FILES_DIR / "the-first-leash.pdf"
    render_pdf(
        output_path=master_pdf_path,
        modules_to_render=CURRICULUM,
        doc_title="The First Leash: Complete Dog Owner Handbook",
        doc_subtitle="A 7-Guide Practical System for Foundations, Stress Reading, and Urban Resilience",
        cover_image_name="first-leash.jpg"
    )

    # Copy to frontend/build/files if it exists
    build_files = REPO_ROOT / "frontend" / "build" / "files" / "the-first-leash.pdf"
    if build_files.parent.exists():
        shutil.copy(master_pdf_path, build_files)
        print(f"Synced to {build_files}")

    print("\nGenerating Individual 7 Module Guides in docs/education/...")
    for mod in CURRICULUM:
        mod_num = mod["number"]
        # Format filename matching existing conventions
        if mod_num == 4:
            file_name = f"Module 4 - {mod['title']}.pdf"
        else:
            file_name = f"Module {mod_num} — {mod['title']}.pdf"
        
        mod_pdf_path = DOCS_EDU_DIR / file_name
        render_pdf(
            output_path=mod_pdf_path,
            modules_to_render=[mod],
            doc_title=f"Guide {mod_num}: {mod['title']}",
            doc_subtitle=mod["strapline"],
            cover_image_name=mod["cover_img"]
        )

    print("\nAll Education PDFs successfully generated!")


if __name__ == "__main__":
    main()
