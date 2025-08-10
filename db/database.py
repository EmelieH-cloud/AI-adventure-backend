
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from core.config import settings

# - SQLAlchemy behöver en så kallad "engine", som skapas med create_engine().
#   Engine är själva kopplingen mellan din Python-kod och databasen.
#   Den tar en databas-URL där du anger vilken databas som används (t.ex. PostgreSQL)
#   och vilken drivrutin som ska användas (t.ex. psycopg2).
#
# - Databasdrivrutinen (som psycopg2) gör det möjligt för Python att kommunicera med databasen,
#   men den skickar bara vidare råa SQL-strängar och returnerar resultat – den gör inget mer.
#
# - SQLAlchemy ligger ovanpå drivrutinen och erbjuder ett Python-gränssnitt för att jobba med databasen.
#   Istället för att skriva SQL som text, kan du definiera tabeller, frågor och operationer i Python.
#   SQLAlchemy översätter sedan detta till korrekt SQL och skickar det till databasen via drivrutinen.

engine = create_engine(
    settings.DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ----------------------------------------------------
# Förklaring av namn och vad som händer:
#
# sessionmaker är en funktion som skapar och returnerar en klass.
# Denna klass (som kallas SessionLocal) används för att skapa sessioner (databasanslutningar).
#
# SessionLocal är namnet på den klass som sessionmaker returnerar.
# Namnet "Local" visar att varje session är lokal för en enskild operation.
#
# När du skriver:
#     db = SessionLocal()
# skapas en ny instans av sessionen (ett objekt) som du använder för att prata med databasen.
#
# Kort sagt:
# - sessionmaker() ger en klass (SessionLocal)
# - SessionLocal() ger en session-instans (ett objekt)
# ----------------------------------------------------


def get_db():
    db=SessionLocal()
    try:
        yield db
    finally: 
        db.close()


Base = declarative_base()

# ----------------------------------------------------
# - Metoden declarative_base() skapar en klass som alla modeller (t.ex. Story, StoryNode) ärver från.
# - Då alla modeller ärver från Base, samlas all metadata (kolumner, nycklar och relationer) 
#   automatiskt i Base.metadata.
# ----------------------------------------------------

def create_tables():
    Base.metadata.create_all(bind=engine)

# ----------------------------------------------------
# - Base.metadata innehåller all information om dina tabeller och kolumner (metadata).
# - create_all() läser denna metadata och skapar tabellerna i databasen.
# - bind=engine anger vilken databasanslutning (engine) som ska användas.
# ----------------------------------------------------
