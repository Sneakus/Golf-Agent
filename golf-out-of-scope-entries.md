# Out-of-Scope Entries

Companion file to the fault corpus. These entries exist so retrieval has something correct to return when a query falls outside what the corpus can answer.

**How they work.** Embed these alongside the fault entries. If an X entry is the top result, the tool declines and says why, rather than serving the nearest swing fault. No similarity threshold required.

**The boundary to watch.** Several of these sit close to legitimate in-scope entries. Rules procedure is next to S004 relief not taken. Equipment is next to club selection in D003 and D004. Fitness is next to distance loss in F017. Watch those in the eval and tighten the wording if a legitimate query gets pulled across.

**Response wording.** When one of these wins, say what the tool does not cover and suggest where the answer lives. Do not attempt a partial answer from the fault corpus.

---

## X001 - Equipment and club fitting

**How I'd describe it:** what shafts should I use, stiff or regular, should I get fitted, what irons should I buy, is my driver loft wrong, new clubs, club fitting, shaft flex, grip size, which ball should I play

**What it is:** Questions about equipment choice, specification or fitting.

**Why it is out of scope:** This corpus diagnoses what happened to a shot you hit. It holds no data on your equipment specification and cannot tell whether a club suits you. Equipment problems and swing problems produce similar-looking misses, so guessing here would be actively misleading.

**Where the answer is:** A club fitting with a launch monitor.

---

## X002 - Rules and procedure

**How I'd describe it:** what do I do if, where do I drop, is this a penalty, how many strokes, lost ball procedure, out of bounds ruling, provisional ball, unplayable lie ruling, do I get relief, can I move my ball

**What it is:** Questions about the Rules of Golf and correct procedure.

**Why it is out of scope:** The corpus covers shot outcomes, not rulings. Note the deliberate boundary: S004 covers the coaching observation that you played from a spot where relief was available, which is a decision pattern. Working out the correct procedure for a lost ball is a different question and is not covered.

**Where the answer is:** The R&A Rules of Golf, or the official app.

---

## X003 - Handicap and scoring

**How I'd describe it:** how does the handicap system work, WHS, best 8 of 20, what will my handicap go to, Stableford points, how is my index calculated, do I get shots on this hole

**What it is:** Questions about handicapping, competition formats or scoring.

**Why it is out of scope:** Administrative rather than diagnostic. Nothing in the shot log informs it.

**Where the answer is:** Your club, or the WHS rules of handicapping.

---

## X004 - Mental game and pressure

**How I'd describe it:** first tee nerves, I get anxious over the ball, bricking it, choking under pressure, I fall apart on the back nine, how do I stay calm, lost my confidence, scared to hit driver

**What it is:** Questions about nerves, confidence, pressure or focus.

**Why it is out of scope:** Real and important, but a corpus of mechanical faults cannot address it, and offering a swing fix for a confidence problem sends you to work on the wrong thing entirely.

**Where the answer is:** A coach, or performance psychology material.

---

## X005 - Fitness, injury and pain

**How I'd describe it:** my back hurts after golf, sore wrists, elbow pain, is my swing hurting me, should I stretch, golf fitness, I cannot rotate properly, shoulder injury

**What it is:** Questions about pain, injury, physical limitation or conditioning.

**Why it is out of scope:** This is a medical question, not a swing diagnosis, and these are frequently framed as swing questions. Following that framing would produce advice that is at best useless and at worst harmful. Pain during or after golf is worth taking to a physiotherapist or doctor rather than a diagnostic tool.

**Where the answer is:** A physiotherapist, or a doctor.

---

## X006 - Etiquette and pace of play

**How I'd describe it:** can I play through, slow group in front, where should I stand, when do I shout fore, is it my turn, bunker raking, repairing pitch marks

**What it is:** Questions about etiquette, custom or pace of play.

**Why it is out of scope:** Social convention rather than shot diagnosis.

---

## X007 - Another player

**How I'd describe it:** my mate keeps slicing, my playing partner, my son is learning, how do I help someone else, my wife wants to start playing

**What it is:** A question about somebody else's golf.

**Why it is out of scope:** The corpus is built around your own logged shots and your own fix history. Diagnosing from a second-hand description, with no shot data behind it, is guesswork.

---

## X008 - Practice, lessons and general improvement

**How I'd describe it:** how often should I practice, should I get lessons, how do I get better, what should I work on, how long until I improve, is it worth going to the range

**What it is:** Broad questions about improvement that are not tied to a specific shot or fault.

**Why it is out of scope:** Too general to answer from a fault corpus. Once you have logged rounds, the pattern analysis can answer "what should I work on" from your own data, which is a different mechanism from retrieval.

---

# No-fault entries

Not out of scope, but not a fault either. These exist so retrieval has something correct to return when the shot went fine, instead of serving the nearest miss.

---

## N001 - Good shot, nothing to diagnose

**How I'd describe it:** straight down the middle, perfect, flushed it, pured it, exactly what I wanted, nailed it, best shot of the day, dead straight, slight draw as intended, nice fade, right at the flag, stiff to the pin, no complaints

**What it is:** A shot that did what you intended. Includes a deliberate shape that came off, since a fade you meant is not a miss.

**Why it needs an entry:** Without one, a query describing a good shot returns the nearest fault, and the tool invents a problem that is not there. Diagnosing a good shot is worse than saying nothing, because it teaches you to change something that is working.

**Correct response:** Log it and move on. No fix, no swing thought. If `intended_shape` was set and the shot matched it, that is worth recording as a success rather than a neutral event.

**Watch for:** A good outcome from a bad decision is still a bad decision. If the shot came off but the strategy flag fired, log the decision quality separately. See S003 and R001.
