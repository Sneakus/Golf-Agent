# Eval Sets v2

Supersedes the v1 eval document. Set A is now populated with real golfer vocabulary sourced from forum discussion rather than written against the corpus.

| Set | Measures | Method |
|---|---|---|
| A: Retrieval | Does the right corpus entry come back for a plain-English query | Hand-labelled queries |
| B: Pattern detection | Does the tool spot multi-shot patterns correctly | Synthetic shot sequences |
| C: Shape capture | How accurate is tapped or drawn shape against measured reality | Range session with launch monitor |

---

# Set A: Retrieval

## Scoring, by subset

Score these separately. A single headline number hides the failures that matter.

| Subset | Queries | Answerable | Metric | Target | Achieved |
|---|---|---|---|---|---|
| A1: Own voice | 20 | 18 | Hit rate at k=5 | 0.85 | 0.94 |
| A2: Sourced vocabulary | 33 | 33 | Hit rate at k=5 | 0.80 | 0.97 |
| A3: Misdiagnosis | 8 | 8 | Hit rate at k=5 | 0.50 | 1.00 |
| A4: Abstention | 6 | 0 | Correct refusal rate | 0.90 | 1.00 |
| **Total** | **67** | **59** | | | |

A1 has 20 queries but 18 answerable, because queries 7 and 15 describe good shots and should return no fault. Those two are scored with the abstention set rather than the retrieval set. All 6 A4 queries are unanswerable by design.

**Why the misdiagnosis target is low.** These are queries where the golfer's own words point at the wrong cause. A system that simply echoes what the user said will score zero here while looking fine everywhere else. Half is a realistic bar and improving it is where the interesting engineering lives.

**If A2 scores much higher than A1**, suspect contamination. A1 is your own phrasing and should be the harder set, not the easier one.

---

## A1: Your own voice

Written by you before seeing the v2 corpus, so uncontaminated. These are closest to how you will actually log.

| # | Query | Expected |
|---|---|---|
| 1 | wedge made contact with the ground too early and lost all power | F007 |
| 2 | thinned lob wedge from side of green | F010 |
| 3 | driver slice way right | F001 |
| 4 | driver hooked low | F004 |
| 5 | topped driver | F009 |
| 6 | hooked 7i shot | F004 |
| 7 | slight draw on 7i shot | No fault |
| 8 | topped 3w from tee box, bobbled down the middle of the fairway | F009 |
| 9 | tried to chip onto the green with lob wedge but ended up massively underpowering it, only travelled 1 meter | F015 or D001 |
| 10 | tried 7i onto green but thinned it, bounced over the edge of the green | F008 |
| 11 | tried utility wedge onto green, the shot faded and didnt reach the green, wrong club choice | D003 primary, F001 secondary |
| 12 | tried bump and run with 8i, came out too hot and rolled over the back of the green | D002 |
| 13 | driver came out low and to the right | F008 and F001 or F003 |
| 14 | 3w shot where ball was beneath my feet ended up in a slice wide right | L001, not F001 |
| 15 | 5h shot perfectly straight down middle | No fault |
| 16 | underpowered putter and overcompensated for green sloping left | P001 and P004 |
| 17 | went to punch out ball from the rough underneath a tree, went well but slightly overpowered | R001 (see gap note) |
| 18 | ball in front of tree, chipped out right but thinned it, bounced along dry ground, rolled on cart path, rested in rough | F008 primary, S004 and C003 secondary, R001 |
| 19 | tried opening club face with lob wedge to chip onto a green up a slope, thinned and ended up in a sand bunker on other side | F010 |
| 20 | got out of bunker onto green with sand wedge, direction fine but left it quite short | D005 |

**Query 18.** R001 was added to the corpus after this query was labelled, and covers exactly this kind of recovery shot. Query 17 was already relabelled to R001 at the time; 18 was missed.

---

## A2: Direct queries, sourced vocabulary

Paraphrased from real forum posts. These use the outcome-and-feeling language golfers actually write in, rather than mechanism terms.

### Full swing

| # | Query | Expected |
|---|---|---|
| 21 | every drive is a banana ball straight into the trees on the right, doing my head in | F001 |
| 22 | ball starts left of target then curves miles right, no idea what that even is | F002 |
| 23 | my miss is a big duck hook that dives left, snap of death off the tee | F004 |
| 24 | ball flies dead right, doesnt curve, feels solid though | F006 |
| 25 | kept hitting it fat all day, taking huge divots behind the ball, chunky as anything | F007 |
| 26 | bladed a load of irons today, thin to win right, ball screaming low across the green | F008 |
| 27 | topped it off the tee and it dribbled about 40 yards, so embarrassing | F009 |
| 28 | kept topping my wedges, sometimes thinning them over the green, cant find the middle | F010 |
| 29 | hit the dreaded S-word twice today, ball shot sideways off the hosel into the trees | F011 |
| 30 | popped my driver straight up in the air, huge sky mark on the crown, went nowhere | F012 |
| 31 | catching it off the toe, feels dead and comes up short and weak | F014 |
| 32 | duffed my chip, club dug in and it moved about a foot, scared to chip now | F015 |
| 33 | thinned a little chip clean across the green like a scared rabbit | F016 |
| 34 | some go left some go right, cant predict it, two completely different misses in a round | F018 |

### Putting

| # | Query | Expected |
|---|---|---|
| 35 | left every putt short all day, kept leaving it on the front lip | P001 |
| 36 | kept blowing putts 4 feet past and missing the one back | P002 |
| 37 | read it to break left, it broke right, misread it completely | P003 |
| 38 | got the line right but the pace was so wrong the break never took | P004 |
| 39 | yanked a couple of short putts left, pushed one right, no idea which way theyre going | P005 |
| 40 | greens were lightning today, three-putted loads, never got the speed all round | P006 |

### Distance, strategy and conditions

| # | Query | Expected |
|---|---|---|
| 41 | got scared over a little pitch and decelerated, left it well short | D001 |
| 42 | took a 7 iron thinking it was enough, came up a club short of the green | D003 |
| 43 | clubbed up to be safe and flew the green into trouble long | D004 |
| 44 | left it in the trap, played it too safe and it barely came out | D005 |
| 45 | missed the green on the wrong side with the pin right by the edge, no green to work with | S001 |
| 46 | went straight at a pin tucked behind the bunker and paid for it | S002 |
| 47 | tried to hit the miracle shot through a tiny gap instead of chipping out, made a mess | S003 and R001 |
| 48 | ball was on the cart path, didnt take my drop, tried to hit it and it went awful | S004 |
| 49 | was freezing out there, striped a drive and it went nowhere, ball not going anywhere in the cold | C001 |
| 50 | into a strong wind my iron ballooned up and dropped way short | C002 |
| 51 | greens were rock hard and fast, everything released and ran off the back | C003 |
| 52 | course was soaking, everything plugged and no roll at all | C004 |
| 53 | punched out of the trees after a wild drive, caught a branch and it went backwards | R001 |

---

## A3: Misdiagnosis subset

The golfer's own words point at the wrong cause. The system should return the correct entry rather than following the user's assumption. Score these separately.

| # | Query | User assumes | Correct entry |
|---|---|---|---|
| 54 | keeps starting way right and then slicing even further right, weak little fade thing | Slice (F001) | F003 push-slice |
| 55 | everything just goes dead straight left, no curve, cant work out why | Hook (F004) | F005 pull |
| 56 | striking irons off the heel, feels like a near shank every time | Shank (F011) | F013 heel strike |
| 57 | ball was below my feet and I kept topping it and shanking it, nightmare lie | Swing fault | L001 |
| 58 | ball above my feet, I keep pulling it left and chunking, cant strike it clean | Swing fault | L002 |
| 59 | downhill slope, kept thinning it and it shot off low right | Thin (F008) | L004 |
| 60 | ball was sitting up nice in the rough, flushed it and it flew miles over the green | Over-clubbed (D004) | L006 flyer lie |
| 61 | flushed a 7 iron but it came out weak and high and dropped way short | Swing fault (F017) | F017 or L006, both acceptable |

---

## A4: Abstention subset

The corpus genuinely cannot answer these. Correct behaviour is declining rather than returning the nearest match.

| # | Query | Why out of scope |
|---|---|---|
| 62 | should I be playing stiff or regular shafts as a beginner, or get fitted first | Equipment and fitting |
| 63 | my mate lost his tee shot near the OB, does he go back to the tee or drop where it went out | Rules procedure |
| 64 | lower back is killing me after every round, is it my swing or just my body | Injury, framed as a swing question |
| 65 | first medal on Saturday and Im bricking it about the first tee, how do I calm the nerves | Mental game |
| 66 | can someone explain how the WHS handicap works, best 8 of 20 and all that | Handicap system |
| 67 | group in front are painfully slow, am I allowed to ask to play through | Etiquette |

**Queries 63 and 64 are the calibration cases.** 63 sits next to S004, which is rules-adjacent and in scope, so the boundary is fine. 64 is framed as a swing question but is actually about injury, and following that framing would be genuinely harmful advice.

---

## Corpus gap identified

**R001 recovery and punch-out does not exist yet.** Queries 17, 47 and 53 all point at it, and it is a high-frequency topic in real discussion. The entry needs to cover deliberate recovery shots where success is measured by position rather than distance, plus the decision of whether to attempt the recovery at all.

Write this entry before running the eval, or three queries will fail for a reason that has nothing to do with retrieval quality.

---

# Set B: Pattern detection

Unchanged from v1. Tests whether the tool spots multi-shot patterns from logged sequences rather than text queries.

| # | Sequence | Expected flag | Should NOT flag |
|---|---|---|---|
| 1 | Hook, block right, hook, block right | Two-way miss (F018) | Separate hook and push problems |
| 2 | Fat, thin, fat, thin | Fat-thin loop, low point control | Two unrelated contact faults |
| 3 | Five approach shots all short, temperature logged at 4 degrees | Conditions (C001) | Distance loss as swing fault |
| 4 | Every putt short across 18 holes | Green speed (P006) | Eighteen P001 records |
| 5 | Three slices, all with stance logged ball below feet | Lie effect (L001) | Slice pattern |
| 6 | Three slices from flat lies | Genuine slice pattern (F001) | Nothing suppressed |
| 7 | Six shots with 7-iron, four missed right | Club-specific pattern | General directional fault |
| 8 | Shanks appearing two rounds after a logged grip change | Fix-induced compensation | New unrelated fault |
| 9 | Short-sided on three holes, then poor recovery each time | Strategy flag on the approach shot | Short game fault |
| 10 | Two bad shots after a fix applied, sample size 2 | Nothing, below threshold | Fix declared failed |

**Scoring**

| Metric | Target | Actual |
|---|---|---|
| Correct pattern identification | | |
| False positive rate | | |
| Suppression accuracy | | |
| Threshold discipline | | |

False positives matter more than misses. A tool that invents patterns sends you chasing faults that do not exist.

---

# Set C: Shape capture accuracy

Unchanged from v1. Range session with launch monitor, validating the input rather than the retrieval.

**Protocol:** hit a shot, look away before the numbers appear, tap the preset and separately draw the freehand trace, then record measured face angle, club path, face-to-path and offline distance. At least 30 shots across several clubs, including deliberately poor strikes.

**Measure:** preset accuracy, direction bias, freehand versus preset, curvature magnitude error, derived face angle error, derived path error.

The direction bias number is the interesting one personally. Most golfers report their shots as straighter than they were, and knowing your own bias lets the tool correct for it.

---

---

# Set D: Generation

Retrieval finds entries. Generation turns them into one piece of advice. Scored separately, because a good answer from bad retrieval and a bad answer from good retrieval are different problems.

## What is enforced, and how

| Rule | Enforcement | Why not just ask the model |
|---|---|---|
| Refuse when out of scope | Decided in code before the model is called | A model given a question and vaguely related documents will find something to say. Removing the opportunity is more reliable than instructing against it. |
| One swing thought | Schema has a single `swing_thought` field | Nowhere to put a second swing instruction |
| Setup does not count as a swing thought | Setup is a separate list limited to pre-address actions | Aim, ball position, stance, gripping down and club choice do not compete for attention during the swing |
| Per-field and total word limits | Programmatic checks on every field, plus a 140-word backstop | Prompt instructions alone are not a guarantee |
| No mechanical jargon | Banned-term list checked across every text field, plus plain-language substitutions in the prompt | Same |
| Plain punctuation | Every text field rejects em dashes and en dashes | Keeps output ready for direct display |
| Every claim cited | All citations and field-level source IDs are validated against retrieval | Catches a hallucinated entry ID rather than letting it pass |
| Setup step matches its line | Each step carries `entry_id` and `fix_index`, and must share meaningful words with that specific Fixes or Adjustments line | A retrieved ID can still be attached to another entry's wording. Lines that only point elsewhere are not selectable |
| Follow-up is code | "If it keeps happening" is the differential table's test text, shown only when a confusable was retrieved. Rows apply in both directions | The model no longer writes this field, so it cannot satisfy two rules at once |
| Sources are code | Built from every entry ID the answer used | The model does not invent the citation list |
| Fit was removed | The model used to report clear, ambiguous, or none | It never fired in testing, including on the two known retrieval misses, so the model's own judgement of fit is not relied on. Retrieval-side miss signals are being evaluated instead |
| Key thought for decisions | S and C entries label the headline Key thought | A strategy or conditions cue is not a swing cue |
| Follow-up diagnosis is grounded | Differential rows are parsed from corpus notes at runtime, with compensation risk as fallback | Keeps uncertainty useful without indexing the notes |

Failures trigger one repair attempt with the specific problems fed back, then revalidation.

## Richer answer format baseline, 23 Sep 2026

This is a new baseline, not a continuation of the earlier generation results. The output shape changed, so its length, repair and cost numbers are not directly comparable.

| Date | Change | Correct refusals | False refusals | Validation failures | Repaired | Words | Setup steps | Tokens and cost | Verification |
|---|---|---|---|---|---|---|---|---|---|
| 23 Sep 2026 | New answer format baseline | 8/8 | 0 | 0 after repair | 18/59 on first attempt | 68.6 average, 98 maximum | 39/59 answers | 293,324 input, 20,385 output, about $1.20 per full run | Full generation eval |
| 23 Sep 2026 | L001 corpus fixes from reading generated answers | | | | | | | | Ambiguous posture wording produced "stay tall", the opposite of the correct cue. An overstated loft explanation claimed a 3-wood had extra loft. Both were fixed in L001. Retrieval remained hit@5 0.966. Posture was verified on both L001 queries and loft on the 3-wood query. Not a full generation rerun. |
| 24 Sep 2026 | Answer-level accuracy on the saved richer-answer run | | | | | | | | 55 of 59 (93%), 95% CI 0.864 to 0.983, as originally labelled. Of the 57 queries where retrieval placed the correct entry in the top five, the answer chose it in 55. After the query 18 correction, 56 of 59 (95%), 95% CI 0.881 to 1.000, which is 56 of those same 57. R001 was added to the corpus after query 18 was labelled and covers exactly this kind of recovery shot. Query 17 was already relabelled to R001 at the time; 18 was missed. This run predates the L001 fixes. Not a generation rerun. |

## Earlier answer format results, 7 Aug 2026

| Run | Answered | Correct refusals | False refusals | Validation failures |
|---|---|---|---|---|
| First pass | 56 | 8/8 | 3 | 12/56 |
| Prompt fixes: substitution table, harder length constraint | 56 | 8/8 | 3 | **0/56** |
| Threshold derived from data, 0.40 to 0.35 | 59 | 8/8 | **0** | 0/59 |

The twelve validation failures were six jargon and six over-length. Both cleared with better instructions, and the repair loop never fired, so it remains a safety net that currently costs nothing. Worth noting that giving the model a plain-language substitution for each banned term worked better than banning the terms alone.

## Choosing the refusal threshold

Swept every value from 0.20 to 0.60 against the eval set.

| Threshold | False refusals | Missed refusals |
|---|---|---|
| 0.20 to 0.38 | 0 | 0 |
| 0.39 | 1 | 0 |
| 0.40 | 3 | 0 |
| 0.45 | 12 | 0 |
| 0.50 | 25 | 0 |

**Missed refusals are zero at every threshold.** Every out-of-scope query is caught by an X entry ranking first, independent of the similarity score. So the threshold contributes nothing to abstention, and at 0.40 its only measured effect was refusing three legitimate questions.

Set to 0.35: the highest zero-false-refusal value is 0.38, backed off for headroom, with the lowest genuine query at 0.388.

**The general point.** Retrieving a correct out-of-scope entry is a more reliable abstention mechanism than a similarity floor, because it makes refusal a retrieval result rather than a confidence judgment. The threshold remains a backstop for queries that are in scope but too vague for any entry to match, and it should almost never fire.

## Cost

142,011 input and 12,598 output tokens across 56 generations, roughly 2,500 input tokens per answer. The input is dominated by the five retrieved entries passed as context.

# Results log

Record every run with a date. The trend is more convincing than any single score, and this table is the artifact worth showing.

| Date | Change made | A1 | A2 | A3 | A4 | hit@1 | Notes |
|---|---|---|---|---|---|---|---|
| 7 Aug 2026 | Baseline. Whole-entry embedding, text-embedding-3-small, no reranking | 0.65 | 0.88 | 1.00 | 0.17 | 0.61 | Parser bug present, see below |
| 7 Aug 2026 | Fixed parser bug: R001 was absorbing the trailing notes sections, making it 8k chars against a 967 char mean | 0.78 | 0.91 | 1.00 | | 0.66 | Both R001 queries now retrieve |
| 7 Aug 2026 | Alias line repeated three times before full entry text | 0.83 | 0.91 | 1.00 | | 0.73 | Adopted. See strategy comparison below |
| | Add reranking | | | | | | |

| 7 Aug 2026 | Added 8 out-of-scope X entries so retrieval has something correct to return when a query is out of scope | 0.70 | 0.91 | 1.00 | 0.83 | 0.66 | Abstention solved without a similarity threshold. Zero false declines |
| 7 Aug 2026 | Adopted alias weighting, added N001 no-fault entry | 0.85 | 0.91 | 1.00 | 0.83 | 0.75 | Good-shot queries now resolve |
| 7 Aug 2026 | Hybrid retrieval: BM25 fused with dense via reciprocal rank fusion | 0.90 | 0.97 | 1.00 | 1.00 | 0.73 | hit@5 0.95. Fixed 4 queries, broke none |

| 7 Aug 2026 | Full metric set added: MRR, NDCG, recall@k, bootstrap CIs, latency and cost. Config unchanged | 0.89 | 0.97 | 1.00 | 1.00 | 0.73 | hit@5 0.949, MRR 0.823, NDCG@5 0.837, recall@5 0.910. Eval now gated in CI |
| 7 Aug 2026 | Extended F007 alias line with plain-language phrasings for hitting the ground before the ball | | | | | | Corpus fix, not a retrieval change. Query 1 was a vocabulary gap |
| 24 Sep 2026 | Query 18 label correction. No change to retrieval | 0.94 | 0.97 | 1.00 | 1.00 | 0.73 | Label change, not a system change. hit@5 stayed 0.966 and hit@1 stayed 0.729. recall@5 moved from 0.927 to 0.928, MRR from 0.827 to 0.828, and NDCG@5 from 0.844 to 0.846, because R001 was already retrieved and is now counted as relevant |
| 24 Sep 2026 | Review corpus fixes: F012 tee height split into a setup step, F009 ball-position fix scoped to wedges and short irons, C002 no longer says wind adds spin, L004 states why downhill contact is difficult | 0.94 | 0.97 | 1.00 | 1.00 | 0.73 | Wording fixes, found by reading answers. hit@5 0.966, hit@1 0.729 and recall@5 0.928 unchanged. MRR moved from 0.828 to 0.825 and NDCG@5 from 0.846 to 0.844. The same two queries still miss |
| 24 Sep 2026 | Differential tests rewritten in plain language with no entry codes | 0.94 | 0.97 | 1.00 | 1.00 | 0.73 | The table is not indexed. hit@5 0.966, hit@1 0.729, recall@5 0.928, MRR 0.825, NDCG@5 0.844, abstention 1.000. Nothing moved. Code now shows this text directly to the golfer |

**Strategy comparison, 7 Aug 2026.** Same 59 answerable queries, four ways of embedding the same corpus.

| Strategy | Avg chars | hit@1 | hit@5 | A1 | A2 | A3 |
|---|---|---|---|---|---|---|
| Whole entry | 839 | 0.66 | 0.88 | 0.78 | 0.91 | 1.00 |
| Alias line only | 90 | 0.68 | 0.88 | 0.83 | 0.91 | 0.88 |
| Name, alias and definition | 187 | 0.66 | 0.88 | 0.78 | 0.94 | 0.88 |
| **Alias weighted, then full entry** | 1080 | **0.73** | **0.90** | **0.83** | 0.91 | **1.00** |

**Why the winner wins.** Alias-only matches A1 on hit rate but drops A3 from 1.00 to 0.88, because the misdiagnosis queries need the situational detail in the body text to let a lie entry outrank a swing fault. Repeating the alias line keeps the vocabulary match without losing that discrimination.

**Caveat on precision.** 59 queries means one query is worth roughly 1.7 points, so differences of two or three queries are not significant. Alias weighting is the right choice on balance rather than a proven margin.

**Full metric set, 7 Aug 2026.** Hybrid retrieval with alias weighting, 59 answerable queries and 8 non-fault queries.

| Metric | Score | 95% CI | What it means |
|---|---|---|---|
| hit@1 | 0.729 | 0.610 to 0.831 | Right entry ranked first |
| hit@5 | 0.949 | 0.881 to 1.000 | Right entry in the top five |
| recall@5 | 0.910 | 0.842 to 0.966 | Share of relevant entries found |
| MRR | 0.823 | 0.742 to 0.898 | How high the first correct hit lands |
| NDCG@5 | 0.837 | 0.759 to 0.904 | Rank-weighted quality |
| Abstention | 1.000 | | 8 of 8 correctly declined, zero false declines |

**What MRR tells us that hit rate does not.** MRR of 0.823 sits close to hit@1 of 0.729, which means that when the correct entry is not ranked first it is almost always second. The ordering is nearly right rather than scattered, so reranking has limited headroom on a corpus this size. That matches the general finding that reranking adds little below roughly 5,000 documents.

**Confidence intervals are 95% percentile bootstrap over 10,000 resamples.** They are wide, because 59 queries is a small set. The information retrieval literature treats 50 queries as a working minimum and suggests roughly 150 for reliably distinguishing systems, so differences of two or three queries between configurations are not significant. The metric improvements recorded above are directional.

**Cost and latency.** Fusion adds 0.10 ms at p50 and 0.14 ms at p95, so retrieval itself is effectively free and the embedding API call dominates end-to-end latency. A full eval run embeds roughly 16,000 tokens at about $0.0003.

**Continuous integration.** The eval runs on every push that touches the corpus, the eval set or the retrieval code, and fails the build if recall@5 drops below 0.90. A corpus edit that breaks retrieval is caught rather than discovered later.

**Hybrid retrieval comparison, 7 Aug 2026.** Same corpus and queries, three retrieval methods.

| Mode | hit@1 | hit@5 | A1 | A2 | A3 | A4 |
|---|---|---|---|---|---|---|
| Dense embeddings only | **0.75** | 0.90 | 0.85 | 0.91 | 1.00 | 0.83 |
| BM25 keyword only | 0.61 | 0.93 | 0.90 | 0.94 | 1.00 | 1.00 |
| **Hybrid, RRF fusion** | 0.73 | **0.95** | **0.90** | **0.97** | 1.00 | **1.00** |

**BM25 alone beats dense embeddings on hit@5**, and wins on every subset. Dense retrieval averages meaning across a whole sentence, which washes out rare distinctive terms. "Hosel" in query 29 and "cart path" in query 48 are the diagnostic words in those queries, and both appear near-verbatim in the target entry's alias line, yet dense retrieval failed both in every run. BM25 scores rare terms highly by construction and caught both.

**Fusion method.** Reciprocal rank fusion, scoring each entry 1/(60 + rank) in each ranked list and summing. It uses only rank order, so cosine similarity and BM25 scores do not need normalising onto a common scale.

**The trade-off.** Hybrid gives up 0.02 on hit@1 against dense while gaining 0.05 on hit@5. At 59 queries that hit@1 difference is roughly one query and is not significant, but the direction is real: fusion finds more and ranks slightly less sharply. Reranking is the natural next step, since it operates on the fused candidate set and addresses exactly that weakness.

**A limitation of RRF, seen in query 24.** BM25 ranked the correct entry first, dense ranked it poorly, and fusion pushed it out of the top five entirely. Averaging ranks can bury an answer that one system is confident about. Worth testing weighted fusion, or guaranteeing each system's top result survives into the candidate set.

## Remaining misses after hybrid

| Query | Problem | Fix |
|---|---|---|
| 1, fat wedge | Corpus gap, not retrieval. F007's alias line has no plain-language phrasing for hitting the ground before the ball | Add aliases to F007 |
| 13, driver low and right | Six words, compound, genuinely ambiguous between three faults | May not be fixable |
| 24, dead right no curve | RRF buried a correct BM25 top-1 | Weighted fusion or candidate-set guarantee |

## Known failures not addressed by embedding strategy

| Problem | Queries | Why it fails | Candidate fix |
|---|---|---|---|
| Abstention | 62 to 67 | Similarity ranges overlap. Out of scope queries score 0.33 to 0.41; answerable ones that miss score 0.34 to 0.51. No threshold separates them. | A classifier step before retrieval, or a check for club and miss vocabulary |
| Good shots | 7, 15 | No corpus entry represents a shot that went fine, so retrieval returns noise | Add a no-fault entry, or detect and short-circuit before retrieval |
| Compound queries | 13, 18 | Several events in one query average into an unfocused vector | Split the query into clauses and retrieve per clause |

Record hit rate before and after reranking separately. The delta demonstrates you measured whether a component earned its place rather than adding it because it is standard.
