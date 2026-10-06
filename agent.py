"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
import re
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool, MCPError


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:

    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    # Start the session
    session = new_session(query, wardrobe)

    # Clear the trace so each run stands alone. app.py and run_eval.py also
    # call this, but `python agent.py` runs two queries back to back — without
    # it, the second run's get_trace() would still carry the first run's lines.
    trace.start_trace()

    # Define a variable count that will count the number of iterations.
    count = 0

    while True:
        count += 1

        # Safety mechanism for the loop not end up in infinit loop. 
        trace.check_iterations(count)

        # Parse the query
        size_match = re.search(
            r"\bsize\s+([A-Za-z0-9]+)",
            query,
            re.IGNORECASE,
        )

        price_match = re.search(
            r"\b(?:under|below|less than)\s*\$?(\d+(?:\.\d+)?)",
            query,
            re.IGNORECASE,
        )

        size = size_match.group(1) if size_match else None
        max_price = float(price_match.group(1)) if price_match else None

        description = query

        if size_match:
            description = description.replace(size_match.group(0), "")

        if price_match:
            description = description.replace(price_match.group(0), "")

        description = description.strip(" ,")

        session["parsed"] = {
            "description": description,
            "size": size,
            "max_price": max_price,
        }

        # inputs is passed as a STRING, not a dict: trace._short() prints only
        # the KEYS of a dict, so {"size": "M"} would render as "dict with keys:
        # size" and the value would be lost.
        trace.step(
            "parse_query",
            inputs=query,
            returned=f"description={description!r}, size={size}, max_price={max_price}",
            note="regex on 'size X' and 'under $N'",
        )

        # Search listings — over MCP (unit 4, Milestone 1) instead of the
        # direct call. Arguments go by NAME now, and the names have to match
        # the registration in mcp_server.py exactly.
        #
        # The direct call this replaced, kept for comparison:
        #     search_results = search_listings(description, size, max_price)
        try:
            search_results = call_tool("search_listings", {
                "description": description,
                "size": size,
                "max_price": max_price,
            })
        except MCPError as exc:
            trace.step("search_listings (via MCP)", note=f"server unreachable: {exc}")
            session["error"] = f"Couldn't reach the listings server — {exc}"
            return session

        session["search_results"] = search_results

        # returned is passed RAW — _short() renders a list of listings as
        # "10 items: <titles>" and an empty list as "[] (empty)".
        trace.step(
            "search_listings (via MCP)",
            inputs=f"description={description!r}, size={size}, max_price={max_price}",
            returned=search_results,
        )

        # Branch: no results
        if not search_results:
            # The graded decision. Recording it is what turns "no fit card was
            # produced" into evidence that the branch deliberately stopped.
            trace.step(
                "branch: search returned nothing",
                note="stopping — suggest_outfit and create_fit_card will NOT run",
            )
            session["error"] = (
                "No matching listings were found. "
                "Try changing the size, increasing the maximum price, "
                "or using broader search terms."
            )
            return session

        # Select first result
        selected_item = search_results[0]
        session["selected_item"] = selected_item

        trace.step(
            "select_item",
            inputs=f"{len(search_results)} candidates",
            returned=selected_item,
            note="first result — highest keyword score",
        )

        # Suggest outfit
        outfit = suggest_outfit(selected_item, wardrobe)
        session["outfit_suggestion"] = outfit

        trace.step(
            "suggest_outfit",
            inputs=f"item={selected_item.get('title')!r}, "
                   f"wardrobe_items={len(wardrobe.get('items', []))}",
            returned=outfit,
        )

        # Create fit card
        fit_card = create_fit_card(outfit, selected_item)
        session["fit_card"] = fit_card

        trace.step(
            "create_fit_card",
            inputs=f"item={selected_item.get('title')!r}, outfit={outfit[:40]!r}…",
            returned=fit_card,
        )

        return session
    


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )