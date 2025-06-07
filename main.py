from game import RPGGame, display_header, display_character_info, display_inventory, display_main_menu

def main():
    game = RPGGame()
    context = {"current_location": "Starting Town"}
    display_header()
    print("Welcome to the Dungeon Master RPG!\n")
    
    while True:
        display_main_menu()
        try:
            choice = input("\nChoose an action (1-7): ")
            
            if choice == '7':
                print("\nThank you for playing!")
                break
            
            if not game.current_player:
                print("Please create a character first!")
                continue
            
            if choice == '1':
                destination = input("\nEnter destination: ")
                output = game.process_input(f"go to {destination}", context)
                print(f"\n{output}")
            elif choice == '2':
                display_inventory(game.current_player)
            elif choice == '3':
                item_name = input("\nEnter item to equip: ")
                output = game.process_input(f"equip {item_name}", context)
                print(f"\n{output}")
            elif choice == '4':
                display_character_info(game.current_player)
            elif choice == '5':
                output = game.process_input("look around", context)
                print(f"\n{output}")
            elif choice == '6':
                npc_name = input("\nEnter NPC name to talk to: ")
                output = game.process_input(f"talk to {npc_name}", context)
                print(f"\n{output}")
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
