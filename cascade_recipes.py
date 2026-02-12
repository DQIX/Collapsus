import json
from collections import Counter
from dataclasses import dataclass

import parsers

with open("data/recipes.json", "r", encoding="utf-8") as data:
    recipes_data = json.load(data)["recipes"]

with open("data/item_locations.json", "r", encoding="utf-8") as data:
    location_data = json.load(data)["locations"]

_RECIPES_BY_NAME = {r["result"].strip().lower(): r for r in recipes_data if r.get("result")}
_LOC_BY_NAME = {l["result"].strip().lower(): (l.get("location") or []) for l in location_data if l.get("result")}


@dataclass(frozen=True)
class CascadeRecipe:
    name: str
    type: str = ""
    notes: str = ""
    image: str = ""
    alchemiracle: bool = False
    location: list[str] | None = None


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def has_recipe(name: str) -> bool:
    return _norm(name) in _RECIPES_BY_NAME


def get_location(name: str) -> list[str]:
    return list(_LOC_BY_NAME.get(_norm(name), []))


def get_recipe(name: str) -> CascadeRecipe | None:
    raw = _RECIPES_BY_NAME.get(_norm(name))
    if not raw:
        return None

    recipe = parsers.Recipe.from_dict(raw)
    loc = get_location(recipe.result)

    return CascadeRecipe(
        name=recipe.result,
        type=recipe.type or "",
        notes=recipe.notes or "",
        image=recipe.image or "",
        alchemiracle=bool(getattr(recipe, "alchemiracle", False)),
        location=loc,
    )


def get_direct_ingredients(name: str) -> list[tuple[str, int]]:
    raw = _RECIPES_BY_NAME.get(_norm(name))
    if not raw:
        return []

    out: list[tuple[str, int]] = []
    for i in range(1, 4):
        item = raw.get(f"item{i}") or ""
        qty = raw.get(f"qty{i}") or 0
        if item:
            try:
                q = int(qty)
            except Exception:
                q = 0
            out.append((item, q))
    return out


def sorted_counter_items(counter: Counter) -> list[tuple[str, int]]:
    return sorted(((k, int(v)) for k, v in counter.items() if v), key=lambda kv: _norm(kv[0]))


def _expand_one_tier(tier: Counter, max_expand_per_item: int, seen_stack: set[str]) -> Counter:
    out = Counter()

    for item_name, item_qty in list(tier.items()):
        qty = int(item_qty)
        if qty <= 0:
            continue

        key = _norm(item_name)
        if not has_recipe(item_name):
            out[item_name] += qty
            continue

        if key in seen_stack:
            out[item_name] += qty
            continue

        if qty > max_expand_per_item:
            expand_qty = max_expand_per_item
            remain_qty = qty - expand_qty
        else:
            expand_qty = qty
            remain_qty = 0

        if remain_qty:
            out[item_name] += remain_qty

        seen_stack.add(key)
        for child_name, child_qty in get_direct_ingredients(item_name):
            cq = max(int(child_qty), 0)
            if cq:
                out[child_name] += expand_qty * cq
        seen_stack.remove(key)

    for k in [k for k, v in out.items() if not v]:
        del out[k]
    return out


def get_equivalence_tiers(name: str, max_depth: int = 8, max_expand_per_item: int = 250) -> list[Counter]:
    if not has_recipe(name):
        return []

    t0 = Counter()
    for child_name, child_qty in get_direct_ingredients(name):
        q = max(int(child_qty), 0)
        if q:
            t0[child_name] += q

    tiers: list[Counter] = [t0]
    seen_stack: set[str] = set()

    for _ in range(max_depth):
        prev = tiers[-1]
        if not any(has_recipe(k) for k in prev.keys()):
            break

        nxt = _expand_one_tier(prev, max_expand_per_item=max_expand_per_item, seen_stack=seen_stack)
        if nxt == prev:
            break

        tiers.append(nxt)

    return tiers


@dataclass
class Ingredient:
    name: str
    count: int
    total: int
    level: int
    location: str
    type: str = ""


def cascade(search_input=""):
    ingredients, trail = [], []
    search_input = (search_input or "").lower()

    for recipe in _RECIPES_BY_NAME.values():
        if (recipe.get("result") or "").lower() == search_input:
            ingredients = _cascade_recursive(recipe.get("result"), 1, 1, ingredients, trail, 0)

    return ingredients


def _cascade_recursive(recipe, count, mult, ingredients, trail, level):
    if recipe is None:
        return ingredients

    if recipe in trail:
        ingredients.append(Ingredient(recipe, count, count * mult, level, ""))
        return ingredients

    raw = _RECIPES_BY_NAME.get(_norm(recipe))
    if raw:
        loc_list = get_location(recipe)
        recipe_type = raw.get("type", "")
        ingredients.append(
            Ingredient(recipe, count, count * mult, level, ", ".join(loc_list) if loc_list else "", recipe_type)
        )

        trail.append(recipe)
        for child_name, qty in get_direct_ingredients(recipe):
            try:
                q = int(qty)
            except Exception:
                q = 0
            _cascade_recursive(child_name, q, count * mult, ingredients, trail, level + 1)
        trail.pop()
        return ingredients

    loc_list = get_location(recipe)
    if loc_list:
        ingredients.append(Ingredient(recipe, count, count * mult, level, ", ".join(loc_list)))

    return ingredients
