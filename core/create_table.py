
from db import Base, engine
from model import Scholarship

Base.metadata.create_all(bind=engine)

print("Scholarship table created successfully!")
