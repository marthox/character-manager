# Character Sheet Module System Design

**Date:** 2026-05-20
**Status:** Approved

## Overview

Replace the flat, hardcoded `Character` model with a composable module system. A character sheet is an ordered collection of modules, each belonging to a category. A character can only have one active module per category — choosing between "D&D 5e Hit Points" or "Wound System" for their `health` slot. The catalog can hold many modules per category; the constraint lives at the character and template level.

The system is multi-system: it works for D&D 5e, Pathfinder, Call of Cthulhu, or any custom tabletop game with a character sheet. The service ships with seeded D&D 5e modules, but they are created through the same API any user would use — there is no privileged built-in layer.

---

## Core Domain Model

Five entities:

### ModuleDefinition
The schema for a module. Lives in a shared catalog.

```
id:          UUID
name:        str
description: str | None
category:    str          ← lowercase string, see Category System
fields:      List[FieldDefinition]
```

### FieldDefinition
A single typed field within a module's schema.

```
name:       str
field_type: FieldType     ← integer | string | boolean | float | list
required:   bool = True
default:    Any = None
```

### SheetTemplate
A reusable, ordered composition of module definitions. Used as a starting point for characters.

```
id:      UUID
name:    str
system:  str              ← e.g. "D&D 5e", "Pathfinder 2e", "Custom"
modules: List[UUID]       ← ordered list of ModuleDefinition ids, one per category
```

### Character
A player's character. Owns its modules independently of the template it was created from.

```
id:          UUID
player:      UUID
name:        str
template_id: UUID | None  ← bookkeeping only, no ongoing behavior
modules:     List[CharacterModule]  ← ordered, one per category
```

### CharacterModule
A module instantiated on a specific character, holding that character's actual values.

```
id:            UUID
definition_id: UUID              ← which ModuleDefinition schema to follow
values:        Dict[str, Any]    ← validated against definition.fields at write time
```

---

## Category System

A category is a plain lowercase string. Rules:

1. Normalized to lowercase before validation and storage
2. Must match `^[a-z][a-z0-9_]*$`
3. No two categories may be identical (enforced at the catalog level by normalization)

Standard categories are seeded at startup and carry no special privilege. Any user can create a module with `health`, `sanity`, `vehicle_stats`, or any other valid string as its category.

### Standard categories (seeded)

| Value | Intended use |
|-------|-------------|
| `health` | HP, wounds, stress, vitality |
| `experience` | XP, milestones, advancement points |
| `attributes` | Core stats (STR/DEX/CON or Body/Mind/Spirit) |
| `skills` | Skill lists and proficiencies |
| `combat` | AC, initiative, speed, proficiency bonus |
| `spells` | Spell slots, magic points, spell book |
| `inventory` | Items and equipment |
| `money` | Currency and wealth |
| `proficiencies` | Weapon, armor, tool, language proficiencies |
| `features` | Class features, feats, racial traits |
| `background` | Backstory, personality, appearance |
| `identity` | Race, class, alignment |
| `death_saves` | Death saving throw tracking |

---

## Uniqueness Constraint

The catalog (`ModuleDefinition`) places no constraint on category — many definitions can share the same category (e.g. "D&D 5e Hit Points", "Wound System", and "Vitality Points" all in `health`).

The constraint applies at the **character** and **template** level:

> A character (or template) may have at most one module per category.

Enforced on:
- `POST /characters/{id}/modules` — rejects if the character already has a module whose definition's category matches the new one
- `POST /templates/{id}/modules` — rejects if the template already has a definition in that category

---

## Template Inheritance

When a character is created from a template:

1. The template's ordered module list is copied to the character as `CharacterModule` entries
2. Values are initialized from each field's `default`
3. The character owns its modules from that point — subsequent template changes do not affect the character
4. `template_id` is stored for bookkeeping only (e.g. "this character started as D&D 5e Base")

Characters may freely add modules beyond the template (e.g. a wizard adds `spells`) or remove modules they don't need, as long as the one-per-category constraint is respected.

---

## Seeded D&D 5e Modules

These are created at startup via the same API users would call. One default template — **"D&D 5e Base"** — includes all of them in the order below.

| Module name | Category | Fields |
|---|---|---|
| D&D 5e Hit Points | `health` | max_hp (int), current_hp (int), temp_hp (int) |
| D&D 5e Experience | `experience` | xp (int), level (int) |
| D&D 5e Ability Scores | `attributes` | strength, dexterity, constitution, intelligence, wisdom, charisma (int) |
| D&D 5e Combat Stats | `combat` | armor_class (int), initiative (int), speed (int), proficiency_bonus (int), inspiration (int) |
| D&D 5e Death Saves | `death_saves` | successes (int), failures (int) |
| D&D 5e Spell Slots | `spells` | level_1 through level_9: total (int), used (int) |
| D&D 5e Currency | `money` | cp, sp, ep, gp, pp (int) |
| D&D 5e Proficiencies | `proficiencies` | weapons, armor, tools, languages (list) |
| D&D 5e Features | `features` | features (list) |
| D&D 5e Background | `background` | backstory, appearance, allies, personality_traits, ideals, bonds, flaws (string) |
| D&D 5e Identity | `identity` | race, subrace, class, alignment (string) |

---

## API Structure

### Module definitions
```
GET    /modules                           list all definitions
POST   /modules                           create a new definition
GET    /modules/{id}                      get one definition
PATCH  /modules/{id}                      update name, description, or fields
DELETE /modules/{id}                      rejected if used by any template or character
```

### Sheet templates
```
GET    /templates                         list all templates
POST   /templates                         create a template
GET    /templates/{id}                    get one template with its module list
PATCH  /templates/{id}                    update name or system
DELETE /templates/{id}                    rejected if any character references it
POST   /templates/{id}/modules            add a definition (enforces one per category)
DELETE /templates/{id}/modules/{def_id}   remove a definition from the template
PATCH  /templates/{id}/modules/order      reorder the module list
```

### Characters
```
GET    /characters                        list, filterable by player
POST   /characters                        create, optionally from a template
GET    /characters/{id}                   get character with all modules
PATCH  /characters/{id}                   update name or player
DELETE /characters/{id}                   delete character and all its modules
```

### Character modules
```
GET    /characters/{id}/modules           list all modules on a character
POST   /characters/{id}/modules           add a module (enforces one per category)
GET    /characters/{id}/modules/{mod_id}  get one module with its values
PATCH  /characters/{id}/modules/{mod_id}  update values (validated against definition)
DELETE /characters/{id}/modules/{mod_id}  remove module from character
```

---

## Migration from Existing Code

The current flat `Character` Pydantic model and its supporting models (`Attribute`, `SpellSlots`, `DeathSaves`, etc.) are replaced by this system. The existing Python models served as the source of truth for the seeded D&D module definitions above and are no longer needed as standalone classes.

The existing `BaseClass`, `CharacterClass`, `Race`, `Background`, `Alignment`, and similar reference models become string fields within module `values` rather than typed domain objects — consistent with the data-only, system-agnostic design.

---

## Out of Scope

- Rules engine / computed fields (future)
- Field-level constraints beyond type validation (min, max, regex — future)
- Module versioning (future)
- User authentication and player ownership enforcement (separate service concern)
