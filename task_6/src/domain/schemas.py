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


class BenchmarkResult(BaseModel):
    users_generated: int
    elapsed_seconds: float
    users_per_second: float