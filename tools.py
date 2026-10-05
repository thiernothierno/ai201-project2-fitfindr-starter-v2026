"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings, get_example_wardrobe







# ── Tool 1: search_listings ───────────────────────────────────────────────────
"""
TODO: 
    1. Load every listing with load_listings(). 
    2. Filter by max_price and by size, when each is provided. 
    3. Score what's left by keyword overlap with description. 
    4. Drop anything scoring zero. 
    5. Sort by score, highest first, and return the listing dicts — at most config.SEARCH_RESULT_LIMIT of them. 
    Test it from a terminal before you move on: 
    python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

"""

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    # Filter
    filtered = []

    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue

        if size is not None and listing["size"] != size:
            continue

        filtered.append(listing)

    # Score by keyword overlap
    query_words = set(description.lower().split())
    results = []

    for listing in filtered:
        description_words = set(listing["description"].lower().split())
        score = len(query_words & description_words)

        if score > 0:
            results.append((score, listing))

    # Highest score first
    results.sort(key=lambda item: item[0], reverse=True)

    # Return listing dictionaries only
    # results[:config.SEARCH_RESULT_LIMIT] take the first N results, where N is SEARCH_RESULT_LIMIT
    return [
        listing
        for score, listing in results[:config.SEARCH_RESULT_LIMIT]
    ]
# print(search_listings('graphic tee', max_price=15))

# print(search_listings("Classic 501s in a perfect medium wash. Some light fading at the knees which adds to the vintage look. No rips or stains.", 
#                       size="W30 L30", max_price=38.00))


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.
    """

    items = wardrobe.get("items", [])

    # Empty wardrobe: give general styling advice
    if not items:
        prompt = f"""
        You are a helpful personal stylist.

        The user is considering this thrifted item:

        Name: {new_item.get("name", "")}
        Category: {new_item.get("category", "")}
        Colors: {", ".join(new_item.get("colors", []))}
        Style tags: {", ".join(new_item.get("style_tags", []))}
        Notes: {new_item.get("notes", "")}

        The user does not have any wardrobe items entered yet.
        Suggest one or two ways they could style this item in general.
        Mention suitable types of tops, bottoms, shoes, and accessories.
        Do not assume they own any specific pieces.

        Give practical, concise styling advice.
        """

        return generate(prompt)

    # Non-empty wardrobe: format the user's existing items
    wardrobe_items = []

    for item in items:
        wardrobe_items.append(
            f"- {item.get('name', '')} "
            f"(category: {item.get('category', '')}, "
            f"colors: {', '.join(item.get('colors', []))}, "
            f"style: {', '.join(item.get('style_tags', []))}, "
            f"notes: {item.get('notes', '')})"
        )

    wardrobe_text = "\n".join(wardrobe_items)

    prompt = f"""
    You are a helpful personal stylist.

    The user is considering this thrifted item:

    Name: {new_item.get("name", "")}
    Category: {new_item.get("category", "")}
    Colors: {", ".join(new_item.get("colors", []))}
    Style tags: {", ".join(new_item.get("style_tags", []))}
    Notes: {new_item.get("notes", "")}

    Here is the user's existing wardrobe:

    {wardrobe_text}

    Suggest one or two complete outfits that combine the new item with
    pieces the user already owns.

    Use the exact names of wardrobe pieces when recommending them.
    Do not invent wardrobe items that are not listed above.

    Keep the suggestions practical and concise.
    """

    return generate(prompt)

# print(suggest_outfit(load_listings()[0], get_example_wardrobe()))

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # TODO: replace this with your implementation
    # 1. Handle missing outfit
    if not outfit or not outfit.strip():
        return "No outfit suggestion is available for this item yet."

    # 2. Build prompt using the item AND the outfit
    prompt = f"""
    Write a short caption for this thrift find.

    Item: {new_item.get("name", "")}
    Price: {new_item.get("price", "")}
    Platform: {new_item.get("platform", "")}

    Suggested outfit:
    {outfit}

    Write 2-4 sentences.
    Mention the item, price, and platform once each.
    Make it sound like a real social media post and describe the vibe.
    """

        # 3. Ask the model
    return generate(prompt)


# ── scratch testing ───────────────────────────────────────────────────────────
# Anything that CALLS a tool belongs in here, never at module level. Module-level
# code runs on every import — including the import inside mcp_server.py, which
# would fire a model call on every single MCP request and print to stdout, the
# channel MCP uses for the protocol itself.
#
#     python tools.py        runs the checks below

if __name__ == "__main__":
    listing = load_listings()[0]
    print("search_listings('graphic tee', max_price=30):")
    for row in search_listings("graphic tee", max_price=30):
        print(f"  {row['id']}  ${row['price']:>6.2f}  {row['title']}")

    print("\ncreate_fit_card:")
    print(" ", create_fit_card("jeans and white sneakers", listing))