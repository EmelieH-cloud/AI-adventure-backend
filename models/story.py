from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base

# ------------------------------------------------------------------------------
# STORY & STORYNODE – SQLAlchemy-modeller för "Choose Your Own Adventure"-spel
#
#   Relationer:
# - En `Story` representerar en hel berättelse (titel, session, skapad)
# - En `StoryNode` representerar en del av berättelsen
#
#   Relationstyp: One-to-Many
# - En `Story` har MÅNGA `StoryNodes` (via `relationship(..., back_populates="story")`)
# - En `StoryNode` tillhör EN `Story` (via `story_id = ForeignKey(...)`)
# ------------------------------------------------------------------------------

class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    session_id = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    nodes = relationship("StoryNode", back_populates="story")


class StoryNode(Base):
    __tablename__ = "story_nodes"
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    content = Column(String)
    is_root = Column(Boolean, default=False)
    is_ending = Column(Boolean, default=False)
    is_winning_ending = Column(Boolean, default=False)
    options = Column(JSON, default=list)
    story = relationship("Story", back_populates="nodes")