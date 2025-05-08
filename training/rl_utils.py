# training/rl_utils.py
import numpy as np
from typing import Dict, Tuple, List
from app.models.pet import PetNeeds  # Assuming models can be imported if needed for type hints

# --- Action Space Definition ---
# These are the abstract actions our RL agent can choose.
ACTIONS = [
    "feed_small",  # e.g., amount=15
    "feed_medium",  # e.g., amount=30
    "play_short",  # e.g., duration_effect=15
    "play_long",  # e.g., duration_effect=30
    "sleep_action",  # e.g., duration_effect=50 (simplified sleep)
    "clean_action",  # e.g., amount=40 (simplified clean)
    "do_nothing"  # Agent explicitly chooses to do nothing, time passes
]
NUM_ACTIONS = len(ACTIONS)

ACTION_MAPPING = {
    "feed_small": {"method": "feed", "params": {"amount": 15}},
    "feed_medium": {"method": "feed", "params": {"amount": 30}},
    "play_short": {"method": "play", "params": {"duration_effect": 15}},
    "play_long": {"method": "play", "params": {"duration_effect": 30}},
    "sleep_action": {"method": "sleep", "params": {"duration_effect": 50}},
    "clean_action": {"method": "clean", "params": {"amount": 40}},
    "do_nothing": {"method": None, "params": {}}  # Special case
}

# --- State Space Discretization ---
# Define bins for each need. More bins = larger state space.
HUNGER_BINS = [0, 25, 50, 75, 100]  # Upper bounds (exclusive for start, inclusive for end) -> 4 categories
HAPPINESS_BINS = [0, 25, 50, 75, 100]  # -> 4 categories
ENERGY_BINS = [0, 25, 50, 75, 100]  # -> 4 categories
CLEANLINESS_BINS = [0, 33, 66, 100]  # -> 3 categories

# Number of discrete states for each need
NUM_HUNGER_STATES = len(HUNGER_BINS) - 1
NUM_HAPPINESS_STATES = len(HAPPINESS_BINS) - 1
NUM_ENERGY_STATES = len(ENERGY_BINS) - 1
NUM_CLEANLINESS_STATES = len(CLEANLINESS_BINS) - 1

TOTAL_NUM_DISCRETE_STATES = NUM_HUNGER_STATES * NUM_HAPPINESS_STATES * NUM_ENERGY_STATES * NUM_CLEANLINESS_STATES


def discretize_value(value: int, bins: List[int]) -> int:
    """Discretizes a continuous value into a bin index."""
    for i in range(len(bins) - 1):
        if bins[i] <= value < bins[i + 1]:
            return i
    # Handle edge case where value might be exactly the last bin's upper bound
    if value == bins[-1]:
        return len(bins) - 2
        # Or if value is somehow out of expected range (should be caught by Pydantic ge/le)
    # Clamp to last bin if value > last bin upper bound (exclusive)
    if value >= bins[-1]:
        return len(bins) - 2
    # Clamp to first bin if value < first bin lower bound
    if value < bins[0]:
        return 0
    raise ValueError(f"Value {value} is outside the defined bins {bins}")


def get_discrete_state_index(pet_needs: Dict) -> int:  # pet_needs is a dict from PetNeeds model
    """Converts a PetNeeds dictionary into a single discrete state index for the Q-table."""
    h_idx = discretize_value(pet_needs['hunger'], HUNGER_BINS)
    p_idx = discretize_value(pet_needs['happiness'], HAPPINESS_BINS)
    e_idx = discretize_value(pet_needs['energy'], ENERGY_BINS)
    c_idx = discretize_value(pet_needs['cleanliness'], CLEANLINESS_BINS)

    # Combine indices into a single unique state index
    # This is like a multidimensional array index flattened
    state_index = (h_idx * (NUM_HAPPINESS_STATES * NUM_ENERGY_STATES * NUM_CLEANLINESS_STATES) +
                   p_idx * (NUM_ENERGY_STATES * NUM_CLEANLINESS_STATES) +
                   e_idx * (NUM_CLEANLINESS_STATES) +
                   c_idx)
    return state_index


def get_pet_needs_from_state_dict(state_dict: Dict) -> Dict:
    """Extracts the 'needs' dictionary from a state dictionary."""
    # The state_dict comes from our JSONL file, which is PetState.model_dump()
    # So, state_dict['needs'] should be the PetNeeds dictionary.
    if 'needs' in state_dict and isinstance(state_dict['needs'], dict):
        return state_dict['needs']
    else:
        # This might happen if the structure is different or 'needs' is missing
        raise ValueError(f"Could not find 'needs' dictionary in state_dict: {state_dict}")


if __name__ == "__main__":
    # Test discretization
    print(f"Total discrete states: {TOTAL_NUM_DISCRETE_STATES}")

    example_needs_data = {"hunger": 10, "happiness": 60, "energy": 80, "cleanliness": 20}
    idx = get_discrete_state_index(example_needs_data)
    print(f"Example needs: {example_needs_data} -> Discrete index: {idx}")

    example_needs_data_2 = {"hunger": 90, "happiness": 10, "energy": 5, "cleanliness": 90}
    idx_2 = get_discrete_state_index(example_needs_data_2)
    print(f"Example needs 2: {example_needs_data_2} -> Discrete index: {idx_2}")

    # Test action mapping
    print(f"Available actions: {ACTIONS}")
    print(f"Mapping for 'feed_small': {ACTION_MAPPING['feed_small']}")