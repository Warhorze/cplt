# csvplot timeline - Tester Feedback

## Overall Impression

The tool feels solid for what it does. You type a command, you get a Gantt chart in your terminal. No browser, no fuss. The CLI is well-structured with clear help text, the `--x` start/end pair convention makes sense once you get it, and error messages are helpful when you mess up. It genuinely fills a niche that other terminal tools don't cover.

## What's Been Fixed Since Last Round

Several issues from the previous feedback session have been addressed:

- **Row stacking now works.** The main complaint last time was that rows sharing the same `--y` value got smashed into one line. That's fixed -- each CSV row now gets its own sub-row within a y-group, so even when all rows share `DH_FACING_NUMMER = 2006`, you can see each one separately. Big improvement.
- **`--y-detail` exists.** Previously suggested as a wish. Now you can do `--y-detail DN_BRONSLEUTEL` to sub-group within a y-label. Works well and makes dense charts readable.
- **`--head` filter added.** Previously you had to pre-filter your CSV externally. Now `--head 5` limits the rows read. Useful for quick exploration of large files.
- **Legend deduplication.** The old issue where "primary (120290146)" appeared three times per segment is gone. Each unique color_key + layer combo appears only once now.
- **Text label collision avoidance.** Labels no longer pile on top of each other blindly -- there's now truncation (to 15 chars) and a basic staggering system that alternates vertical offsets when labels are close in time.

## What Still Feels Off

### 1. Layer distinction is still too subtle

When using two layers (e.g. `--x START1 --x END1 --x START2 --x END2`), the visual difference between layer 0 (half-block `hd`) and layer 1 (filled half-block `fhd`) is hard to spot. They look nearly identical in most terminals. The vertical offset between layers (~0.45) helps, but when you're scanning a busy chart, your eye can't quickly tell "this is the primary range" vs "this is the secondary range." Some kind of more obvious differentiation would help -- different colors per layer, dashed vs solid, or at minimum a clearer marker style contrast.

### 2. The title is always just "csvplot"

Every chart says "csvplot" at the top. That's not useful once you know what tool you're using. I'd rather see the filename or the `--y` column name there, something that tells me what I'm actually looking at. When you're running multiple plots in a row to compare things, they all look the same at the top.

### 3. No way to zoom into a time range

If your data spans 2 years but you care about a specific month, you're stuck looking at the full range. There's a `view_start`/`view_end` on the `PlotSpec` dataclass but no CLI flags to set them. Something like `--from 2025-01-01 --to 2025-03-01` would be really handy for focusing on a slice.

### 4. The `--x` convention is not immediately obvious

The first time I used it, I instinctively typed `--x START END` (two values after one flag). But it's actually `--x START --x END`. This works fine once you know, but the help text could do a better job explaining it upfront. The error message when you give only one `--x` is clear ("requires at least 2 values"), but you have to fail first to learn the pattern. A short example in the help output would save time.

### 5. No color when `--color` is not specified

Without `--color`, everything is white (or gray for secondary layers). With only a few y-groups this is fine, but with more it would be hard to visually follow which bar belongs to which group. Auto-coloring by y-group when no `--color` is given would make the default output more useful.

### 6. Legend says "primary" / "layer 1" -- means nothing to the user

The legend labels like "primary (120290146)" or "layer 1 (117987179)" use internal terminology. As a user, I don't think in terms of "primary" and "layer 1", and the number next to it is just the raw value from the `--color` column with no context. I see "primary (120290146)" and I have no idea what 120290146 refers to -- is that an article? A store? A variant? The legend doesn't tell me which column that value came from, so it's just a mystery number. At minimum it should show the column name, e.g. "SH_ARTIKEL_S1: 120290146". Even better would be replacing the layer jargon with the actual column pair names, e.g. "DH_PV_STARTDATUM - DH_PV_EINDDATUM (SH_ARTIKEL_S1: 120290146)".

### 7. The `--marker-label` without `--marker` silently does nothing

If you accidentally pass `--marker-label "Release"` without `--marker`, it's just ignored. Not a big deal, but a small warning would prevent confusion.

### 8. `--txt` label positioning is inconsistent

The text labels from `--txt` jump around vertically -- sometimes they sit right on the bar, other times they float above or below it. When you're scanning a chart with multiple segments, your eye has to hunt for which label belongs to which bar. The staggering logic helps avoid overlaps, but the result looks messy because labels at different vertical offsets don't feel visually "attached" to their segment anymore. It would feel much cleaner if labels were consistently placed -- either always on the bar or always directly above it -- even if that means some labels get dropped when they'd collide.

### 9. Multiple `--y` feels like it should create separate groups, not concatenate

When I do `--y DH_FACING_NUMMER --y SH_FORMULE`, the values get joined as "4006 | 181". That's one valid behavior, but my instinct was that it would create two levels of grouping (facing within formule, or vice versa). The concatenation works but feels like a flat string join rather than a structured grouping. This might just need clearer documentation about what multiple `--y` actually does.

## What Works Well

- **Error handling is excellent.** Wrong column name, missing file, odd number of `--x` values, unparseable marker date -- every case I tried gave a clear, colored error with no traceback. Very polished.
- **`--no-open-end` is useful.** Toggling between "extend NULLs to today" and "skip them" changes the chart meaningfully and both modes work correctly. Good default to have open-end on.
- **Marker looks good.** The red vertical line with label renders cleanly and stands out. Nice for highlighting reference dates.
- **The y-detail feature is the right abstraction.** Rather than forcing complex y-axis logic, `--y-detail` lets you add one more dimension when you need it. Simple and effective.
- **`--head` is great for exploration.** Being able to quickly peek at the first N rows before committing to a full render is exactly the kind of workflow shortcut a CLI tool should have.
- **Help text organization.** The Formatting/Filtering panels in `--help` make it easy to scan. Required options are clearly marked.
- **Sub-row stacking.** Now that rows with the same y-value get their own visual lanes, the chart is genuinely useful for real data. This was the blocker last round and it's fixed well.
