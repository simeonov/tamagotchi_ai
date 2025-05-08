# app/api/v1/endpoints/pet_interactions.py
from fastapi import APIRouter, HTTPException, Body
from uuid import UUID
from typing import Optional
from app.services import pet_service
from app.models.pet import PetState # Pydantic model for response

router = APIRouter()

class CreatePetRequest(BaseModel): # Pydantic model for request body
    name: str

@router.post("/pets", response_model=PetState, status_code=201)
async def create_pet_endpoint(payload: CreatePetRequest = Body(...)):
    """Create a new virtual pet."""
    created_pet_state = pet_service.create_new_pet(name=payload.name)
    return created_pet_state

@router.get("/pets/{pet_id}", response_model=PetState)
async def get_pet_endpoint(pet_id: UUID):
    """Get the current state of a pet."""
    pet = pet_service.get_pet_by_id(pet_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    # Ensure pet's state is up-to-date before returning
    if pet.state.is_alive:
        pet.tick()
    return pet.state

@router.post("/pets/{pet_id}/feed", response_model=Optional)
async def feed_pet_endpoint(pet_id: UUID, amount: int = Body(default=20, embed=True)):
    """Feed the pet."""
    updated_pet_state = pet_service.feed_pet(pet_id, amount)
    if not updated_pet_state:
        pet = pet_service.get_pet_by_id(pet_id)
        if not pet:
            raise HTTPException(status_code=404, detail="Pet not found")
        else: # Pet exists but might not be alive or action failed
            return pet.state # Return current state even if action had no effect
    return updated_pet_state

@router.post("/pets/{pet_id}/play", response_model=Optional)
async def play_with_pet_endpoint(pet_id: UUID, duration_minutes: int = Body(default=15, embed=True)):
    """Play with the pet."""
    updated_pet_state = pet_service.play_with_pet(pet_id, duration_minutes)
    if not updated_pet_state:
        pet = pet_service.get_pet_by_id(pet_id)
        if not pet:
            raise HTTPException(status_code=404, detail="Pet not found")
        else:
            return pet.state
    return updated_pet_state

# We'll need a background task or scheduler to call pet_service.update_all_pets_tick() periodically.
# FastAPI's BackgroundTasks or a library like APScheduler can be used for this.