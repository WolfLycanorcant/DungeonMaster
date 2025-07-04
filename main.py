from game import RPGGame, GroqEngine, display_header, display_character_info, display_inventory, display_main_menu

def create_character(game):
    print("\n--- Character Creation ---")
    while True:
        name = input("Enter your character's name: ").strip()
        if name:
            break
            
    while True:
        char_class = input("Choose your class (Warrior, Mage, Rogue): ").strip().capitalize()
        if char_class.lower() in ['warrior', 'mage', 'rogue']:
            break
            
    try:
        game.create_character(name, char_class)
        print(f"\nWelcome, {name} the {char_class}!")
        print("Character created successfully!")
        return True
    except Exception as e:
        print(f"Error creating character: {str(e)}")
        return False

def main():
    # Initialize the Groq engine
    groq_engine = GroqEngine()
    
    # Initialize the game with the Groq engine
    game = RPGGame(groq_engine)
    context = {"current_location": "Starting Town"}
    display_header()
    print("Welcome to the Dungeon Master RPG!\n")
    
    # Initial character creation
    while not game.current_player:
        if not create_character(game):
            if input("\nTry again? (y/n): ").lower() != 'y':
                print("\nGoodbye!")
                return
    
    while True:
        display_main_menu(has_character=bool(game.current_player))
        try:
            choice = input("\nChoose an option: ").strip()
            
            if not game.current_player:
                if choice == '1':
                    create_character(game)
                elif choice.lower() in ['exit', 'quit', '7']:
                    print("\nThank you for playing!")
                    break
                else:
                    print("\nPlease create a character first!")
                continue
                
            # Game commands when character exists
            if choice == '1':  # Move
                destination = input("\nEnter destination: ").strip()
                if destination:
                    try:
                        output = game.process_input(f"go {destination}", context)
                        # Ensure we print the complete output
                        print("\n" + "="*80)
                        print(output)
                        print("="*80)
                    except Exception as e:
                        print(f"\nError processing command: {str(e)}")
            elif choice == '2':  # Inventory
                display_inventory(game.current_player)
            elif choice == '3':  # Equip
                item_name = input("\nEnter item to equip: ").strip()
                if item_name:
                    output = game.process_input(f"equip {item_name}", context)
                    print(f"\n{output}")
            elif choice == '4':  # Status
                display_character_info(game.current_player)
            elif choice == '5':  # Look
                try:
                    output = game.process_input("look", context)
                    # Ensure we print the complete output
                    print("\n" + "="*80)
                    print(output)
                    print("="*80)
                except Exception as e:
                    print(f"\nError processing command: {str(e)}")
            elif choice.startswith('6 '):  # Talk to NPC (format: '6 NPCName')
                npc_name = choice[1:].strip()
                if npc_name:
                    try:
                        output = game.process_input(f"talk to {npc_name}", context)
                        # Ensure we print the complete output
                        print("\n" + "="*80)
                        print(output)
                        print("="*80)
                    except Exception as e:
                        print(f"\nError talking to NPC: {str(e)}")
            elif choice == '6':  # If just '6' was entered, prompt for NPC name
                npc_name = input("\nEnter NPC name to talk to: ").strip()
                if npc_name:
                    try:
                        output = game.process_input(f"talk to {npc_name}", context)
                        # Ensure we print the complete output
                        print("\n" + "="*80)
                        print(output)
                        print("="*80)
                    except Exception as e:
                        print(f"\nError talking to NPC: {str(e)}")
            elif choice == '7':  # Save game
                filename = input("\nEnter save file name (leave blank for auto-name): ").strip()
                try:
                    save_path = game.save_game(filename or None)
                    print(f"\nGame saved successfully to: {save_path}")
                except Exception as e:
                    print(f"\nError saving game: {str(e)}")
            elif choice == '8':  # Load game
                print("\nAvailable saves:")
                try:
                    saves = game.list_saves()
                    if not saves:
                        print("No save files found.")
                        continue
                        
                    for i, save in enumerate(saves, 1):
                        print(f"{i}. {save}")
                    
                    while True:
                        try:
                            selection = input("\nSelect save to load (number) or 'c' to cancel: ").strip().lower()
                            if selection == 'c':
                                break
                                
                            idx = int(selection) - 1
                            if 0 <= idx < len(saves):
                                game = game.load_game(saves[idx])
                                print(f"\nGame loaded successfully from: {saves[idx]}")
                                context = {"current_location": game.current_player.current_location if game.current_player else "Unknown"}
                                break
                            else:
                                print("Invalid selection. Please try again.")
                        except ValueError:
                            print("Please enter a valid number or 'c' to cancel.")
                except Exception as e:
                    print(f"\nError loading game: {str(e)}")
            elif choice in ['9', 'exit', 'quit']:
                if input("\nAre you sure you want to quit? Any unsaved progress will be lost. (y/n): ").lower() == 'y':
                    print("\nThank you for playing!")
                    break
            else:
                print("\nInvalid choice. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Thank you for playing!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    main()
