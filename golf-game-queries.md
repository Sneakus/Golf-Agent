# Set G: Range game

Queries for the golf range game on jonesai.dev. The game names every shot from a 15-name grid (start direction by curve) plus strike faults, and it knows the true cause of every shot it simulates. Each query here describes one of those shots in a golfer's voice, so every query has a known correct answer.

Set G is a held-out retrieval test. It was not used to tune the system. No answers are generated from it for the game, and the game does not use Golf Agent's answers. The game reads the knowledge base directly (see `export_knowledge_base.py`), because it already knows the true cause of every shot.

Draw, fade, straight and air shot are left out. The game handles those with its own text.

## How the set is built

- 17 shot names times 3 club groups, 51 queries.
- Each query describes only what the golfer would see and feel, never the shot name. It names one club from its group.
- Golfer is right-handed. Left means left of the target line.
- Woods are hit off a tee.

| Club group | Clubs | Subset heading |
|---|---|---|
| Woods | driver, 3-wood, off a tee | A1 |
| Irons | 5-hybrid, 5-iron, 7-iron, 9-iron | A2 |
| Wedges | pitching wedge, sand wedge | A3 |

**Why the headings say A1, A2 and A3.** `eval_harness.parse_evals` only reads subset headings of the form `## A<digit>`, and generate.py's answer-accuracy report breaks results down by A1, A2 and A3. Using those labels lets generate.py's eval mode and evaluate.py run this file unchanged, with the breakdown falling out by club group. In this file A1 means woods, A2 irons and A3 wedges. It has nothing to do with Set A's subsets.

**Expected entries by shot.**

| Shot | Expected entries |
|---|---|
| Pull-hook | F004, F005 |
| Pull-draw | F005, F004 |
| Pull | F005 |
| Pull-fade | F002 |
| Pull-slice | F002 |
| Hook | F004 |
| Slice | F001 |
| Push-hook | F004 |
| Push-draw | F004, F006 |
| Push | F006 |
| Push-fade | F003 |
| Push-slice | F003 |
| Heel | F013 |
| Toe | F014 |
| Fat | F007 (F007 or F015 for wedges) |
| Thin | F008 (F010 for wedges) |
| Topped | F009 (F010 for wedges) |

There are no abstention queries. Every query is a fault the corpus covers.

---

## A1: Woods

| # | Query | Shot | Expected |
|---|---|---|---|
| 1 | teed up the driver, ball took off left of the fairway and just kept turning left into the trees | Pull-hook | F004, F005 |
| 2 | 3 wood off the tee started out left of my line and curved gently a bit more left, ended in the left rough | Pull-draw | F005, F004 |
| 3 | driver went dead straight left from the moment it left the tee, no curve on it at all | Pull | F005 |
| 4 | drive started left of the fairway then curved softly back to the right and finished just left of centre | Pull-fade | F002 |
| 5 | 3 wood off the tee started left then bent hard right, finished way over in the right rough | Pull-slice | F002 |
| 6 | drive started straight down the middle of the fairway then turned over hard left and dived into the left trees | Hook | F004 |
| 7 | driver started on line then peeled off hard to the right and curved all the way into the trees on the right | Slice | F001 |
| 8 | 3 wood off the tee started well right of the fairway then whipped back left across it and finished in the left rough | Push-hook | F004 |
| 9 | drive started out to the right of the fairway and curved gently back left, finished on the right half of the fairway | Push-draw | F004, F006 |
| 10 | driver came off the tee straight right, no bend at all, just a straight line into the right rough | Push | F006 |
| 11 | 3 wood started right of the fairway and drifted a little further right in the air | Push-fade | F003 |
| 12 | driver started right and then curved hard further right, sailed out of bounds on the right | Push-slice | F003 |
| 13 | caught the driver off the heel, felt clunky, lost a good twenty yards and it slid off to the right | Heel | F013 |
| 14 | hit my 3 wood out near the toe, felt dead in my hands, came up short and turned a bit left | Toe | F014 |
| 15 | 3 wood off a low tee, the club hit the turf behind the ball first, took a scrape of grass and the ball went nowhere | Fat | F007 |
| 16 | driver came off low on the face with a sting in my hands, ball flew on a low line and never climbed | Thin | F008 |
| 17 | driver hit the top of the ball, it hopped off the tee and rolled along the ground about 50 yards | Topped | F009 |

## A2: Irons

| # | Query | Shot | Expected |
|---|---|---|---|
| 18 | 9 iron started left of the flag and then turned hard left, ended up way left of the green | Pull-hook | F004, F005 |
| 19 | 5 hybrid started a touch left of the pin and curved softly further left, missed the green on the left side | Pull-draw | F005, F004 |
| 20 | 7 iron flew straight left of the green, no curve whatsoever, started there and stayed there | Pull | F005 |
| 21 | 5 iron started left of the flag and floated gently back right, finished on the left side of the green | Pull-fade | F002 |
| 22 | my 7 iron started at the left bunker then curved a long way right and finished right of the green | Pull-slice | F002 |
| 23 | 5 hybrid started at the flag then dove hard left and ran away into the left rough | Hook | F004 |
| 24 | 9 iron came off the face on line with the pin then curved sharply right and missed the green right | Slice | F001 |
| 25 | 7 iron took off well right of the green then curved hard back left and finished left of the flag | Push-hook | F004 |
| 26 | 5 iron set off right of the pin and turned gently back left toward it, ended up just right of the hole | Push-draw | F004, F006 |
| 27 | 9 iron flew dead straight but right of the green the whole way, felt solid, never curved | Push | F006 |
| 28 | 5 hybrid started right of the green and slid a bit further right as it came down | Push-fade | F003 |
| 29 | 5 iron started right of target and kept bending harder right, ended in the trees right of the green | Push-slice | F003 |
| 30 | 7 iron came off the heel, jarring feel down near the shaft, ball came out weak and slid right | Heel | F013 |
| 31 | caught my 5 iron out on the toe, felt the club twist in my hands, ball dropped short and turned left | Toe | F014 |
| 32 | 7 iron hit the ground a few inches before the ball, big chunk of turf, ball only went half the distance | Fat | F007 |
| 33 | 9 iron met the ball with the bottom edge, shot out low and hot and ran through the back of the green | Thin | F008 |
| 34 | 5 hybrid caught the top half of the ball, it never got off the ground and scuttled 30 yards along the fairway | Topped | F009 |

## A3: Wedges

| # | Query | Shot | Expected |
|---|---|---|---|
| 35 | pitching wedge from 110 started left of the flag and kept turning left, finished well left of the green | Pull-hook | F004, F005 |
| 36 | sand wedge from 80 yards started left of the pin and drifted a little further left, just off the left edge | Pull-draw | F005, F004 |
| 37 | pitching wedge went straight left of the pin, no bend at all, straight into the left bunker | Pull | F005 |
| 38 | sand wedge started at the left edge of the green and moved gently right, finished pin high left of the hole | Pull-fade | F002 |
| 39 | pitching wedge started left of the green then curved right all the way across it, finished in the right rough | Pull-slice | F002 |
| 40 | full pitching wedge started straight at the pin and then turned sharply left, ended up off the left of the green | Hook | F004 |
| 41 | sand wedge started at the flag and curved a long way right, missed the green on the right | Slice | F001 |
| 42 | pitching wedge started right of the green then curved hard left and finished over on the left side of the flag | Push-hook | F004 |
| 43 | sand wedge started right of the pin and curled gently back left, finished a few feet right of it | Push-draw | F004, F006 |
| 44 | pitching wedge went straight right, no curve at all, finished in the bunker right of the green | Push | F006 |
| 45 | sand wedge from 70 yards started right of the flag and floated further right, ended on the right fringe | Push-fade | F003 |
| 46 | pitching wedge started right and curved hard further right, missed the green by twenty yards on the right | Push-slice | F003 |
| 47 | sand wedge caught on the heel, dead feel, came off weak and drifted right | Heel | F013 |
| 48 | pitching wedge struck out on the toe, felt weak in the hands, came up short and left | Toe | F014 |
| 49 | sand wedge from 50 yards dug into the ground behind the ball, it plopped forward about ten yards | Fat | F007, F015 |
| 50 | pitching wedge caught the ball on the leading edge, came out low with no spin and ran over the back of the green | Thin | F010 |
| 51 | sand wedge from 40 yards hit the top of the ball, it rolled along the ground and never got airborne | Topped | F010 |

---

## Retrieval check

Run on 2026-10-20 with `evaluate.py --k 7`, hybrid, alias_weighted, against golf-fault-corpus-v3.md and golf-out-of-scope-entries.md.

| Subset | n | hit@1 | hit@7 |
|---|---|---|---|
| A1: Woods | 17 | 0.24 | 0.53 |
| A2: Irons | 17 | 0.35 | 0.59 |
| A3: Wedges | 17 | 0.29 | 0.59 |
| **All** | **51** | **0.294** | **0.569** |

22 queries miss at k=7: 1, 2, 5, 6, 7, 8, 9, 10, 18, 19, 22, 24, 25, 26, 27, 35, 36, 40, 41, 42, 43, 44. Query 27 is also a false decline, with N001 ranked first ("felt solid").

Every miss is a start-direction or curve shot. Every strike-fault query (heel, toe, fat, thin, topped) hits. The misses mention a course feature (fairway, green, pin, flag, bunker, rough), which pulls S005, D005, S001, L002 and similar entries ahead of the F001 to F006 entries, whose aliases do not describe start line and curve this way. This is a retrieval gap, not a wording problem, so these queries were left as written. Generate.py can only diagnose from a retrieved entry, so these 22 cannot produce a matching answer until retrieval changes.

## Wording changes after the retrieval check

Four queries were reworded because a word read two ways in a left/right description. None of the four changed from miss to hit.

| # | Before | After | Reason |
|---|---|---|---|
| 6 | drive started right at the middle of the fairway... | drive started straight down the middle of the fairway... | "right at" reads as a direction |
| 18 | 9 iron came off left of the flag and turned hard left again... | 9 iron started left of the flag and then turned hard left... | "again" implied a second turn |
| 24 | 9 iron left the face on line with the pin... | 9 iron came off the face on line with the pin... | "left" used as a verb in a left/right query |
| 25 | ...then swung hard back left... | ...then curved hard back left... | "swung" reads as the golfer's swing |
