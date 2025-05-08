# app/services/pet_service.py
from uuid import UUID
from typing import Dict, Optional
from app.models.pet import Pet, PetState

# In-memory storage for now. Replace with MongoDB interaction later.
_pets_db: Dict[UUID, Pet] = {}

def create_new_pet(name: str) -> PetState:
    pet_instance = Pet(name=name)
    _pets_db[pet_instance.state.id] = pet_instance
    return pet_instance.state

def get_pet_by_id(pet_id: UUID) -> Optional[Pet]:
    return _pets_db.get(pet_id)

def feed_pet(pet_id: UUID, amount: int = 20) -> Optional:
    pet = get_pet_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.feed(amount)
        return pet.state
    return None

def play_with_pet(pet_id: UUID, duration_minutes: int = 15) -> Optional:
    pet = get_pet_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.play(duration_minutes)
        return pet.state
    return None

def update_all_pets_tick():
    """Periodically called to update all active pets."""
    for pet_id in list(_pets_db.keys()): # list() to avoid issues if a pet is removed
        pet = _pets_db.get(pet_id)
        if pet and pet.state.is_alive:
            pet.tick()
        elif pet and not pet.state.is_alive:
            # Handle "dead" pet, e.g., log it, remove from active list
            print(f"Pet {pet.state.name} ({pet.state.id}) is no longer alive.")
            # del _pets_db[pet_id] # Or mark as inactive
            pass