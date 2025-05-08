# training/q_learning_agent.py
import numpy as np
import random
from typing import List, Tuple, Optional # Ensure Optional is imported
import os # Ensure os is imported for path operations

# Use relative import for rl_utils since they are in the same 'training' package
from training.rl_utils import (
    TOTAL_NUM_DISCRETE_STATES,
    NUM_ACTIONS,
    ACTIONS,
    # get_discrete_state_index, # Not directly used by QLearningAgent itself
    # get_pet_needs_from_state_dict # Not directly used by QLearningAgent itself
)
import structlog

log = structlog.get_logger(__name__)

class QLearningAgent:
    def __init__(self,
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.99,
                 exploration_rate: float = 1.0,
                 exploration_decay_rate: float = 0.001,
                 min_exploration_rate: float = 0.01,
                 q_table_load_path: Optional[str] = None):
        """
        Initializes the Q-Learning Agent.

        Args:
            learning_rate (alpha): How much new information overrides old information.
            discount_factor (gamma): Importance of future rewards.
            exploration_rate (epsilon): Initial probability of choosing a random action.
            exploration_decay_rate: Rate at which epsilon decays.
            min_exploration_rate: Minimum value for epsilon.
            q_table_load_path: Path to load a pre-trained Q-table from.
        """
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = exploration_rate
        self.epsilon_decay = exploration_decay_rate
        self.epsilon_min = min_exploration_rate

        self.num_states = TOTAL_NUM_DISCRETE_STATES
        self.num_actions = NUM_ACTIONS
        self.actions_list = ACTIONS  # For mapping index to action name if needed

        if q_table_load_path and os.path.exists(q_table_load_path):
            try:
                self.q_table = np.load(q_table_load_path)
                log.info("Q-table loaded successfully.", path=q_table_load_path, shape=self.q_table.shape)
                if self.q_table.shape != (self.num_states, self.num_actions):
                    log.warn("Loaded Q-table shape mismatch. Reinitializing.",
                             loaded_shape=self.q_table.shape,
                             expected_shape=(self.num_states, self.num_actions))
                    self.q_table = np.zeros((self.num_states, self.num_actions))
            except Exception as e:
                log.error("Failed to load Q-table. Initializing new one.", path=q_table_load_path, error=str(e))
                self.q_table = np.zeros((self.num_states, self.num_actions))
        else:
            if q_table_load_path:
                log.warn("Q-table load path provided but file not found. Initializing new Q-table.",
                         path=q_table_load_path)
            self.q_table = np.zeros((self.num_states, self.num_actions))
            log.info("New Q-table initialized.", shape=self.q_table.shape)

    def choose_action(self, state_index: int, is_training: bool = True) -> int:
        """
        Chooses an action using an epsilon-greedy strategy.

        Args:
            state_index: The discrete index of the current state.
            is_training: If True, applies exploration. If False, purely exploits.

        Returns:
            The index of the chosen action.
        """
        if is_training and random.uniform(0, 1) < self.epsilon:
            return random.randint(0, self.num_actions - 1)  # Explore
        else:
            # Check for ties, choose randomly among best actions
            best_actions = np.flatnonzero(self.q_table[state_index] == np.max(self.q_table[state_index]))
            return random.choice(best_actions)  # Exploit

    def update_q_table(self, state_index: int, action_index: int, reward: float, next_state_index: int, done: bool):
        """
        Updates the Q-value for a given state-action pair using the Q-learning rule.
        Q(s,a) = Q(s,a) + lr * (reward + gamma * max_q(s') - Q(s,a))
        If done, the future reward (max_q(s')) is 0.
        """
        old_value = self.q_table[state_index, action_index]

        if done:
            next_max_q = 0.0  # No future reward if the episode is finished
        else:
            next_max_q = np.max(self.q_table[next_state_index])

        new_value = old_value + self.lr * (reward + self.gamma * next_max_q - old_value)
        self.q_table[state_index, action_index] = new_value

    def decay_exploration_rate(self, episode_num: Optional[int] = None):
        """Decays the exploration rate (epsilon)."""
        # Simple exponential decay:
        # self.epsilon = self.epsilon_min + (self.epsilon_max - self.epsilon_min) * np.exp(-self.epsilon_decay * episode_num)
        # Or simpler linear decay per call:
        if self.epsilon > self.epsilon_min:
            self.epsilon -= self.epsilon_decay  # Subtract decay rate
            if self.epsilon < self.epsilon_min:
                self.epsilon = self.epsilon_min
        # log.debug("Epsilon decayed", new_epsilon=self.epsilon)

    def save_q_table(self, file_path: str):
        """Saves the Q-table to a file."""
        try:
            # Ensure directory exists
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)
            np.save(file_path, self.q_table)
            log.info("Q-table saved successfully.", path=file_path)
        except Exception as e:
            log.error("Error saving Q-table.", path=file_path, error=str(e))
