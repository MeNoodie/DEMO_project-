from typing import Any, Dict


def get_structural_requirement(floors: int) -> int:
    if floors <= 1:
        return 4
    if floors == 2:
        return 6
    if floors == 3:
        return 8
    return 9


def get_priority_weights(priority: str) -> Dict[str, float]:
    weights = {
        "cooling": {"thermal": 0.4, "cost": 0.2, "sustainability": 0.4},
        "cost": {"thermal": 0.2, "cost": 0.5, "sustainability": 0.3},
        "sustainability": {"thermal": 0.3, "cost": 0.2, "sustainability": 0.5},
    }
    return weights.get(priority, weights["cooling"])


def get_cost_score(budget: str) -> int:
    return {
        "low": 9,
        "moderate": 6,
        "high": 3,
    }.get(budget, 6)


def get_rainfall_factor(rainfall: str) -> int:
    return {
        "low": 3,
        "medium": 6,
        "high": 9,
    }.get(rainfall, 5)


def get_speed_requirement(timeline: str) -> int:
    normalized = {
        "flexible": "flexible",
        "standard": "moderate",
        "moderate": "moderate",
        "fast_track": "fast",
        "fast": "fast",
    }.get(timeline, "moderate")

    return {
        "flexible": 3,
        "moderate": 6,
        "fast": 9,
    }[normalized]


def adjust_tradeoff(tradeoff: str) -> Dict[str, int]:
    if tradeoff in {"cost_over_sustainability", "cost", "lower upfront cost"}:
        return {"cost_bonus": 2, "sustainability_bonus": 0}
    if tradeoff in {"sustainability_over_cost", "sustainability", "long-term sustainability"}:
        return {"cost_bonus": 0, "sustainability_bonus": 2}
    return {"cost_bonus": 0, "sustainability_bonus": 0}


def get_climate(location: str) -> str:
    text = location.lower()
    tropical_states = [
        "jharkhand",
        "bihar",
        "odisha",
        "west bengal",
        "assam",
        "kerala",
        "tamil nadu",
    ]

    for state in tropical_states:
        if state in text:
            return "tropical"
    return "moderate"


def compute_project_requirements(user_input: Dict[str, Any]) -> Dict[str, Any]:
    floors = int(user_input.get("floors", 1))
    budget = user_input.get("budget_level", user_input.get("budget", "moderate"))
    priority = user_input.get("priority", "cooling")
    rainfall = user_input.get("rainfall", "medium")
    timeline = user_input.get("timeline", "standard")
    tradeoff = user_input.get("cost_preference", user_input.get("tradeoff", "balanced"))
    location = user_input.get("location", "")
    material_tone = user_input.get("material_tone", "balanced")

    structural_req = get_structural_requirement(floors)
    cost_score = get_cost_score(budget)
    rainfall_factor = get_rainfall_factor(rainfall)
    speed_req = get_speed_requirement(timeline)
    weights = get_priority_weights(priority)
    climate = get_climate(location)
    tradeoff_adj = adjust_tradeoff(tradeoff)

    thermal_index = round((rainfall_factor * 0.35) + (weights["thermal"] * 10), 2)
    eco_index = round((weights["sustainability"] * 10) + tradeoff_adj["sustainability_bonus"], 2)
    budget_pressure = round((cost_score * 0.7) + (tradeoff_adj["cost_bonus"] * 0.8), 2)
    constructability_index = round((speed_req * 0.6) + (structural_req * 0.4), 2)

    if material_tone == "natural":
        suggested_family = "bio-based composites, stabilized earth blocks, engineered bamboo"
    elif material_tone == "high_performance":
        suggested_family = "AAC blocks, geopolymer concrete, high-performance insulation systems"
    else:
        suggested_family = "hybrid palette combining local low-carbon and engineered materials"

    return {
        "structural_requirement": structural_req,
        "cost_sensitivity": cost_score,
        "rainfall_risk": rainfall_factor,
        "speed_requirement": speed_req,
        "thermal_weight": weights["thermal"],
        "cost_weight": weights["cost"],
        "sustainability_weight": weights["sustainability"],
        "climate": climate,
        "tradeoff_adjustment": tradeoff_adj,
        "engineering_indices": {
            "thermal_performance_index": thermal_index,
            "budget_pressure_index": budget_pressure,
            "eco_priority_index": eco_index,
            "constructability_index": constructability_index,
        },
        "suggested_material_family": suggested_family,
    }
