# src/adapters/outbound/db/models.py
from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ModuleDefinitionORM(Base):
    __tablename__ = "module_definitions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, index=True)
    fields = Column(JSON, nullable=False, default=list)


class SheetTemplateORM(Base):
    __tablename__ = "sheet_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    system = Column(String, nullable=False)
    modules = Column(JSON, nullable=False, default=list)


class CharacterORM(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True)
    player = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    template_id = Column(String, nullable=True)
    modules = relationship(
        "CharacterModuleORM",
        back_populates="character",
        cascade="all, delete-orphan",
    )


class CharacterModuleORM(Base):
    __tablename__ = "character_modules"

    id = Column(String, primary_key=True)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False, index=True)
    definition_id = Column(String, nullable=False)
    values = Column(JSON, nullable=False, default=dict)
    character = relationship("CharacterORM", back_populates="modules")
