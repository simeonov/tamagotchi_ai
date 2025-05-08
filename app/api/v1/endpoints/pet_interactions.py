# app/api/v1/endpoints/pet_interactions.py
from fastapi import APIRouter, HTTPException, Body
from uuid import UUID
from typing import Optional, List
from app.services import pet_service # This now contains async functions
from app.models.pet import PetState
from pydantic import BaseModel

router = APIRouter()

class CreatePetRequest(BaseModel):
    name: str

class InteractionAmountRequest(BaseModel):
    amount: int

@router.post("/pets", response_model=PetState, status_code=201)
async def create_pet_endpoint(payload: CreatePetRequest = Body(...)):
    created_pet_state = await pet_service.create_new_pet(name=payload.name)
    return created_pet_state

@router.get("/pets", response_model=List) # Specify List of PetState
async def list_pets_endpoint():
    return await pet_service.list_all_pets()

@router.get("/pets/{pet_id}", response_model=PetState)
async def get_pet_endpoint(pet_id: UUID):
    pet_state = await pet_service.get_pet_state_by_id(pet_id)
    if not pet_state:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet_state

@router.post("/pets/{pet_id}/feed", response_model=PetState)
async def feed_pet_endpoint(pet_id: UUID, payload: InteractionAmountRequest = Body(default=InteractionAmountRequest(amount=25))):
    updated_pet_state = await pet_service.feed_pet(pet_id, payload.amount)
    if not updated_pet_state:
        existing_pet_state = await pet_service.get_pet_state_by_id(pet_id)
        if not existing_pet_state:
            raise HTTPException(status_code=404, detail="Pet not found")
        return existing_pet_state
    return updated_pet_state

@router.post("/pets/{pet_id}/play", response_model=PetState)
async def play_with_pet_endpoint(pet_id: UUID, payload: InteractionAmountRequest = Body(default=InteractionAmountRequest(amount=20))):
    updated_pet_state = await pet_service.play_with_pet(pet_id, payload.amount)
    if not updated_pet_state:
        existing_pet_state = await pet_service.get_pet_state_by_id(pet_id)
        if not existing_pet_state:
            raise HTTPException(status_code=404, detail="Pet not found")
        return existing_pet_state
    return updated_pet_state

@router.post("/pets/{pet_id}/sleep", response_model=PetState)
async def sleep_pet_endpoint(pet_id: UUID, payload: InteractionAmountRequest = Body(default=InteractionAmountRequest(amount=50))):
    updated_pet_state = await pet_service.put_pet_to_sleep(pet_id, payload.amount)
    if not updated_pet_state:
        existing_pet_state = await pet_service.get_pet_state_by_id(pet_id)
        if not existing_pet_state:
            raise HTTPException(status_code=404, detail="Pet not found")
        return existing_pet_state
    return updated_pet_state

@router.post("/pets/{pet_id}/clean", response_model=PetState)
async def clean_pet_endpoint(pet_id: UUID, payload: InteractionAmountRequest = Body(default=InteractionAmountRequest(amount=40))):
    updated_pet_state = await pet_service.clean_pet(pet_id, payload.amount)
    if not updated_pet_state:
        existing_pet_state = await pet_service.get_pet_state_by_id(pet_id)
        if not existing_pet_state:
            raise HTTPException(status_code=404, detail="Pet not found")
        return existing_pet_state
    return updated_pet_state