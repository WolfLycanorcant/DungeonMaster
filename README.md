# Dungeon Master RPG

A text-based RPG game with Groq AI integration, built with Python and Flask. Experience a dynamic adventure with rich character progression, interactive gameplay, and immersive world exploration.

## Features

- **Character System**
  - Create characters with unique classes (Warrior, Mage, Rogue)
  - Detailed character attributes and progression
  - Visual character status panel with health, mana, and experience bars
  - Equipment management with weapon, armor, and accessory slots

- **Gameplay**
  - Dynamic world generation with Groq AI
  - Real-time combat system with turn-based mechanics
  - Interactive NPCs with AI-powered dialogue
  - Location-based exploration with unique encounters
  - Dynamic "look around" functionality with contextual descriptions
  - Time-of-day based environment changes
  - Enemy encounters with varying difficulty levels

- **Inventory & Items**
  - Comprehensive inventory management system
  - Item categories (weapons, armor, consumables, quest items)
  - Item details including value, weight, and special properties
  - Equipment comparison and quick-equip functionality

- **User Interface**
  - **Responsive Design** - Works on desktop and tablet devices
  - **Interactive Console** - Rich text output with proper formatting and colors
  - **Status Panels** - Real-time updates for character stats and inventory
  - **Visual Feedback** - Animated messages and loading indicators
  - **Error Handling** - Clear error messages and recovery options
  - **Keyboard Shortcuts** - Quick access to common commands
  - **Accessibility** - High contrast mode and text scaling options

## 🚀 Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file with your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=mixtral-8x7b-instruct
   ```

3. **Launch the Game**
   ```bash
   # Windows
   ./start.bat
   
   # Linux/MacOS
   python -m Server.app
   ```

4. **Access the Game**
   Open your browser and navigate to:
   ```
   http://localhost:30000
   ```

## Game Controls

### Character Management
- Click "Start New Game" to create a new character
- Select your character class (Warrior, Mage, or Rogue)
- Click "Character Status" to view your character's stats and equipment
- Use the inventory panel to manage your items and equipment

### Combat
- Click "Start Combat" to begin a battle
- Use "Player Attack" to attack enemies
- Special abilities unlock as you level up
- Monitor your health and mana during combat

### Exploration
- **Look Around** - Get detailed descriptions of your current location
- **Dynamic Environment** - Experience changing descriptions based on time of day
- **Interactive Elements** - Discover and interact with objects in the environment
- **NPC Awareness** - See what NPCs are nearby and what they're doing
- **Hidden Secrets** - Find hidden items and locations through careful observation

### NPC Interaction
- Talk to NPCs for quests and information
- Complete quests to earn rewards
- Build relationships with different factions

### Inventory & Equipment
- Drag and drop items to equip/unequip
- Sort and filter your inventory
- Check item details by hovering over them
- Compare equipment stats before equipping

## 🌟 Recent Updates

### v1.2.0 - Enhanced Exploration
- Completely revamped "look around" system
- Dynamic environment descriptions based on time and location
- Improved NPC presence and activities in locations
- Better error handling and recovery
- Smoother UI with loading states and animations

### v1.1.0 - UI Improvements
- Redesigned console output with better formatting
- Visual feedback for actions and errors
- Improved mobile responsiveness
- Streamlined inventory management

## 🎮 Game Mechanics

### Character Progression
- Gain experience points (XP) through combat and quests
- Level up to increase attributes and unlock abilities
- Each class has unique skill trees and playstyles
- Attribute points can be allocated on level up

### Combat System
- Turn-based combat with initiative order
- Different attack types (melee, ranged, magic)
- Status effects and conditions (poison, stun, etc.)
- Critical hits and special abilities

### Inventory System
- Weight-based carrying capacity
- Item rarity system (common, uncommon, rare, epic, legendary)
- Stackable items where applicable
- Quick slots for frequently used items

### World Interaction
- Dynamic day/night cycle
- Weather system affecting gameplay
- NPC schedules and routines
- Interactive objects in the environment

### Recent Updates
- Added visual character status panel
- Implemented detailed inventory management
- Enhanced equipment comparison
- Improved UI/UX with tooltips and help text
- Added support for item tooltips and detailed descriptions
- Implemented responsive design for different screen sizes
- Groq AI generates dynamic content for locations and NPC dialogue

## Project Structure

```
Dungeon Master/
├── Server/
│   ├── app.py          # Flask application
│   └── templates/      # HTML templates
├── game.py            # Game logic and character classes
├── requirements.txt   # Project dependencies
├── start.bat         # Start script
└── .env             # Environment variables
```

## Technology Stack

- Python 3.x
- Flask
- Groq AI
- HTML/CSS/JavaScript

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
