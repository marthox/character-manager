# src/domain/seeder.py
from domain.models.field_definition import FieldDefinition, FieldType
from domain.models.module_definition import ModuleDefinition
from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


def _int(name: str, default: int = 0) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.INTEGER, default=default)


def _str(name: str) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.STRING, default="")


def _lst(name: str) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.LIST, default=[])


DND5E_MODULES = [
    ModuleDefinition(
        name="D&D 5e Hit Points",
        category="health",
        description="Hit point tracking",
        fields=[_int("max_hp", 10), _int("current_hp", 10), _int("temp_hp")],
    ),
    ModuleDefinition(
        name="D&D 5e Experience",
        category="experience",
        description="XP and level tracking",
        fields=[_int("xp"), _int("level", 1)],
    ),
    ModuleDefinition(
        name="D&D 5e Ability Scores",
        category="attributes",
        description="The six core ability scores",
        fields=[
            _int("strength", 10),
            _int("dexterity", 10),
            _int("constitution", 10),
            _int("intelligence", 10),
            _int("wisdom", 10),
            _int("charisma", 10),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Combat Stats",
        category="combat",
        description="AC, initiative, speed, proficiency bonus",
        fields=[
            _int("armor_class", 10),
            _int("initiative"),
            _int("speed", 30),
            _int("proficiency_bonus", 2),
            _int("inspiration"),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Death Saves",
        category="death_saves",
        description="Death saving throw tracking",
        fields=[_int("successes"), _int("failures")],
    ),
    ModuleDefinition(
        name="D&D 5e Spell Slots",
        category="spells",
        description="Spell slot tracking by level",
        fields=[
            f
            for level in range(1, 10)
            for f in (_int(f"level_{level}_total"), _int(f"level_{level}_used"))
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Currency",
        category="money",
        description="Coin purse",
        fields=[_int("cp"), _int("sp"), _int("ep"), _int("gp"), _int("pp")],
    ),
    ModuleDefinition(
        name="D&D 5e Proficiencies",
        category="proficiencies",
        description="Weapons, armor, tools, languages",
        fields=[_lst("weapons"), _lst("armor"), _lst("tools"), _lst("languages")],
    ),
    ModuleDefinition(
        name="D&D 5e Features",
        category="features",
        description="Class features, feats, racial traits",
        fields=[_lst("features")],
    ),
    ModuleDefinition(
        name="D&D 5e Background",
        category="background",
        description="Backstory and personality",
        fields=[
            _str("backstory"),
            _str("appearance"),
            _str("allies"),
            _str("personality_traits"),
            _str("ideals"),
            _str("bonds"),
            _str("flaws"),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Identity",
        category="identity",
        description="Race, class, alignment",
        fields=[_str("race"), _str("subrace"), _str("class"), _str("alignment")],
    ),
]

DND5E_TEMPLATE_NAME = "D&D 5e Base"


def seed_dnd5e(
    module_repo: ModuleDefinitionRepository,
    template_repo: SheetTemplateRepository,
) -> None:
    # Idempotent: skip if template already exists
    if any(t.name == DND5E_TEMPLATE_NAME for t in template_repo.list_all()):
        return

    existing_by_name = {m.name: m for m in module_repo.list_all()}
    seeded_modules: list[ModuleDefinition] = []
    for mod in DND5E_MODULES:
        if mod.name not in existing_by_name:
            module_repo.save(mod)
            seeded_modules.append(mod)
        else:
            seeded_modules.append(existing_by_name[mod.name])

    template = SheetTemplate(
        name=DND5E_TEMPLATE_NAME,
        system="D&D 5e",
        modules=[m.id for m in seeded_modules],
    )
    template_repo.save(template)
