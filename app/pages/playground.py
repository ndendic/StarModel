from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from sqlmodel import Field
from pages.templates import page_template
from uuid import uuid4

rt = APIRouter()

class Playground(SQLEntity, table=True):
    """Interactive landing page showcasing StarModel's reactive magic."""
    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    name: str = Field(default="")
    age: int = Field(default=0)
    email: str = Field(default="")
    phone: str = Field(default="")
    address: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")
    

@rt('/playground')
@page_template(title="⭐ StarModel - Reactive Entity Management for Python")
def index(req: Request):
    """Revolutionary landing page showcasing StarModel's reactive magic."""
    entity = Playground.get(req)
    
    return Main(
        entity,
        Form(
            Input(label="Name", name="name", data_text=entity.name, data_bind=entity.name),
            Input(label="Age", name="age", data_text=entity.age, data_bind=entity.age),
            Input(label="Email", name="email", data_text=entity.email, data_bind=entity.email),
            Input(label="Phone", name="phone", data_text=entity.phone, data_bind=entity.phone),
            Input(label="Address", name="address", data_text=entity.address, data_bind=entity.address),
            Input(label="City", name="city", data_text=entity.city, data_bind=entity.city),
            Input(label="State", name="state", data_text=entity.state, data_bind=entity.state),
        ),
        cls="min-h-screen"
    )