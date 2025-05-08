# simulation/simulator.py
import sys
import os

# Add the project root to the Python path
# This allows imports from the 'app' module when running this script directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.models.pet import Pet, PetState, PetNeeds  # This should now work
from simulation.agents import BaseAgent, NurturingAgent, RandomAgent  # Import your agents
import random
import json
from uuid import UUID, uuid4  # Not used directly in this file's current version but good to keep if PetState uses it
from datetime import datetime
import structlog
from typing import Optional, List, Dict

log = structlog.get_logger(__name__)


# --- Reward Function Definition ---
# This is crucial and will need tuning.
# For now, a simple reward function.
def calculate_reward(previous_needs: PetNeeds, current_needs: PetNeeds, action_taken: Optional[str], is_alive_now: bool,
                     was_alive_before: bool) -> float:
    reward = 0.0

    if not is_alive_now and was_alive_before:
        return -200.0  # Large penalty for pet "dying"

    if not is_alive_now:  # No rewards if not alive
        return 0.0

    # Reward for improving needs, penalty for worsening beyond a threshold
    # Hunger: Lower is better
    if current_needs.hunger < previous_needs.hunger:
        reward += (previous_needs.hunger - current_needs.hunger) * 0.2
    elif current_needs.hunger > 85 and current_needs.hunger > previous_needs.hunger:  # Penalize if very hungry and getting worse
        reward -= (current_needs.hunger - previous_needs.hunger) * 0.3

    # Happiness: Higher is better
    if current_needs.happiness > previous_needs.happiness:
        reward += (current_needs.happiness - previous_needs.happiness) * 0.3
    elif current_needs.happiness < 15 and current_needs.happiness < previous_needs.happiness:  # Penalize if very unhappy and getting worse
        reward -= (previous_needs.happiness - current_needs.happiness) * 0.4

    # Energy: Higher is better (but not excessively, maybe a target range)
    if current_needs.energy > previous_needs.energy:
        reward += (current_needs.energy - previous_needs.energy) * 0.15
    elif current_needs.energy < 15 and current_needs.energy < previous_needs.energy:
        reward -= (previous_needs.energy - current_needs.energy) * 0.2

    # Cleanliness: Higher is better
    if current_needs.cleanliness > previous_needs.cleanliness:
        reward += (current_needs.cleanliness - previous_needs.cleanliness) * 0.1
    elif current_needs.cleanliness < 15 and current_needs.cleanliness < previous_needs.cleanliness:
        reward -= (previous_needs.cleanliness - current_needs.cleanliness) * 0.15

    # Small penalty for existing in a bad state, encouraging action
    if current_needs.hunger > 80: reward -= 0.5
    if current_needs.happiness < 20: reward -= 1.0
    if current_needs.energy < 20: reward -= 0.5
    if current_needs.cleanliness < 20: reward -= 0.3

    # Small reward for just being alive and relatively okay
    if is_alive_now and current_needs.hunger < 50 and current_needs.happiness > 50 and current_needs.energy > 50 and current_needs.cleanliness > 50:
        reward += 1.0

    # Action-specific rewards/penalties (optional can be complex)
    # if action_taken == "play" and current_needs.happiness < 30:
    #     reward += 5 # Extra reward for playing when very unhappy

    return round(reward, 2)


def run_episode(agent: BaseAgent, pet_name: str, max_steps: int = 200) -> List[Dict]:
    pet = Pet(name=pet_name)
    episode_data = []
    log.info("Starting new simulation episode", pet_name=pet_name, agent_type=type(agent).__name__, max_steps=max_steps)

    for step in range(max_steps):
        if not pet.state.is_alive:
            log.info("Pet is no longer alive, ending episode.", pet_name=pet_name, step=step)
            # Add final "done" state if not already captured
            # last_record = episode_data[-1] if episode_data else None
            # if last_record and not last_record["is_done"]: # Should not happen if logic is correct
            #     # This state is after it died, so no action, reward is from previous step
            #     episode_data.append({
            #         "step": step,
            #         "state": pet.state.model_dump(mode='json'), # S_{t+1} (dead state)
            #         "action": None, # No action taken by agent in dead state
            #         "action_params": None,
            #         "reward": 0, # No reward for this transition
            #         "next_state": pet.state.model_dump(mode='json'), # Still dead
            #         "is_done": True,
            #         "pet_id": str(pet.state.id),
            #         "timestamp": datetime.utcnow().isoformat()
            #     })
            break

        current_pet_state_obj = pet.state.model_copy(deep=True)  # S_t (Pydantic model)
        previous_needs_obj = current_pet_state_obj.needs.model_copy(deep=True)
        was_alive_before_action = current_pet_state_obj.is_alive

        # Agent chooses action
        action_tuple = agent.choose_action(current_pet_state_obj)

        action_name = None
        action_params = None

        if action_tuple:
            action_name, action_params = action_tuple
            # Apply action to pet
            if hasattr(pet, action_name):
                action_method = getattr(pet, action_name)
                action_method(**action_params)  # This calls pet.tick() internally
                log.debug("Agent action performed", pet_name=pet_name, step=step, action=action_name,
                          params=action_params)
            else:
                log.warn("Agent chose invalid action", pet_name=pet_name, step=step, action=action_name)
                action_name = "invalid_action"  # Log it as such
                pet.tick()  # Still tick time forward
        else:
            # Agent chose no action, just let time pass
            pet.tick()
            log.debug("Agent chose no action, time ticks.", pet_name=pet_name, step=step)

        next_pet_state_obj = pet.state  # S_{t+1} (Pydantic model)

        # Calculate reward
        reward = calculate_reward(previous_needs_obj, next_pet_state_obj.needs, action_name,
                                  next_pet_state_obj.is_alive, was_alive_before_action)
        is_done = not next_pet_state_obj.is_alive

        # Log data
        # We need to serialize Pydantic models for JSON storage
        record = {
            "step": step,
            "state": current_pet_state_obj.model_dump(mode='json'),  # S_t
            "action": action_name,  # A_t
            "action_params": action_params,  # A_t params
            "reward": reward,  # R_{t+1}
            "next_state": next_pet_state_obj.model_dump(mode='json'),  # S_{t+1}
            "is_done": is_done,
            "pet_id": str(current_pet_state_obj.id),  # Use ID from S_t
            "timestamp": datetime.utcnow().isoformat()
        }
        episode_data.append(record)

        if is_done:
            log.info("Pet reached terminal state (is_done=True)", pet_name=pet_name, step=step)
            break

    log.info("Episode finished.", pet_name=pet_name, total_steps=len(episode_data),
             final_happiness=pet.state.needs.happiness if pet else None)
    return episode_data


def generate_synthetic_data(num_episodes: int, agent_type: str = "random", output_file_prefix: str = "synthetic_data"):
    all_episodes_data = []

    for i in range(num_episodes):
        pet_name = f"SimPet_{i + 1}"
        if agent_type == "nurturing":
            agent = NurturingAgent(agent_id=f"Nurturer_{i + 1}")
        elif agent_type == "random":
            agent = RandomAgent(agent_id=f"Randomizer_{i + 1}")
        else:
            log.error(f"Unknown agent type: {agent_type}")
            return

        episode_data = run_episode(agent, pet_name, max_steps=500)  # Adjust max_steps
        all_episodes_data.extend(episode_data)

        # Optionally save each episode to a separate file or append to a larger one
        # For simplicity, we'll save all at the end here.

    output_filename = f"{output_file_prefix}_{agent_type}_{num_episodes}_episodes_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.jsonl"
    with open(output_filename, 'w') as f:
        for record in all_episodes_data:
            f.write(json.dumps(record) + '\n')
    log.info(f"Synthetic data generated and saved to {output_filename}", total_records=len(all_episodes_data))
    return output_filename


if __name__ == "__main__":
    # This is for direct execution of the simulator script
    from app.core.logging_config import setup_logging

    setup_logging(log_level_str="INFO")  # Ensure logging is configured if run directly

    # Example: Generate data using a random agent
    # generate_synthetic_data(num_episodes=5, agent_type="random", output_file_prefix="data/raw/sim_random")
    # Example: Generate data using a nurturing agent
    generate_synthetic_data(num_episodes=10, agent_type="nurturing", output_file_prefix="data/raw/sim_nurturing")

    # You would typically call generate_synthetic_data from a managing script or a DVC pipeline.