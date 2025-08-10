from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from core.prompts import STORY_PROMPT
from models.story import Story, StoryNode
from core.models import StoryLLMResponse
from core.models import StoryNodeLLM
from dotenv import load_dotenv
from dotenv import load_dotenv
import os

if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

class StoryGenerator:

    @classmethod
    def _get_llm(cls):
      
        return ChatOpenAI(model="gpt-4o-mini")
    
    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str="fantasy") -> Story:
        # Hämtar LLM-instansen (språkmodellen)
        llm = cls._get_llm()

        # Skapar en parser som kan tolka LLM:s JSON-output enligt StoryLLMResponse modellen
        story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)

        # Bygger prompten med två meddelanden:
        # 1. System-meddelande med den fasta story-prompten (instruktioner)
        # 2. Human-meddelande som anger temat för storyn
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                STORY_PROMPT
            ),
            (
                "human",
                f"Create the story with this theme: {theme}"
            )
        ]).partial(
            # Lägger till instruktioner för exakt JSON-format från story_parser i prompten
            format_instructions=story_parser.get_format_instructions()
        )

        # Skickar prompten till LLM och får tillbaka ett rått svar
        raw_response = llm.invoke(prompt.invoke({}))

        # Plockar ut svaret som text (hanterar om svaret ligger i 'content' attribut)
        response_text = raw_response
        if hasattr(raw_response, "content"):
            response_text = raw_response.content
        
            # Tolkar LLM:s JSON-svar till en Python-objektstruktur enligt Pydantic-modellen
            story_structure = story_parser.parse(response_text)

            # Skapar en ny Story-instans för databasen med titel och session_id
            story_db = Story(title=story_structure.title, session_id=session_id)

            # Lägger till story-objektet i databasen (men sparar ej ännu)
            db.add(story_db)

            # Flusha databasen för att t.ex. generera ID och säkerställa att objektet är tillagd
            db.flush()

            root_node_data = story_structure.rootNode
            if isinstance(root_node_data, dict):
                root_node_data = StoryNodeLLM.model_validate(root_node_data)
            
            # skicka in root-storyn så den läggs in i databasen 
            cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

            db.commit()
            return story_db

    @classmethod
    def _process_story_node(cls, db: Session, story_id: int, node_data: StoryNodeLLM, is_root: bool=False) -> StoryNode:
        node = StoryNode(
            story_id=story_id,
            content=node_data.content if hasattr(node_data, "content") else node_data["content"],
            is_root=is_root,
            is_ending=node_data.isEnding if hasattr(node_data, "isEnding") else node_data["isEnding"],
            is_winning_ending=node_data.isWinningEnding if hasattr(node_data, "isWinningEnding") else node_data["isWinningEnding"],
            options=[]  # just nu är options tomt, dvs ingen koll är gjord än 
        )
        db.add(node)
        db.flush()

        # om noden inte är en ending node, och options finns, och inte är tom
        if not node.is_ending and hasattr(node_data, "options") and node_data.options:
            # skapa en variabel att spara alla options för noden i 
            options_list = []

            # kolla igenom alla dens options , och om detta option innehåller en nextnode, skicka in den noden igen. 
            for option_data in node_data.options:
                next_node = option_data.nextNode
                if isinstance(next_node, dict):
                    next_node = StoryNodeLLM.model_validate(next_node)
                child_node = cls._process_story_node(db, story_id, next_node, is_root=False)

                options_list.append({
                    "text": option_data.text,
                    "node_id": child_node.id
                })

            node.options = options_list
            db.flush()
        return node

