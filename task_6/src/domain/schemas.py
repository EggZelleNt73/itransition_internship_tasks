from pydantic import BaseModel


class UserProfile(BaseModel):
    full_name: str
    street_address: str
    latitude: float
    longitude: float
    height_cm: int
    weight_kg: int
    eye_color: str
    phone_number: str
    email_address: str