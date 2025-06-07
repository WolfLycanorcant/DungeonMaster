from typing import Dict, Any, List, Optional
import json

class Item:
    def __init__(self, name: str, item_type: str, stats: Dict[str, Any], stackable: bool = False, max_stack: int = 1):
        self.name = name
        self.item_type = item_type
        self.stats = stats
        self.stackable = stackable
        self.max_stack = max_stack
        self.quantity = 1 if stackable else None
        
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
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
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
        con_mod = (self.attributes["constitution"] - 10) // 2
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
        else:
            return f"Unknown item type: {item.item_type}"
        
        self.inventory.remove(item)
        return f"Equipped {item.name}"
        
    def get_attack_bonus(self) -> int:
        weapon = self.equipped["weapon"]
        if weapon:
            return self.attributes["strength"] + weapon.stats.get("bonus", 0)
        return self.attributes["strength"]
        
    def get_defense_bonus(self) -> int:
        armor = self.equipped["armor"]
        if armor:
            return self.attributes["dexterity"] + armor.stats.get("bonus", 0)
        return self.attributes["dexterity"]
        
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
