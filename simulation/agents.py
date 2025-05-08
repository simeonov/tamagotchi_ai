# simulation/agents.py
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict
from app.models.pet import PetState  # Assuming models can be imported
import random


class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    def choose_action(self, pet_state: PetState) -> Optional[Tuple[str, Dict]]:
        """
        Decides an action based on the pet's current state.
        Returns: Tuple of (action_name, action_params_dict) or None for no action.
        Example: ("feed", {"amount": 20})
        """
        pass


class NurturingAgent(BaseAgent):
    def choose_action(self, pet_state: PetState) -> Optional[Tuple[str, Dict]]:
        if not pet_state.is_alive:
            return None

        # Prioritize critical needs
        if pet_state.needs.hunger > 80:
            return ("feed", {"amount": 30})
        if pet_state.needs.energy < 20:
            return ("sleep", {"duration_effect": 60})
        if pet_state.needs.happiness < 30:
            return ("play", {"duration_effect": 25})
        if pet_state.needs.cleanliness < 30:
            return ("clean", {"amount": 50})

        # Proactive care
        if pet_state.needs.hunger > 50 and random.random() < 0.7:
            return ("feed", {"amount": 20})
        if pet_state.needs.happiness < 60 and random.random() < 0.6:
            return ("play", {"duration_effect": 15})
        if pet_state.needs.cleanliness < 70 and random.random() < 0.5:
            return ("clean", {"amount": 30})
        if pet_state.needs.energy < 50 and pet_state.needs.happiness > 70 and random.random() < 0.4:  # Only sleep if happy enough
            return ("sleep", {"duration_effect": 40})

        return None  # No action if pet is generally okay


class RandomAgent(BaseAgent):
    def choose_action(self, pet_state: PetState) -> Optional[Tuple[str, Dict]]:
        if not pet_state.is_alive or random.random() < 0.3:  # Sometimes does nothing
            return None

        possible_actions = [
            ("feed", {"amount": random.randint(10, 30)}),
            ("play", {"duration_effect": random.randint(10, 25)}),
            ("sleep", {"duration_effect": random.randint(30, 70)}),
            ("clean", {"amount": random.randint(20, 50)})
        ]
        return random.choice(possible_actions)

# Add more agent types: NeglectfulAgent, PlayfulAgent etc.