# Club Table and Outcome Picker

Two reference documents. The club table seeds the distance logic; the picker is the UI contract that the corpus indexes against.

---

# Part 1: Club table

Seed from your Trackman numbers, then let logged on-course data override. On-course carry typically runs shorter than range carry, so expect these to drift down.

## Fields

| Field | Notes |
|---|---|
| `club_name` | As it appears in the picker |
| `club_type` | Driver, wood, hybrid, iron, wedge, putter |
| `loft` | Affects expected curvature per degree of face-to-path |
| `baseline_carry` | Seeded from range data |
| `baseline_total` | Carry plus typical run |
| `carry_std_dev` | Your actual dispersion, which sets the pin-hunting threshold |
| `offline_std_dev` | Lateral dispersion |
| `shot_count` | How many logged shots the numbers rest on |
| `last_updated` | |
| `in_bag` | So you can retire a club without losing its history |

## Populated table

Seeded from a TrackMan Range session, 5 August 2026, Convert on. Two carry figures per club, as discussed: `baseline_carry` from well-struck shots for club selection, `expected_carry` across all shots for risk and strategy.

| Club | Type | Baseline carry | Expected carry | Carry SD | Baseline total | Session avg total | Consistency | Shots |
|---|---|---|---|---|---|---|---|---|
| Driver (Ping G425) | Driver | 231 | 221 | 9.0 | 257 | 233 | 29 | 11 of more |
| 3 wood | Wood | 162 | 122 | 16.3 | 200 | 168 | 50 | 11, complete |
| 5 iron | Iron | 168 | 159 | 8.3 | 190 | 184 | 19 | 11, complete |
| 5 hybrid | Hybrid | 153 | 138 | 9.3 | 173 | 165 | 25 | 11, complete |
| 7 iron | Iron | 152 | 152 | 8.6 | 168 | 162 | 18 | 11 of more |
| 9 iron | Iron | 129 | 124 | 8.0 | 139 | 134 | 11 | 11 of more |
| Pitching wedge | Wedge | 109 | 106 | 5.8 | 117 | 112 | 12 | 11 of more |
| Lob wedge | Wedge | 77 | 77 | 4.0 | 83 | 83 | 6 | 3, complete |

**Session avg total and consistency come from the app header** and cover every shot hit with that club, including warm-up. They are therefore unbiased, unlike the per-shot columns. Where the two disagree, trust the app figure for expected performance and the computed figure for well-struck performance.

**How the completeness column was derived.** Comparing the average total of the supplied rows against the app's session average identifies which clubs have shots missing. Driver, 7 iron, 9 iron and pitching wedge all show a gap, meaning shots were hit that were not captured, and those shots were worse than the ones that were. Driver is the largest at 17 yards, so its true mishit rate is materially worse than the 18% computed here.

**On the consistency figure.** It does not map cleanly onto carry standard deviation: the 5 iron has a wide carry spread but scores 19, while the 7 iron is much tighter and scores 18. It likely incorporates lateral dispersion or is computed on total rather than carry. Treat it as a directional signal rather than a metric until its definition is confirmed.

**Still to capture:** 6 iron, 8 iron, utility wedge, sand wedge, putter. Log these next session.

**Mishit rule used:** any shot carrying under 80% of that club's median carry is treated as a mishit and excluded from `baseline_carry`. Crude but transparent, and it correctly caught the four duffed 3 woods and the topped hybrid without discarding merely below-average strikes.

**Sample size and selection caveat.** These are the last 11 shots per club in the session, taken after warming up with each club, rather than a full random sample. That leaves `baseline_carry` sound, since a well-struck shot is a well-struck shot whenever it happened, but makes `expected_carry` and the mishit rates optimistic, because pre-warm-up misses are excluded. The 3 wood figures in particular should be treated as a floor on how bad it gets. On-course logging has no warm-up to exclude, so these will drift toward honest as real rounds accumulate. Weight the seeded values low and let logged data override them quickly.

## Observations from the seed session

**The 5 iron is going further than the 5 hybrid.** 168 against 153, a 15 yard inversion. That is backwards, and it means one of those clubs is currently doing no useful job. Either the hybrid needs more loft-appropriate expectations or it is being mis-hit relative to the iron.

**The 3 wood is the problem club by a distance.** Mishit rate of 36%, carry standard deviation nearly twice the irons, and four shots that barely moved. Its expected carry of 122 is 40 yards below its baseline of 162, which is the single widest gap in the bag. On strategy grounds it should almost never be the club unless the shot genuinely needs it.

**The 69 yard gap between driver and 3 wood** is the other structural problem, though it is partly an artifact of the 3 wood inconsistency rather than a pure gapping issue.

**Iron dispersion is genuinely tight.** Standard deviations of 8 to 9 yards across the 5, 7 and 9 irons, and the 7 iron had no mishits at all. That is the strength in the bag and it is what the strategy logic should lean on.

## Notes

**`carry_std_dev` is the field that makes strategy analysis possible.** Without your actual dispersion, the tool cannot tell you whether going at a tucked pin was reasonable. With it, S002 becomes a calculation rather than a platitude.

**Set `shot_count` thresholds before trusting the numbers.** Below roughly 20 logged shots for a club, keep using the seeded range figure. Golf variance will otherwise rewrite your 7-iron distance after three bad swings.

**Wedges need the most attention.** Full-swing carry is nearly useless for wedges, since most wedge shots are partial. Consider logging a `swing_length` field (quarter, half, three-quarter, full) for wedges only, and building separate baselines per length.

---

# Part 2: Outcome picker

The picker is what you tap after a shot. It replaces the old `result` field, captures shape and contact in one interaction, and indexes directly onto corpus entries.

## Design constraint

Two taps maximum, one preferred. Anything more and logging dies by the fourth hole.

## Context switching

The picker shows different options depending on what the system already knows, which removes most of the tapping:

| Context | Trigger | Picker shown |
|---|---|---|
| Full swing | Any club except putter, over 40 yards to pin | Ball flight grid |
| Short game | Under 40 yards to pin, or wedge from off the green | Short game picker |
| Bunker | `lie` is sand | Bunker picker |
| Putting | Club is putter | Putting picker |

Distance to pin is already derived from GPS, so this switching costs nothing.

## Full swing: ball flight grid

A three by three grid. Columns are start direction, rows are curvature. One tap gives you both.

| | Curves left | Straight | Curves right |
|---|---|---|---|
| **Starts left** | Pull-draw / pull-hook | Pull | Pull-fade / pull-slice |
| **Starts straight** | Draw / hook | Straight | Fade / slice |
| **Starts right** | Push-draw / push-hook | Push | Push-fade / push-slice |

**On draw versus hook.** Same cell. The tool derives magnitude from the endpoint positions, so it decides whether it was a draw or a hook rather than asking you. This is the reconciliation step, and it removes a judgement call you would get wrong anyway.

**Centre cell doubles as "good".** A straight shot that finished where you aimed needs no further classification.

## Full swing: contact strip

A row beneath the grid, for when contact is the story rather than shape.

- Fat
- Thin
- Top
- Shank
- Skied (only shown for driver and woods)
- Off the toe
- Off the heel

Contact and shape are not exclusive. A thinned slice is both, so allow one from each if the user wants, but never require it.

## Short game picker

- Good
- Chunked
- Bladed
- Left short
- Ran long
- Wrong club

## Bunker picker

- Good out
- Left in bunker
- Left short
- Thinned across
- Too much sand

## Putting picker

Two rows, because pace and line are separate and the corpus needs them separated.

**Pace:** Good, left short, ran past

**Line:** Good, missed left, missed right, misread break

Allowing one from each row is what makes P004 work, since a putt that was short and low may have had a correct read and a pace error.

## Optional second layer

Only if the user taps for it. Never required.

- Trajectory: low, normal, high
- Freehand shape trace
- Commitment: committed, unsure

## Drop and penalty flags

Separate control, not part of the outcome picker, since it describes what happens next rather than what just happened.

- Taking a drop, with reason
- Ball not found
- Provisional

This should be prominent enough to actually get used. If it is buried, the position chain silently breaks and the data quietly rots.

## Mapping to corpus entries

Every picker option maps to at least one corpus entry, and the situational fields decide which entry wins:

| Picker option | Primary entry | Overridden when |
|---|---|---|
| Fade / slice | F001 | `stance` is ball below feet, then L001 |
| Draw / hook | F004 | `stance` is ball above feet, then L002 |
| Pull-fade | F002 | |
| Push-fade | F003 | |
| Pull | F005 | |
| Push | F006 | |
| Fat | F007 | `lie` is heavy rough or downhill, then L005 or L004 |
| Thin | F008 | `lie` is downhill, then L004 |
| Top | F009 | |
| Thinned wedge | F010 | |
| Shank | F011 | |
| Skied | F012 | |
| Off the heel | F013 | |
| Off the toe | F014 | |
| Chunked (short game) | F015 | |
| Bladed (short game) | F016 | |
| Left short (short game) | D001 | |
| Ran long (short game) | D002 | |
| Wrong club, short | D003 | Cold or into wind, then C001 or C002 |
| Wrong club, long | D004 | Downwind, then C002 |
| Left short (bunker) | D005 | |
| Putt left short | P001 | Round-wide pattern, then P006 |
| Putt ran past | P002 | Round-wide pattern, then P006 |
| Misread break | P003 | Pace was also off, then P004 |
| Missed left / right (putt) | P005 | |

The override column is the important part. It is what stops the tool diagnosing a swing fault when the lie or the conditions already explain the miss.
