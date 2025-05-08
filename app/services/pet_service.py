# app/services/pet_service.py
from uuid import UUID
from typing import Optional, List, Dict
from app.models.pet import Pet, PetState  # Pet class is for logic, PetState for data
from app.core.database import get_database, PETS_COLLECTION
from pymongo.errors import DuplicateKeyError
import structlog

log = structlog.get_logger(__name__)


# We no longer use the in-memory _pets_db.
# The Pet class instances will be created on-demand from DB data.

async def _get_pet_instance_from_db(pet_id: UUID) -> Optional[Pet]:
    """Helper to fetch pet data and reconstruct the Pet logic instance."""
    db = get_database()
    pet_data = await db.find_one({"id": str(pet_id)})  # Store UUID as string
    if pet_data:
        # Reconstruct PetState from DB data
        # Note: MongoDB stores UUID as string if we don't use a custom codec.
        # Pydantic should handle string to UUID conversion if `id` field is UUID type.
        # Ensure all fields in PetState are present in pet_data or have defaults.
        try:
            pet_state_from_db = PetState(**pet_data)
            pet_instance = Pet(name=pet_state_from_db.name)  # Re-init with name
            pet_instance.state = pet_state_from_db  # Then assign the full state
            # We might need to restore _last_tick_time and _last_age_update_time if they were persisted
            # For simplicity now, Pet init sets them to utcnow.
            # If these were stored, they'd need to be datetime objects.
            # pet_instance._last_tick_time = pet_state_from_db.last_updated_at # Example
            return pet_instance
        except Exception as e:
            log.error("Error reconstructing Pet instance from DB", pet_id=str(pet_id), error=str(e), data=pet_data)
            return None
    return None


async def _save_pet_state_to_db(pet_state: PetState):
    """Helper to save the PetState to MongoDB."""
    db = get_database()
    # Convert PetState to dict. Pydantic's model_dump() is useful.
    # Store UUID as string for broader compatibility, Pydantic handles conversion.
    pet_dict = pet_state.model_dump(mode='json')  # mode='json' ensures UUIDs are strings
    pet_dict["id"] = str(pet_state.id)  # Ensure id is string

    await db.update_one(
        {"id": str(pet_state.id)},
        {"$set": pet_dict},
        upsert=True  # Create if not exists, update if exists
    )


async def create_new_pet(name: str) -> PetState:
    pet_instance = Pet(name=name)  # This creates a new PetState with a new UUID
    await _save_pet_state_to_db(pet_instance.state)
    log.info("pet_created_and_saved_to_db", pet_id=str(pet_instance.state.id), name=name)
    return pet_instance.state


async def get_pet_state_by_id(pet_id: UUID) -> Optional:
    pet_instance = await _get_pet_instance_from_db(pet_id)
    if pet_instance:
        if pet_instance.state.is_alive:
            pet_instance.tick()  # Apply time-based changes
            await _save_pet_state_to_db(pet_instance.state)  # Save updated state
        return pet_instance.state
    return None


async def list_all_pets() -> List:
    db = get_database()
    pets_cursor = db.find()
    pet_states = []
    async for pet_data in pets_cursor:
        try:
            # Reconstruct PetState to ensure it's valid and to apply any defaults
            # or transformations defined in the Pydantic model.
            pet_state_from_db = PetState(**pet_data)

            # Optionally, reconstruct the full Pet instance to apply a tick if needed,
            # but for a list view, this might be too slow if many pets.
            # For now, just return the state as is from DB for listing.
            # If consistent ticking is needed for list view, this logic needs adjustment.
            # For simplicity, we assume list view doesn't need immediate tick.
            pet_states.append(pet_state_from_db)
        except Exception as e:
            log.error("Error reconstructing PetState for listing", data=pet_data, error=str(e))
            continue  # Skip problematic records
    return pet_states


async def _perform_pet_action(pet_id: UUID, action_func_name: str, **kwargs) -> Optional:
    pet_instance = await _get_pet_instance_from_db(pet_id)
    if pet_instance and pet_instance.state.is_alive:
        action_method = getattr(pet_instance, action_func_name)
        action_method(**kwargs)  # This calls tick() internally and updates state
        await _save_pet_state_to_db(pet_instance.state)
        log.info(f"pet_action_{action_func_name}", pet_id=str(pet_id), **kwargs,
                 new_state=pet_instance.state.model_dump(exclude={'id'}))
        return pet_instance.state
    elif pet_instance:  # Pet exists but is not alive
        log.warn(f"pet_action_{action_func_name}_attempt_not_alive", pet_id=str(pet_id))
        return pet_instance.state  # Return current (not alive) state
    log.warn(f"pet_action_{action_func_name}_attempt_not_found", pet_id=str(pet_id))
    return None


async def feed_pet(pet_id: UUID, amount: int = 25) -> Optional:
    return await _perform_pet_action(pet_id, "feed", amount=amount)


async def play_with_pet(pet_id: UUID, duration_effect: int = 20) -> Optional:
    return await _perform_pet_action(pet_id, "play", duration_effect=duration_effect)


async def put_pet_to_sleep(pet_id: UUID, duration_effect: int = 50) -> Optional:
    return await _perform_pet_action(pet_id, "sleep", duration_effect=duration_effect)


async def clean_pet(pet_id: UUID, amount: int = 40) -> Optional:
    return await _perform_pet_action(pet_id, "clean", amount=amount)


async def update_all_pets_tick_globally():
    """Periodically called to update all active pets."""
    db = get_database()
    active_pets_cursor = db.find({"is_alive": True})
    updated_count = 0
    async for pet_data in active_pets_cursor:
        try:
            pet_id_str = str(pet_data.get("id"))  # Ensure ID is string for logging
            pet_instance = Pet(name=pet_data.get("name", "Unknown"))  # Re-init with name
            pet_instance.state = PetState(**pet_data)  # Assign full state
            # pet_instance._last_tick_time = pet_instance.state.last_updated_at # Restore time

            if pet_instance.state.is_alive:  # Double check
                pet_instance.tick()
                await _save_pet_state_to_db(pet_instance.state)
                updated_count += 1
            # If tick makes it not alive, it will be saved as such.
        except Exception as e:
            log.error("Error during global tick for a pet",
                      pet_id=pet_id_str if 'pet_id_str' in locals() else "unknown", data=pet_data, error=str(e))
            continue

    if updated_count > 0:
        log.debug("global_tick_processed_db", updated_pets=updated_count)