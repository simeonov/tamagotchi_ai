# app/services/pet_service.py
from uuid import UUID
from typing import Dict, Optional, List
from app.models.pet import Pet, PetState
import structlog

log = structlog.get_logger(__name__)

_pets_db: Dict[UUID, Pet] = {}

def create_new_pet(name: str) -> PetState:
    pet_instance = Pet(name=name)
    _pets_db[pet_instance.state.id] = pet_instance
    log.info("pet_created", pet_id=str(pet_instance.state.id), name=name)
    return pet_instance.state

def get_pet_instance_by_id(pet_id: UUID) -> Optional[Pet]:
    return _pets_db.get(pet_id)

def get_pet_state_by_id(pet_id: UUID) -> Optional:
    pet_instance = get_pet_instance_by_id(pet_id)
    if pet_instance:
        if pet_instance.state.is_alive: # Ensure tick is called before returning state
            pet_instance.tick()
        return pet_instance.state
    return None

def list_all_pets() -> List:
    active_pets = []
    for pet_instance in _pets_db.values():
        if pet_instance.state.is_alive:
            pet_instance.tick() # Update state before listing
        active_pets.append(pet_instance.state)
    return active_pets


def feed_pet(pet_id: UUID, amount: int = 25) -> Optional:
    pet = get_pet_instance_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.feed(amount)
        log.info("pet_fed", pet_id=str(pet_id), amount=amount, new_hunger=pet.state.needs.hunger)
        return pet.state
    elif pet: # Pet exists but is not alive
        log.warn("pet_feed_attempt_not_alive", pet_id=str(pet_id))
        return pet.state
    log.warn("pet_feed_attempt_not_found", pet_id=str(pet_id))
    return None

def play_with_pet(pet_id: UUID, duration_effect: int = 20) -> Optional:
    pet = get_pet_instance_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.play(duration_effect)
        log.info("pet_played_with", pet_id=str(pet_id), effect=duration_effect, new_happiness=pet.state.needs.happiness)
        return pet.state
    elif pet:
        log.warn("pet_play_attempt_not_alive", pet_id=str(pet_id))
        return pet.state
    log.warn("pet_play_attempt_not_found", pet_id=str(pet_id))
    return None

def put_pet_to_sleep(pet_id: UUID, duration_effect: int = 50) -> Optional:
    pet = get_pet_instance_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.sleep(duration_effect)
        log.info("pet_slept", pet_id=str(pet_id), effect=duration_effect, new_energy=pet.state.needs.energy)
        return pet.state
    elif pet:
        log.warn("pet_sleep_attempt_not_alive", pet_id=str(pet_id))
        return pet.state
    log.warn("pet_sleep_attempt_not_found", pet_id=str(pet_id))
    return None

def clean_pet(pet_id: UUID, amount: int = 40) -> Optional:
    pet = get_pet_instance_by_id(pet_id)
    if pet and pet.state.is_alive:
        pet.clean(amount)
        log.info("pet_cleaned", pet_id=str(pet_id), amount=amount, new_cleanliness=pet.state.needs.cleanliness)
        return pet.state
    elif pet:
        log.warn("pet_clean_attempt_not_alive", pet_id=str(pet_id))
        return pet.state
    log.warn("pet_clean_attempt_not_found", pet_id=str(pet_id))
    return None

def update_all_pets_tick_globally():
    """Periodically called to update all active pets. For background task."""
    updated_count = 0
    for pet_id in list(_pets_db.keys()):
        pet = _pets_db.get(pet_id)
        if pet and pet.state.is_alive:
            pet.tick()
            updated_count +=1
        elif pet and not pet.state.is_alive:
            # Potentially log this event once, or move to an "inactive" list
            # For now, the tick method handles not updating if not alive.
            pass
    if updated_count > 0:
        log.debug("global_tick_processed", updated_pets=updated_count, total_pets_in_db=len(_pets_db))