import json
import os
import time
import logging
import random
from typing import Dict, Any, List, Optional
from pathlib import Path
import save_system
import functools
import re
import sys
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from groq import Groq
from cachetools import LRUCache, cached
from dotenv import load_dotenv
# NPC and Relationship Management Classes

@dataclass
class NPCRelationship:
    """Tracks the relationship between an NPC and another entity (player or NPC)."""
    affinity: int = 0  # -100 to 100 scale
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    known_facts: Set[str] = field(default_factory=set)
    
    def update_affinity(self, change: int) -> None:
        """Update the affinity score with bounds checking."""
        self.affinity = max(-100, min(100, self.affinity + change))
    
    def add_fact(self, fact: str) -> None:
        """Add a known fact about this relationship."""
        self.known_facts.add(fact)
    
    def has_fact(self, fact: str) -> bool:
        """Check if a fact is known about this relationship."""
        return fact in self.known_facts

class NPC:
    """Represents a non-player character with relationships and memory."""
    
    def __init__(self, name: str, role: str, location: str, faction: str = "neutral"):
        self.name = name
        self.role = role
        self.location = location
        self.faction = faction
        self.relationships: Dict[str, NPCRelationship] = {}
        self.inventory: List[Dict] = []
        self.schedule: Dict[str, str] = {}
        self.known_locations: Set[str] = {location}
        self.first_met: datetime = datetime.now()
        self.last_seen: datetime = datetime.now()
        self.is_merchant: bool = False
        self.merchant_inventory: List[Dict] = []
        
    def update_relationship(self, entity_id: str, affinity_change: int = 0, fact: Optional[str] = None) -> NPCRelationship:
        """Update relationship with another entity."""
        if entity_id not in self.relationships:
            self.relationships[entity_id] = NPCRelationship()
        
        relationship = self.relationships[entity_id]
        
        if affinity_change != 0:
            relationship.update_affinity(affinity_change)
        
        if fact:
            relationship.add_fact(fact)
            
        relationship.interaction_count += 1
        relationship.last_interaction = datetime.now()
        
        return relationship
    
    def get_relationship(self, entity_id: str) -> NPCRelationship:
        """Get relationship with another entity, creating if it doesn't exist."""
        if entity_id not in self.relationships:
            self.relationships[entity_id] = NPCRelationship()
        return self.relationships[entity_id]
    
    def get_disposition(self, entity_id: str) -> str:
        """Get a text description of the relationship disposition."""
        if entity_id not in self.relationships:
            return "neutral"
            
        affinity = self.relationships[entity_id].affinity
        
        if affinity <= -70:
            return "hostile"
        elif affinity <= -30:
            return "unfriendly"
        elif affinity <= 30:
            return "neutral"
        elif affinity <= 70:
            return "friendly"
        else:
            return "ally"
    
    def knows_about(self, entity_id: str, fact: str) -> bool:
        """Check if NPC knows a specific fact about an entity."""
        if entity_id not in self.relationships:
            return False
        return self.relationships[entity_id].has_fact(fact)
    
    def to_dict(self) -> Dict:
        """Convert NPC data to a dictionary for serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "location": self.location,
            "faction": self.faction,
            "relationships": {
                entity_id: {
                    "affinity": rel.affinity,
                    "last_interaction": rel.last_interaction.isoformat() if rel.last_interaction else None,
                    "interaction_count": rel.interaction_count,
                    "known_facts": list(rel.known_facts)
                }
                for entity_id, rel in self.relationships.items()
            },
            "inventory": self.inventory,
            "schedule": self.schedule,
            "known_locations": list(self.known_locations),
            "first_met": self.first_met.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_merchant": self.is_merchant,
            "merchant_inventory": self.merchant_inventory
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPC':
        """Create an NPC from a dictionary."""
        npc = cls(
            name=data["name"],
            role=data["role"],
            location=data["location"],
            faction=data.get("faction", "neutral")
        )
        
        # Restore relationships
        for entity_id, rel_data in data.get("relationships", {}).items():
            relationship = NPCRelationship()
            relationship.affinity = rel_data["affinity"]
            relationship.interaction_count = rel_data["interaction_count"]
            relationship.known_facts = set(rel_data.get("known_facts", []))
            
            if rel_data["last_interaction"]:
                relationship.last_interaction = datetime.fromisoformat(rel_data["last_interaction"])
                
            npc.relationships[entity_id] = relationship
        
        # Restore other attributes
        npc.inventory = data.get("inventory", [])
        npc.schedule = data.get("schedule", {})
        npc.known_locations = set(data.get("known_locations", []))
        npc.first_met = datetime.fromisoformat(data.get("first_met", datetime.now().isoformat()))
        npc.last_seen = datetime.fromisoformat(data.get("last_seen", datetime.now().isoformat()))
        npc.is_merchant = data.get("is_merchant", False)
        npc.merchant_inventory = data.get("merchant_inventory", [])
        
        return npc

class NPCMemory:
    """Manages NPCs and their relationships in the game world."""
    
    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        self.factions: Dict[str, Dict[str, int]] = {}
        
    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the memory system."""
        self.npcs[npc.name.lower()] = npc
        
        # Initialize faction relationships if needed
        if npc.faction not in self.factions:
            self.factions[npc.faction] = {}
    
    def get_npc(self, name: str) -> Optional[NPC]:
        """Get an NPC by name (case-insensitive)."""
        return self.npcs.get(name.lower())
    
    def update_npc_location(self, npc_name: str, new_location: str) -> None:
        """Update an NPC's location."""
        npc = self.get_npc(npc_name)
        if npc:
            npc.location = new_location
            npc.known_locations.add(new_location)
            npc.last_seen = datetime.now()
    
    def update_faction_relationship(self, faction1: str, faction2: str, change: int) -> None:
        """Update the relationship between two factions."""
        if faction1 not in self.factions:
            self.factions[faction1] = {}
        if faction2 not in self.factions:
            self.factions[faction2] = {}
            
        current = self.factions[faction1].get(faction2, 0)
        self.factions[faction1][faction2] = max(-100, min(100, current + change))
        
        # Make it bidirectional for now (can be asymmetric if needed)
        current = self.factions[faction2].get(faction1, 0)
        self.factions[faction2][faction1] = max(-100, min(100, current + change))
    
    def get_faction_relationship(self, faction1: str, faction2: str) -> int:
        """Get the relationship score between two factions."""
        if faction1 == faction2:
            return 100  # Same faction is always allied with itself
            
        return self.factions.get(faction1, {}).get(faction2, 0)
    
    def to_dict(self) -> Dict:
        """Convert NPC memory to a dictionary for serialization."""
        return {
            "npcs": {name: npc.to_dict() for name, npc in self.npcs.items()},
            "factions": self.factions
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NPCMemory':
        """Create an NPCMemory from a dictionary."""
        memory = cls()
        
        # Restore NPCs
        for npc_data in data.get("npcs", {}).values():
            npc = NPC.from_dict(npc_data)
            memory.add_npc(npc)
        
        # Restore faction relationships
        memory.factions = data.get("factions", {})
        
        return memory

# Basic logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GroqEngine:
    def __init__(self):
        """Initialize the Groq AI engine."""
        load_dotenv()
        self.api_key = os.getenv('GROQ_API_KEY')
        self.description_cache = LRUCache(maxsize=128)
        self.model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
        self.client = None
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables. Some features may be limited.")
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info(f"Successfully initialized Groq client with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
    
    @cached(cache=LRUCache(maxsize=128), key=lambda *args, **kwargs: (
        'generate_description',
        args[1].get('location', ''),
        tuple((k, tuple(sorted(v.items())) if isinstance(v, dict) else v) 
             for k, v in args[1].items() if k != 'location')
    ))
    def generate_description(self, context: Dict[str, Any]) -> str:
        """
        Generate a location description using Groq AI.
        
        Args:
            context: A dictionary containing location and NPC information
            
        Returns:
            str: Generated description text
        """
        if not self.client:
            return f"You are in {context.get('location', 'an unknown location')}."
            
        try:
            # Extract NPC information
            npcs_info = context.get('npcs', [])
            npc_descriptions = []
            
            for npc in npcs_info:
                name = npc.get('name', 'Someone')
                role = npc.get('role', 'person')
                
                # Special handling for predefined NPCs
                if name == "Eldrin":
                    npc_descriptions.append(f"Eldrin, the town's shopkeeper, is here, surrounded by various wares and potions.")
                elif name == "Gorak":
                    npc_descriptions.append(f"Gorak, the guard captain, stands watch with a stern expression.")
                elif name == "Lily":
                    npc_descriptions.append(f"Lily, the herbalist, tends to her collection of plants and herbs.")
                else:
                    npc_descriptions.append(f"{name} the {role} is here.")
            
            # Build the prompt
            system_prompt = (
                "You are a creative assistant that generates rich, detailed descriptions of locations in a fantasy RPG. "
                "Focus on creating an immersive atmosphere with vivid sensory details. "
                "Keep the description concise but evocative, around 2-3 paragraphs maximum."
            )
            
            user_prompt = f"Describe the location: {context.get('location', 'a place')}"
            if 'description' in context and context['description']:
                user_prompt += f"\nBase description: {context['description']}"
                
            if npc_descriptions:
                user_prompt += "\n\nPeople you see here:" + "\n- " + "\n- ".join(npc_descriptions)
                
            if 'instructions' in context:
                user_prompt += f"\n\n{context['instructions']}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=400,  # Increased for more detailed descriptions
                temperature=0.7,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            fallback = f"You are in {context.get('location', 'an unknown location')}."
            if 'npcs' in context and context['npcs']:
                npc_names = ", ".join([npc.get('name', 'Someone') for npc in context['npcs']])
                fallback += f" You see {npc_names} here."
            return fallback
    
    def clear_cache(self) -> None:
        """Clear the description cache."""
        self.description_cache.clear()
        logger.info("Description cache cleared.")

    def generate_npc_dialogue(self, npc_name: str, player_name: str, location: str, 
                           player_message: str = "", npc_role: str = "person", 
                           player_class: str = "adventurer") -> str:
        """
        Generate NPC dialogue using Groq AI.
        
        Args:
            npc_name: Name of the NPC
            player_name: Name of the player character
            location: Current location
            player_message: Optional message from the player
            npc_role: The role/occupation of the NPC
            player_class: The class/occupation of the player character
            
        Returns:
            str: The NPC's response
        """
        if not self.client:
            return "The NPC seems to be ignoring you."
            
        try:
            
            system_prompt = (
                f"You are {npc_name}, a {npc_role} in a fantasy RPG. "
                f"You are currently in {location}. "
                f"You are talking to {player_name}, a {player_class}. "
                "Keep your responses concise, in-character, and appropriate for your role. "
                "If the player is being rude or aggressive, respond accordingly. "
                "If you don't know something, make something up that fits the setting."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": player_message or f"{player_name} approaches you."}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.7,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating NPC dialogue: {e}")
            return f"{npc_name} seems to be lost in thought..."

    def generate_description(self, context: Dict[str, Any]) -> str:
        """Generate a location description using Groq AI."""
        if not self.client:
            return "The location is dark and foreboding."

        def hashable_list_from_dicts(dicts, key='name'):
            return tuple(sorted(d[key] for d in dicts if key in d)) if dicts else ()

        cache_key_items = []
        if 'name' in context:
            cache_key_items.append(('name', context['name']))
        if 'description' in context:
            cache_key_items.append(('description', context['description']))
        if 'npcs' in context and isinstance(context['npcs'], list):
            cache_key_items.append(('npcs', hashable_list_from_dicts(context['npcs'])))
        if 'enemies' in context and isinstance(context['enemies'], list):
            if context['enemies'] and isinstance(context['enemies'][0], dict):
                cache_key_items.append(('enemies', hashable_list_from_dicts(context['enemies'])))
            else:
                cache_key_items.append(('enemies', tuple(sorted(context['enemies']))))
        if 'exits' in context and isinstance(context['exits'], list):
            cache_key_items.append(('exits', tuple(sorted(context['exits']))))

        cache_key = tuple(sorted(cache_key_items))

        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        try:
            location_desc = context.get('description', 'Unknown location')
            prompt_details = f"Context: Location Name: {context.get('name', 'N/A')}, NPCs: {context.get('npcs', [])}, Exits: {context.get('exits', [])}."
            prompt = f"""
            You are a master Dungeon Master. Describe this location:
            {location_desc}
            {prompt_details}
            
            Provide a vivid, immersive description that includes:
            - Sensory details
            - Points of interest
            - Environmental conditions
            - Potential dangers
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Dungeon Master. Provide vivid, immersive descriptions of locations. Include sensory details, points of interest, environmental conditions, and potential dangers. Keep the description under 1000 tokens."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=False
            )
            
            # Check if we got a valid response
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("No valid response from Groq for location description.")
                return "You find yourself in a place that defies description."
                
            # Get the full response text
            full_response = response.choices[0].message.content
            
            # Cache the full response
            self.description_cache[cache_key] = full_response
            
            return full_response
        except Exception as e:
            logger.warning("Failed to generate location description: %s", e)
            return "The location is dark and foreboding."

    @functools.lru_cache(maxsize=128)
    def generate_npc_dialogue(self, npc_name: str, player_name: str, location: str, 
                           player_message: str = "", npc_role: str = "person", 
                           player_class: str = "adventurer") -> str:
        """
        Generate NPC dialogue using Groq AI.
        
        Args:
            npc_name: Name of the NPC
            player_name: Name of the player character
            location: Current location
            player_message: Optional message from the player
            npc_role: The role/occupation of the NPC
            player_class: The class/occupation of the player character
            
        Returns:
            str: The NPC's response
        """
        if not self.client:
            return f"{npc_name} looks at you but says nothing."

        cache_key = ("npc_dialogue", npc_name, player_name, location, player_class, npc_role, player_message)
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        try:
            # Base system prompt with player class and NPC role
            system_prompt = f"""You are {npc_name}, a {npc_role} in a fantasy RPG. 
            You are currently in {location}. {player_name}, a {player_class}, is talking to you.
            Respond naturally to what they say, keeping responses brief (1-2 sentences)."""
            
            # Adjust tone based on NPC role
            if "merchant" in npc_role.lower():
                system_prompt += " You are eager to do business and promote your wares."
            elif "guard" in npc_role.lower() or "soldier" in npc_role.lower():
                system_prompt += " You are professional and alert, watching for trouble."
            else:
                system_prompt += " You are polite and helpful."
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": player_message or f"{player_name} greets you."}
                ],
                temperature=0.7,
                max_tokens=200,
                top_p=1.0,
                frequency_penalty=0.5,
                presence_penalty=0.5,
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning(f"No valid response from Groq for NPC dialogue with {npc_name}")
                return f"{npc_name} seems lost in thought."
                
            dialogue = response.choices[0].message.content.strip()
            
            # Cache the full response
            self.description_cache[cache_key] = dialogue
            return dialogue
            
        except Exception as e:
            logger.warning(f"Failed to generate NPC dialogue: {e}")
            return f"{npc_name} mumbles something unintelligible."

    @functools.lru_cache(maxsize=128)
    def generate_action_description(self, player_tuple: tuple, action: str) -> str:
        """Generate a description of the player's action using Groq AI.
        player_tuple should be a hashable representation of essential player attributes.
        Example: (player_name, player_class, player_level)
        """
        if not self.client:
            return f"You {action}."

        cache_key = ("action", player_tuple, action.lower())
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        try:
            player_name, player_class, player_level = player_tuple
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a master storyteller. Describe the action in an engaging way. Player: {player_name} (Level {player_level} {player_class}). Keep your response under 200 characters."},
                    {"role": "user", "content": f"Describe this action in 1-2 sentences: {action}"}
                ],
                temperature=0.7,
                max_tokens=200,
                stream=False
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning(f"No valid response from Groq for action: {action}")
                return f"You {action}."
                
            description = response.choices[0].message.content.strip()
            
            # Cache the full response
            self.description_cache[cache_key] = description
            return description
            
        except Exception as e:
            logger.warning(f"Failed to generate action description: {e}")
            return f"You {action}."

    @functools.lru_cache(maxsize=128)
    def generate_combat_description(self, player_tuple: tuple, enemy_tuple: tuple) -> str:
        """
        Generate a description of a combat scenario using Groq AI.
        player_tuple: (name, class, level, current_hp)
        enemy_tuple: (name, level, current_hp)
        """
        if not self.client:
            return "The clash of steel rings out!"

        cache_key = ("combat", player_tuple, enemy_tuple)
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        try:
            player_name, player_class, player_level, player_hp = player_tuple
            enemy_name, enemy_level, enemy_hp = enemy_tuple
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master storyteller. Describe a combat scene in an engaging way. Keep it under 300 characters."},
                    {"role": "user", "content": f"Describe a combat scene between {player_name} (Level {player_level} {player_class}) and {enemy_name} (Level {enemy_level})."}
                ],
                temperature=0.8,
                max_tokens=300,
                stream=False
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("No valid response from Groq for combat description.")
                return f"Combat begins between {player_name} and {enemy_name}!"
                
            description = response.choices[0].message.content.strip()
            
            # Cache the full response
            self.description_cache[cache_key] = description
            return description
            
        except Exception as e:
            logger.warning(f"Failed to generate combat description: {e}")
            return f"Combat begins between {player_name} and {enemy_name}!"

class Item:
    def __init__(self, name: str, item_type: str, stats: Dict[str, Any], stackable: bool = False, max_stack: int = 1):
        self.name = name
        self.item_type = item_type
        self.stats = stats
        self.stackable = stackable
        self.max_stack = max_stack
        self.quantity = 1 if not stackable else None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.item_type,
            "stats": self.stats,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "quantity": self.quantity
        }

    def __str__(self):
        if self.stackable:
            return f"{self.name} x{self.quantity} ({self.item_type})"
        return f"{self.name} ({self.item_type})"

    def __eq__(self, other):
        if isinstance(other, Item):
            return (self.name == other.name and 
                    self.item_type == other.item_type and 
                    self.stats == other.stats)
        return False

    def can_stack_with(self, other: 'Item') -> bool:
        return (self.stackable and 
                other.stackable and 
                self.name == other.name and 
                self.item_type == other.item_type and 
                self.stats == other.stats)

class Character:
    def __init__(self, name: str, character_class: str, level: int = 1):
        self.name = name
        # Normalize and validate character class
        valid_classes = ['Warrior', 'Mage', 'Rogue']
        character_class = character_class.capitalize()
        if character_class not in valid_classes:
            raise ValueError(f"Invalid character class: {character_class}. Must be one of {', '.join(valid_classes)}")
        self.character_class = character_class
        self.level = level
        self.attributes = {
            "toughness": 10,          # Was strength
            "nimbleness": 10,         # Was dexterity
            "hardyness": 10,          # Was constitution
            "book smarts": 10,        # Was intelligence
            "street smarts": 10,      # Was wisdom
            "approachability": 10      # Was charisma
        }
        self.hit_points = self.calculate_hit_points()
        self.inventory: List[Item] = []
        self.inventory_weight = 0
        self.max_inventory_weight = 50  # Base weight capacity
        self.equipped = {
            "weapon": None,
            "armor": None,
            "accessories": []
        }
        self.current_location = "Starting Town"

    def unequip_item(self, slot: str) -> str:
        """Unequip an item and return it to inventory"""
        if slot not in self.equipped:
            return f"Invalid equipment slot: {slot}"
            
        item = self.equipped[slot]
        if item:
            self.equipped[slot] = None
            self.inventory.append(item)
            return f"Unequipped {item.name}"
        return "No item equipped in that slot"
        
    def calculate_hit_points(self) -> int:
        base_hp = 10
        con_mod = (self.attributes["hardyness"] - 10) // 2
        return base_hp + (con_mod * self.level)
        
    def add_item(self, item: Item):
        self.inventory.append(item)
        
    def equip_item(self, item: Item):
        if item not in self.inventory:
            return f"{item.name} is not in inventory"

        if item.item_type == "weapon":
            self.equipped["weapon"] = item
        elif item.item_type == "armor":
            self.equipped["armor"] = item
        elif item.item_type == "accessory":
            self.equipped["accessories"].append(item)

    def format_status(self) -> str:
        """Format character status in a readable way using list join."""
        parts = []
        
        # Character info
        parts.append("=== Character Info ===")
        parts.append(f"Name: {self.name}")
        parts.append(f"Class: {self.character_class}")
        parts.append(f"Level: {self.level}")
        parts.append(f"HP: {self.hit_points}")
        parts.append("")
        
        # Attributes
        parts.append("=== Attributes ===")
        for attr, value in self.attributes.items():
            parts.append(f"{attr.capitalize()}: {value}")
        parts.append("")
        
        # Inventory
        parts.append("=== Inventory ===")
        if not self.inventory:
            parts.append("Inventory is empty")
        else:
            for item in self.inventory:
                parts.append(f"- {item}") # Relies on Item.__str__
        parts.append("")
        
        # Equipment
        parts.append("=== Equipment ===")
        weapon_name = self.equipped["weapon"].name if self.equipped["weapon"] else "None"
        armor_name = self.equipped["armor"].name if self.equipped["armor"] else "None"
        parts.append(f"Weapon: {weapon_name}")
        parts.append(f"Armor: {armor_name}")

        parts.append("Accessories:")
        if self.equipped['accessories']:
            for accessory in self.equipped['accessories']:
                parts.append(f"- {accessory.name}")
        else:
            parts.append("  None") # Indent "None" for accessories for clarity
        
        return "\n".join(parts)
    
    def get_attack_bonus(self) -> int:
        weapon = self.equipped["weapon"]
        if weapon:
            return self.attributes["toughness"] + weapon.stats.get("bonus", 0)
        return self.attributes["toughness"]
        
    def get_defense_bonus(self) -> int:
        armor = self.equipped["armor"]
        if armor:
            return self.attributes["nimbleness"] + armor.stats.get("bonus", 0)
        return self.attributes["nimbleness"]
        
    def get_item(self, item_name: str) -> Optional[Item]:
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                return item
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class": self.character_class,
            "level": self.level,
            "attributes": self.attributes,
            "hit_points": self.hit_points,
            "inventory": [item.to_dict() for item in self.inventory],
            "equipped": {
                "weapon": self.equipped["weapon"].to_dict() if self.equipped["weapon"] else None,
                "armor": self.equipped["armor"].to_dict() if self.equipped["armor"] else None,
                "accessories": [item.to_dict() for item in self.equipped["accessories"]]
            }
        }

class LazyRuleLoader:
    def __init__(self, rules_dir_path: str):
        self.rules_dir_path = rules_dir_path
        self._loaded_rules: Dict[str, Any] = {}
        if not os.path.isdir(self.rules_dir_path):
            # Create the directory if it doesn't exist
            try:
                os.makedirs(self.rules_dir_path)
                logger.info("Rules directory '%s' created.", self.rules_dir_path)
            except OSError as e:
                logger.warning("Could not create rules directory '%s': %s", self.rules_dir_path, e)
                # Depending on desired behavior, could raise an error or proceed with an empty loader
                # For now, it will proceed, and attempts to load files will fail gracefully.

    def __getitem__(self, rule_filename: str) -> Dict[str, Any]:
        if rule_filename not in self._loaded_rules:
            filepath = os.path.join(self.rules_dir_path, rule_filename)
            try:
                with open(filepath, 'r') as f:
                    self._loaded_rules[rule_filename] = json.load(f)
            except FileNotFoundError:
                logger.warning("Rule file '%s' not found.", filepath)
                self._loaded_rules[rule_filename] = {} # Return empty dict if file not found
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON from '%s'.", filepath)
                self._loaded_rules[rule_filename] = {} # Return empty dict if JSON is invalid
        return self._loaded_rules[rule_filename]

    def __setitem__(self, key: str, value: Any):
        raise NotImplementedError("Rules are read-only after initial definition.")

    def __delitem__(self, key: str):
        raise NotImplementedError("Rules are read-only and cannot be deleted.")

    def keys(self) -> List[str]:
        try:
            return [f for f in os.listdir(self.rules_dir_path) if f.endswith('.json')]
        except FileNotFoundError:
            logger.warning("Rules directory '%s' not found when trying to list keys.", self.rules_dir_path)
            return []

    def __iter__(self):
        return iter(self.keys())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self.__getitem__(key)
        except KeyError: # Should be handled by __getitem__ returning {}
            return default if default is not None else {}

class RPGGame:
    def __init__(self, groq_engine: GroqEngine, save_dir: str = "saves"):
        self.groq_engine = groq_engine
        self.save_dir = save_dir
        self.current_player = None
        self.combat_mode = False
        self.current_enemy = None
        self.session_history: List[Dict[str, str]] = []
        self.npc_memory = NPCMemory()
        self.game_time = {
            'day': 1,
            'hour': 8,  # Start at 8:00 AM
            'minute': 0,
            'last_updated': time.time()
        }
        # Ensure save directory exists
        os.makedirs(self.save_dir, exist_ok=True)
        self.command_handlers = {
            # Movement and location
            "look": self._handle_look,
            "l": self._handle_look,
            "go": self._handle_go,
            "move": self._handle_go,
            "travel": self._handle_go,
            "location": self._handle_location,  # Show current location
            "where am i": self._handle_location,  # Natural language for location
            
            # Inventory and equipment
            "inventory": self._handle_inventory,
            "i": self._handle_inventory,
            "equip": self._handle_equip,
            
            # Character status
            "status": self._handle_status,
            "stats": self._handle_status,
            
            # NPC interaction
            "talk": self._handle_talk,
            "npc": self._handle_npc_info,
            "npcs": self._handle_npcs,
            
            # Time
            "time": self._handle_time,
            "what time is it": self._handle_time,  # Natural language time command
            
            # Navigation
            "exits": self._handle_exits,   # Show available exits
            "locations": self._handle_exits, # Alias for exits
            
            # Game management
            "save": self._handle_save,
            "load": self._handle_load,
            "saves": self._handle_list_saves,
            "help": self._handle_help,
            "h": self._handle_help,
            "exit": self._handle_exit,
            "quit": self._handle_exit,
        }
        self.session_memory = {
            "actions": [],
            "player_state": {},
            "location_history": [],
            "npc_interactions": {},
            "environment": {},
            "last_prompt": "",
            "last_response": "",
            "context_summary": "",
            "important_events": [],
            "visited_locations": set(),
            "npcs_met": set(),
        }
        
        # Initialize location cache
        self._current_location_cache = {}
        self._last_known_player_location = None
        
        # Initialize game data
        self.locations = {}
        self.initialize_locations()
        self._initialize_npcs()
        
    def initialize_locations(self):
        """Initialize game locations with their descriptions and connections."""
        self.locations = {
            "Starting Town": {
                "description": "A small, peaceful town with a few shops and houses. The town square is bustling with activity. The cobblestone streets are lined with colorful market stalls, and the scent of freshly baked bread wafts from the local bakery. To the north stands a sturdy blacksmith's forge, while to the east you can see the apothecary's shop with its colorful bottles in the window. The sound of cheerful music and raucous laughter draws your attention to 'The Tipsy Traveler' tavern, where the warm glow of the hearth spills out through its inviting windows. The friendly bartender, Branwen, is known for her hearty stew and local gossip.",
                "connections": ["Forest Clearing", "Mountain Pass", "Riverside Dock", "Blacksmith's Forge", "Apothecary's Shop", "The Tipsy Traveler Tavern"],
                "npcs": ["Eldrin", "Gorak", "Marla", "Thorik", "Branwen"]
            },
            "Blacksmith's Forge": {
                "description": "The heat from the forge hits you as you enter the blacksmith's workshop. The walls are lined with tools and weapons in various stages of completion. The blacksmith looks up from their work as you enter.",
                "connections": ["Starting Town"],
                "npcs": ["Thorik"]
            },
            "Apothecary's Shop": {
                "description": "The apothecary's shop is filled with the scent of dried herbs and potions. Shelves line the walls, packed with jars of mysterious ingredients and colorful liquids. The apothecary is busy at work behind the counter.",
                "connections": ["Starting Town"],
                "npcs": ["Eldrin"]
            },
            "The Tipsy Traveler Tavern": {
                "description": "The tavern is warm and inviting, with a crackling fire in the hearth. Patrons sit at wooden tables, enjoying food and drink. The bartender wipes down the counter while keeping an eye on the room.",
                "connections": ["Starting Town"],
                "npcs": ["Branwen"]
            },
            "Forest Clearing": {
                "description": "A serene clearing in the middle of a dense forest. The air is fresh and filled with the sounds of wildlife.",
                "connections": ["Starting Town", "Ancient Ruins"],
                "npcs": ["Lily"]
            },
            "Mountain Pass": {
                "description": "A narrow path winding through the mountains. The air is thin and the wind howls through the rocks.",
                "connections": ["Starting Town", "Dwarven Mines"],
                "npcs": []
            },
            "Dwarven Mines": {
                "description": "The entrance to ancient dwarven mines. The air is filled with the sound of dripping water and distant echoes.",
                "connections": ["Mountain Pass"],
                "npcs": []
            },
            "Ancient Ruins": {
                "description": "Crumbling stone structures covered in vines. There's an air of mystery and ancient power here.",
                "connections": ["Forest Clearing"],
                "npcs": []
            }
        }

    def _initialize_npcs(self):
        """Initialize NPCs in the game world."""
        # Starting Town NPCs
        # Eldrin now runs the Apothecary
        eldrin = NPC("Eldrin", "Apothecary", "Apothecary's Shop", "merchants")
        eldrin.is_merchant = True
        eldrin.merchant_inventory = [
            {"name": "Health Potion", "price": 50, "type": "consumable"},
            {"name": "Mana Potion", "price": 60, "type": "consumable"},
            {"name": "Antidote", "price": 40, "type": "consumable"},
            {"name": "Herbal Remedy", "price": 30, "type": "consumable"},
            {"name": "Smelling Salts", "price": 25, "type": "consumable"}
        ]
        
        # Blacksmith NPC
        thorik = NPC("Thorik", "Blacksmith", "Blacksmith's Forge", "craftsmen")
        thorik.is_merchant = True
        thorik.merchant_inventory = [
            {"name": "Iron Sword", "price": 100, "type": "weapon"},
            {"name": "Steel Dagger", "price": 75, "type": "weapon"},
            {"name": "Chainmail Armor", "price": 200, "type": "armor"},
            {"name": "Iron Helmet", "price": 80, "type": "armor"},
            {"name": "Repair Kit", "price": 50, "type": "tool"}
        ]
        
        # Tavern Keeper
        branwen = NPC("Branwen", "Bartender", "The Tipsy Traveler Tavern", "tavern_keepers")
        branwen.is_merchant = True
        branwen.merchant_inventory = [
            {"name": "Ale", "price": 5, "type": "food", "effects": ["restore 5 hp"]},
            {"name": "Hearty Stew", "price": 10, "type": "food", "effects": ["restore 15 hp"]},
            {"name": "Room for the Night", "price": 20, "type": "service", "effects": ["fully restore hp"]},
            {"name": "Local Rumor", "price": 5, "type": "information"}
        ]
        
        gorak = NPC("Gorak", "Guard Captain", "Starting Town", "town_guard")
        marla = NPC("Marla", "Baker", "Starting Town", "townsfolk")
        lily = NPC("Lily", "Herbalist", "Forest Clearing", "druids")
        
        # Add NPCs to memory
        self.npc_memory.add_npc(eldrin)
        self.npc_memory.add_npc(gorak)
        self.npc_memory.add_npc(marla)
        self.npc_memory.add_npc(thorik)
        self.npc_memory.add_npc(branwen)
        self.npc_memory.add_npc(lily)
        
        # Set up some initial faction relationships
        self.npc_memory.update_faction_relationship("town_guard", "merchants", 50)  # Guards like merchants
        self.npc_memory.update_faction_relationship("town_guard", "bandits", -75)  # Guards hate bandits
        self.npc_memory.update_faction_relationship("druids", "bandits", -50)  # Druids dislike bandits

    def _handle_look(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
            
        current_loc = self.current_player.current_location
        if not current_loc:
            return "You don't seem to be anywhere specific right now."
        
        # Get location data and ensure it exists
        location_data = self.locations.get(current_loc, {})
        if not location_data:
            # If location doesn't exist in our data, create a basic entry
            location_data = {
                "description": f"You are in {current_loc}.",
                "npcs": []
            }
            self.locations[current_loc] = location_data
        
        # Get all NPCs in this location
        npcs_here = [npc for npc in self.npc_memory.npcs.values() 
                    if hasattr(npc, 'location') and npc.location.lower() == current_loc.lower()]
        
        # Update location's NPC list
        location_npcs = []
        for npc in npcs_here:
            if npc.name not in location_npcs:
                location_npcs.append(npc.name)
        
        # Update location data with current NPCs
        if "npcs" not in location_data:
            location_data["npcs"] = []
        
        # Add any new NPCs to the location's NPC list
        for npc_name in location_npcs:
            if npc_name not in location_data["npcs"]:
                location_data["npcs"].append(npc_name)
        
        # Generate dynamic description based on time of day and NPCs present
        time_of_day = self._get_time_of_day()
        description_parts = []
        
        # Start with base description if available
        base_desc = location_data.get("description", f"You are in {current_loc}.")
        description_parts.append(base_desc)
        
        # Add time of day flavor
        time_flavor = {
            "morning": "The morning sun casts long shadows across the area.",
            "day": "The area is bathed in daylight.",
            "evening": "The setting sun paints the sky in warm colors.",
            "night": "The area is dimly lit by moonlight and stars."
        }.get(time_of_day, "")
        
        if time_flavor and time_flavor not in description_parts[0]:
            description_parts.append(time_flavor)
        
        # Add NPC descriptions
        if npcs_here:
            npc_descriptions = []
            for npc in npcs_here:
                role = getattr(npc, 'role', 'person')
                # Define actions for specific NPCs first
                specific_actions = {
                    "Eldrin": ["arranging potions on a shelf", "chatting with customers", "inspecting his wares"],
                    "Gorak": ["standing at attention", "patrolling the area", "keeping a watchful eye on the town"],
                    "Lily": ["tending to herbs", "mixing potions", "chatting with visitors"]
                }
                
                # If this is one of our predefined NPCs, use their specific actions
                if npc.name in specific_actions:
                    action = random.choice(specific_actions[npc.name])
                else:
                    # Fall back to role-based actions for other NPCs
                    npc_actions = {
                        "shopkeeper": ["arranging wares on a table", "chatting with customers", "inspecting goods"],
                        "guard captain": ["giving orders to the guards", "inspecting the town's defenses", "speaking with townsfolk"],
                        "herbalist": ["sorting herbs", "preparing remedies", "tending to plants"],
                        "blacksmith": ["hammering at the forge", "shaping metal on an anvil", "tending to the furnace"],
                        "merchant": ["arranging wares on a table", "chatting with customers", "inspecting goods"],
                        "guard": ["standing watch", "patrolling the area", "keeping a sharp eye out"],
                        "mage": ["studying a dusty tome", "muttering incantations", "mixing potions"],
                        "villager": ["going about their business", "chatting with neighbors", "enjoying the day"]
                    }
                    action = random.choice(npc_actions.get(role.lower(), ["standing nearby"]))
                npc_descriptions.append(f"{npc.name} the {role} is {action}.")
            
            description_parts.append("\n" + "\n".join(npc_descriptions))
        else:
            # Only add this if there are no NPCs and it's not already in the description
            if "don't see anyone" not in base_desc.lower() and "no one" not in base_desc.lower():
                description_parts.append("\nYou don't see anyone else here at the moment.")
        
        # Update the location description with the new dynamic description
        location_data["description"] = " ".join(description_parts).strip()
        
        # Build the response
        response_parts = [location_data["description"]]
        
        # Add exit information if available
        if "exits" in location_data and location_data["exits"]:
            exits = ", ".join(location_data["exits"])
            response_parts.append(f"\nExits: {exits}")
        
        return "\n".join(response_parts)
    
    def _get_time_of_day(self) -> str:
        """Return a string representing the current time of day."""
        hour = self.game_time['hour']
        if 5 <= hour < 10:
            return "morning"
        elif 10 <= hour < 17:
            return "day"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _handle_inventory(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
            
        response = []
        
        # Show equipped items first
        equipped_items = []
        if self.current_player.equipped["weapon"]:
            equipped_items.append(f"Weapon: {self.current_player.equipped['weapon'].name}")
        if self.current_player.equipped["armor"]:
            equipped_items.append(f"Armor: {self.current_player.equipped['armor'].name}")
        if self.current_player.equipped["accessories"]:
            accessories = ", ".join(acc.name for acc in self.current_player.equipped["accessories"])
            equipped_items.append(f"Accessories: {accessories}")
            
        if equipped_items:
            response.append("Equipped Items:")
            response.extend(f"- {item}" for item in equipped_items)
        else:
            response.append("No items equipped.")
            
        # Show inventory
        if self.current_player.inventory:
            response.append("\nInventory:")
            for item in self.current_player.inventory:
                # Check if item is equipped
                is_equipped = False
                equipped_slot = None
                
                if self.current_player.equipped["weapon"] and item == self.current_player.equipped["weapon"]:
                    equipped_slot = "weapon"
                elif self.current_player.equipped["armor"] and item == self.current_player.equipped["armor"]:
                    equipped_slot = "armor"
                elif item in self.current_player.equipped["accessories"]:
                    equipped_slot = "accessory"
                
                if equipped_slot:
                    response.append(f"- {item.name} (equipped as {equipped_slot})")
                else:
                    response.append(f"- {item.name}")
        else:
            response.append("\nYour inventory is empty.")
            
        return "\n".join(response)

    def _handle_time(self, args: List[str]) -> str:
        """Handle time command."""
        return f"Current time: {self.get_current_time_str()}"

    def _handle_status(self, args: List[str]) -> str:
        """Handle status command."""
        if not self.current_player:
            return "You need to create a character first."
        
        status = [
            f"Time: {self.get_current_time_str()}",
            "",
            self.current_player.format_status()
        ]
        return "\n".join(status)

    def _handle_equip(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        if not args:
            return "What would you like to equip?"
        item_name = " ".join(args)
        for item in self.current_player.inventory:
            if item.name.lower() == item_name.lower():
                # Assuming Character.equip_item returns a string response
                return self.current_player.equip_item(item)
        return f"You don't have '{item_name}' in your inventory."

    def move_player(self, destination: str) -> str:
        """
        Move the player to a new location if it's a valid destination.
        
        Args:
            destination: The name of the location to move to
            
        Returns:
            str: Message describing the result of the movement attempt
        """
        current_location = self.current_player.current_location
        location_data = self.locations.get(current_location, {})
        
        # Check if destination is a valid location from current location
        connections = location_data.get('connections', [])
        if not connections:
            return f"You can't go anywhere from {current_location}."
            
        # Find the destination in the connections (case-insensitive)
        destination_lower = destination.lower()
        valid_destinations = [loc for loc in connections if loc.lower() == destination_lower]
        
        if not valid_destinations:
            return f"You can't go to {destination} from here. Available locations: {', '.join(connections)}"
            
        # Get the properly cased destination name
        new_location = valid_destinations[0]
        
        # Update player's location
        self.current_player.current_location = new_location
        
        # Update session memory
        if 'visited_locations' not in self.session_memory:
            self.session_memory['visited_locations'] = set()
        self.session_memory['visited_locations'].add(new_location)
        
        # Return the description of the new location
        new_location_data = self.locations.get(new_location, {})
        return f"You have arrived at {new_location}. {new_location_data.get('description', '')}"

    def advance_time(self, minutes: int = None) -> None:
        """
        Advance the game time by a random or specified number of minutes.
        
        Args:
            minutes: Number of minutes to advance. If None, advances by a random amount between 10 and 60 minutes.
        """
        if minutes is None:
            minutes = random.randint(10, 60)
            
        # Add minutes to current time
        self.game_time['minute'] += minutes
        
        # Handle minute overflow
        while self.game_time['minute'] >= 60:
            self.game_time['minute'] -= 60
            self.game_time['hour'] += 1
            
            # Handle hour overflow
            if self.game_time['hour'] >= 24:
                self.game_time['hour'] = 0
                self.game_time['day'] += 1
        
        # Update last updated timestamp
        self.game_time['last_updated'] = time.time()
    
    def get_current_time_str(self) -> str:
        """
        Get the current in-game time as a formatted string.
        
        Returns:
            str: Formatted time string (e.g., "Day 1, 08:30 AM")
        """
        hour = self.game_time['hour']
        ampm = 'AM' if hour < 12 else 'PM'
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        return f"Day {self.game_time['day']}, {display_hour:02d}:{self.game_time['minute']:02d} {ampm}"

    def _handle_go(self, args: List[str]) -> str:
        """
        Handle player movement to a new location.
        
        Args:
            args: List of destination location words
            
        Returns:
            str: Description of the movement and new location
        """
        if not self.current_player:
            return "You need to create a character first."
            
        if not args:
            return "Where would you like to go?"
            
        # Handle different command formats: "go to the X", "go to X", or "go X"
        if len(args) >= 3 and args[0].lower() == 'to' and args[1].lower() == 'the':
            destination = " ".join(args[2:])  # "go to the mountain pass" -> "mountain pass"
        elif len(args) >= 2 and args[0].lower() == 'to':
            destination = " ".join(args[1:])   # "go to mountain pass" -> "mountain pass"
        else:
            destination = " ".join(args)        # "go mountain pass" -> "mountain pass"
            
        current_location = self.current_player.current_location
        
        # Normalize the destination to match the case in connections
        location_data = self.locations.get(current_location, {})
        connections = location_data.get('connections', [])
        
        # Find case-insensitive match in connections
        normalized_connections = {loc.lower(): loc for loc in connections}
        
        if destination.lower() in normalized_connections:
            # Use the properly cased version from connections
            destination = normalized_connections[destination.lower()]
            
            # Check if the destination is a special location that should trigger talking to an NPC
            npc_to_talk = None
            if destination == "Apothecary's Shop":
                npc_to_talk = "Eldrin"
            elif destination == "Blacksmith's Forge":
                npc_to_talk = "Thorik"
            elif destination == "The Tipsy Traveler Tavern":
                npc_to_talk = "Branwen"
            
            # If it's a special location with an NPC, handle the talk command
            if npc_to_talk:
                return self._handle_talk([npc_to_talk])
            
            # Move to the new location
            result = self.move_player(destination)
            
            # Get current location after movement
            new_location = self.current_player.current_location
            
            # If location changed, update session memory and advance time
            if current_location != new_location:
                self.advance_time()  # Advance time when changing locations
                self.update_session_memory(
                    f"traveled from {current_location} to {new_location}",
                    f"Arrived at {new_location}."
                )
                
                # Update location memory and add discovery event if first visit
                self.update_location_memory(new_location)
                if 'visited_locations' not in self.session_memory:
                    self.session_memory['visited_locations'] = set()
                    
                if new_location not in self.session_memory['visited_locations']:
                    self.session_memory['visited_locations'].add(new_location)
                    self.add_important_event(
                        event_type="discovery",
                        description=f"Discovered {new_location}",
                        location=new_location,
                        importance=7
                    )
            
            return result
        else:
            return f"You can't go to {destination} from here. Available locations: {', '.join(connections)}"
                
    def _extract_and_create_npcs(self, text: str, location: str) -> List[str]:
        """
        Extract NPC names from text and create them in the game if they don't exist.
        
        Args:
            text: The text to search for NPC names
            location: The current location where NPCs should be created
            
        Returns:
            List of NPC names that were found and potentially created
        """
        import re
        
        # Look for proper nouns that are likely NPC names
        potential_npcs = re.findall(r'(?<!\.\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
        
        created_npcs = []
        
        # Define predefined NPCs and their roles
        predefined_npcs = {
            "Eldrin": {"role": "Shopkeeper", "faction": "merchants"},
            "Gorak": {"role": "Guard Captain", "faction": "town_guard"},
            "Lily": {"role": "Herbalist", "faction": "druids"}
        }
        
        # Filter out common false positives and existing NPCs
        common_false_positives = {'The', 'You', 'I', 'He', 'She', 'It', 'We', 'They', 'This', 'That', 'Here', 'There'}
        
        for name in potential_npcs:
            # Skip if it's a common word or already exists
            if (name in common_false_positives or 
                any(npc.name.lower() == name.lower() for npc in self.npc_memory.npcs.values())):
                continue
                
            # Skip if it's a location name
            if name in self.locations:
                continue
                
            # Check if this is a predefined NPC
            if name in predefined_npcs:
                npc_info = predefined_npcs[name]
                role = npc_info["role"]
                faction = npc_info["faction"]
                
                # Create the predefined NPC with their specific role and faction
                new_npc = NPC(name, role, location, faction)
                
                # Add to NPC memory
                self.npc_memory.add_npc(new_npc)
                created_npcs.append(name)
                
                # Ensure location exists in self.locations
                if location not in self.locations:
                    self.locations[location] = {"description": f"You are in {location}.", "npcs": []}
                
                # Add to location's NPC list if not already present (case-insensitive check)
                if "npcs" not in self.locations[location]:
                    self.locations[location]["npcs"] = []
                    
                if not any(npc.lower() == name.lower() for npc in self.locations[location]["npcs"]):
                    self.locations[location]["npcs"].append(name)
                    logger.info(f"Added {name} to {location}'s NPC list")
                
                logger.info(f"Created new NPC: {name} the {role} at {location}")
        
        return created_npcs

    def _handle_talk(self, args: List[str]) -> str:
        """
        Handle conversation with an NPC.
        
        Args:
            args: List of words containing the NPC's name
            
        Returns:
            str: The NPC's dialogue or an error message
        """
        if not self.current_player:
            return "You need to create a character first."
            
        if not args:
            return "Who would you like to talk to?"

        # Handle both "talk to npc" and "talk npc" formats
        if args[0].lower() == 'to' and len(args) > 1:
            npc_name = ' '.join(args[1:])
        else:
            npc_name = ' '.join(args)
            
        if not npc_name:
            return "You need to specify who you want to talk to."
            
        # Get current location details
        location = self.current_player.current_location
        location_details = self.get_current_location()
        if not location_details:
            return "You can't see anyone around to talk to."
            
        # Find NPC in current location with fuzzy matching
        npc = None
        npc_name_found = None
        
        # First try exact match in NPC memory
        npc = self.npc_memory.get_npc(npc_name)
        if npc:
            npc_name_found = npc_name
        else:
            # If not found, try to find the closest matching NPC name in the current location
            location_npcs = location_details.get("npcs", [])
            
            # First try simple case-insensitive partial match
            for candidate in location_npcs:
                if npc_name.lower() in candidate.lower():
                    npc_name_found = candidate
                    npc = self.npc_memory.get_npc(candidate)
                    break
                    
            # If still no match, try more flexible matching
            if not npc and len(npc_name) > 2:  # Only try fuzzy matching for names longer than 2 chars
                for candidate in location_npcs:
                    # Check for transpositions, missing/extra characters (common typos)
                    if (abs(len(npc_name) - len(candidate)) <= 2 and
                        sum(1 for a, b in zip(npc_name.lower(), candidate.lower()) if a == b) >= max(len(npc_name), len(candidate)) - 1):
                        npc_name_found = candidate
                        npc = self.npc_memory.get_npc(candidate)
                        break
        
        # If we still don't have an NPC, try to find any NPC in the location
        if not npc and location_npcs:
            for candidate in location_npcs:
                npc_candidate = self.npc_memory.get_npc(candidate)
                if npc_candidate:
                    npc_name_found = candidate
                    npc = npc_candidate
                    break
                    
        # If we still don't have an NPC, create a new one if we have a name
        if not npc and npc_name_found:
            npc = NPC(
                name=npc_name_found,
                role="villager",
                location=location
            )
            self.npc_memory.add_npc(npc)
            
        if not npc:
            return f"You don't see anyone named '{npc_name}' here. Try 'look' to see who's around."
            
        # At this point, we should have a valid NPC

        # Update NPC's last seen time and location
        npc.last_seen = datetime.now()
        npc.location = location
        
        # Ensure player has a relationship with this NPC
        player_id = f"player_{self.current_player.name.lower().replace(' ', '_')}"
        relationship = npc.get_relationship(player_id)
        
        # First meeting handling
        if relationship.interaction_count == 0:
            if 'npcs_met' not in self.session_memory:
                self.session_memory['npcs_met'] = set()
            self.session_memory['npcs_met'].add(npc_name_found)
            self.add_important_event(
                event_type="social",
                description=f"Met {npc_name_found} for the first time",
                location=location,
                importance=6
            )
        
        # Generate NPC dialogue with relationship context
        disposition = npc.get_disposition(player_id)
        
        # Create a more detailed role description that includes relationship status
        npc_role = getattr(npc, 'role', 'person')
        detailed_role = f"{npc_role} who is {disposition} towards {self.current_player.name}"
        
        dialogue = self.groq_engine.generate_npc_dialogue(
            npc_name_found,
            self.current_player.name,
            location,
            npc_role=detailed_role,
            player_class=getattr(self.current_player, 'character_class', 'adventurer')
        )
        
        # Check for and create any NPCs mentioned in the dialogue
        created_npcs = self._extract_and_create_npcs(dialogue, location)
        if created_npcs:
            logger.info(f"Created new NPCs from dialogue: {', '.join(created_npcs)}")
            # Update the location description to include the new NPCs
            if location in self.locations and "npcs" in self.locations[location]:
                npc_list = self.locations[location]["npcs"]
                if npc_list:
                    npc_descriptions = [f"{npc} the {self.npc_memory.get_npc(npc).role if self.npc_memory.get_npc(npc) else 'villager'}" 
                                       for npc in npc_list if self.npc_memory.get_npc(npc)]
                    if npc_descriptions:
                        self.locations[location]["description"] = (
                            f"You are in {location}. You see {', '.join(npc_descriptions)} here."
                        )
        
        # Update relationship based on interaction
        # Positive affinity for general conversation
        if relationship.interaction_count < 5:  # Diminishing returns
            relationship.update_affinity(5 - relationship.interaction_count)
        
        relationship.interaction_count += 1
        relationship.last_interaction = datetime.now()
        
        # Add to conversation history
        self.update_session_memory(
            f"talked to {npc_name_found}",
            f"{npc_name_found}: {dialogue}"
        )
        
        return f"{npc_name_found}: {dialogue}"

    def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """
        Process user input and dispatch it to the appropriate command handler.
        
        Args:
            user_input: The raw input string from the user
            context: Optional context dictionary for additional information
            
        Returns:
            str: The response to display to the user
        """
        if not user_input.strip():
            return "Please enter a command. Type 'help' for a list of commands."
            
        # Convert to lowercase for case-insensitive matching
        input_lower = user_input.strip().lower()
        
        # First try to find a multi-word command match (like 'what time is it')
        for cmd in self.command_handlers:
            if ' ' in cmd and input_lower.startswith(cmd):
                # Extract arguments after the command
                args = user_input[len(cmd):].strip().split()
                try:
                    return self.command_handlers[cmd](args)
                except Exception as e:
                    return f"Error executing command: {str(e)}"
        
        # If no multi-word command matched, split into command and arguments
        parts = input_lower.split()
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Check if the command exists in the command handlers
        if command in self.command_handlers:
            try:
                # Call the appropriate handler with the arguments
                return self.command_handlers[command](args)
            except Exception as e:
                logger.error(f"Error executing command '{command}': {str(e)}")
                return f"An error occurred while processing your command: {str(e)}"
        else:
            return f"Unknown command: {command}. Type 'help' for a list of available commands."

    def _handle_time(self, args: List[str]) -> str:
        """
        Display the current in-game time and time of day.
        
        Args:
            args: Not used
            
        Returns:
            str: Current in-game time and time of day
        """
        time_str = self.get_current_time_str()
        time_of_day = self._get_time_of_day()
        return f"Current time: {time_str} ({time_of_day.capitalize()})"

    def _handle_location(self, args: List[str]) -> str:
        """
        Show the player's current location with description.
        
        Args:
            args: Not used
            
        Returns:
            str: Current location description
        """
        if not self.current_player:
            return "You need to create a character first."
            
        current_location = self.current_player.current_location
        location_data = self.locations.get(current_location, {})
        
        # Get time of day for description
        time_of_day = self._get_time_of_day()
        
        # Build the response
        response = [f"You are in {current_location}."]
        
        # Add time of day flavor text if available
        if "descriptions" in location_data and time_of_day in location_data["descriptions"]:
            response.append(location_data["descriptions"][time_of_day])
        elif "description" in location_data:
            response.append(location_data["description"])
            
        # Add NPCs in the location if any
        npcs = location_data.get("npcs", [])
        if npcs:
            npc_list = ", ".join(npcs)
            response.append(f"\nYou see here: {npc_list}")
            
        return "\n".join(response)

    def _handle_exits(self, args: List[str]) -> str:
        """
        Show available exits from the current location.
        
        Args:
            args: Not used
            
        Returns:
            str: List of available exits
        """
        if not self.current_player:
            return "You need to create a character first."
            
        current_location = self.current_player.current_location
        location_data = self.locations.get(current_location, {})
        
        # First check for explicit exits
        if "exits" in location_data and location_data["exits"]:
            exits = ", ".join(location_data["exits"])
            return f"Available exits: {exits}"
            
        # Fall back to connections if no explicit exits
        if "connections" in location_data and location_data["connections"]:
            exits = ", ".join(location_data["connections"])
            return f"Available exits: {exits}"
            
        return f"There are no visible exits from {current_location}."

    def _handle_npcs(self, args: List[str]) -> str:
        """
        List all NPCs in the current location.
        
        Args:
            args: Not used
            
        Returns:
            str: List of NPCs in the current location
        """
        if not self.current_player:
            return "You need to create a character first."
            
        current_location = self.current_player.current_location
        location_data = self.locations.get(current_location, {})
        
        # Get NPCs from location data
        npc_names = location_data.get('npcs', [])
        
        if not npc_names:
            return f"There are no NPCs in {current_location} right now."
            
        # Get NPC details from NPC memory
        npcs = []
        for npc_name in npc_names:
            npc = self.npc_memory.get_npc(npc_name)
            if npc:
                role = getattr(npc, 'role', 'person')
                npcs.append(f"- {npc_name} (the {role})")
            else:
                npcs.append(f"- {npc_name}")
        
        return f"NPCs in {current_location}:\n" + "\n".join(npcs)

    def _handle_npc_info(self, args: List[str]) -> str:
        """
        Display information about an NPC.
        
        Args:
            args: List containing the NPC's name
            
        Returns:
            str: Information about the NPC or an error message
        """
        if not self.current_player:
            return "You need to create a character first."
            
        if not args:
            return "Which NPC would you like information about?"
            
        npc_name = ' '.join(args)
        npc = self.npc_memory.get_npc(npc_name)
        
        if not npc:
            return f"You don't know anyone named {npc_name}."
            
        # Get player's relationship with this NPC
        player_id = f"player_{self.current_player.name.lower().replace(' ', '_')}"
        relationship = npc.get_relationship(player_id)
        disposition = npc.get_disposition(player_id)
        
        # Format NPC information
        info = [
            f"=== {npc.name} ===",
            f"Role: {npc.role}",
            f"Faction: {npc.faction}",
            f"Location: {npc.location}",
            f"Disposition: {disposition} ({relationship.affinity} / 100)",
            f"Times met: {relationship.interaction_count}",
            f"Last seen: {npc.last_seen.strftime('%Y-%m-%d %H:%M') if npc.last_seen else 'Unknown'}",
            "\nKnown locations:" + ("\n- " + "\n- ".join(npc.known_locations) if npc.known_locations else " None"),
        ]
        
        # Add faction relationships if any
        faction_relationships = []
        for faction, score in self.npc_memory.factions.get(npc.faction, {}).items():
            status = "friendly" if score > 30 else "neutral" if score > -30 else "hostile"
            faction_relationships.append(f"{faction}: {status} ({score})")
            
        if faction_relationships:
            info.append("\nFaction relationships:")
            info.extend(faction_relationships)
        
        return "\n".join(info)

    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state for saving."""
        if not self.current_player:
            raise ValueError("No player character exists to save")
            
        return {
            'player': {
                'name': self.current_player.name,
                'character_class': self.current_player.character_class,
                'level': self.current_player.level,
                'hit_points': self.current_player.hit_points,
                'max_hit_points': self.current_player.max_hit_points,
                'current_location': self.current_player.current_location,
                'inventory': [item.to_dict() for item in self.current_player.inventory],
                'equipped': {
                    'weapon': self.current_player.equipped['weapon'].to_dict() if self.current_player.equipped['weapon'] else None,
                    'armor': self.current_player.equipped['armor'].to_dict() if self.current_player.equipped['armor'] else None,
                    'accessories': [item.to_dict() for item in self.current_player.equipped['accessories']]
                },
                'attributes': self.current_player.attributes
            },
            'game_state': {
                'locations_visited': list(self.session_memory.get('visited_locations', set())),
                'npcs_met': list(self.npc_memory.npcs.keys()),
                'game_time': self.game_time,
                'session_history': self.session_history[-100:],  # Keep last 100 entries
            },
            'npc_data': self.npc_memory.to_dict()
        }

    def load_game_state(self, game_data: Dict[str, Any]) -> None:
        """Load a game state from saved data."""
        # Load player data
        player_data = game_data.get('player', {})
        if not player_data:
            raise ValueError("No player data found in save file")

        # Create player
        self.current_player = Character(
            name=player_data['name'],
            character_class=player_data['character_class'],
            level=player_data['level']
        )
        
        # Restore player state
        self.current_player.hit_points = player_data['hit_points']
        self.current_player.max_hit_points = player_data['max_hit_points']
        self.current_player.current_location = player_data['current_location']
        self.current_player.attributes = player_data.get('attributes', {})
        
        # Restore inventory
        self.current_player.inventory = []
        for item_data in player_data.get('inventory', []):
            item = Item(
                name=item_data['name'],
                item_type=item_data['item_type'],
                stats=item_data['stats'],
                stackable=item_data.get('stackable', False),
                max_stack=item_data.get('max_stack', 1)
            )
            if 'quantity' in item_data:
                item.quantity = item_data['quantity']
            self.current_player.inventory.append(item)
        
        # Restore equipped items
        equipped_data = player_data.get('equipped', {})
        if equipped_data.get('weapon'):
            weapon_data = equipped_data['weapon']
            weapon = Item(
                name=weapon_data['name'],
                item_type=weapon_data['item_type'],
                stats=weapon_data['stats']
            )
            self.current_player.equipped['weapon'] = weapon
        
        if equipped_data.get('armor'):
            armor_data = equipped_data['armor']
            armor = Item(
                name=armor_data['name'],
                item_type=armor_data['item_type'],
                stats=armor_data['stats']
            )
            self.current_player.equipped['armor'] = armor
        
        self.current_player.equipped['accessories'] = []
        for acc_data in equipped_data.get('accessories', []):
            accessory = Item(
                name=acc_data['name'],
                item_type=acc_data['item_type'],
                stats=acc_data['stats']
            )
            self.current_player.equipped['accessories'].append(accessory)
        
        # Restore game state
        game_state = game_data.get('game_state', {})
        self.session_memory['visited_locations'] = set(game_state.get('locations_visited', []))
        self.game_time = game_state.get('game_time', self.game_time)
        self.session_history = game_state.get('session_history', [])
        
        # Restore NPC data
        if 'npc_data' in game_data:
            self.npc_memory = NPCMemory.from_dict(game_data['npc_data'])
        
        return "Game loaded successfully!"

    def _handle_save(self, args: List[str]) -> str:
        """Handle save game command."""
        if not self.current_player:
            return "No active game to save. Create a character first."
            
        save_name = args[0] if args else None
        try:
            game_data = self.get_game_state()
            return save_system.save_game(game_data, save_name)
        except Exception as e:
            return f"Error saving game: {str(e)}"

    def _handle_load(self, args: List[str]) -> str:
        """Handle load game command."""
        if not args:
            return "Please specify a save file to load. Use 'saves' to list available saves."
        
        save_name = args[0]
        try:
            game_data = save_system.load_game(save_name)
            self.load_game_state(game_data)
            return f"Game loaded successfully from '{save_name}'"
        except Exception as e:
            return f"Error loading game: {str(e)}"

    def _handle_list_saves(self, args: List[str]) -> str:
        """List all available save files."""
        saves = save_system.list_saves()
        if not saves:
            return "No save files found."
        
        result = ["=== Available Saves ==="]
        for i, save in enumerate(saves, 1):
            result.append(f"{i}. {save['name']} - {save['date']} (Character: {save['character']})")
        
        result.append("\nUse 'load <number>' to load a save.")
        return "\n".join(result)

    def _handle_help(self, args: List[str]) -> str:
        """Display help information about available commands and game features."""
        help_text = [
            f"\n=== {self.current_player.name}'s Adventure - Help ===" if self.current_player else "\n=== Adventure Game - Help ===",
            "Available commands:",
            "  look, l          - Look around your current location",
            "  go <direction>   - Move in a direction (north, south, east, west, etc.)",
            "  inventory, i     - View your inventory",
            "  equip <item>     - Equip an item from your inventory",
            "  status, stats    - View your character's status",
            "  time             - Check the current in-game time",
            "  talk <npc>       - Talk to an NPC",
            "  npc <name>       - Get information about an NPC",
            "  save [name]      - Save your game (optional name)",
            "  load <name>      - Load a saved game",
            "  saves            - List all saved games",
            "  help, h          - Show this help message",
            "  exit, quit       - Exit the game"
        ]
        return "\n" + "\n".join(help_text)
        help_text.append("Type 'help combat' for combat commands.")
        help_text.append("Type 'help movement' for movement commands.")
        
        # Check for specific help topics
        if args:
            topic = args[0].lower()
            if topic == "memory":
                help_text.append(self._get_memory_help())
            elif topic == "combat":
                help_text.append(self._get_combat_help())
            elif topic == "movement":
                help_text.append(self._get_movement_help())
        
        return "\n".join(help_text)

    def _handle_exit(self, args: List[str]) -> str:
        """Handle exit command."""
        return "exit"

    def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user input using command handlers."""
        if not user_input.strip():
            return ""
            
        # Split input into command and arguments
        parts = user_input.lower().split()
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Advance time for any command except looking around
        if command not in ["look", "l", "inventory", "i", "status", "stats", "help", "h"]:
            self.advance_time()
        
        # Check for NPC interaction patterns (e.g., "talk to npc" or "npc_name, hello")
        if ',' in user_input or any(word in user_input.lower() for word in ["talk to", "say to", "tell"]):
            return "Please use the 'Talk to NPC' button at the top to interact with NPCs."
            
        # Check for command handlers first
        handler = self.command_handlers.get(command)
        if handler:
            return handler(args)
            
        # If no command handler matches, check if this is an NPC interaction
        if self.current_player:
            location_data = self.get_current_location()
            if location_data and 'npcs' in location_data:
                # Check if the input starts with an NPC's name
                for npc in location_data['npcs']:
                    if user_input.lower().startswith(npc.lower()):
                        return f"To talk to {npc}, please use the 'Talk to NPC' button at the top."
            
            # If not an NPC interaction, use Groq AI for natural language processing
            player_tuple = (
                self.current_player.name,
                self.current_player.character_class,
                self.current_player.level
            )
            # Pass the original, un-lowercased, stripped input for more natural AI descriptions
            try:
                return self.groq_engine.generate_action_description(player_tuple, user_input.strip())
            except Exception as e:
                if 'relationship_status' in str(e):
                    return "Please use the 'Talk to NPC' button at the top to interact with NPCs."
                raise
                
        return f"I don't understand '{user_input}'. Type 'help' for a list of commands."

    # def load_rules(self): # This method is no longer needed due to LazyRuleLoader
    #     """Load all rule files from the Json Files directory."""
    #     rules_dir = "Json Files"
    #     for filename in os.listdir(rules_dir):
    #         if filename.endswith('.json'):
    #             try:
    #                 with open(os.path.join(rules_dir, filename), 'r') as f:
    #                     self.rules[filename] = json.load(f) # Now handled by LazyRuleLoader
    #             except Exception as e:
    #                 print(f"Warning: Failed to load {filename}: {e}")

    def update_session_memory(self, action: str, response: str):
        """
        Update the session memory with the latest action and response.
        
        Args:
            action: The player's action or input
            response: The game's response to the action
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        action_entry = {
            "timestamp": timestamp,
            "action": action,
            "response": response,
            "location": self.current_player.current_location if self.current_player else "Unknown"
        }
        
        # Update session history and actions
        self.session_history.append(action_entry)
        self.session_memory["actions"].append(action_entry)
        
        # Keep only the most recent 50 actions to prevent memory bloat
        if len(self.session_memory["actions"]) > 50:
            self.session_memory["actions"] = self.session_memory["actions"][-50:]
            
        # Update last prompt/response
        self.session_memory["last_prompt"] = action
        self.session_memory["last_response"] = response
        
        # Update location memory if player exists
        if self.current_player:
            self.update_location_memory(self.current_player.current_location)
            self._update_player_state()
        
        # Update context summary
        self._update_context_summary()
        
        # Periodically generate a new session summary
        if len(self.session_memory["actions"]) % 10 == 0:  # Every 10 actions
            if self.current_player:
                self.session_memory["last_summary"] = self.generate_session_summary()
        if self.current_player:
            self._update_player_state()
            
    def _update_player_state(self):
        """Update the player state in session memory."""
        if not self.current_player:
            return
            
        self.session_memory["player_state"] = {
            "name": self.current_player.name,
            "class": self.current_player.character_class,
            "level": self.current_player.level,
            "hit_points": self.current_player.hit_points,
            "location": self.current_player.current_location,
            "inventory": [item.name for item in self.current_player.inventory],
            "equipped": {
                "weapon": self.current_player.equipped["weapon"].name if self.current_player.equipped["weapon"] else None,
                "armor": self.current_player.equipped["armor"].name if self.current_player.equipped["armor"] else None,
                "accessories": [acc.name for acc in self.current_player.equipped["accessories"] if acc]
            },
            "status_effects": []  # Can be expanded with actual status effects
        }
    
    def _update_context_summary(self):
        """Generate and update the context summary for the current game state."""
        if not self.current_player:
            self.session_memory["context_summary"] = "New game session started."
            return
            
        # Get recent actions (last 3)
        recent_actions = self.session_memory.get("actions", [])[-3:]
        
        # Initialize environment with default values if not present
        if 'environment' not in self.session_memory:
            self.session_memory['environment'] = {
                'time_of_day': 'day',
                'weather': 'clear'
            }
            
        # Ensure required environment keys exist
        env = self.session_memory['environment']
        if 'time_of_day' not in env:
            env['time_of_day'] = 'day'
        if 'weather' not in env:
            env['weather'] = 'clear'
        
        # Build context parts
        context_parts = [
            f"Current Location: {self.current_player.current_location}",
            f"Time: {env['time_of_day'].capitalize()}",
            f"Weather: {env['weather'].capitalize()}",
            "\nRecent Actions:"
        ]
        
        # Add recent actions
        for action in recent_actions:
            # Safely get timestamp and action text
            timestamp = action.get('timestamp', 'Unknown Time')
            action_text = action.get('action', 'Unknown Action')
            context_parts.append(f"- [{timestamp}] {action_text}")
        
        # Add NPCs in current location if available
        current_location = self.session_memory.get('current_location', {})
        if isinstance(current_location, dict) and 'npcs' in current_location:
            npcs = current_location.get('npcs', [])
            if npcs and isinstance(npcs, list):
                context_parts.append("\nNPCs here: " + ", ".join(str(npc) for npc in npcs))
        
        # Add player status
        context_parts.extend([
            "\nPlayer Status:",
            f"HP: {self.current_player.hit_points}",
            f"Level: {self.current_player.level} {self.current_player.character_class}"
        ])
        
        self.session_memory["context_summary"] = "\n".join(context_parts)
    
    def build_groq_context(self) -> str:
        """Build a rich context string for Groq AI prompts."""
        if not hasattr(self, 'session_memory') or not self.session_memory:
            return "New game session. No context available yet."
            
        # Start with the pre-built context summary
        context = [self.session_memory.get("context_summary", "")]
        
        # Add any additional context that might be useful for the AI
        if self.combat_mode and self.current_enemy:
            context.append(f"\nCOMBAT: Engaged with {self.current_enemy.get('name', 'an enemy')} (HP: {self.current_enemy.get('hp', '?')})")
        
        # Add items in the current location if available
        if 'items' in self.session_memory.get('current_location', {}):
            items = self.session_memory['current_location']['items']
            if items:
                context.append("\nItems here: " + ", ".join(items))
        
        # Add any important game state information
        if self.session_memory.get('player_state', {}).get('status_effects'):
            effects = self.session_memory['player_state']['status_effects']
            if effects:
                context.append("\nStatus Effects: " + ", ".join(effects))
        
        return "\n".join(filter(None, context))

    def _generate_session_summary(self):
        """Generate a summary of recent actions for session context."""
        recent_actions = self.session_memory.get("actions", [])[-5:]
        if not recent_actions:
            return "No recent actions to summarize."
            
        summary = ["Recent Events:"]
        
        for action in recent_actions:
            timestamp = action.get('timestamp', '??:??')
            location = action.get('location', 'unknown location')
            summary.append(f"- [{timestamp}] {location}: {action.get('action', '...')}")
            
            # Add a brief response summary if available
            response = action.get('response', '')
            if response:
                summary.append(f"  > {response.split('.')[0]}")
        
        return "\n".join(summary)

    # build_prompt method removed as it's no longer used.
    # AI prompts are now generated directly within the specific GroqEngine methods
    # (generate_description, generate_npc_dialogue, generate_action_description, generate_combat_description).

    def initialize_game_data(self):
        """Initialize game data including locations and items."""
        self.locations = {
            "Starting Town": {
                "description": "A bustling town with cobblestone streets and wooden houses.",
                "exits": ["Forest", "Market Square"],
                "npcs": ["Mayor", "Shopkeeper", "Guard"]
            },
            "Forest": {
                "description": "A dense forest with tall trees and winding paths.",
                "exits": ["Starting Town", "Cave"],
                "enemies": ["Goblin", "Wolf", "Bandit"],
                "npcs": ["Forest Ranger", "Herbalist"]
            },
            "Market Square": {
                "description": "A busy marketplace with various shops and stalls.",
                "exits": ["Starting Town", "Blacksmith", "Tavern"],
                "npcs": ["Merchant", "Blacksmith", "Innkeeper"]
            },
            "Cave": {
                "description": "A dark and foreboding cave with glowing crystals.",
                "exits": ["Forest"],
                "enemies": ["Goblin", "Orc Warrior", "Cave Spider"]
            }
        }

        self.enemies = {
            "Goblin": {
                "level": 1,
                "hit_points": 10,
                "attributes": {
                    "strength": 8,
                    "dexterity": 12,
                    "constitution": 9
                }
            },
            "Orc Warrior": {
                "level": 2,
                "hit_points": 15,
                "attributes": {
                    "strength": 14,
                    "dexterity": 10,
                    "constitution": 12
                }
            },
            "Wolf": {
                "level": 1,
                "hit_points": 8,
                "attributes": {
                    "strength": 10,
                    "dexterity": 15,
                    "constitution": 8
                }
            },
            "Bandit": {
                "level": 2,
                "hit_points": 12,
                "attributes": {
                    "strength": 12,
                    "dexterity": 14,
                    "constitution": 10
                }
            },
            "Cave Spider": {
                "level": 3,
                "hit_points": 20,
                "attributes": {
                    "strength": 15,
                    "dexterity": 18,
                    "constitution": 12
                }
            }
        }

    def create_character(self, name: str, character_class: str) -> Character:
        """Create a new character with the given name and class."""
        try:
            self.current_player = Character(name, character_class)
            # Add starting items based on class
            if character_class.lower() == "warrior":
                self.current_player.add_item(Item("Iron Sword", "weapon", {"bonus": 5, "weight": 2}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"bonus": 3, "weight": 3}))
            elif character_class.lower() == "mage":
                self.current_player.add_item(Item("Wooden Staff", "weapon", {"bonus": 3, "weight": 1}))
                self.current_player.add_item(Item("Robe", "armor", {"bonus": 1, "weight": 2}))
            elif character_class.lower() == "rogue":
                self.current_player.add_item(Item("Dagger", "weapon", {"bonus": 4, "weight": 1}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"bonus": 2, "weight": 2}))
            return self.current_player
        except ValueError as e:
            logger.error("Error creating character: %s", e)
            return None

    def get_current_location(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get the current location details. Uses a cache that can be refreshed."""
        if not self.current_player:
            return {}

        # Check cache first
        if not force_refresh and \
           self._current_location_cache and \
           self.current_player.current_location == self._last_known_player_location:
            return self._current_location_cache

        # If cache miss, refresh is forced, or player has moved, fetch new data
        location_name = self.current_player.current_location
        base_location_data = self.locations.get(location_name, {})

        if not base_location_data:
            logger.warning("Location data for '%s' not found in self.locations.", location_name)
            self._current_location_cache = {
                "name": location_name,
                "description": "An unknown area.",
                "dynamic_description": "It's an unfamiliar place."
            }
            self._last_known_player_location = location_name
            return self._current_location_cache
            
        # Update the last known location
        self._last_known_player_location = location_name
        
        # Get NPC information with their correct roles
        npcs_info = []
        for npc_name in base_location_data.get("npcs", []):
            npc = self.npc_memory.get_npc(npc_name)
            if npc:
                npcs_info.append({
                    "name": npc.name,
                    "role": getattr(npc, 'role', 'person'),
                    "faction": getattr(npc, 'faction', 'neutral')
                })
        
        # Generate dynamic description if not in cache
        dynamic_description = self.groq_engine.generate_description({
            "location": location_name,
            "description": base_location_data.get("description", ""),
            "exits": base_location_data.get("exits", []),
            "npcs": npcs_info,
            "instructions": "When describing NPCs, maintain their specified roles. "
                            "Eldrin is always the shopkeeper, Gorak is always the guard captain, "
                            "and Lily is always the herbalist."
        })
        
        # Update cache with location data
        self._current_location_cache = {
            "name": location_name,
            "description": base_location_data.get("description", ""),
            "dynamic_description": dynamic_description,
            "exits": base_location_data.get("exits", []),
            "npcs": base_location_data.get("npcs", []),
            "items": base_location_data.get("items", [])
        }

        return self._current_location_cache

    def handle_attack(self) -> str:
        """Handle player attack during combat."""
        if not self.current_enemy:
            return "No enemy to attack!"
            
        # Calculate attack roll
        roll = random.randint(1, 20)
        # Access squad_tactics.json through LazyRuleLoader
        squad_tactics_rules = self.rules["squad_tactics.json"]
        if not squad_tactics_rules: # Handle case where rule file failed to load
             logger.warning("squad_tactics.json rules not available for combat.")
             hit_bonus = self.current_player.attributes.get("strength", 0) # Default bonus
             damage = self.current_player.attributes.get("strength", 0) # Default damage
        else:
            hit_bonus = self.current_player.attributes.get("strength", 0) + squad_tactics_rules.get("combat", {}).get("hit_bonus", 0)
            damage = self.current_player.attributes.get("strength", 0) + squad_tactics_rules.get("combat", {}).get("damage_bonus", 0)

        total_roll = roll + hit_bonus
        
        # Check if hit
        if total_roll >= 10:  # Base AC
            self.current_enemy.hit_points -= damage
            
            if self.current_enemy.hit_points <= 0:
                self.end_combat("You defeated the enemy!")
                return "You strike a killing blow! The enemy falls to the ground."
                
            return f"You hit the {self.current_enemy.name} for {damage} damage!"
        
        return f"You miss the {self.current_enemy.name}!"

    def end_combat(self, message: str) -> str:
        """End combat mode with a message."""
        self.combat_mode = False
        self.current_enemy = None
        return message

    def show_inventory(self):
        """Display the player's inventory in a formatted way using list join."""
        if not self.current_player:
            return "No player character selected"

        parts = []
        parts.append("=" * 50)
        parts.append("Inventory:")
        parts.append("=" * 50)
        # Note: f-string with \n might be okay, but for consistency, could also be separate appends.
        # For this specific line, f-string is fine as it's a single conceptual unit.
        parts.append(f"\nWeight: {self.current_player.inventory_weight}/{self.current_player.max_inventory_weight} kg")
        parts.append("-" * 50)

        parts.append("\nEquipped:") # Leading newline for spacing
        parts.append("-" * 10)
        weapon_name = self.current_player.equipped["weapon"].name if self.current_player.equipped["weapon"] else "None"
        armor_name = self.current_player.equipped["armor"].name if self.current_player.equipped["armor"] else "None"
        parts.append(f"Weapon: {weapon_name}")
        parts.append(f"Armor: {armor_name}")

        parts.append("\nAccessories:") # Leading newline for spacing
        if self.current_player.equipped["accessories"]:
            for acc in self.current_player.equipped["accessories"]:
                parts.append(f"- {acc.name}")
        else:
            parts.append("  None") # Indent "None"

        parts.append("\nInventory Items:") # Leading newline for spacing
        if self.current_player.inventory:
            for item in self.current_player.inventory:
                parts.append(f"- {item}") # Relies on Item.__str__
        else:
            parts.append("  Your inventory is empty.") # Indent for clarity

        return "\n".join(parts)



    def unequip_item(self, slot: str) -> str:
        """Unequip an item from a specific slot."""
        if not self.current_player:
            return "No player character selected"

        if slot not in self.current_player.equipped:
            return f"Invalid slot: {slot}"

        item = self.current_player.equipped[slot]
        if not item:
            return f"No item equipped in {slot}"

        self.current_player.equipped[slot] = None
        return f"Unequipped {item.name} from {slot}"

    def examine_item(self, item_name: str) -> str:
        """Examine an item in detail."""
        if not self.current_player:
            return "No player character selected"

        item = next((i for i in self.current_player.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            return f"No item named '{item_name}' in inventory"

        return f"""
Examining {item.name}:
Type: {item.item_type}
Weight: {item.stats.get('weight', 0)} kg
Attributes: {json.dumps(item.stats, indent=2)}
"""
    
    def save_game(self, filename: str = None) -> str:
        """
        Save the current game state to a file, including NPC system data.
        
        Args:
            filename: Optional filename to save to. If not provided, uses a timestamp.
            
        Returns:
            str: Status message indicating success or failure
        """
        if not self.current_player:
            return "No active game to save."
            
        # Create saves directory if it doesn't exist
        os.makedirs(self.save_dir, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.current_player.name}_{timestamp}.json"
        elif not filename.endswith('.json'):
            filename += '.json'
            
        save_path = os.path.join(self.save_dir, filename)
        
        try:
            # Prepare game data for saving
            save_data = {
                "player": self.current_player.to_dict(),
                "session_memory": self.session_memory,
                "npc_memory": self.npc_memory.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "version": "1.1.0"  # Bump version for NPC system
            }
            
            # Save to file
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
                
            return f"Game saved successfully to {filename}"
            
        except Exception as e:
            logger.error(f"Error saving game: {e}")
            return f"Failed to save game: {e}"

    def load_game(self, filename: str) -> str:
        """
        Load a saved game from a file, including NPC system data.
        
        Args:
            filename: Name of the save file to load
            
        Returns:
            str: Status message indicating success or failure
        """
        if not filename.endswith('.json'):
            filename += '.json'
            
        save_path = os.path.join(self.save_dir, filename)
        
        if not os.path.exists(save_path):
            return f"Save file '{filename}' not found."
            
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
                
            # Verify version compatibility
            save_version = save_data.get('version', '1.0.0')  # Default to 1.0.0 for backward compatibility
            if save_version not in ["1.0.0", "1.1.0"]:
                return f"Incompatible save file version: {save_version}"
            
            # Load player data
            player_data = save_data.get('player', {})
            if not player_data:
                return "Invalid save file: Missing player data"
                
            # Create player from saved data
            self.current_player = Character(
                name=player_data['name'],
                character_class=player_data['character_class'],
                level=player_data['level']
            )
            
            # Restore player state
            if 'hit_points' in player_data:
                self.current_player.hit_points = player_data['hit_points']
            
            # Restore inventory
            if 'inventory' in player_data:
                self.current_player.inventory = [
                    Item(
                        item['name'], 
                        item['item_type'], 
                        item.get('stats', {}),
                        item.get('stackable', False), 
                        item.get('max_stack', 1)
                    )
                    for item in player_data['inventory']
                ]
            
            # Restore equipped items
            if 'equipped' in player_data:
                equipped = player_data['equipped']
                if 'weapon' in equipped and equipped['weapon']:
                    w = equipped['weapon']
                    self.current_player.equipped['weapon'] = Item(w['name'], w['item_type'], w.get('stats', {}))
                    
                if 'armor' in equipped and equipped['armor']:
                    a = equipped['armor']
                    self.current_player.equipped['armor'] = Item(a['name'], a['item_type'], a.get('stats', {}))
                
                if 'accessories' in equipped:
                    self.current_player.equipped['accessories'] = [
                        Item(acc['name'], acc['item_type'], acc.get('stats', {}))
                        for acc in equipped['accessories']
                    ]
            
            # Restore session memory
            self.session_memory = save_data.get('session_memory', {})
            
            # Convert lists back to sets for compatibility
            if 'visited_locations' in self.session_memory and isinstance(self.session_memory['visited_locations'], list):
                self.session_memory['visited_locations'] = set(self.session_memory['visited_locations'])
            if 'npcs_met' in self.session_memory and isinstance(self.session_memory['npcs_met'], list):
                self.session_memory['npcs_met'] = set(self.session_memory['npcs_met'])
            
            # Load NPC memory if available (version 1.1.0+)
            if save_version >= "1.1.0" and 'npc_memory' in save_data:
                self.npc_memory = NPCMemory.from_dict(save_data['npc_memory'])
            else:
                # For older saves, initialize with default NPCs and update with any met NPCs
                self._initialize_npcs()
                if 'npcs_met' in self.session_memory:
                    for npc_name in self.session_memory['npcs_met']:
                        if npc_name in self.npc_memory.npcs:
                            self.npc_memory.npcs[npc_name].last_seen = datetime.now()
            
            # Restore game state
            self.current_enemy = save_data.get('current_enemy')
            self.combat_mode = save_data.get('combat_mode', False)
            self.current_time = save_data.get('current_time', time.time())
            self.current_weather = save_data.get('current_weather', 'clear')
            
            # Invalidate location cache to force refresh
            self._current_location_cache = None
            self._last_known_player_location = self.current_player.current_location
            
            # Update the location cache
            self.get_current_location(force_refresh=True)
            
            # Update NPC last seen times if needed
            current_time = datetime.now()
            for npc in self.npc_memory.npcs.values():
                if not hasattr(npc, 'last_seen'):
                    npc.last_seen = current_time
            
            return f"Game loaded successfully. Welcome back, {self.current_player.name}!"
            
        except Exception as e:
            logger.error(f"Error loading game: {e}")
            return f"Failed to load game: {str(e)}"
    
    def list_saves(self) -> List[str]:
        """List all available save files."""
        save_dir = Path("saves")
        if not save_dir.exists():
            return []
        return [f.name for f in save_dir.glob("*.json") if f.is_file()]
        
    # ===== Memory Management Methods =====
    
    def generate_session_summary(self) -> str:
        """
        Generate a summary of the current game session.
        
        Returns:
            str: A concise summary of the session
        """
        if not hasattr(self, 'current_player') or not self.current_player:
            return "No active game session to summarize."
            
        summary_parts = []
        
        # Basic session info
        summary_parts.append(f"Session with {self.current_player.name} the {self.current_player.character_class} (Level {self.current_player.level})")
        
        # Location info
        if 'current_location' in self.session_memory and self.session_memory['current_location']:
            loc = self.session_memory['current_location']
            summary_parts.append(f"Currently in: {loc.get('name', 'Unknown location')}")
            
        # Recent activities
        if self.session_memory.get('actions'):
            recent_actions = [
                f"- {action['action']}" 
                for action in self.session_memory['actions'][-5:]  # Last 5 actions
                if 'action' in action
            ]
            if recent_actions:
                summary_parts.append("\nRecent actions:" + "\n" + "\n".join(recent_actions))
        
        # Important events (combat, quests, etc.)
        if self.combat_mode:
            summary_parts.append("\nCurrently in combat!")
            if self.current_enemy:
                summary_parts.append(f"Fighting: {self.current_enemy.get('name', 'an enemy')}")
        
        return "\n".join(summary_parts)
    
    def update_location_memory(self, location_name: str) -> None:
        """
        Update location-specific memories.
        
        Args:
            location_name: Name of the location to update memories for
        """
        if 'location_memories' not in self.session_memory:
            self.session_memory['location_memories'] = {}
            
        if location_name not in self.session_memory['location_memories']:
            self.session_memory['location_memories'][location_name] = {
                'first_visited': datetime.now().isoformat(),
                'visit_count': 1,
                'last_visited': datetime.now().isoformat(),
                'important_events': []
            }
        else:
            loc_mem = self.session_memory['location_memories'][location_name]
            loc_mem['visit_count'] = loc_mem.get('visit_count', 0) + 1
            loc_mem['last_visited'] = datetime.now().isoformat()
    
    def add_important_event(self, event_type: str, description: str, location: str = None, importance: int = 5) -> None:
        """
        Record an important game event.
        
        Args:
            event_type: Type of event (e.g., 'combat', 'quest', 'discovery')
            description: Description of the event
            location: Where the event occurred (defaults to current location)
            importance: Importance level (1-10)
        """
        if 'important_events' not in self.session_memory:
            self.session_memory['important_events'] = []
            
        event = {
            'type': event_type,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'location': location or (self.current_player.current_location if self.current_player else 'unknown'),
            'importance': max(1, min(10, importance))  # Clamp between 1-10
        }
        
        self.session_memory['important_events'].append(event)
        
        # Also add to location memories if applicable
        if event['location'] != 'unknown':
            if 'location_memories' not in self.session_memory:
                self.session_memory['location_memories'] = {}
            if event['location'] not in self.session_memory['location_memories']:
                self.session_memory['location_memories'][event['location']] = {
                    'first_visited': datetime.now().isoformat(),
                    'visit_count': 0,
                    'last_visited': datetime.now().isoformat(),
                    'important_events': []
                }
            self.session_memory['location_memories'][event['location']]['important_events'].append(event)
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of game memories.
        
        Returns:
            dict: Structured memory summary
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'player': {
                'name': self.current_player.name if self.current_player else 'No player',
                'level': self.current_player.level if self.current_player else 1,
                'class': self.current_player.character_class if self.current_player else 'None'
            },
            'current_location': self.session_memory.get('current_location', {}).get('name', 'Unknown'),
            'locations_visited': len(self.session_memory.get('visited_locations', [])),
            'npcs_met': len(self.session_memory.get('npcs_met', [])),
            'important_events': self.session_memory.get('important_events', []),
            'session_duration': self._calculate_session_duration()
        }
        
        # Add location memories if available
        if 'location_memories' in self.session_memory:
            summary['location_memories'] = {
                loc: {
                    'visit_count': mem.get('visit_count', 0),
                    'last_visited': mem.get('last_visited'),
                    'event_count': len(mem.get('important_events', []))
                }
                for loc, mem in self.session_memory['location_memories'].items()
            }
            
        return summary
    
    def _calculate_session_duration(self) -> str:
        """Calculate the duration of the current session."""
        if not self.session_memory.get('actions'):
            return "0 minutes"
            
        try:
            first_action = self.session_memory['actions'][0]['timestamp']
            last_action = self.session_memory['actions'][-1]['timestamp']
            
            # Parse timestamps
            fmt = "%Y-%m-%d %H:%M:%S"
            start = datetime.strptime(first_action, fmt)
            end = datetime.strptime(last_action, fmt)
            
            # Calculate duration
            duration = end - start
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if hours > 0:
                return f"{hours} hours and {minutes} minutes"
            return f"{minutes} minutes"
            
        except (KeyError, ValueError):
            return "Unknown duration"

def display_header():
    print("\n" + "=" * 80)
    print("Dungeon Master RPG")
    print("=" * 80)
    print()
    
def save_game_command(game: RPGGame, filename: str = None) -> str:
    """Handle the save game command from the UI."""
    return game.save_game(filename)

def load_game_command(game: RPGGame, filename: str) -> str:
    """Handle the load game command from the UI."""
    return game.load_game(filename)

def list_saves_command(game: RPGGame) -> List[str]:
    """List all available save files."""
    return game.list_saves()

def display_character_info(player: Character):
    print("Player Info:")
    print(f"Name: {player.name}")
    print(f"Class: {player.character_class}")
    print(f"Level: {player.level}")
    print(f"HP: {player.hit_points}")
    print("\nAttributes:")
    for attr, value in player.attributes.items():
        print(f"{attr.capitalize()}: {value}")
    print()

def display_inventory(player: Character):
    print("Inventory:")
    if not player.inventory:
        print("Empty")
        return
    
    for item in player.inventory:
        print(f"- {item.name} ({item.item_type})")
    print()

def display_main_menu(has_character: bool = False):
    print("\nMain Menu:")
    if not has_character:
        print("1. Create a new character")
    else:
        print("1. Move to a new location")
        print("2. View inventory")
        print("3. Equip item")
        print("4. View character status")
        print("5. Look around")
        print("6. Talk to NPC")
        print("7. Save game")
        print("8. Load game")
        print("9. Exit game")
    print()

if __name__ == '__main__':
    display_header()
    print("Welcome to the Text RPG!")
    game = RPGGame()
    
    # Character creation
    print("\n--- Character Creation ---")
    while True:
        name = input("Enter your character's name: ").strip()
        if name:
            break
            
    while True:
        char_class = input("Choose your class (Warrior, Mage, Rogue): ").strip()
        if char_class.lower() in ['warrior', 'mage', 'rogue']:
            break

    player = game.create_character(name, char_class)
    print(f"\nWelcome, {player.name} the {player.character_class}!")
    print(game.show_inventory())
    print("\nType 'help' to see the main menu")
    
    # Main game loop
    while True:
        display_main_menu()
        user_input = input("\n> ").strip()
        if user_input.lower() == "exit":
            break
            
        response = game.process_input(user_input)
        print(response)
    
    print("\nThank you for playing!")
