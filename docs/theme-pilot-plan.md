# Theme Pilot Plan

Plan for the first theme pass over five sermons (DT-259, DT-273). Nothing here has been built or run. Boundaries are in DT-273: the passage is fixed first and themes come from the sermon, never the other way. Every model result is a suggestion until Paul or pastoral staff approve it.

## Goal

Learn whether a model's theme suggestions are good enough to review, and what the first approved theme list should be. The pilot does not publish anything.

## The Five Sermons

Picked for spread: preacher, genre, year and series frame. All are published, with a current transcript in the dev database.

| Date | Preacher | Passage | Title (series) | Words | Why |
| --- | --- | --- | --- | --- | --- |
| 2026-11-08 | Donny Cho | Genesis 13:1-18 | Money as an Idol (A Culture of Giving) | 8,156 | Already read closely. Clear subject. Calibration case. |
| 2022-11-13 | Joshua Kim | Judges 3:12-30 | Ehud's Weakness (God's Presence in Our Brokenness) | 5,243 | Old Testament narrative. Series title may read as a theme and is not. |
| 2024-03-24 | Andrew Pae | Luke 23:32-43 | Palm Sunday: The Suffering of the King (Lent: Luke) | 5,564 | Gospel narrative with a season frame. Lent and Palm Sunday must not become themes. |
| 2019-12-29 | Brian Park | Genesis 18:16-33 | Abraham's Prayer (The Blueprint of Redemption) | 5,187 | Prayer is both a frame and a subject here. Tests the difference. |
| 2018-09-02 | Donny Cho | Ephesians 5:21-33 | Marriage as Submission (The Gospel and Marriage) | 7,357 | Epistle, hard topic, one of 8 sermons on this passage. |

Total about 31,500 words. Swap any of them if you prefer. The set has no Psalm or wisdom text. Say if you want one.

## Step 1: Paul Writes Themes First

Before the model runs, Paul writes the themes he would give each sermon: 2 to 5 per sermon, short labels, and one line on why. A plain file is enough. This is the measuring stick. The model's output is not shown until this is done.

## Step 2: Prompt

One call per sermon. Inputs:

- The authored passage and series, as context only.
- The edited transcript, split into paragraphs with their IDs (`p001`, and so on). The standard Metro Podcast opening is left in. The prompt says to ignore it.
- A theme vocabulary: none in the pilot. The model proposes labels freely.

Output, as JSON checked by code:

```
{
  "themes": [
    {
      "label": "short noun phrase",
      "why": "one sentence",
      "evidence": [ {"paragraph_id": "p013", "quote": "exact words from that paragraph"} ],
      "confidence": "high | medium | low"
    }
  ],
  "none_reason": "set only when themes is empty"
}
```

Prompt rules:

1. The passage is given. Do not infer or change it. Do not output any scripture reference as a finding.
2. A theme is a subject the sermon addresses in this passage. Series names, seasons and campaign labels are frames, not themes.
3. A passing mention is not a theme. A theme needs development in at least two places, or a clear statement by the preacher.
4. Quote exact words. Every theme needs 1 to 3 quotes, each from one paragraph.
5. Return the fewest themes that are well supported. Returning none is allowed, with a reason.
6. Do not say what the preacher "believes". Say what the sermon addresses.

Code checks, with no model involved:

- Each quote must appear in the cited paragraph, in either the edited or raw text. A theme with a failed quote is dropped and logged.
- Each `paragraph_id` must exist.

## Step 3: Compare

For each sermon, line up Paul's themes with the model's. Paul marks each model theme as one of: agrees, close (different words, same subject), wrong, or frame (a series or season label). Paul also marks each of his own themes the model missed.

Numbers to report:

- Agreed or close, as a share of the model's themes.
- Wrong and frame, as a share of the model's themes.
- Paul's themes the model missed.
- Any theme with a failed quote check.

The pilot passes when Paul says he would review the output, not redo it. A rough bar: most model themes agree or are close, and wrong plus frame stays small. Paul sets the bar after seeing the first results. If it fails, change the prompt and rerun, keeping old rows.

## Step 4: First Theme List

Cluster the labels from all five sermons with Paul's. Paul and pastoral staff approve a first list, with a label and a one-line meaning for each. The handoff's starting hypotheses are suffering, money, repentance, humility and anxiety, with sin, prayer, idolatry, grace, mercy, providence, hope, kingship, weakness and worship as secondary. These come from about 64 sermon titles and are not confirmed. Use them as candidates only.

## Review Tool

A command-line queue first: show the theme, the quote, two paragraphs of context either side, and the audio time. Keys to approve, reject with a reason, or edit the label. A Center City page comes after the table design settles.

## What Gets Built

1. The prompt and a script that runs it on the five sermons and prints the result. No database writes yet.
2. The quote check and its tests.
3. A comparison sheet for Paul's labels.
4. After the pilot: the `theme` and `sermon_analysis` tables (DT-273) and the review queue.

## Cost

Prices are per million tokens, from the Claude API model table dated 2026-11-03. Check them before a large run. Batch processing is half price and runs asynchronously. Cached prompt text reads at about a tenth of the input price.

Estimates assume about 1.35 tokens per word, 3,000 tokens of prompt per sermon and 3,000 tokens of output per sermon, including thinking. These are guesses to be replaced by measured use.

| Model | Input | Output | Pilot, 5 sermons | All 692 | All 692, batch |
| --- | --- | --- | --- | --- | --- |
| Haiku 5.5 | $0.10 | $0.50 | under $0.05 | about $2 | about $1 |
| Sonnet 5.5 | $2 | $10 | about $0.30 | about $34 | about $17 |
| Opus 5.5 | $4 | $20 | about $0.55 | about $67 | about $34 |
| Fable 5.2 | $8 | $40 | about $1.10 | about $134 | about $67 |

The corpus is 4.5 million words, about 6.1 million tokens. Several prompt versions on five sermons stay under $25 even on Fable 5.2. The real cost of this work is review time, not model cost.

Running through the API needs an API key. Running through Claude Code subagents needs none but is slower and uses plan allowance.

## Risks

- **Intro and outro.** Every transcript opens with the standard podcast intro and the scripture reading. The prompt ignores the intro. Marking it in the data is DT-250.
- **Short transcripts.** 5 sermons have under 3,000 words and 1 has under 1,500. Check each is a full sermon before analysis.
- **Preacher skew.** Donny Cho preached 565 of 760 sermons. The first theme list will lean toward his preaching.
- **Mislabeling.** The main risk is calling a sermon "about" a theme it only mentions. The mention rule, the evidence rule and Paul's review address it. The quote check does not.
- **Duplicates.** Same passage in consecutive weeks is common. Each sermon is analyzed alone.

## Decisions Needed From Paul

1. Approve or swap the five sermons.
2. Write his themes for them before the model runs.
3. Choose the model for the pilot, and how to run it: API key, or Claude Code subagents.
