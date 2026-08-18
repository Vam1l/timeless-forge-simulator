# Timeless Forge Simulator

A reproducible wrapper around [Forge](https://github.com/Card-Forge/forge)'s headless AI-vs-AI simulation mode for testing Magic: The Gathering Timeless matchups.

## What this MVP does

- validates Forge `.dck` files (60-card main deck and up to 15-card sideboard)
- runs pre-board and post-board matchup batches
- materializes post-board decks from explicit sideboard plans
- saves raw Forge logs plus JSON, CSV, and Markdown summaries
- reports win rate and a 95% Wilson confidence interval
- includes a deterministic mock engine so the full pipeline can be tested without Forge

Forge is the rules and gameplay engine; this project orchestrates experiments and analyzes results. Forge's AI is heuristic. Its own documentation warns that it is strongest with aggro/midrange, weaker with control, and poor with many combo decks. Simulation results are therefore directional evidence—not tournament truth.

## Requirements

- Python 3.11+
- Java 17+
- a current Forge desktop installation containing `forge.jar`

## Quick start

```bash
python -m timeless_forge validate examples/decks
python -m timeless_forge run examples/experiment.json --forge-jar /path/to/forge.jar
```

To verify the project before installing Forge:

```bash
python -m unittest discover -s tests -v
python -m timeless_forge run examples/experiment.mock.json --mock
```

Results are written to `results/<run-id>/` unless `output_dir` is set in the experiment file.

## Forge command used

The runner invokes Forge's documented simulation interface:

```bash
java -jar forge.jar sim -d DeckA.dck DeckB.dck -D /absolute/deck/directory -n 100 -q -c 120
```

For post-board testing, it creates temporary `.dck` files after applying the configured `in`/`out` plan, then runs those files through the same Forge engine.

## Experiment format

See [`examples/experiment.json`](examples/experiment.json). Each matchup specifies two decks, pre-board games, post-board games, and optional sideboard plans. Card names must match the deck file exactly; quantities are expanded automatically.

```json
{
  "name": "Mardu metagame trial",
  "games_preboard": 100,
  "games_postboard": 200,
  "clock_seconds": 120,
  "matchups": [
    {
      "deck_a": "mardu-energy.dck",
      "deck_b": "dimir-tempo.dck",
      "sideboard_a": {"in": ["2 Suncleanser"], "out": ["2 Thoughtseize"]},
      "sideboard_b": {"in": [], "out": []}
    }
  ]
}
```

## Interpreting results

- Run at least 400–1,000 games per configuration for narrower sampling error.
- Treat mirrors and straightforward creature matchups as more credible than stack-heavy control or combo.
- Review raw logs for loops, timeouts, unimplemented cards, and systematic AI misplays.
- A 50% result over 400 decisive games has a roughly ±4.9 percentage-point 95% interval before accounting for AI/model bias.
- Arena-specific cards or mechanics may lag in Forge. Validate card availability before relying on a matchup.

## Manual GitHub upload

Extract the ZIP. On the empty GitHub repository page, choose **uploading an existing file**, then upload the *contents* of the `timeless-forge-simulator` folder—not the ZIP itself. GitHub's mobile browser may not preserve folders reliably; a desktop browser is recommended.

## Roadmap

- structured parsing against pinned Forge output fixtures
- automated alternating seat/order experiments if Forge exposes a stable flag
- metagame-weighted aggregate scores
- mulligan/decision diagnostics from logs
- card implementation audit against Forge data
- web dashboard and parallel workers

## Licensing

This wrapper is MIT licensed. Forge is a separate GPL-3.0 project and is not bundled here.
