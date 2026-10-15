"""
Synthetic data generator for the PathMind readiness-to-change classifier (v1).

Generates ~4,000 labeled examples (JSONL: {"text", "label"}) over the five fixed
Transtheoretical Model stages, using Indian-student personas with heavy lexical
variation and deliberately ambiguous / borderline cases.

> This classifier is a SCREENING HEURISTIC, not a psychological diagnosis.
> It must not be used to label a person's mental state or make clinical claims.
"""
import json
import os
import random

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))

LABELS = ["precontemplation", "contemplation", "preparation", "action", "maintenance"]

# ---------------------------------------------------------------- personas
# (descriptor, goal_context)
PERSONAS = {
    "school": [
        ("a class 7 student", "my maths marks"),
        ("a class 8 student", "my studies"),
        ("a class 9 student", "my science grades"),
        ("a class 10 student", "my board exam preparation"),
        ("a class 11 student", "my physics preparation"),
        ("a class 12 student", "my JEE/NEET preparation"),
        ("a class 10 student", "my English writing"),
        ("a class 9 student", "my daily study routine"),
        ("a class 12 student", "my chemistry syllabus"),
        ("a class 8 student", "my homework habits"),
    ],
    "college": [
        ("a first-year B.Tech student", "my coding practice"),
        ("a second-year engineering student", "my programming skills"),
        ("a final-year BCA student", "my placement preparation"),
        ("a college student", "my CGPA"),
        ("a second-year B.Sc student", "my backlog subjects"),
        ("a final-year B.Tech student", "my interview preparation"),
        ("a first-year college student", "my attendance"),
        ("a third-year engineering student", "my DSA practice"),
        ("an MCA student", "my project work"),
        ("a final-year student", "my resume building"),
    ],
    "switcher": [
        ("a working professional", "switching from sales to data analysis"),
        ("an accountant", "moving into digital marketing"),
        ("a teacher", "transitioning to content writing"),
        ("a mechanical engineer", "learning software development"),
        ("a bank clerk", "preparing for UPSC"),
        ("a call-centre employee", "learning web development"),
        ("an HR executive", "moving into product management"),
        ("a shop-floor supervisor", "upskilling in Excel and analytics"),
    ],
    "business": [
        ("a small-business aspirant", "opening my own tea stall"),
        ("a home baker", "starting an online bakery"),
        ("a tailor", "expanding my boutique business"),
        ("a small-shop owner", "taking my kirana store online"),
        ("a freelancer", "building my design services business"),
        ("a college student", "starting a tiffin service"),
        ("a housewife", "selling handmade crafts online"),
        ("a mobile-repair shop owner", "adding accessories to my shop"),
    ],
}

FILLERS = ["", "honestly, ", "to be honest, ", "tbh, ", "well, ", "see, ", "look, ",
           "frankly, ", "you know, ", "at this point, "]
HEDGES = ["", " I guess.", " I think.", " maybe.", " not sure though.", " that's what I feel.",
          " that's my situation.", " I don't know."]
ENDERS = ["", ".", "!", " that's it.", " so yeah.", " that's the truth."]

# ------------------------------------------------------------------ helpers
def fill(template):
    return template


def vary(text):
    """Light lexical swaps to add surface variation."""
    swaps = [
        ("studying", "study"), ("started studying", "started study"),
    ]
    return text


def sample_persona(cat):
    return random.choice(PERSONAS[cat])


def pick(*items):
    return random.choice(items)

# ================================================== precontemplation ======
# Not considering change; defensive or unaware. Includes anti-cue cases where
# the person uses change-y words ("plan", "goal") while rejecting change.
PRE_T = [
    "{f}i am {who} and i dont see any problem with {goal}{e}",
    "{f}my {goal} is fine the way it is, everyone else should just stop bothering me{h}{e}",
    "{f}why should i change anything? my {goal} is not that bad{h}{e}",
    "{f}as {who}, i honestly feel people make a big deal out of {goal} for no reason{h}{e}",
    "{f}everyone keeps telling me to work on {goal} but i think they are exaggerating{h}{e}",
    "{f}i am {who}; my {goal} has always been like this and it never hurt me{h}{e}",
    "{f}change? i dont need any change in {goal}. i am comfortable{h}{e}",
    "{f}my parents keep pushing me about {goal} but i dont see the point{h}{e}",
    "{f}i am {who} and {goal} is simply not a priority for me, maybe never will be{h}{e}",
    "{f}people say i should improve {goal} but honestly i feel fine without it{h}{e}",
    "{f}all my friends also ignore {goal}, so whats the big deal{h}{e}",
    "{f}as {who}, i think {goal} is overrated, i am doing okay without trying{h}{e}",
    "{f}teachers scold me about {goal} but that is just how school is{h}{e}",
    "{f}i have no plan and i dont want one; my {goal} will sort itself out{h}{e}",
    "{f}plans are for other people. i am {who} and {goal} can wait{h}{e}",
    "{f}my {goal} might be average but i have seen worse, so no worries{h}{e}",
    "{f}i am {who}; they say i need to fix {goal} but i disagree completely{h}{e}",
    "{f}dont lecture me about {goal}, i have heard it all before and nothing changed{h}{e}",
    "{f}as {who}, i would rather do anything else than think about {goal}{h}{e}",
    "{f}goals are nice for others; i am {who} and mine can stay as they are{h}{e}",
    "{f}i tried thinking about {goal} once and it felt pointless, so i stopped{h}{e}",
    "{f}my {goal} is what it is. i am not the kind of person who changes{h}{e}",
    "{f}i am {who} and i refuse to stress about {goal} like everyone else does{h}{e}",
    "{f}why fix what is not broken? my {goal} is not broken{h}{e}",
]

# ================================================== contemplation ========
# Aware, ambivalent, thinking about change within ~6 months. Cue words like
# "change", "started" appear but in tentative/negated frames.
CON_T = [
    "{f}i am {who} and lately i have been wondering if i should do something about {goal}{h}{e}",
    "{f}sometimes i think about improving {goal}, but then i also feel it may be too late{h}{e}",
    "{f}as {who}, i know my {goal} needs work, but i am not sure where to begin{h}{e}",
    "{f}i keep going back and forth on whether to take {goal} seriously{h}{e}",
    "{f}part of me wants to fix {goal}, part of me just wants to leave it alone{h}{e}",
    "{f}i am {who}; people around me are changing and i wonder if i should too{h}{e}",
    "{f}maybe in the next few months i should start working on {goal}, not sure though{h}{e}",
    "{f}i think about {goal} a lot these days but i have not actually done anything about it{h}{e}",
    "{f}as {who}, i can see {goal} is becoming a problem, yet i keep postponing it{h}{e}",
    "{f}my friend started working on their goals and it made me think about {goal}{h}{e}",
    "{f}i am {who} and i am torn: {goal} matters, but changing feels scary{h}{e}",
    "{f}if i am honest, {goal} worries me, but i dont know if i am ready to act{h}{e}",
    "{f}i have been reading about how to improve {goal} but only reading, nothing more{h}{e}",
    "{f}as {who}, i wonder what my life would look like if i fixed {goal}{h}{e}",
    "{f}change sounds nice for {goal} but i am not convinced i can actually do it{h}{e}",
    "{f}i am {who}; everyone says i should start, and maybe they are right, maybe not{h}{e}",
    "{f}i dream about {goal} getting better but i wake up and do nothing{h}{e}",
    "{f}as {who}, i have started noticing how much {goal} affects my daily life{h}{e}",
    "{f}nothing has changed yet, but i cannot stop thinking that something should{h}{e}",
    "{f}i am {who} and i keep asking myself whether {goal} is worth the effort{h}{e}",
    "{f}some days i feel motivated about {goal}, other days i dont care at all{h}{e}",
    "{f}as {who}, i am weighing the pros and cons of working on {goal}{h}{e}",
    "{f}i want {goal} to improve but the thought of the effort involved puts me off{h}{e}",
    "{f}i am {who}; i am aware {goal} is slipping and i feel guilty about it{h}{e}",
]

# ================================================== preparation =========
# Intends to act soon, taking small steps: planning, researching, gathering
# resources, setting dates. Anti-cues: mentions of "not yet started" big action.
PRP_T = [
    "{f}i am {who} and i have decided to work on {goal} starting next month{h}{e}",
    "{f}i am preparing a study plan for {goal}; i will begin properly this week{h}{e}",
    "{f}as {who}, i have started collecting notes and resources for {goal}{h}{e}",
    "{f}i joined a small study group yesterday to help with {goal}{h}{e}",
    "{f}i am {who}; i bought the books i need for {goal} and set a start date{h}{e}",
    "{f}i have told my family that from Monday i am seriously working on {goal}{h}{e}",
    "{f}as {who}, i downloaded a timetable app and blocked one hour daily for {goal}{h}{e}",
    "{f}i spoke to a mentor about {goal} and we sketched a rough plan{h}{e}",
    "{f}i am {who} and i have enrolled in a short course related to {goal}{h}{e}",
    "{f}small steps first: i cleaned my study desk and made a checklist for {goal}{h}{e}",
    "{f}as {who}, i am researching the best way to improve {goal} before i begin{h}{e}",
    "{f}i have not started the real work yet, but i have a clear plan for {goal} now{h}{e}",
    "{f}i am {who}; i set a goal to begin {goal} work next week and told my friend{h}{e}",
    "{f}i visited the library today to find material for {goal}{h}{e}",
    "{f}as {who}, i have made a list of everything i need to change about {goal}{h}{e}",
    "{f}i tried one practice set for {goal} yesterday just to test the waters{h}{e}",
    "{f}i am {who} and i have asked my teacher for guidance on {goal}{h}{e}",
    "{f}i made a 30-day challenge sheet for {goal}; day one starts tomorrow{h}{e}",
    "{f}as {who}, i have cut down distractions so i can focus on {goal} soon{h}{e}",
    "{f}i signed up for a free trial class related to {goal} to see if it suits me{h}{e}",
    "{f}i am {who}; my plan for {goal} is written down and pinned on my wall{h}{e}",
    "{f}i have been watching videos about {goal} and taking notes, starting practice soon{h}{e}",
    "{f}as {who}, i arranged my schedule so that {goal} gets priority from next week{h}{e}",
    "{f}i did a small mock test for {goal} to find my weak areas before the real prep{h}{e}",
]

# ================================================== action ================
# Actively changing behaviour now: present-tense doing, recent start, effort,
# visible behaviour change. Includes setback mentions to stay realistic.
ACT_T = [
    "{f}i am {who} and i have been working on {goal} every day for the past two weeks{h}{e}",
    "{f}i started my new routine for {goal} last Monday and i am sticking to it{h}{e}",
    "{f}as {who}, i now spend two hours daily on {goal}, no excuses{h}{e}",
    "{f}i changed my habits: {goal} gets my mornings now and i can feel the difference{h}{e}",
    "{f}i am {who}; for the last month i have been actively improving {goal}{h}{e}",
    "{f}i finally took action on {goal} and joined evening classes last week{h}{e}",
    "{f}as {who}, i am doing practice problems for {goal} every single night{h}{e}",
    "{f}it has been three weeks since i started, and {goal} is slowly getting better{h}{e}",
    "{f}i am {who} and i quit my old lazy routine; {goal} is my focus now{h}{e}",
    "{f}i am in the middle of changing things: {goal} takes up most of my free time{h}{e}",
    "{f}as {who}, i track my {goal} progress in a diary and review it weekly{h}{e}",
    "{f}i started waking up at 6am to work on {goal} and it is actually happening{h}{e}",
    "{f}i am {who}; i asked for extra assignments related to {goal} and i am doing them{h}{e}",
    "{f}my {goal} routine is new but real: two weeks in and i have not missed a day{h}{e}",
    "{f}as {who}, i am learning new techniques for {goal} and applying them daily{h}{e}",
    "{f}i reduced my phone time to one hour so i can work on {goal} properly{h}{e}",
    "{f}i am {who} and i have already finished the first unit of my {goal} plan{h}{e}",
    "{f}it is hard but i am doing it: {goal} practice every morning before college{h}{e}",
    "{f}as {who}, i switched my weekend plans to focus on {goal}{h}{e}",
    "{f}i slipped once last week but got back on track with {goal} the next day{h}{e}",
    "{f}i am {who}; my {goal} scores in the last mock were better than before{h}{e}",
    "{f}i am actively rewriting my notes for {goal} every evening now{h}{e}",
    "{f}as {who}, i practise {goal} with a friend and we keep each other accountable{h}{e}",
    "{f}four weeks into my new {goal} habit and i can see real progress{h}{e}",
]

# ================================================== maintenance ==========
# Sustaining change, preventing relapse: long duration, systems, identity
# shift, helping others, vigilance about slipping back.
MNT_T = [
    "{f}i am {who} and i have kept up my {goal} routine for over six months now{h}{e}",
    "{f}it has been a year since i turned {goal} around, and i am not going back{h}{e}",
    "{f}as {who}, {goal} is just part of who i am now; i do it without thinking{h}{e}",
    "{f}i built systems so {goal} stays on track even on my busiest days{h}{e}",
    "{f}i am {who}; old habits around {goal} sometimes tempt me but i catch myself{h}{e}",
    "{f}six months of consistent {goal} work; my only goal now is to not slip{h}{e}",
    "{f}as {who}, i now mentor juniors on {goal} because i have been through it{h}{e}",
    "{f}i have maintained my {goal} progress for months by keeping the same routine{h}{e}",
    "{f}i am {who} and {goal} improvement stuck because i made it a daily non-negotiable{h}{e}",
    "{f}whenever i feel like skipping {goal} work, i remember how far i have come{h}{e}",
    "{f}as {who}, i review my {goal} habits monthly to make sure nothing is slipping{h}{e}",
    "{f}it has become automatic: {goal} is simply what i do every day now{h}{e}",
    "{f}i am {who}; i survived exam season without dropping my {goal} routine{h}{e}",
    "{f}my {goal} is stable now; i focus on protecting the progress i made{h}{e}",
    "{f}as {who}, i have a relapse plan for {goal}: if i miss two days, i restart small{h}{e}",
    "{f}eight months in and {goal} feels like second nature to me{h}{e}",
    "{f}i am {who} and i still do weekly check-ins on {goal} to stay honest{h}{e}",
    "{f}people ask me how i fixed {goal}; i tell them consistency, one day at a time{h}{e}",
    "{f}as {who}, my {goal} streak is 200 days and i intend to keep it alive{h}{e}",
    "{f}i moved past the hard part; now {goal} maintenance is just my lifestyle{h}{e}",
    "{f}i am {who}; even during festivals and travel i kept my {goal} habit going{h}{e}",
    "{f}the change in {goal} is permanent now; i protect it like any valuable thing{h}{e}",
    "{f}as {who}, i notice early warning signs when {goal} starts slipping and i act fast{h}{e}",
    "{f}one year of {goal} discipline behind me; the next year is about sustaining it{h}{e}",
]

TEMPLATES = {
    "precontemplation": PRE_T,
    "contemplation": CON_T,
    "preparation": PRP_T,
    "action": ACT_T,
    "maintenance": MNT_T,
}

# Template-level holdout: templates whose index % 5 == 0 are NEVER used in
# training — they generate the test set only. This measures generalization to
# unseen phrasings instead of template memorization. Same for BORDERLINE.
TEST_MOD = 5


def is_test_template(idx):
    return idx % TEST_MOD == 0


# ---------------- borderline / ambiguous cases ---------------------------
# Each entry: (label, text template, why-it-is-ambiguous).
# Ambiguity introduced by: mixing cues from adjacent stages, negated cues,
# short/garbled responses, time references near stage boundaries, and
# emotional statements that straddle readiness.
BORDERLINE = [
    ("contemplation",
     "i am {who}; i bought books for {goal} last month but i have not opened them, not sure if i really want this",
     "preparation cue (bought books) negated -> contemplation"),
    ("preparation",
     "as {who}, i keep thinking about {goal} and i finally wrote down a start date for next week",
     "contemplation rumination + concrete date -> preparation"),
    ("contemplation",
     "i started a new routine for {goal} twice but quit both times; maybe i will try again someday",
     "action cue (started) + relapse + vague timing -> contemplation"),
    ("action",
     "i am {who}; i began working on {goal} three days ago and i am trying to keep it going",
     "very early action, fragile -> still action"),
    ("maintenance",
     "i am {who}; four months into my {goal} routine now, mostly worried about keeping it up during exams",
     "action duration stretching toward maintenance; vigilance -> maintenance"),
    ("precontemplation",
     "i am {who} and my {goal} is fine; my friend thinks i need help but that is their problem",
     "external pressure explicitly rejected -> precontemplation"),
    ("contemplation",
     "honestly {goal} scares me because i know i am falling behind, but i dont know what to do about it",
     "awareness + fear, no intent -> contemplation"),
    ("preparation",
     "i have a plan for {goal} and i told two friends, just waiting for this week to end before i begin",
     "clear intent + public commitment, not yet acting -> preparation"),
    ("action",
     "i am {who}; {goal} work started this month, already missed a few days but i am still in it",
     "active with lapses -> action"),
    ("maintenance",
     "i am {who}; {goal} used to be a struggle, now it is just my routine, i barely think about it",
     "automaticity, identity shift -> maintenance"),
    ("precontemplation",
     "everyone has goals; mine for {goal} is to be left alone about it",
     "uses 'goals' but rejects change -> precontemplation (anti-cue)"),
    ("contemplation",
     "i downloaded three apps for {goal} and deleted two; the third one is still there, untouched",
     "preparation-like acquisition, zero engagement -> contemplation"),
    ("preparation",
     "as {who}, i am not practising {goal} yet, but my timetable, books and mentor are all ready",
     "explicit 'not yet' + full setup -> preparation"),
    ("action",
     "week two of my {goal} plan; hard but happening",
     "very short, minimal cues -> action"),
    ("maintenance",
     "i am {who}; i slipped on {goal} for a week last month and climbed back; the system held",
     "relapse survived via systems -> maintenance"),
    ("contemplation",
     "{goal}?? i dont know. maybe. whatever happens happens.",
     "short, ambivalent, garbled -> contemplation"),
    ("precontemplation",
     "nah, {goal} is not for people like me",
     "identity rejection, very short -> precontemplation"),
    ("preparation",
     "starting {goal} prep on the 1st. this time for real. i have told everyone.",
     "date + public commitment -> preparation"),
    ("action",
     "i am doing it. {goal}. every day. tired but doing it.",
     "short, present-tense doing -> action"),
    ("maintenance",
     "{goal} is handled. has been for a year. moving on to bigger things.",
     "sustained, looking beyond -> maintenance"),
    ("contemplation",
     "i am {who}; part of me signed up for a {goal} workshop, part of me hopes it gets cancelled",
     "ambivalence with a preparation cue -> contemplation"),
    ("preparation",
     "i keep failing at {goal} so this time i made a proper step-by-step plan first",
     "past action failures + current planning -> preparation"),
    ("precontemplation",
     "i am {who}; i know exactly what is wrong with my {goal} and i still dont care",
     "awareness without any intent -> precontemplation (awareness is not readiness)"),
    ("maintenance",
     "as {who}, i now teach {goal} to others; keeping my own practice sharp is the easy part",
     "teaching others, sustained -> maintenance"),
    ("action",
     "i am {who}; day 10 of the {goal} challenge, no zero days so far",
     "early, counting days -> action"),
]

# Short garbled / noisy real-world style answers, labeled by intent reading
NOISY = [
    ("precontemplation", "no"),
    ("precontemplation", "not interested"),
    ("precontemplation", "skip"),
    ("precontemplation", "idk dont care"),
    ("precontemplation", "leave me alone"),
    ("contemplation", "idk maybe"),
    ("contemplation", "thinking"),
    ("contemplation", "not sure"),
    ("contemplation", "maybe later"),
    ("contemplation", "confused"),
    ("preparation", "planning"),
    ("preparation", "starting soon"),
    ("preparation", "getting ready"),
    ("preparation", "will start monday"),
    ("preparation", "making a plan"),
    ("action", "started"),
    ("action", "doing it"),
    ("action", "in progress"),
    ("action", "working on it"),
    ("action", "day 5"),
    ("maintenance", "going strong"),
    ("maintenance", "still at it"),
    ("maintenance", "keeping it up"),
    ("maintenance", "habit now"),
    ("maintenance", "one year done"),
]


def render(template, cat):
    who, goal = sample_persona(cat)
    text = template.format(f=random.choice(FILLERS), h=random.choice(HEDGES),
                           e=random.choice(ENDERS), who=who, goal=goal)
    text = text.replace("  ", " ").strip()
    # grammar repair: templates use "my {goal}" but many goals are verb phrases
    # ("switching from sales...") or already start with "my " ("my maths marks").
    text = text.replace("my " + goal, goal)
    text = text.replace("My " + goal, goal[0].upper() + goal[1:])
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def main():
    cats = list(PERSONAS.keys())
    counts = {label: 0 for label in LABELS}
    train_counts = {label: 0 for label in LABELS}
    test_counts = {label: 0 for label in LABELS}
    train_ex, test_ex = [], []
    seen = set()

    def add(label, text, bucket):
        key = (label, text.strip().lower())
        if key in seen:
            return False
        seen.add(key)
        (train_ex if bucket == "train" else test_ex).append(
            {"text": text.strip(), "label": label})
        (train_counts if bucket == "train" else test_counts)[label] += 1
        counts[label] += 1
        return True

    TARGET_PER_CLASS = 700  # from templates; borderline/noisy add more on top
    attempts = 0
    while any(counts[l] < TARGET_PER_CLASS for l in LABELS) and attempts < 60000:
        attempts += 1
        label = random.choice(LABELS)
        if counts[label] >= TARGET_PER_CLASS:
            continue
        cat = random.choice(cats)
        tidx = random.randrange(len(TEMPLATES[label]))
        bucket = "test" if is_test_template(tidx) else "train"
        add(label, render(TEMPLATES[label][tidx], cat), bucket)

    # borderline cases: repeat each with fresh persona draws so counts grow
    for _ in range(6):
        for bidx, (label, template, _why) in enumerate(BORDERLINE):
            cat = random.choice(cats)
            add(label, render(template, cat),
                "test" if is_test_template(bidx) else "train")

    # noisy short answers (each a few times, they are already short).
    # Each unique (label, text) lands in exactly one bucket via coin flip so
    # the test set contains unseen surface forms too.
    for _ in range(8):
        for label, text in NOISY:
            add(label, text, random.choice(["train", "train", "train", "test"]))

    random.shuffle(train_ex)
    random.shuffle(test_ex)
    examples = train_ex + test_ex
    random.shuffle(examples)

    def write(name, rows):
        out = os.path.join(HERE, name)
        with open(out, "w", encoding="utf-8") as f:
            for ex in rows:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        return out

    write("data.jsonl", examples)
    write("data_train.jsonl", train_ex)
    write("data_test.jsonl", test_ex)

    log = f"""# Generation log — readiness classifier synthetic data (v1)

Generated: 2026-10-15 (seed=42, deterministic). Script: `generate_data.py`.

## Totals
- Total examples: {len(examples)} (train={len(train_ex)}, test={len(test_ex)})
- Per-class counts (total):
{chr(10).join(f"  - {l}: {counts[l]}" for l in LABELS)}
- Train per-class: {train_counts}
- Test per-class: {test_counts}

## Split methodology (template-level holdout)
- A random 80/20 row split would leak: the SAME template skeleton appears in
  both train and test with only slot words swapped, so 100% test accuracy would
  measure template memorization, not understanding (this was observed: 1.0000
  accuracy on a row-level split).
- Instead, templates are held out at the TEMPLATE level: for each class, template
  indices with `idx % 5 == 0` (5 of 24, ~21%) generate ONLY test examples; the
  remaining 19 generate ONLY train examples. Same rule for the 25 BORDERLINE
  templates (5 held out). Each noisy short answer is assigned wholly to train or
  test by coin flip (3:1) so identical surface strings never appear in both.
- The test set therefore contains phrasing patterns the model has never seen —
  a much more honest estimate of generalization within the synthetic
  distribution. `train.py` fits on `data_train.jsonl` only; `evaluate.py` scores
  on `data_test.jsonl` only. `data.jsonl` is the union (kept for reference).

## Templates
- 24 templates per class x 5 classes = 120 main templates (see `generate_data.py`,
  lists PRE_T / CON_T / PRP_T / ACT_T / MNT_T).
- Each template has slots: `{{f}}` (10 filler openers), `{{who}}`/`{{goal}}`
  (38 personas across 4 categories), `{{h}}` (7 hedges), `{{e}}` (6 enders).
- Personas: school (10, classes 6-12 + boards/JEE/NEET), college (10, B.Tech/BCA/B.Sc/MCA,
  CGPA/backlogs/placements/DSA), career switchers (8), small-business aspirants (8).
- ~700 examples per class drawn from templates; exact-duplicate (label+text) pairs
  rejected.

## How ambiguity was introduced
1. **25 hand-written borderline templates** (`BORDERLINE`), each generated 6x with
   fresh persona draws (~{25*6} examples). Each carries a "why" note: negated
   preparation cues (bought books, never opened), ambivalence with action cues
   (signed up for workshop but hopes it is cancelled), short/garbled answers,
   awareness-without-intent (precontemplation, not contemplation), relapse
   survived by systems (maintenance), time boundaries (4 months: action vs
   maintenance — labeled by vigilance-about-relapse).
2. **25 noisy one-to-three-word answers** (`NOISY`: "idk maybe", "starting soon",
   "day 5", "habit now", ...) each repeated 8x (~200 examples) — mimics terse
   onboarding replies.
3. **Anti-cue templates inside classes**: e.g. precontemplation examples that use
   the words "plan"/"goal" while rejecting change ("i have no plan and i dont
   want one"), and contemplation examples containing "started"/"change" in
   tentative or negated frames ("nothing has changed yet, but..."). This is meant
   to stop the model from keying on single cue words — though on purely synthetic
   data the model can still memorize template skeletons (see eval_report.md).

## Known limitations of this data
- All examples are synthetic: vocabulary, grammar patterns and class boundaries
  come from the template author's head, not from real learners.
- Real onboarding text will have typos, Hinglish/code-mixing, and messier
  reasoning than this data — expect a real-world accuracy drop.
- Borderline labels reflect the author's judgment of TTM stage boundaries;
  a human rater study was not done.
"""
    with open(os.path.join(HERE, "generation_log.md"), "w", encoding="utf-8") as f:
        f.write(log)
    print(f"Wrote {len(examples)} examples total "
          f"(train={len(train_ex)}, test={len(test_ex)})")
    print("train per-class:", train_counts)
    print("test per-class:", test_counts)


if __name__ == "__main__":
    main()
