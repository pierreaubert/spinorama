# CEA2034 extraction QA

Corpus: `src/graphextract/datas/graph-cea2034` (18 graphs; the QA
gate pins 17, JBL M2 is legend-free and documented below).
QA gate: `src/graphextract/tests/test_qa_cea2034.py::test_cea2034_graph_measures_families`
(parametrized per graph; generic rules only — curve families, observed
support floors, DI-on-right-axis, right axis displaying the core DI
band). Printed DI spans vary by vendor (PMC 0..50, Danley -5..15,
Harman/Erin/ASR near -10..40), so the gate checks the core band, not
one window.
No per-graph extraction logic is allowed to satisfy it; only the
per-graph expected family sets are test data.

Slow by design (full OCR + extraction per graph); the fast suite skips it:

    pytest src/graphextract/tests -q --ignore=src/graphextract/tests/test_qa_cea2034.py

## Generic mechanisms (no custom features)

- Band-split steering: DI ink lives in its own offset band; dB-claimed
  ink is masked for DI re-tracks and above-split rows are avoided seeds.
- Twin-paint adoption (`snap_legend_seeds`): a DI key takes its
  same-family twin's paint only when that paint inks two separated
  bands. A chromatic paint must show chromatic ink in both bands
  (`_paint_two_banded` voter gate): achromatic impostor pixels (tick
  digits, text halo, grid dots) inside a dark paint's tolerance box
  used to fake a second band and steal DI keys (e.g. Paradigm Persona
  SPDI black key adopted Sound-Power purple, latched the dB pack, and
  its spurious offset vetoed the right-axis identity). Each band's
  median paint must also agree within one box radius: two different
  paints sharing a loose box (teal dB upstairs, grey-green DI
  downstairs) are not one shared paint.
- Sibling adoption is directional: dB keys never adopt a
  directivity sibling's paint (they measure their own band first; a
  washed dB key starves honestly instead of latching the DI band and
  starving its twin). This unblocked Aoshida/Danley DI ink that
  drifted-colour dB tracks had claimed first.
- Split enforcement (`_enforce_db_split`, `_enforce_di_split`): the
  evidence split separates the bands by construction, so a track
  whose median sits fully on the wrong side re-tracks fenced into
  its home band when a same-family or same-paint twin exists
  (dashed twins seed the far band first and never come back). The
  keep-condition (lands home with solid support) is the backstop;
  otherwise samples stay and flag. Replacements keep label/panel_id.
- Straddle-skip in the offset proof: a DI track straddling the split
  (p10 above, p90 below) never votes — one offset cannot explain ink
  from both bands, and the majority band games the IQR into a
  spurious tight solve that would veto the family curves.
- Thin-sample demotion: an unsolvable directivity track (fewer
  observed samples than the solvers need, no stated offset) goes
  missing honestly; the series stays for review instead of shipping
  junk points.
- Consensus offset proof (`_recover_di_right_axis`): the DI offset
  identity is proven only when solved offsets agree within 2 dB;
  disagreement keeps the anchored right-axis fit (safe fallback) and
  flags for review.
- Commitment taint-penalty + deferral/pin, over-claim eviction,
  supplement pruning, family-less marker pool exclusion.

## Known gaps (honest misses, flagged in reviews)

- Neumann: the two `Listening`/`Window` halves of one split legend
  entry both track full-height (spanning bands, .34/.44); ERDI is
  weak (.07, dashed); SP keeps a low interpolation tail (52.5dB);
  the `DI offset` marker rides onto the right axis.
- Aoshida: SPDI is an honest miss (washed grey key starved, then a
  cross-family sibling adoption it cannot use; its 2 junk points go
  missing via thin-sample demotion).
- Danley: SPDI is a fragment (.03, thin pale ink shared rows with
  ERDI); dB support dipped where the restored SP now overlaps
  siblings (shared ink honestly demoted); the literal `N/A` entry
  starves to zero.
- Sovox: thin lines, only 2 right-axis anchors — no right axis, weak
  ER (.34), DI label stays on dB.
- JBL M2: legend-free; hue-peak supplement seeds only, no DI axis.
- Weak-but-sane members pinned by floors: Aiyima LW (.25, ER gap),
  CWM SP (.30), LSR ER (.22), Devialet marker (.02, rides harmlessly).

## Per-graph results (post-fix sweep)

Outcome is `PARTIAL_REVIEW` everywhere (reviews always carry notes);
the axis column is the right-axis method plus its span over the panel.
Support is observed fraction per family. DI families read on y_right
in dB; recovered spans match the printed ticks where verified (PMC
0..50, Danley -5..15 with ERDI reading 0..6 against it).

| graph | right axis | dB families (support) | DI families (support) | notes |
|---|---|---|---|---|
| ascilab-c6b | identity 40.3, (-0.5, 49.7) | sp .88 lw/er/on .5-.9 | spdi .50 erdi .48 | both DI on right |
| aiyima-s400 | identity 40.5, (-2.8, 47.5) | on .77 sp .62 er .61 lw .27 | spdi .22 erdi .32 | ER gap (lw weak) |
| devialet | identity 50.5, (-5.8, 44.4) | on .82 lw .48 er .71 sp .62 spdi .33 erdi .26 | marker .02 | marker rides, harmless |
| topping-m4a | identity 40.5, (-5.8, 44.4) | all .6-.8 | spdi .23 erdi .33 | |
| cwm7.5 | identity 60.2, (-10.3, 40.0) | pir .90 er .65 lw .46 on .45 sp .30 | erdi .65 spdi .72 | sp weak; span ≈ printed -10..40 |
| lsr708i | identity 55.0, (-5.2, 45.3) | sp .70 lw .76 er .22 | spdi .98 erdi .95 | ER weak; no onaxis label in graph |
| m2 | none | supplement .70-.99 | — | legend-free; no DI axis (documented) |
| persona3f | identity 50.0, (-5.6, 45.0) | sp .88 er .98 lw .88 on .93 | spdi .93 erdi .99 | fixed: was clamped latch |
| neumann-kh80 | identity 38.6, (-4.2, 46.5) | on .71 er .64 lw .34/.44 sp .53 | spdi .79 erdi .07 | fixed: SP/DI bands converged; LW split entries span; ERDI weak |
| aoshida-knight | identity -40.0, (-5.1, 45.1) | on .67 lw .87 er .77 sp .76 | erdi .68 | SP unlatched; SPDI honest miss |
| danley-sm100f | identity -35.0, (-5.1, 45.1) | on .72 lw .82 er .87 sp .81 | erdi .72 | N/A honest miss; SPDI fragment; dB support dipped via dup-claims |
| pmc10-4/10/12/15-xbd/15 | identity 70.0, (0.0, 50..52) | all .8-1.0 | di/erdi .95-.99 | span matches printed 0..50 ticks (verified on pmc12 image) |
| revel-f228 | stated 45, (-0.5, 49.9) | on .77 lw .87 er .62 sp .71 | spdi .99 | |
| sovox-minimax3 | none | on .75 er .34 | erdi label on dB | thin lines, 2 anchors only (documented) |
