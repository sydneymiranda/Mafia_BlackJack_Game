"""
The boss mechanic: reach a target bankroll within a number of rounds,
or the run resets. Hitting the target raises the stakes for next time.
No UI code here — gui.py calls evaluate_round() after each hand.
"""

import database
import constants as C

SHOP_ITEMS = {
    "peek": {
        "name": "Peek",
        "price": 75,
        "desc": "Reveal the dealer's hidden card immediately.",
    },
    "sharp_eyes": {
        "name": "Sharp Eyes",
        "price": 150,
        "desc": "The dealer can't cheat you this round.",
    },
    "insurance": {
        "name": "Insurance Voucher",
        "price": 100,
        "desc": "Halves your loss if you bust or lose this round.",
    },
}


def target_for_level(level):
    return C.BASE_LOAN_TARGET * level


def rounds_for_level(level):
    return max(C.MIN_LOAN_ROUNDS, C.BASE_LOAN_ROUNDS - (level - 1))


def npc_count_for_level(level):
    return min(C.MAX_NPCS, (level - 1) // 2)


def cheat_chance_for_level(level):
    return min(0.5, 0.08 * (level - 1))


def evaluate_round(user_id, balance):
    """Call once after a round fully resolves. Returns:
        {"event": "success"|"failed"|"continue", "message": str, "loan_level": int}
    """
    state = database.get_loan_state(user_id)
    loan_level = state["loan_level"]
    target = state["target"]
    rounds_left = state["rounds_left"] - 1

    if balance >= target:
        new_level = loan_level + 1
        new_target = target_for_level(new_level)
        new_rounds = rounds_for_level(new_level)
        database.set_loan_state(user_id, new_level, new_target, new_rounds)
        return {
            "event": "success",
            "message": f"Target hit! The boss ups the stakes — level {new_level}, ${new_target} next.",
            "loan_level": new_level,
        }

    if rounds_left <= 0:
        database.reset_run(user_id)
        return {
            "event": "failed",
            "message": "You didn't make the number. The boss doesn't forgive debts — starting over.",
            "loan_level": 1,
        }

    database.set_loan_state(user_id, loan_level, target, rounds_left)
    return {
        "event": "continue",
        "message": f"{rounds_left} round(s) left to reach ${target}.",
        "loan_level": loan_level,
    }


def buy_item(user_id, item_id):
    """Returns (ok, message)."""
    item = SHOP_ITEMS.get(item_id)
    if item is None:
        return False, "Unknown item"
    balance = database.get_balance(user_id)
    if balance < item["price"]:
        return False, "Not enough cash"
    database.set_balance(user_id, balance - item["price"])
    database.add_item(user_id, item_id)
    return True, f"Bought {item['name']}"
