# Blackjack

A desktop Blackjack game with a Tkinter GUI. Standard library only — no installs needed.

## Run

```
python main.py
```

## Structure

- `card.py` — single `Card`
- `deck.py` — shuffled multi-deck shoe, auto-reshuffles when low
- `hand.py` — hand value logic (soft aces, blackjack, bust)
- `engine.py` — `GameEngine`: all rules and state (betting, dealing, hit/stand, payouts). No UI code — testable on its own.
- `gui.py` — `BlackjackGUI`: Tkinter view. Draws the table and forwards clicks to the engine.
- `main.py` — entry point

## Rules implemented

- 4-deck shoe, reshuffled automatically when it runs low
- Blackjack pays 3:2
- Dealer stands on 17+
- Chip betting ($10/$25/$50/$100) with a running balance
- Game ends when balance hits $0
