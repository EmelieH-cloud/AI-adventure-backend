import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from sqlalchemy.orm import Session
from db.database import get_db, SessionLocal
from models.story import Story, StoryNode
from models.job import StoryJob
from schemas.story import (
    CompleteStoryNodeResponse, CompleteStoryResponse, CreateStoryRequest
)
from schemas.job import StoryJobResponse
from core.story_generator import StoryGenerator

router = APIRouter(
    prefix="/stories",
    tags=["stories"]
)

# ---------------------------------------------------------
# parametern session_id är en valfri sträng (Optional[str]).
# Värdet hämtas från en cookie i HTTP-requesten med namnet 'session_id'.
# Om cookien saknas (inte finns hos klienten) sätts session_id till None som standard.
# Detta gör att funktionen kan kontrollera om användaren redan har en session eller
# om den behöver skapa en ny.

def get_session_id(session_id: Optional[str]=Cookie(None)):
    if not session_id:
        session_id=str(uuid.uuid4())
    return session_id

@router.post("/create", response_model=StoryJobResponse)
def create_story(
    # Innan handlern (create_story) faktiskt körs, måste FastAPI förbereda alla
    # parametrar som den behöver (t.ex. request, db, session_id osv).
    # Parametrarnas typer berättar för FastAPI vad som ska hämtas varifrån:
    #
    # | Typ/Annotation          | FastAPI hämtar från               |
    # |------------------------ |-----------------------------------|
    # | Pydantic-modell         | JSON-body i request               |
    # | BackgroundTasks         | Skapas automatiskt av FastAPI     |
    # | Response                | Skapas automatiskt av FastAPI     |
    # | Depends                 | Hämtas via en funktion            |

        request: CreateStoryRequest,
        background_tasks: BackgroundTasks,
        response: Response,
        session_id: str = Depends(get_session_id),
        db: Session = Depends(get_db)
):
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    # Ett HTTP-response består av tre huvuddelar:
# 1. Statuskod: Anger om anropet lyckades (t.ex. 200 OK).
# 2. Headers: Metadata om svaret, t.ex. cookies, content-type, cache-inställningar.
# 3. Body: Det faktiska innehållet, ofta JSON-data, som klienten vill ha.
#
# - `response_model` definierar hur JSON-data i response BODY ska se ut,
#   dvs. hur det objekt du returnerar ska konverteras till JSON.
# - `response` (Response-objektet) ger dig möjlighet att påverka response HEADERS,
#   till exempel för att sätta cookies eller ändra statuskod.
#
# Det betyder att:
# - När du använder `response.set_cookie()` ändrar du HTTP-headerdelen,
# - När du returnerar ett Pydantic-objekt (t.ex. `job`) konverteras det till JSON
#   enligt `response_model` och skickas i response body.
#
# Sammanfattningsvis: `response_model` styr innehållet i body, medan
# `response` används för att styra metadata i headers.

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id=job_id,
        session_id=session_id,
        theme=request.theme,
        status="pending"
    )
    db.add(job)
    db.commit()

    # task läggs till i kö, inget exekveras ännu. 
    background_tasks.add_task(
        generate_story_task,
        job_id=job_id,
        theme=request.theme,
        session_id=session_id
    )

    return job  
    # http-response skickas till klienten enligt response_model 
    # - nu börjar background task exekvera. 
    # db instansen DÖR när request-response cykeln slutförs.
    # request och response-cykeln kommer alltså stängas innan generering är klar.
    # Detta innebär att background_task behöver egna resursobjekt (tex en db-instans) att jobba med.

def generate_story_task(job_id: str, theme: str, session_id: str):
    # generate_story_task är inte en request-response
    # - det är bara ett jobb som körs i bakgrunden. 
    # Användaren har ingen aning om när det är klart.
   
    db = SessionLocal()
    try:
        job = db.query(StoryJob).filter(StoryJob.job_id == job_id).first()
        if not job:
            return

        try:
            job.status = "processing"
            db.commit() # spara ändringen 

            story = StoryGenerator.generate_story(db, session_id, theme)

            job.story_id = story.id  
            job.status = "completed" 
            job.completed_at = datetime.now()
            db.commit() # spara ändringen 
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now()
            job.error = str(e)
            db.commit()
    finally:
        db.close()

@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
def get_complete_story(story_id: int, db: Session=Depends(get_db)):
    story = db.query(Story).filter(Story.id==story_id).first()
    if not story:
        raise HTTPException(status_code=404, details="Story not found")
   
    complete_story = build_complete_story_tree(db, story)
    return complete_story

def build_complete_story_tree(db: Session, story: Story) -> CompleteStoryResponse:
    nodes = db.query(StoryNode).filter(StoryNode.story_id == story.id).all()
    node_dict = {}

    for node in nodes:
        node_response = CompleteStoryNodeResponse(
            id=node.id,
            content=node.content,
            is_ending=node.is_ending,
            is_winning_ending=node.is_winning_ending,
            options=node.options
        )
        node_dict[node.id] = node_response

    root_node = next((node for node in nodes if node.is_root), None)
    if not root_node:
        raise HTTPException(status_code=500, detail="No root node found")

    return CompleteStoryResponse(
        id=story.id,
        title=story.title,
        session_id=story.session_id,
        created_at=story.created_at,
        root_node=node_dict[root_node.id],
        all_nodes=node_dict
    )
