# app/models/pet.py
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timedelta

class PetNeeds(BaseModel):
    hunger: int = Field(default=50, ge=0, le=100)
    happiness: int = Field(default=50, ge=0, le=100)
    energy: int = Field(default=100, ge=0, le=100)
    cleanliness: int = Field(default=70, ge=0, le=100) # Added cleanliness

class PetState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    needs: PetNeeds = Field(default_factory=PetNeeds)
    is_alive: bool = True
    age_days: int = 0 # Added age

class Pet:
    def __init__(self, name: str):
        self.state = PetState(name=name)
        self._last_tick_time = datetime.utcnow()
        self._last_age_update_time = datetime.utcnow()

        # Decay rates (per hour) - can be moved to config.local or pet type specific
        self._hunger_increase_rate_per_hour = 8
        self._happiness_decay_rate_per_hour = 6
        self._energy_decay_rate_per_hour = 7
        self._cleanliness_decay_rate_per_hour = 5

    def tick(self):
        """Simulates the passage of time and updates needs and age."""
        if not self.state.is_alive:
            return

        now = datetime.utcnow()
        time_delta_seconds = (now - self._last_tick_time).total_seconds()
        hours_passed = time_delta_seconds / 3600

        # Decay/Increase needs
        self.state.needs.hunger = min(100, self.state.needs.hunger + int(self._hunger_increase_rate_per_hour * hours_passed))
        self.state.needs.happiness = max(0, self.state.needs.happiness - int(self._happiness_decay_rate_per_hour * hours_passed))
        self.state.needs.energy = max(0, self.state.needs.energy - int(self._energy_decay_rate_per_hour * hours_passed))
        self.state.needs.cleanliness = max(0, self.state.needs.cleanliness - int(self._cleanliness_decay_rate_per_hour * hours_passed))

        # Update age (roughly every 24 hours of real time for simplicity)
        age_delta_seconds = (now - self._last_age_update_time).total_seconds()
        if age_delta_seconds >= 86400: # 24 * 60 * 60
            self.state.age_days += int(age_delta_seconds // 86400)
            self._last_age_update_time += timedelta(days=int(age_delta_seconds // 86400))


        # Basic "death" conditions
        if self.state.needs.hunger >= 100 or \
           self.state.needs.energy <= 0 or \
           self.state.needs.happiness <= 0 or \
           self.state.needs.cleanliness <= 0: # Example condition
            self.state.is_alive = False

        self.state.last_updated_at = now
        self._last_tick_time = now

    def feed(self, amount: int = 25):
        if not self.state.is_alive: return
        self.state.needs.hunger = max(0, self.state.needs.hunger - amount)
        self.state.needs.happiness = min(100, self.state.needs.happiness + amount // 5) # Small happiness boost
        self.tick()

    def play(self, duration_effect: int = 20): # duration_effect can be abstract points
        if not self.state.is_alive: return
        self.state.needs.happiness = min(100, self.state.needs.happiness + duration_effect)
        self.state.needs.energy = max(0, self.state.needs.energy - duration_effect // 2)
        self.tick()

    def sleep(self, duration_effect: int = 50):
        if not self.state.is_alive: return
        self.state.needs.energy = min(100, self.state.needs.energy + duration_effect)
        self.state.needs.hunger = min(100, self.state.needs.hunger + duration_effect // 10) # Gets a bit hungry while sleeping
        self.tick()

    def clean(self, amount: int = 40):
        if not self.state.is_alive: return
        self.state.needs.cleanliness = min(100, self.state.needs.cleanliness + amount)
        self.state.needs.happiness = min(100, self.state.needs.happiness + amount // 8) # Small happiness boost
        self.tick()