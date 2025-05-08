# training/evaluate_rl_agent.py
import os
import sys
import numpy as np
from typing import List, Dict, Optional

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logging_config import setup_logging

setup_logging(log_level_str="INFO")  # Or from settings

import structlog
from app.models.pet import Pet, PetState  # For instantiating the pet
from training.q_learning_agent import QLearningAgent
from training.rl_utils import (
    get_discrete_state_index,
    get_pet_needs_from_state_dict,
    ACTIONS,
    ACTION_MAPPING  # We'll use this to apply the chosen action
)
# We might need the reward function if we want to log rewards during evaluation
from simulation.simulator import calculate_reward  # Import from sibling directory

log = structlog.get_logger(__name__)


def run_evaluation_episode(agent: QLearningAgent,
                           pet_name: str,
                           max_steps: int = 200,
                           render: bool = False) -> Dict:
    """
    Runs a single evaluation episode using the trained QLearningAgent.
    The agent will always choose the best action (no exploration).
    """
    pet = Pet(name=pet_name)
    episode_rewards = 0
    episode_steps = 0
    action_log =  []

    log.info("Starting evaluation episode", pet_name=pet_name, max_steps=max_steps)

    for step in range(max_steps):
        if not pet.state.is_alive:
            log.info("Pet is no longer alive, ending evaluation episode.", pet_name=pet_name, step=step)
            break

        current_pet_state_obj = pet.state.model_copy(deep=True)
        previous_needs_obj = current_pet_state_obj.needs.model_copy(deep=True)
        was_alive_before_action = current_pet_state_obj.is_alive

        try:
            current_needs_dict = get_pet_needs_from_state_dict(current_pet_state_obj.model_dump(mode='json'))
            state_idx = get_discrete_state_index(current_needs_dict)
        except ValueError as e:
            log.error("Error discretizing state during evaluation.", error=str(e),
                      pet_state=current_pet_state_obj.model_dump(mode='json'))
            break  # Cannot proceed if state is invalid

        # Agent chooses action based on Q-table (exploitation mode)
        action_idx = agent.choose_action(state_idx, is_training=False)
        action_name = ACTIONS[action_idx]
        action_details = ACTION_MAPPING.get(action_name)
        action_log.append(action_name)

        if render:  # Simple console rendering
            log.info("Eval Step", step=step, pet_name=pet_name,
                     hunger=pet.state.needs.hunger, happiness=pet.state.needs.happiness,
                     energy=pet.state.needs.energy, cleanliness=pet.state.needs.cleanliness,
                     chosen_action=action_name)

        if action_details and action_details["method"]:
            action_method_name = action_details["method"]
            action_params = action_details["params"]
            if hasattr(pet, action_method_name):
                action_method_callable = getattr(pet, action_method_name)
                action_method_callable(**action_params)  # This calls pet.tick() internally
            else:
                log.warn("RL Agent chose an action with no valid method in Pet class.", action=action_name)
                pet.tick()  # Still tick time forward if action is unhandled
        elif action_name == "do_nothing":
            pet.tick()  # Time passes
        else:
            log.error("RL Agent chose an unmapped action or action with no method.", action=action_name)
            pet.tick()  # Default to time passing

        next_pet_state_obj = pet.state

        # Calculate reward for this step (optional for eval, but good for metrics)
        # Note: The reward function is based on the *agent's* perspective during training.
        # Here, we are observing the outcome of the learned policy.
        reward = calculate_reward(previous_needs_obj, next_pet_state_obj.needs, action_name,
                                  next_pet_state_obj.is_alive, was_alive_before_action)
        episode_rewards += reward
        episode_steps += 1

        if not next_pet_state_obj.is_alive:
            log.info("Pet reached terminal state during evaluation.", pet_name=pet_name, step=step)
            break

    log.info("Evaluation episode finished.", pet_name=pet_name, total_steps=episode_steps, total_reward=episode_rewards,
             survived=(pet.state.is_alive))
    return {
        "pet_name": pet_name,
        "total_steps": episode_steps,
        "total_reward": episode_rewards,
        "survived": pet.state.is_alive,
        "final_happiness": pet.state.needs.happiness,
        "final_hunger": pet.state.needs.hunger,
        "action_log": action_log
    }


def evaluate_agent(q_table_path: str, num_eval_episodes: int = 10, max_steps_per_episode: int = 300,
                   render_episodes: bool = False):
    log.info("Starting agent evaluation...", q_table=q_table_path, episodes=num_eval_episodes)

    if not os.path.exists(q_table_path):
        log.error("Q-table not found for evaluation.", path=q_table_path)
        return

    # Initialize agent with exploration rate set to 0 for pure exploitation
    # Or, use a very small epsilon if you still want a tiny bit of randomness,
    # but for true policy evaluation, epsilon should be 0.
    agent = QLearningAgent(
        q_table_load_path=q_table_path,
        exploration_rate=0.0,  # Pure exploitation
        min_exploration_rate=0.0  # Not relevant if exploration_rate is 0
    )
    # We don't need learning_rate or discount_factor for evaluation of a fixed policy.

    all_episode_results = []
    total_survived = 0

    for i in range(num_eval_episodes):
        pet_name = f"EvalPet_{i + 1}"
        # Render the first few episodes if render_episodes is True
        should_render_this_episode = render_episodes and (i < 3)  # e.g., render first 3

        episode_result = run_evaluation_episode(agent, pet_name, max_steps_per_episode,
                                                render=should_render_this_episode)
        all_episode_results.append(episode_result)
        if episode_result["survived"]:
            total_survived += 1

    # Calculate and log aggregate metrics
    avg_steps = np.mean([res["total_steps"] for res in all_episode_results])
    avg_reward = np.mean([res["total_reward"] for res in all_episode_results])
    survival_rate = (total_survived / num_eval_episodes) * 100

    log.info("--- Evaluation Summary ---")
    log.info(f"Total episodes evaluated: {num_eval_episodes}")
    log.info(f"Average steps per episode: {avg_steps:.2f}")
    log.info(f"Average reward per episode: {avg_reward:.2f}")
    log.info(f"Survival rate: {survival_rate:.2f}%")

    # You can save these results to a file or further analyze action logs
    # For example, print action distribution:
    from collections import Counter
    all_actions_taken = []
    for res in all_episode_results:
        all_actions_taken.extend(res["action_log"])

    if all_actions_taken:
        action_counts = Counter(all_actions_taken)
        log.info("Action distribution during evaluation:", counts=action_counts)
    else:
        log.info("No actions were logged during evaluation.")


if __name__ == "__main__":
    models_dir = os.path.join(PROJECT_ROOT, "models")
    q_table_path = os.path.join(models_dir, "tamagotchi_q_table.npy")  # Default path

    if not os.path.exists(q_table_path):
        log.error(f"Trained Q-table not found at {q_table_path}. Please run train_rl_agent.py first.")
        sys.exit(1)

    evaluate_agent(
        q_table_path=q_table_path,
        num_eval_episodes=20,  # Number of times to run the simulation with the agent
        max_steps_per_episode=500,  # Max length of one simulation run
        render_episodes=True  # Set to True to see step-by-step logs for a few episodes
    )