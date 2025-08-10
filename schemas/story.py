from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

# Varför byggs modeller med -base, -schema, -response och -request?
# -schema beskriver inte ett helt objekt utan bara en mindre del av objektet. 
# -base beskriver själva grundobjektet för att användas i flera olika responses eller requests.
# -Förklaring: 
#    I en applikation brukar man utföra olika operationer kopplat till grundobjekten
#    Det innebär att det tillkommer data till det grundobjektet. Ny data skickas oftast tillbaka i ett response.
#    Men själva grundobjektet har fortfarande samma struktur som innan.
#    Därför låter man response-modeller ärva från basmodellen istället för att duplicera fälten.

class StoryOptionsSchema(BaseModel):
    text: str
    node_id: Optional[int] = None


class StoryNodeBase(BaseModel):
    content: str
    is_ending: bool = False
    is_winning_ending: bool = False


class CompleteStoryNodeResponse(StoryNodeBase):
    id: int
    options: List[StoryOptionsSchema] = []

    class Config:
        from_attributes = True


class StoryBase(BaseModel):
    title: str
    session_id: Optional[str] = None

    class Config:
        from_attributes = True


class CreateStoryRequest(BaseModel):
    theme: str


class CompleteStoryResponse(StoryBase):
    id: int
    created_at: datetime
    root_node: CompleteStoryNodeResponse
    all_nodes: Dict[int, CompleteStoryNodeResponse]

    class Config:
        from_attributes = True