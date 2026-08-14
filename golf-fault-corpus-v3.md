# Golf Fault-Fix Corpus v3

Consolidated. Supersedes `golf-fault-corpus-v1.md` and Part 2 of `golf-shot-log-and-corpus-v2.md`. All 45 entries in one document, since the retrieval pipeline will chunk one entry per record.

Companion documents: `golf-shot-log-schema-v2.md` for the data model, `golf-club-table-and-picker.md` for the UI contract, `golf-eval-sets-v2.md` for the tests.

---

## How to read an entry

Every entry has the same fields:

- **How I'd describe it.** The phrasings a golfer would actually use. This is what retrieval matches against, so it matters more than the technical name.
- **What it is.** The mechanical definition.
- **Causes.** Always plural, each with a distinguishing signal. A miss almost never has one cause, and a tool that pretends otherwise will be confidently wrong.
- **Fixes.** Written as external cues where possible, meaning they describe the intended effect rather than a body part to move. Motor learning research consistently finds these work better.
- **Evidence tier.** How much to trust it.
- **Compensation risk.** What this fix might break. This is what the feedback loop writes back against.

## Evidence tiers

- `settled` - supported by launch monitor physics or large datasets
- `consensus` - widely taught, no hard evidence either way
- `contested` - credible coaches genuinely disagree
- `contradicted` - traditional teaching that evidence has undermined

## Categories

| Prefix | Category | Purpose |
|---|---|---|
| F | Swing faults | What went wrong in the swing |
| P | Putting | Pace, line and read |
| D | Distance and power | Club selection and speed control |
| L | Lie and situation | Suppresses false swing diagnoses |
| S | Strategy | Decision errors where the swing was fine |
| C | Conditions | Round-level effects |
| R | Recovery | Shots judged on position, not distance |

## Foundational assumptions

- Clubface at impact controls roughly 85% of start direction with driver, 75% with a mid-iron.
- Face angle relative to club path controls curvature. Face open to path curves right, closed to path curves left.
- All directions are for a right-handed golfer.
- Strike location can create curve on its own via gear effect, independently of face and path.

---

# Swing faults

## F001 - Slice

**How I'd describe it:** sliced it, big fade, fell off to the right, cut across it, banana

**What it is:** Face open to path, producing right curvature. The classic amateur version starts left or straight and curves hard right.

**Causes**
1. Out-to-in path with face open to that path. Distinguishing signal: ball starts left of target then curves right.
2. Face open to target and to path. Signal: ball starts right and curves further right.
3. Heel strike via gear effect. Signal: face marking toward the heel, ball speed down, curve present even when path feels neutral.
4. Early extension pushing the hands out and the path left. Signal: often paired with thin or heel contact.

**Fixes**
- Strengthen the grip so the face sits more closed. Highest-leverage single change, because face dominates start direction.
- Feel the clubhead exit right of the target through impact.
- Check strike location on the face before changing anything in the swing.

**Evidence tier:** settled

**Compensation risk:** Fixing path alone without addressing the face turns a slice into a straight pull. Expect that as the intermediate stage rather than a new problem.

---

## F002 - Pull-slice

**How I'd describe it:** started left then cut back right, dead left then sliced, weak left-to-right

**What it is:** Face closed to target but path even further left, so the face is open relative to the path. Starts left, curves right. One of the most common amateur ball flights.

**Causes**
1. Steep out-to-in path with a face that is closed to target but open to path. Signal: divot points left, ball starts left.
2. Over-the-top transition from the top. Signal: shoulders opening early, steep angle of attack.

**Fixes**
- Shallow the path so it works more right, while keeping face awareness so the ball does not simply become a pull.
- Feel the trail elbow drop in front of the hip in transition.

**Evidence tier:** settled

**Compensation risk:** Path correction alone converts this to a pull. Both changes usually have to happen together.

---

## F003 - Push-slice

**How I'd describe it:** started right and kept going right, blocked it then it sliced, big miss right

**What it is:** Face open to target with path also right of target but face open relative to it. Starts right, curves further right. The biggest single-shot miss in golf by total offline distance.

**Causes**
1. In-to-out path with the face badly open to it. Signal: divot points right, ball starts right.
2. Very late or absent face rotation. Signal: hands ahead but face lagging open.

**Fixes**
- Rotate the face closed earlier through impact.
- Check grip strength first, since this pattern usually has a weak grip underneath it.

**Evidence tier:** settled

**Compensation risk:** Closing the face on an in-to-out path can flip this straight to a hook. Change one variable at a time.

---

## F004 - Hook

**How I'd describe it:** hooked it, snapped it left, duck hook, went hard left

**What it is:** Face closed to path, producing left curvature.

**Causes**
1. In-to-out path with face closed to that path. Signal: ball starts right then curves left.
2. Over-active hands through impact. Signal: inconsistent, often alternates with blocks.
3. Toe strike via gear effect. Signal: face marking toward the toe, curve appears even on a decent-feeling swing.
4. Grip too strong. Signal: face closes without any hand action.

**Fixes**
- Weaken the grip slightly.
- Feel the chest continuing to rotate through impact rather than the hands taking over.

**Evidence tier:** settled

**Compensation risk:** Hooks and blocks are often the same fault. A player who hooks will start blocking right to avoid the left miss, then hook again when the block frightens them. Treat a two-way miss as one problem, not two.

---

## F005 - Pull

**How I'd describe it:** pulled it, straight left, no curve just left

**What it is:** Face and path both left of target and matched to each other, so the ball starts left and stays left.

**Causes**
1. Out-to-in path with the face square to that path. Signal: no curvature, purely directional.
2. Aim and alignment left without the player realising. Signal: consistent, repeatable, feels like a good strike.

**Fixes**
- Check alignment before touching the swing. This one is disproportionately an aim problem.
- If alignment is good, work the path more right while keeping the face matched.

**Evidence tier:** settled

**Compensation risk:** Common landing point after fixing a slice. If pulls appear where slices used to be, the face work succeeded and the path is now the remaining variable.

---

## F006 - Push / block

**How I'd describe it:** blocked it, pushed it right, straight right, held it off

**What it is:** Face and path both right of target and matched. Starts right, no curve.

**Causes**
1. In-to-out path with face square to it. Signal: no curvature, straight right.
2. Hanging back on the trail side so the low point moves back and the path swings right. Signal: often paired with thin or fat contact.
3. Alignment right of target. Signal: repeatable and feels solid.

**Fixes**
- Check alignment first.
- Feel pressure moving into the lead side through transition.

**Evidence tier:** settled

**Compensation risk:** Frequently pairs with hook as a two-way miss. See F004.

---

## F007 - Fat / heavy / chunk

**How I'd describe it:** chunked it, fat, heavy, took a divot before the ball, hit the ground before the ball, club hit the turf first, caught the ground too early, hit behind it, dug into the ground, lost all the power, came up 30 yards short

**What it is:** Low point behind the ball, so the club contacts ground first and loses energy.

**Causes**
1. Weight hanging back on the trail side. Signal: divot starts well behind the ball, finish balance poor.
2. Early release or casting from the top. Signal: divot shallow and long, high ball flight, distance loss.
3. Added spine tilt away from target in the downswing. Signal: pattern worsens with longer clubs.
4. Body rotation stalling so the arms release early. Signal: strong shots alternate with fat ones.
5. Poor arc height control, independent of low point position. Signal: fat shots occur even when weight and low point look correct.

**Fixes**
- Feel pressure into the lead foot before the club reaches the ball.
- Feel the hands ahead of the clubhead at impact.
- Check ball position, since too far forward creates fat contact even with a good low point.

**Evidence tier:** settled

**Compensation risk:** The fat-thin loop. Fear of fat contact produces lifting, which produces thin. Treat both as one low-point problem rather than opposite faults.

---

## F008 - Thin / skulled

**How I'd describe it:** thinned it, caught it thin, bladed it, screamed low across the green, stung my hands

**What it is:** Contact at or above the ball's equator, producing a low, fast, low-spin shot.

**Causes**
1. Instinctive lift to avoid an expected fat shot. Signal: follows a fat shot in the same round or same session.
2. Early extension raising the hands through impact. Signal: paired with heel strikes.
3. Loss of posture or standing up through the shot. Signal: more common under pressure or with awkward lies.
4. Trying to help or scoop the ball into the air. Signal: most common with wedges and short irons.
5. Hanging back so the club is on its way up at contact. Signal: shared cause with F007.

**Fixes**
- Feel the clubhead brushing the ground after the ball rather than at it.
- Keep chest covering the ball through impact.
- Trust the loft to do the lifting rather than helping it.

**Evidence tier:** settled

**Compensation risk:** Correcting thin by consciously staying down often reintroduces fat. The stable fix is low point control, not a body position.

---

## F009 - Top

**How I'd describe it:** topped it, dribbled it along the ground, hit the top of the ball, barely moved

**What it is:** Extreme version of thin. Club contacts the upper hemisphere of the ball, producing a ground-bound shot.

**Causes**
- Same cluster as F008, in more severe form: lifting, early extension, loss of posture, weight hanging back.
- Ball position too far back with a lofted club, causing the leading edge to arrive high. Signal: happens mainly with wedges.

**Fixes**
- Same as F008.
- Check that ball position has not crept back in the stance.

**Evidence tier:** settled

**Compensation risk:** Highly emotive miss that tends to trigger over-correction into fat contact on the next shot. Log the following shot too, since the pattern matters more than the individual miss.

---

## F010 - Topped or thinned wedge

**How I'd describe it:** thinned a wedge, bladed a lob wedge over the green, caught it thin from 40 yards

**What it is:** Thin contact specifically with a high-lofted club. Worth separating from F008 because the causes skew differently and the consequences are worse, since a thinned wedge travels much further than intended.

**Causes**
1. Trying to help the ball up with the most lofted club in the bag. Signal: happens on short shots, not full swings.
2. Deceleration through impact. Signal: short backswing, longer follow through, or the reverse.
3. Weight hanging back on a shot the player is anxious about. Signal: worse over hazards or tight pins.
4. Ball position too far forward so the club is past low point. Signal: consistent across attempts.

**Fixes**
- Keep pressure on the lead side throughout, since these shots do not need a weight shift.
- Accelerate through the ball rather than at it.
- Let the loft do the work and feel the leading edge staying low through the strike.

**Evidence tier:** settled for mechanics, consensus for the deceleration cue

**Compensation risk:** Over-correcting produces a chunk that goes ten yards, which is the more damaging miss in most situations.

---

## F011 - Shank

**How I'd describe it:** shanked it, hosel rocket, dead right off the hosel, socket

**What it is:** Ball strikes the hosel rather than the face, firing sharply right.

**Causes**
1. Hands and hosel moving closer to the ball in space through impact. Signal: the primary mechanical cause regardless of path direction.
2. Weight moving toward the toes in the downswing. Signal: balance falling forward at finish.
3. Steep out-to-in path pushing the hosel out toward the ball. Signal: divot points left.
4. Excessively inside takeaway forcing a loop back out. Signal: divot points right.

**Fixes**
- Feel weight in the heels through impact.
- Feel the strike toward the toe side of the face.
- Address the ball slightly toward the toe as a temporary calibration.

**Evidence tier:** settled that it is multi-cause, contested on which cause dominates

**Compensation risk:** Frequently appears immediately after fixing another fault, because a new movement pattern changes the hand path before the player has calibrated to it. A shank following a swing change is often evidence the change is happening, not that it is wrong.

---

## F012 - Skied drive

**How I'd describe it:** skied it, popped it straight up, hit the top of the driver, mark on the crown

**What it is:** Steep negative attack angle with the driver, contacting the ball high on the face or crown.

**Causes**
1. Excessively steep attack angle with a club that needs a shallow or upward one. Signal: crown marks, very high launch, distance loss.
2. Ball teed too low for the strike pattern. Signal: easy to test and rule out first.
3. Weight moving toward the target too aggressively with the driver. Signal: divot after a driver shot from a tee.

**Fixes**
- Tee it higher and feel the clubhead travelling level or slightly up at impact.
- Feel the trail shoulder staying below the lead shoulder through impact.

**Evidence tier:** settled

**Compensation risk:** Note that "hit down on it" is correct for irons and wrong for the driver. Applying an iron cue to the driver is a common source of this miss.

---

## F013 - Heel strike

**How I'd describe it:** off the heel, felt it near the hosel, lost distance and it faded

**What it is:** Contact toward the heel of the face. Reduces ball speed and, on a driver, adds fade or slice spin through gear effect.

**Causes**
1. Hands moving closer to the ball through impact, often with early extension. Signal: paired with thin contact.
2. Standing too close at address. Signal: consistent, present from the first swing.
3. Out-to-in path bringing the heel through first. Signal: divot points left.

**Fixes**
- Feel weight in the heels and the strike toward the toe.
- Check setup distance from the ball before changing anything dynamic.

**Evidence tier:** settled

**Compensation risk:** Shares its mechanism with the shank. Persistent heel strikes are worth treating seriously before they become F011.

---

## F014 - Toe strike

**How I'd describe it:** off the toe, felt dead, lost distance and it drew left

**What it is:** Contact toward the toe of the face. Reduces ball speed and, on a driver, adds draw or hook spin through gear effect.

**Causes**
1. Standing too far from the ball. Signal: consistent from the first swing.
2. Early extension or pulling the hands in through impact. Signal: variable, worse under pressure.
3. Excessively in-to-out path. Signal: divot points right.

**Fixes**
- Check setup distance first.
- Feel the chest rotating through rather than the arms pulling in.

**Evidence tier:** settled

**Compensation risk:** Can mask a face problem, since gear effect draw spin partially offsets an open face. Fixing the strike can reveal a slice that was hidden underneath it.

---

## F015 - Chunked chip

**How I'd describe it:** chunked a chip, duffed it, moved it two feet, hit it fat from just off the green

**What it is:** Ground contact before the ball on a short shot around the green.

**Causes**
1. Weight on the trail foot at address or shifting back during the stroke. Signal: the single most common cause on short shots.
2. Trying to lift the ball rather than striking down on it. Signal: scooping motion, hands behind the clubhead at impact.
3. Deceleration through the ball. Signal: backswing longer than follow through.
4. Wrist hinge released early. Signal: club bottoming out before the ball.

**Fixes**
- Set up with weight favouring the lead side and keep it there.
- Feel the handle leading the clubhead through impact.
- Keep the through-swing at least as long as the backswing.

**Evidence tier:** settled for mechanics, consensus for the weight distribution ratio

**Compensation risk:** Leads directly to F016, since a chunk on one hole often produces a bladed chip on the next.

---

## F016 - Bladed chip

**How I'd describe it:** bladed a chip, thinned it across the green, sent it 40 yards past

**What it is:** Thin contact on a short shot, sending the ball far past target.

**Causes**
1. Reaction to a previous chunk, lifting through impact. Signal: follows F015 closely in time.
2. Trying to help the ball into the air. Signal: hands behind the ball at impact.
3. Ball position too far forward. Signal: consistent across attempts.
4. Standing up out of posture through the stroke. Signal: worse under pressure.

**Fixes**
- Keep chest over the ball through the stroke.
- Feel the club brushing the turf after the ball.
- Trust the loft.

**Evidence tier:** settled

**Compensation risk:** The paired opposite of F015. Both come from the same low-point uncertainty, so treat them as one entry when they alternate.

---

## F017 - Weak high flight / distance loss

**How I'd describe it:** ballooned it, went nowhere, high and short, no penetration

**What it is:** Excessive spin loft producing high launch, high spin and poor energy transfer. The ball climbs and falls short.

**Causes**
1. Too much dynamic loft at impact, often from early release. Signal: high flight, shallow divot, distance well below normal for the club.
2. Off-centre strike reducing smash factor. Signal: check face marking before anything else.
3. Attack angle too steep relative to dynamic loft. Signal: deep divot with high flight.

**Fixes**
- Feel the hands ahead of the clubhead at impact to reduce dynamic loft.
- Check strike location first, since a centre-face miss explains most single-shot distance loss.

**Evidence tier:** settled

**Compensation risk:** Reducing loft too aggressively produces a low, weak flight with insufficient carry. There is an optimum, not a direction.

---

## F018 - Two-way miss

**How I'd describe it:** no idea where it's going, left one hole right the next, can't commit to a line

**What it is:** Alternating left and right misses within a round, usually a single underlying fault plus a compensation rather than two separate faults.

**Causes**
1. In-to-out path with variable face rotation, producing hooks when the hands are active and blocks when they are not. Signal: misses cluster as F004 and F006.
2. Steep out-to-in path with variable face, producing pulls and pull-slices. Signal: misses cluster as F002 and F005.
3. A recent swing change not yet calibrated. Signal: appeared shortly after working on something new.

**Fixes**
- Diagnose the path first, then the face. Chasing each individual miss will make it worse.
- Accept one miss direction temporarily so the pattern becomes readable.

**Evidence tier:** consensus

**Compensation risk:** This is the entry that most needs the feedback loop. A two-way miss is usually evidence that a previous fix created a compensation, so the fix history matters more than the current shot.

---

---

# Putting

## P001 - Putt left short

**How I'd describe it:** left it short, never got there, died before the hole, weak putt

**What it is:** Insufficient pace to reach the hole.

**Causes**
1. Deceleration through impact. Signal: backswing longer than through-swing.
2. Misjudged green speed, usually on slower greens or into grain. Signal: pattern across several putts in the same round.
3. Strike away from the centre of the putter face. Signal: feels dead, distance loss on a stroke that felt normal.
4. Uphill putt under-read for slope. Signal: specific to the hole.

**Fixes**
- Match backswing and through-swing length.
- Take a practice putt at the fringe before the round to calibrate speed.

**Evidence tier:** settled for strike, consensus for the stroke-length cue

**Compensation risk:** Over-correcting produces P002 on the comeback putt, which is how three-putts happen.

---

## P002 - Putt ran past

**How I'd describe it:** ran way past, too much pace, blew it by, sent it four feet past

**What it is:** Excessive pace, leaving a significant return putt.

**Causes**
1. Misjudged green speed, usually on faster or downhill greens. Signal: pattern across the round.
2. Over-correction after leaving a previous putt short. Signal: follows P001.
3. Downhill or downgrain not accounted for. Signal: hole-specific.

**Fixes**
- Calibrate speed on the practice green before the round and note it in the log.
- Aim to finish 12 to 18 inches past the hole rather than dying it in.

**Evidence tier:** consensus

**Compensation risk:** Pairs directly with P001. If both appear in one round, the problem is green speed calibration, not your stroke.

---

## P003 - Misread the break

**How I'd describe it:** read it wrong, played too much break, not enough break, it never turned

**What it is:** Line was wrong for the slope, independent of stroke quality.

**Causes**
1. Under-reading the slope. Signal: ball finishes low side of the hole.
2. Over-reading the slope. Signal: ball finishes high side, or misses above the hole.
3. Grain not accounted for. Signal: more relevant on some grass types than others.

**Fixes**
- Read from the low side of the putt.
- Note which direction you tend to err in, since most golfers are consistently one or the other.

**Evidence tier:** consensus

**Compensation risk:** See P004. Break errors and pace errors are not independent, so diagnosing one without the other will mislead you.

---

## P004 - Pace and break interaction

**How I'd describe it:** under-hit it and it broke more than I expected, hit it firm and it held the line

**What it is:** Not a fault on its own, but the concept that explains many apparent misreads. A putt hit softly spends longer on the slope and breaks more. A putt hit firmly breaks less.

**Why it matters:** A putt that finishes short and low of the hole may have had a correct read and a pace error, not a read error. Diagnosing it as a misread sends you off adjusting the wrong thing.

**Fixes**
- Decide your intended pace before reading the line, since the read depends on it.
- When logging, record both pace and finishing position, not just "missed left."

**Evidence tier:** settled physics, consensus on the coaching application

**Compensation risk:** This entry is the one that stops P001 and P003 from being misattributed to each other.

---

## P005 - Pulled or pushed putt

**How I'd describe it:** pulled the putt, pushed it right, missed the start line, never started on line

**What it is:** Ball started off the intended line, independent of read.

**Causes**
1. Putter face open or closed at impact. Signal: dominant factor, as with the full swing.
2. Stroke path across the ball. Signal: secondary, matters less than face.
3. Eye line inside or outside the ball, distorting perceived line. Signal: consistent directional bias.
4. Aim error at address. Signal: the stroke was fine, the setup was not.

**Fixes**
- Check aim with an alignment aid before assuming the stroke is at fault.
- Focus on the face pointing at the start line at impact.

**Evidence tier:** settled that face dominates start line

**Compensation risk:** Aim errors get compensated for by stroke manipulation, so fixing aim can briefly make the stroke worse until it recalibrates.

---

## P006 - Green speed misjudged for the day

**How I'd describe it:** greens were quicker than I thought all day, everything came up short, couldn't get the speed

**What it is:** A round-level calibration error rather than a shot-level fault.

**Causes**
1. Seasonal or weather change in green speed. Signal: affects most putts in the round.
2. Time of day, since morning dew slows greens and afternoon drying speeds them up. Signal: pattern shifts through the round.
3. Recent maintenance. Signal: unpredictable, worth noting in the log.

**Fixes**
- Calibrate on the practice green and record the perceived speed for the round.
- Adjust once, deliberately, rather than shot by shot.

**Evidence tier:** settled that conditions affect speed, consensus on the adjustment method

**Compensation risk:** This is the entry that should suppress P001 and P002 diagnoses when the pattern is round-wide. A round-level problem should not generate eighteen shot-level fault records.

---

---

# Distance and power

## D001 - Decelerated short shot

**How I'd describe it:** quit on it, decelerated, only went a metre, gave up on the shot

**What it is:** Loss of speed through impact on a short shot, producing a heavily under-distanced result.

**Causes**
1. Uncertainty about the shot or club. Signal: log the commitment field, it will usually say unsure.
2. Backswing too long for the shot, requiring deceleration to control distance. Signal: consistent across attempts.
3. Fear of over-hitting, often with a hazard behind the pin. Signal: hazard field will show it.

**Fixes**
- Shorten the backswing so you can accelerate through.
- Pick a landing spot rather than thinking about the hole.

**Evidence tier:** consensus

**Compensation risk:** Overlaps heavily with the chunked chip. If the ball moved barely at all, distinguish whether the club hit the ground first, since the fix differs.

---

## D002 - Over-hit short shot

**How I'd describe it:** came out too hot, ran through the back, too much on it, hit it too hard

**What it is:** Excess distance on a short shot, usually from too little loft or too much speed for the shot.

**Causes**
1. Club too low-lofted for the amount of carry needed. Signal: bump and run with a mid-iron running out.
2. Too much speed applied to compensate for a perceived need to reach.
3. Firm greens or firm run-off areas. Signal: conditions field, and a pattern across the round.

**Fixes**
- Pick landing spot first, then choose the club that gets it there with normal pace.
- On firm days, land it shorter and let it run.

**Evidence tier:** consensus

**Compensation risk:** Correcting with more loft and the same speed produces D001.

---

## D003 - Wrong club, came up short

**How I'd describe it:** wrong club, didn't have enough, needed one more club, came up short of the green

**What it is:** Contact was acceptable but the club could not cover the distance.

**Causes**
1. Distance estimate based on best-case carry rather than average. Signal: your logged average for that club will show it.
2. Conditions not accounted for, particularly cold air or into wind. Signal: weather fields.
3. Elevation not accounted for on an uphill shot.

**Fixes**
- Club selection off your logged average carry, not your best.
- Add a club for cold or into wind rather than swinging harder.

**Evidence tier:** settled that temperature and wind affect carry

**Compensation risk:** Swinging harder with the short club produces contact faults. The fix is the club, not more effort.

---

## D004 - Wrong club, went long

**How I'd describe it:** too much club, flew the green, went long, one club too many

**What it is:** Contact was acceptable but the club carried further than needed.

**Causes**
1. Downwind or warm conditions increasing carry. Signal: weather fields.
2. Downhill shot not accounted for.
3. Adrenaline or a firmer strike than usual. Signal: compare achieved distance against your average.

**Fixes**
- Club off the actual number including elevation and wind.
- Take note of which conditions consistently add distance for you.

**Evidence tier:** settled

**Compensation risk:** Long is frequently worse than short, since greens are usually defended more severely at the back. This is a strategy entry as much as a distance one.

---

## D005 - Bunker shot left short

**How I'd describe it:** left it in the bunker, got out but left it short, took too much sand, didn't get it to the hole

**What it is:** Insufficient distance from a greenside bunker despite escaping.

**Causes**
1. Entry point too far behind the ball, taking too much sand. Signal: deep divot in the sand, distance well short.
2. Deceleration through the sand. Signal: short follow through.
3. Sand heavier or wetter than expected. Signal: conditions, and a pattern across the round.
4. Face not open enough, so the club digs rather than sliding.

**Fixes**
- Enter the sand a consistent distance behind the ball and accelerate through.
- Commit to a full finish, since bunker shots need more speed than they feel like they should.

**Evidence tier:** settled on entry point, consensus on the amounts

**Compensation risk:** Over-correcting produces thin bunker contact, which sends the ball across the green. That is the more damaging miss.

---

---

# Lie and situation

## L001 - Ball below feet

**How I'd describe it:** ball below my feet and it went right, sloping away from me, sidehill lie

**What it is:** A lie that promotes a fade or slice for every golfer, regardless of swing.

**Why it matters:** The resulting right-curving shot is usually a lie effect, not a swing fault. Diagnosing it as a slice will send you fixing something that is not broken.

**Adjustments**
- Aim left to allow for the curve.
- Grip closer to the end of the club and stay in posture, since standing up is the common error.
- Take one more club, as the lie costs distance.

**Evidence tier:** settled

**Compensation risk:** If your log shows slices only from this lie, the corpus should suppress the slice diagnosis entirely.

---

## L002 - Ball above feet

**How I'd describe it:** ball above my feet and it went left, sloping toward me, hooked off a sidehill

**What it is:** A lie that promotes a draw or hook, because the club sits more closed relative to the swing.

**Adjustments**
- Aim right to allow for the curve.
- Grip down on the club.
- Expect less distance and club accordingly.

**Evidence tier:** settled

**Compensation risk:** As with L001, this is a lie effect. Do not log it as a hook.

---

## L003 - Uphill lie

**How I'd describe it:** uphill lie, ball above the level of my feet up the slope, hit it high and short

**What it is:** The slope adds effective loft, producing higher launch and less distance.

**Adjustments**
- Take more club.
- Set your shoulders parallel to the slope.
- Expect a slight draw tendency.

**Evidence tier:** settled

---

## L004 - Downhill lie

**How I'd describe it:** downhill lie, ball below me on a slope, came out low and running

**What it is:** The slope reduces effective loft, producing lower launch and more run. Also the hardest lie to make clean contact from.

**Adjustments**
- Take less club and expect run.
- Set shoulders with the slope and chase the club down it.
- Expect a fade tendency.

**Evidence tier:** settled

**Compensation risk:** Thin and fat contact are both common here. A contact miss from a downhill lie should be weighted less heavily as evidence of a swing fault.

---

## L005 - Heavy rough

**How I'd describe it:** buried in the rough, grass grabbed the club, came out weak, thick lie

**What it is:** Grass between club and ball reduces control, closes the face through resistance, and cuts distance unpredictably.

**Adjustments**
- Take more loft and prioritise getting back to the fairway.
- Grip more firmly and expect the face to close.
- Steepen the angle of attack to reduce grass interference.

**Evidence tier:** settled

**Compensation risk:** Distance from rough is highly variable, so distance-control faults logged from rough should not be counted against your club averages.

---

## L006 - Flyer lie

**How I'd describe it:** came out hot from the rough, flew the green from a light lie, no spin on it

**What it is:** Light rough gets between club and ball, reducing spin and causing the ball to fly further than expected with less stopping power.

**Adjustments**
- Club down and expect run.
- Do not aim at a pin you cannot afford to fly.

**Evidence tier:** settled

**Compensation risk:** Easily mislogged as a distance-control error or over-swing when it is a lie effect.

---

---

# Strategy

## S001 - Short-sided

**How I'd describe it:** short-sided myself, no green to work with, missed on the wrong side

**What it is:** Missing on the side of the green where the pin leaves you almost no room to land the next shot.

**Why it matters:** This is a strategy error made on the previous shot, not a technique error on the current one. The recovery shot being difficult is the consequence, not the cause.

**Adjustments**
- Aim at the centre of the green rather than the pin when the pin is tucked.
- Identify the safe miss before the shot and bias toward it.

**Evidence tier:** settled by strokes gained analysis

**Compensation risk:** Attempting a heroic recovery from short-sided compounds the original error. The tool should flag the previous shot, not this one.

---

## S002 - Aimed at a tucked pin

**How I'd describe it:** went at the flag, should have played to the middle, pin was tucked

**What it is:** Targeting a pin position that offers no margin for normal dispersion.

**Why it matters:** Given that amateur dispersion is wide even for low handicaps, aiming at a tucked pin means the expected outcome is a miss on the difficult side.

**Adjustments**
- Aim at the centre unless your logged dispersion for that club genuinely supports going at the pin.
- Let your own data set the threshold rather than a general rule.

**Evidence tier:** settled by strokes gained analysis

---

## S003 - Failed hero recovery

**How I'd describe it:** tried to thread it through the trees, went for the green when I shouldn't have, should have chipped out

**What it is:** Attempting a low-probability recovery instead of returning to play.

**Why it matters:** The expected cost of the failed attempt usually exceeds the saved stroke from success. Worth logging separately from the swing that executed it, since the swing may have been fine.

**Adjustments**
- Estimate the gap width and required curve honestly.
- Default to the shot that returns you to the fairway.

**Evidence tier:** settled by strokes gained analysis

**Compensation risk:** A successful hero shot reinforces the decision even though it was still a bad bet. Log the decision quality separately from the outcome, or the tool learns the wrong lesson.

---

## S004 - Relief not taken

**How I'd describe it:** played it off the path, didn't take a drop, could have moved it

**What it is:** Playing from a situation where free relief was available.

**Why it matters:** A rules knowledge gap, not a swing issue. Cart paths, ground under repair, immovable obstructions and casual water usually allow free relief.

**Adjustments**
- Check for relief before playing any awkward lie near a man-made surface.

**Evidence tier:** settled by the rules

---

## S005 - Wrong side of the fairway

**How I'd describe it:** right side of the fairway but the wrong angle, blocked out by a bunker, no shot at the pin from there

**What it is:** A drive that finished in play but on the side that leaves a poor angle for the approach.

**Adjustments**
- Pick the side of the fairway that opens the green before choosing the tee shot line.
- Note which side each hole's pin position favours.

**Evidence tier:** settled by strokes gained analysis

---

---

# Conditions

## C001 - Cold conditions

**How I'd describe it:** freezing today, ball going nowhere, everything short

**What it is:** Cold air is denser and the ball is less responsive, reducing carry meaningfully.

**Adjustments**
- Club up and expect reduced carry across the bag.
- Do not adjust your swing to compensate, since the distance loss is environmental.

**Evidence tier:** settled

**Compensation risk:** Swinging harder in cold conditions produces contact faults. If the log shows a cold day, distance shortfalls should not be diagnosed as swing problems.

---

## C002 - Wind

**How I'd describe it:** into the wind, downwind, crosswind pushed it, blowing hard

**What it is:** Wind affects carry and curvature disproportionately, since a ball hit into wind spins more and climbs.

**Adjustments**
- Into wind, club up and swing easier rather than harder, since extra speed adds spin and makes it climb.
- Downwind, expect less stopping power.
- Crosswind amplifies existing curve, so a fade into a left-to-right wind will go much further right than usual.

**Evidence tier:** settled

**Compensation risk:** A shot that curved more than expected in crosswind is not necessarily a bigger swing fault. The tool should discount curvature evidence in strong crosswind.

---

## C003 - Firm and fast conditions

**How I'd describe it:** running forever, greens not holding, bouncing through the back, summer conditions

**What it is:** Dry, firm turf adds run and reduces stopping power everywhere.

**Adjustments**
- Land approach shots shorter and plan for release.
- Around the greens, favour lower running shots and account for the run-out.

**Evidence tier:** settled

**Compensation risk:** Shots that ran through the back are often correctly struck. Log the condition so the tool does not read them as distance-control errors.

---

## C004 - Soft and wet conditions

**How I'd describe it:** soggy, plugged, no run at all, ball stopping dead, winter conditions

**What it is:** Wet turf removes run and can produce plugged or muddy lies.

**Adjustments**
- Expect carry distance only, with no run.
- Mud on the ball causes unpredictable curve that is not a swing fault.

**Evidence tier:** settled

**Compensation risk:** Directional misses with mud on the ball should be excluded from fault pattern analysis entirely.

---

---

# Recovery

## R001 - Recovery and punch-out

**How I'd describe it:** punched out from the trees, chipped it back to the fairway, took my medicine, tried to thread it through a gap, hit a branch, played it safe out sideways

**What it is:** A deliberate shot from trouble where the objective is position rather than distance. This entry exists separately from every other because the success criterion is different. A 60-yard punch-out that finds the fairway is a good shot. Judged on distance, it looks like a disaster.

**Two separate things to judge**

**1. The decision.** Was attempting the recovery correct at all?
- Gap width and required curve against your actual dispersion for that club
- Lie quality, since a clean lie supports more ambition than a buried one
- What success saves against what failure costs
- Whether a lateral chip-out leaves a full shot you can commit to

**2. The execution.** Given the decision, was it played well?
- Contact under a low ceiling, which requires a delofted strike
- Distance control, since overpowering a punch-out often runs into new trouble
- Curve control if the shot needed shape

**Common execution faults**
1. Not clubbing up. Delofting the club costs distance, so a punch needs more club than the number suggests. Signal: came up short despite good contact.
2. Overpowering it. Signal: executed well but ran further than intended, often into new trouble.
3. Full follow-through under a low branch. Signal: caught a branch on the way out.
4. Fat or thin contact from an unfamiliar setup. Signal: ball back, hands forward and a shortened swing is not a rehearsed position.

**Adjustments**
- Ball back, hands forward, weight favouring the lead side, abbreviated follow-through.
- Take at least one more club than the distance suggests.
- Pick the widest gap available rather than the most direct one.
- Choose a specific landing area, since "back to the fairway" is not a target.

**Evidence tier:** consensus for the technique, settled by strokes gained analysis for the decision

**Compensation risk:** Pairs with S003. A successful hero shot was often still a bad bet, so log decision quality separately from outcome or the tool learns to reward gambling. Equally, a failed punch-out from a correct decision is bad luck rather than a fault, and should not feed swing pattern analysis.

---

# Notes on using this corpus

## Situational entries exist to suppress false diagnoses

The L and C categories are arguably more important than the swing faults. Their job is to tell the tool "that was the lie, not you." A diagnostic tool that cannot say that will send you off fixing things that are not broken, which makes you worse rather than better.

When building retrieval, weight them accordingly: if the lie or conditions field explains the miss, the situational entry should outrank the swing fault entry.

## Consistency changes what a miss means

Frequency and spread across clubs matter as much as the miss itself.

| Pattern | Reading |
|---|---|
| Same miss, multiple clubs, repeatedly | Systemic fault. Posture, low point, ball position, grip. One root cause. |
| Same miss, one club only | Club-specific. Setup, length, or a confidence issue with that club. |
| Different misses scattered through the round | Strike consistency rather than a specific fault. Do not prescribe a fault fix. |
| One instance of a miss in a round | Variance. Do not diagnose at all. |

This should gate diagnosis entirely. A single topped shot in eighteen holes is noise, and a tool that offers a fix for it is training you to chase ghosts.

## Differential diagnosis: when the fix does not work

Some entries look nearly identical from the golfer's side but have different causes and different fixes. When a fix has been applied properly and has not helped, the most likely explanation is not that the fix was wrong. It is that the diagnosis was.

The table below lists which entries are commonly mistaken for which. When the feedback loop records a fix as "no change" after the minimum sample size, the tool should offer the confusable neighbour rather than a second fix from the same entry.

| Entry | Commonly confused with | What separates them |
|---|---|---|
| F011 shank | F013 heel strike | Shank hits the hosel and fires sharply right. Heel strike stays on the face, just loses ball speed and fades. Check the face marking. |
| F008 thin | F009 top | Degree, not kind. Thin still gets airborne, top does not. |
| F001 slice | F002 pull-slice, F003 push-slice | Where it starts. Left means F002, right means F003, straight means F001. |
| F004 hook | F005 pull, F002 pull-slice | Whether it curves. A pull goes straight left with no curve. |
| F001 slice | L001 ball below feet | If it only happens on that lie, it is the lie. |
| F004 hook | L002 ball above feet | Same test. |
| F007 fat | F015 chunked chip | Same fault, different context. Full swing versus short game, and the fixes differ. |
| F015 chunked chip | D001 decelerated | Did the club hit the ground first, or was the strike clean but gutless? |
| F017 weak high flight | F014 toe strike | Check the face marking before assuming a swing fault. |
| D003 wrong club short | C001 cold, F017 distance loss | Conditions and strike quality both mimic a club selection error. |
| D004 wrong club long | L006 flyer lie | A flyer from light rough is not over-clubbing. |
| P001 putt short | P003 misread, P004 pace and break | A putt finishing short and low may have had a perfect read. |
| P001, P002 | P006 green speed | If it is happening all round, it is calibration, not stroke. |
| F008 thin, F007 fat | L004 downhill lie | Contact misses from a downhill lie are expected and should be discounted. |

**The escalation rule.** After a fix is logged as no change or worse, and the sample size threshold has been met, the tool should say so plainly and name the alternative. Something like: "That fix has not moved the needle over 40 shots. This might not be a shank at all. Heel strikes feel almost the same. Check where the ball is marking the face."

Naming the uncertainty is better than quietly serving another fix, because it teaches the golfer the distinction rather than just handing them a new drill.

## Language rules for anything the tool says

The advice is worthless if it cannot be applied standing over a ball.

- **One thought at a time.** Never more than one swing thought per shot. This is one of the better-supported findings in motor learning.
- **Short.** A sentence or two. If it needs a paragraph, it is a range thought, not a course thought.
- **External over internal.** Describe the effect, not the body part. "Brush the grass after the ball" beats "shift your weight forward through impact." Also better supported by the evidence.
- **Plain words.** No face-to-path, no dynamic loft, no low point, unless the golfer has asked for the mechanics.
- **Say the uncertainty out loud.** "This might be X rather than Y" is more useful than false confidence, and it is what makes the escalation rule work.

## Multi-cause entries stay multi-cause

Every entry lists several causes deliberately. Retrieval returns the whole entry, and the distinguishing signals are what narrow it down on the day. Do not collapse these into single causes to make the output tidier.

## Decision quality is logged separately from outcome

A hero recovery that comes off was still a bad bet. If the tool learns from outcomes alone, it will teach you to gamble. This applies to S003 and R001 particularly.

## Gaps still open

- Bunker play beyond D005: plugged lies, downhill lies in sand, long bunker shots
- Wind-specific shot-making: knockdowns, holding a shot against a crosswind
- Trajectory control as a deliberate skill rather than a miss
- Mental and pressure effects, which are real but sit outside what this corpus should try to diagnose

Add these once v1 is retrieving well. Do not expand the corpus before measuring it, or you will not know which changes helped.

