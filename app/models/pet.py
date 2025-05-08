# app/models/pet.py
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timedelta


class PetNeeds(BaseModel):
    hunger: int = Field(default=50, ge=0, le=100)
    happiness: int = Field(default=50, ge=0, le=100)
    energy: int = Field(default=100, ge=0, le=100)
    # Add more needs like cleanliness later


class PetState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    needs: PetNeeds = Field(default_factory=PetNeeds)
    is_alive: bool = True
    # Add age, evolutionary_stage, personality_traits later


class Pet:
    def __init__(self, name: str):
        self.state = PetState(name=name)
        self._last_tick_time = datetime.utcnow()
        # Define decay rates (can be moved to config)
        self._hunger_decay_rate_per_hour = 10
        self._happiness_decay_rate_per_hour = 5
        self._energy_decay_rate_per_hour = 8

    def tick(self):
        """Simulates the passage of time and updates needs."""
        now = datetime.utcnow()
        time_delta_seconds = (now - self._last_tick_time).total_seconds()
        hours_passed = time_delta_seconds / 3600

        # Decay needs (simplified)
        self.state.needs.hunger = max(0, min(100, self.state.needs.hunger + int(
            self._hunger_decay_rate_per_hour * hours_passed)))
        self.state.needs.happiness = max(0, min(100, self.state.needs.happiness - int(
            self._happiness_decay_rate_per_hour * hours_passed)))
        self.state.needs.energy = max(0, min(100, self.state.needs.energy - int(
            self._energy_decay_rate_per_hour * hours_passed)))

        # Basic "death" condition
        if self.state.needs.hunger >= 100 or self.state.needs.energy <= 0:
            self.state.is_alive = False

        self.state.last_updated_at = now
        self._last_tick_time = now
        # print(f"Pet {self.state.name} ticked. Hunger: {self.state.needs.hunger}, Happiness: {self.state.needs.happiness}") # For debug

    def feed(self, amount: int = 20):
        if not self.state.is_alive: return
        self.state.needs.hunger = max(0, self.state.needs.hunger - amount)
        self.state.needs.happiness = min(100,
                                         self.state.needs.happiness + amount // 2)  # Feeding also makes pet happier
        self.tick()  # Update other needs due to time passage

    def play(self, duration_minutes: int = 15):
        if not self.state.is_alive: return
        self.state.needs.happiness = min(100, self.state.needs.happiness + duration_minutes)
        self.state.needs.energy = max(0, self.state.needs.energy - duration_minutes // 2)  # Playing uses energy
        self.tick()

    # Add more interaction methods: sleep(), clean(), teach_trick() etc.
    # Add methods for making sounds, expressing emotions (rule-based initially)
    # Example from: Dogs wag tails, cats purr.