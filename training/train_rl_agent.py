# training/train_rl_agent.py
import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now the relative imports should work, and imports from 'app' should also work.
import json # This was already here, just for context
from typing import List, Dict, Optional # Added Optional

from app.core.logging_config import setup_logging # Absolute import from app
setup_logging(log_level_str="INFO")

import structlog
from training.load_data import load_jsonl_data
from training.q_learning_agent import QLearningAgent
from training.rl_utils import (
    get_discrete_state_index,
    get_pet_needs_from_state_dict,
    ACTIONS
)

log = structlog.get_logger(__name__)

def train_agent(data_file_path: str,
                num_episodes_to_train: int,  # Number of full episodes from data to process
                q_table_save_path: str = "models/q_table.npy",
                q_table_load_path: Optional[str] = None,
                learning_rate: float = 0.1,
                discount_factor: float = 0.99,
                initial_epsilon: float = 1.0,
                epsilon_decay: float = 0.0001,  # Slower decay for more records
                min_epsilon: float = 0.01
                ):
    """
    Trains the Q-Learning agent using data from a JSONL file.
    The data is assumed to be a list of (state, action, reward, next_state, done) transitions.
    """
    log.info("Starting Q-learning agent training...", data_file=data_file_path, episodes=num_episodes_to_train)

    # Load all transitions from the data file
    all_transitions = load_jsonl_data(data_file_path)
    if not all_transitions:
        log.error("No training data loaded. Exiting.")
        return

    log.info(f"Loaded {len(all_transitions)} total transitions from data file.")

    agent = QLearningAgent(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        exploration_rate=initial_epsilon,
        exploration_decay_rate=epsilon_decay,
        min_exploration_rate=min_epsilon,
        q_table_load_path=q_table_load_path
    )

    # Group transitions by episode (pet_id)
    episodes_data: Dict[str, List[Dict]] = {}
    for transition in all_transitions:
        pet_id = transition.get("pet_id")
        if pet_id:
            if pet_id not in episodes_data:
                episodes_data[pet_id] = []
            episodes_data[pet_id].append(transition)

    # Sort transitions within each episode by step
    for pet_id in episodes_data:
        episodes_data[pet_id].sort(key=lambda x: x.get("step", 0))

    log.info(f"Grouped data into {len(episodes_data)} episodes.")

    actual_episodes_trained = 0
    # Iterate through episodes for training
    # We use num_episodes_to_train to control how many "simulated" episodes we learn from
    # This is more about passes over the data than real-time episodes.

    # For offline learning from a fixed dataset, we iterate multiple times (epochs)
    # over the dataset or a subset of it.
    # Let's consider `num_episodes_to_train` as epochs over the available episodes.

    available_episode_ids = list(episodes_data.keys())
    if not available_episode_ids:
        log.error("No episodes found in the data. Exiting training.")
        return

    for epoch in range(num_episodes_to_train):  # num_episodes_to_train now acts as epochs
        total_epoch_reward = 0
        num_steps_in_epoch = 0

        # Process all available episodes in each epoch
        for pet_id in available_episode_ids:
            episode_transitions = episodes_data[pet_id]

            for transition in episode_transitions:
                state_dict = transition.get("state")
                action_name = transition.get("action")
                reward = transition.get("reward")
                next_state_dict = transition.get("next_state")
                done = transition.get("is_done")

                if None in [state_dict, action_name, reward, next_state_dict, done]:
                    log.warn("Skipping transition with missing data.", transition_step=transition.get("step"))
                    continue

                try:
                    # Convert full state dicts to PetNeeds dicts, then to discrete indices
                    current_needs = get_pet_needs_from_state_dict(state_dict)
                    state_idx = get_discrete_state_index(current_needs)

                    next_needs = get_pet_needs_from_state_dict(next_state_dict)
                    next_state_idx = get_discrete_state_index(next_needs)
                except ValueError as e:
                    log.error("Error processing state for discretization.", error=str(e), step_data=transition)
                    continue

                try:
                    action_idx = ACTIONS.index(action_name)
                except ValueError:
                    # This can happen if the agent in simulation took an "invalid_action"
                    # or an action not in our defined RL ACTIONS list.
                    # For Q-learning, we need a defined action from its action space.
                    # If the logged action was "do_nothing" or similar and it's in ACTIONS, it's fine.
                    # If it's truly an unknown action to the RL agent, we might skip or map it.
                    if action_name == "invalid_action" or action_name is None:  # from simulator
                        # If agent did nothing or invalid, perhaps map to our "do_nothing" RL action
                        if "do_nothing" in ACTIONS:
                            action_idx = ACTIONS.index("do_nothing")
                        else:  # Or skip if no such mapping
                            log.debug("Skipping transition with unmappable action from simulation.",
                                      sim_action=action_name, step=transition.get("step"))
                            continue
                    else:
                        log.warn("Action from data not in RL agent's action space. Skipping.",
                                 action_from_data=action_name, step=transition.get("step"))
                        continue

                agent.update_q_table(state_idx, action_idx, reward, next_state_idx, done)
                total_epoch_reward += reward
                num_steps_in_epoch += 1

        agent.decay_exploration_rate()  # Decay epsilon after each full pass over the data (epoch)

        if num_steps_in_epoch > 0:
            avg_reward_this_epoch = total_epoch_reward / num_steps_in_epoch
            log.info(f"Epoch {epoch + 1}/{num_episodes_to_train} completed.",
                     avg_reward=avg_reward_this_epoch,
                     current_epsilon=agent.epsilon,
                     steps_processed=num_steps_in_epoch)
        else:
            log.info(f"Epoch {epoch + 1}/{num_episodes_to_train} completed. No steps processed.")

        # Save Q-table periodically (e.g., every 10 epochs)
        if (epoch + 1) % 10 == 0 or (epoch + 1) == num_episodes_to_train:
            agent.save_q_table(q_table_save_path)
            # Also good to version this with DVC if it's a significant checkpoint
            # dvc_add_cmd = f"dvc add {q_table_save_path}"
            # log.info(f"To version with DVC: {dvc_add_cmd} && git add {q_table_save_path}.dvc")

    log.info("Training finished.")
    agent.save_q_table(q_table_save_path)  # Final save
    log.info(f"Final Q-table saved to {q_table_save_path}")


if __name__ == "__main__":
    # Find the most recent simulation data file in data/raw
    data_raw_path = os.path.join(PROJECT_ROOT, "data", "raw")
    latest_data_file = None
    latest_time = 0
    if os.path.exists(data_raw_path):
        for filename in os.listdir(data_raw_path):
            if filename.startswith("sim_") and filename.endswith(".jsonl"):
                file_path = os.path.join(data_raw_path, filename)
                file_mod_time = os.path.getmtime(file_path)
                if file_mod_time > latest_time:
                    latest_time = file_mod_time
                    latest_data_file = file_path

    if not latest_data_file:
        log.error("No simulation data file found in data/raw/. Please run simulator.py first.")
        sys.exit(1)

    log.info(f"Using data file for training: {latest_data_file}")

    # Define models directory
    models_dir = os.path.join(PROJECT_ROOT, "models")
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        log.info(f"Created models directory: {models_dir}")

    q_table_path = os.path.join(models_dir, "tamagotchi_q_table.npy")

    # Example training run:
    train_agent(
        data_file_path=latest_data_file,
        num_episodes_to_train=100,  # This is now effectively epochs over the dataset
        q_table_save_path=q_table_path,
        q_table_load_path=q_table_path if os.path.exists(q_table_path) else None,  # Continue training if table exists
        learning_rate=0.05,  # Might need smaller LR for offline batch learning
        discount_factor=0.95,
        initial_epsilon=0.5,  # Start with less exploration if data is good
        epsilon_decay=0.0005,  # Slower decay over more epochs
        min_epsilon=0.05
    )