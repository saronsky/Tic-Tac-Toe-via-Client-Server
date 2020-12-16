#! /usr/bin/python3

# Import the socket module
import socket
# Import command line arguments
from sys import argv
import sys
import os
import pickle
import time

clearScreen = lambda: os.system('cls')


class TTTClient:
    """TTTClient deals with networking and communication with the TTTServer."""

    def __init__(self):
        """Initializes the client and create a client socket."""
        # Create a TCP/IP socket
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, address, port_number):
        """Keeps repeating connecting to the server and returns True if
        connected successfully."""
        while True:
            try:
                print("Connecting to the game server...")
                # Connection time out 10 seconds
                self.client_socket.settimeout(1000)
                # Connect to the specified host and port
                self.client_socket.connect((address, int(port_number)))
                # Return True if connected successfully
                print("Connected!")
                return True
            except:
                # Caught an error
                print("There is an error when trying to connect to " +
                      str(address) + "::" + str(port_number) + "\n ", sys.exc_info())
                self.__connect_failed__()

    def __connect_failed__(self):
        """(Private) This function will be called when the attempt to connect
        failed."""
        # Ask the user what to do with the error
        choice = input("[A]bort, [C]hange address and port, or [R]etry?")
        if choice.lower() == "a":
            exit()
        elif choice.lower() == "c":
            address = input("Please enter the address: ")
            port_number = input("Please enter the port: ")

    def s_sendCommand(self, command_type, msg):
        """Sends a message to the server with an agreed command type token
        to ensure the message is delivered safely."""
        # A 1 byte command_type character is put at the front of the message
        # as a communication convention
        try:
            self.client_socket.send((command_type + msg).encode())
        except:
            # If any error occurred, the connection might be lost
            self.__connection_lost()

    def s_send(self, msg):
        try:
            self.client_socket.send(msg.encode())
        except:
            # If any error occurred, the connection might be lost
            self.__connection_lost()

    def s_recvCommand(self, size, expected_type):
        """Receives a packet with specified size from the server and check
        its integrity by comparing its command type token with the expected
        one."""
        try:
            msg = self.client_socket.recv(size).decode()
            # If received a quit signal from the server
            if msg[0] == "Q":
                why_quit = ""
                try:
                    # Try receiving the whole reason why quit
                    why_quit = self.client_socket.recv(1024).decode()
                except:
                    pass
                # Print the reason
                print(msg[1:] + why_quit)
                # Throw an error
                raise Exception
            # If received an echo signal from the server
            elif msg[0] == "E":
                # Echo the message back to the server
                self.s_sendCommand("e", msg[1:])
                # Recursively retrieve the desired message
                return self.s_recvCommand(size, expected_type)
            # If the command type token is not the expected type
            elif msg[0] != expected_type:
                print("The received command type \"" + msg[0] + "\" does not " +
                      "match the expected type \"" + expected_type + "\".")
                # Connection lost
                self.__connection_lost()
            # If received an integer from the server
            elif msg[0] == "I":
                # Return the integer
                return int(msg[1:])
            # In other case
            else:
                # Return the message
                return msg[1:]
            # Simply return the raw message if anything unexpected happened
            # because it shouldn't matter any more
            return msg
        except:
            # If any error occurred, the connection might be lost
            self.__connection_lost()
        return None

    def s_recv(self, size):
        """Receives a packet with specified size from the server and check
        its integrity by comparing its command type token with the expected
        one."""
        try:
            msg = self.client_socket.recv(size).decode()
            return msg
        except:
            # If any error occurred, the connection might be lost
            self.__connection_lost()

    def s_recvBoard(self):
        """Receive the list of names from the server"""
        try:
            return pickle.loads(self.client_socket.recv(4096))
        except:
            self.__connection_lost()
            return None

    def __connection_lost(self):
        """(Private) This function will be called when the connection is lost."""
        print("Error: connection lost.")
        try:
            # Try and send a message back to the server to notify connection lost
            self.client_socket.send("q".encode())
        except:
            pass
        # Raise an error to finish
        raise Exception

    def close(self):
        """Shut down the socket and close it"""
        # Shut down the socket to prevent further sends/receives
        self.client_socket.shutdown(socket.SHUT_RDWR)
        # Close the socket
        self.client_socket.close()


class TTTClientGame(TTTClient):
    """TTTClientGame deals with the game logic on the client side."""

    def __init__(self):
        """Initializes the client game object."""
        TTTClient.__init__(self)

    def start_game(self):
        """Starts the game and gets basic game information from the server."""
        print("Waiting for second player...")
        # Receive the player's ID from the server
        self.player_id = int(self.s_recvCommand(128, "A"))
        # Confirm the ID has been received
        self.s_sendCommand("c", "1")

        # Tell the user that connection has been established
        self.__connected__()

        # Receive the assigned role from the server
        self.role = str(self.s_recvCommand(2, "R"))
        # Confirm the assigned role has been received
        self.s_sendCommand("c", "2")

        # Receive the mactched player's ID from the server
        self.match_id = int(self.s_recvCommand(128, "I"))
        # Confirm the mactched player's ID has been received
        self.s_sendCommand("c", "3")

        print(("You are now matched against player " + str(self.match_id)
               + "\nYou are the symbol \"" + self.role + "\""))
        time.sleep(3)
        # Start the main loop
        self.__main_loop()

    def __connected__(self):
        """(Private) This function is called when the client is successfully
        connected to the server."""
        # Welcome the user
        clearScreen()
        print("Welcome to Tic Tac Toe online, player " + str(self.player_id))

    def __main_loop(self):
        """The main game loop."""
        while True:
            # Get the board content from the server
            board_content = self.s_recvCommand(10, "B")
            # Get the command from the server
            command = self.s_recvCommand(2, "C")
            # Update the board
            self.__update_board__(command, board_content)

            if command == "Y":
                # If it's this player's turn to move
                self.__player_move__(board_content)
            elif command == "N":
                # If the player needs to just wait
                self.__player_wait__()
                # Get the move the other player made from the server
                move = self.s_recvCommand(2, "I")
                self.__opponent_move_made__(move)
            elif command == "D":
                # If the result is a draw
                print("It's a draw.")
                break
            elif command == "W":
                # If this player wins
                print("You WIN!")
                # Draw winning path
                self.__draw_winning_path__(self.s_recvCommand(4, "P"))
                time.sleep(3)
                # Break the loop and finish
                break
            elif command == "L":
                # If this player loses
                print("You lose.")
                # Draw winning path
                self.__draw_winning_path__(self.s_recvCommand(4, "P"))
                time.sleep(3)
                # Break the loop and finish
                break
            else:
                # If the server sends back anything unrecognizable
                # Simply print it
                print("Error: unknown message was sent from the server")
                # And finish
                break
        # Display the updated lobby after the game finishes
        self.updateLobby()
        self.displayLobby()

    def __update_board__(self, command, board_string):
        """(Private) Updates the board."""
        clearScreen()
        if command == "Y":
            # If it's this player's turn to move, print out the current
            # board with " " converted to the corresponding position number
            print("Current board: \n" + self.format_board(
                self.show_board_pos(board_string)))
            print("Your symbol: " + str(self.role))
        else:
            # Print out the current board
            print("Current board:\n" + self.format_board(board_string))
            print("Your symbol: " + str(self.role))

    def __player_move__(self, board_string):
        """(Private) Lets the user input the move and sends it back to the
        server."""
        while True:
            # Prompt the user to enter a position
            try:
                position = int(input('Please enter the position (1~9):'))
            except:
                print("Invalid input.")
                continue

            # Ensure user-input data is valid
            if 1 <= position <= 9:
                # If the position is between 1 and 9
                if board_string[position - 1] != " ":
                    # If the position is already been taken,
                    # Print out a warning
                    print("That position has already been taken." +
                          "Please choose another one.")
                else:
                    # If the user input is valid, break the loop
                    break
            else:
                print("Please enter a value between 1 and 9 that" +
                      "corresponds to the position on the grid board.")
        # Loop until the user enters a valid value

        # Send the position back to the server
        self.s_sendCommand("i", str(position))

    def __player_wait__(self):
        """(Private) Lets the user know it's waiting for the other player to
        make a move."""
        print("Waiting for the other player to make a move...")

    def __opponent_move_made__(self, move):
        """(Private) Shows the user the move that the other player has taken."""
        print("Your opponent took up number " + str(move))

    def __draw_winning_path__(self, winning_path):
        """(Private) Shows to the user the path that has caused the game to win or lose."""
        # Generate a new human readable path string
        readable_path = ""
        for c in winning_path:
            readable_path += str(int(c) + 1) + ", "

        print("The path is: " + readable_path[:-2])

    def show_board_pos(self, s):
        """(Static) Converts the empty positions " " (a space) in the board
        string to its corresponding position index number."""

        new_s = list("123456789")
        for i in range(0, 9):
            if (s[i] != " "):
                new_s[i] = s[i]
        return "".join(new_s)

    def format_board(self, s):
        """(Static) Formats the grid board."""

        # If the length of the string is not 9
        if len(s) != 9:
            # Then print out an error message
            print("Error: there should be 9 symbols.")
            # Throw an error
            raise Exception

        # Draw the grid board
        # print("|1|2|3|");
        # print("|4|5|6|");
        # print("|7|8|9|");
        return ("|" + s[0] + "|" + s[1] + "|" + s[2] + "|\n"
                + "|" + s[3] + "|" + s[4] + "|" + s[5] + "|\n"
                + "|" + s[6] + "|" + s[7] + "|" + s[8] + "|\n")

    def displayLobby(self):
        """Displays the lobby to the client"""
        global game_list
        # Clear the screen first, displays new lobby information
        clearScreen()
        lobbyHeader1 = '\n'
        lobbyHeader2 = '              Tic-Tac-Toe Game Lobby           '
        lobbyHeader3 = '\n'
        lobbyHeader4 = 'Game ID        Player 1        Player 2        '
        lobbyHeader5 = '-----------------------------------------------'

        lobbyFooter1 = '-----------------------------------------------'
        lobbyFooter2 = '\n'
        lobbyFooter3 = 'Options:\nType \"N\" to create a new game\nType ' \
                       '\"R\" to refresh the lobby\nType \"S\" to get the scoreboard\nType \"E\" to exit\nType \"C\" to view the chat\nType a Game' \
                       'ID# to join an existing game\nOr send a chat to everyone by starting your message with \">\"'
        lobbyFooter4 = '\n\n'

        # Display updated lobby
        # ----------------------------------------
        print(lobbyHeader1)
        print(lobbyHeader2)
        print(lobbyHeader3)
        print(lobbyHeader4)
        print(lobbyHeader5)

        if len(game_list) == 0:
            print('\nThere are no active games\n')
        else:
            for gameDetails in game_list:
                print(gameDetails)

        print(lobbyFooter1)
        print(lobbyFooter2)
        print(lobbyFooter3)
        print(lobbyFooter4)

    def updateLobby(self):
        """Update the lobby when the client requests it"""
        global game_list
        self.s_sendCommand("r", "")
        game_list = self.s_recvBoard()
        self.displayLobby()


class gameDetails:
    """Handles the game details for the players and their ID's"""

    def __init__(self):
        self.GameID = 0
        self.Player1 = 'Waiting for player'
        self.Player2 = 'Waiting for player'
        self.Player1ID = 0
        self.Player2ID = 1

    def __str__(self):
        # return str(self.GameID) + ', ' + self.Player1 + ', ' + self.Player2
        return str(self.GameID) + '              ' + self.Player1 + '           ' + self.Player2

    def __repr__(self):
        return str(self)


def gameLobby(client):
    """Handles the display of the lobby and taking input from the client"""
    global game_list
    game_list = client.s_recvBoard()
    client.displayLobby()
    while True:
        player_input = input("What do you want to do: ")
        if player_input[0] == '>':
            client.s_send(player_input)
            player_input = 'c'
        player_input = player_input.lower()
        # Check for correct letter input
        if len(player_input) != 1:
            print("You need to type 1 character, try again...")
            continue
        # Type 'C' to view the chat
        elif player_input == 'c':
            client.s_sendCommand("c", "")
            print(client.s_recv(4096))
            while True:
                player_input_for_stats = input("Type \"C\" to continue: ").lower()
                if player_input_for_stats != 'c':
                    print("That's not the correct format...")
                else:
                    break
            client.displayLobby()
        # Type "R" to refresh the lobby
        elif player_input == 'r':
            print("About to receive new player data...")
            client.updateLobby()

        # Type "N" to create a new game
        elif player_input == 'n':
            clearScreen()
            print("Creating new game...")
            client.s_sendCommand("n", "")
            client.start_game()

        # Type "E" to exit
        elif player_input == 'e':
            print("Exiting session...")
            client.s_sendCommand("e", "")
            client.close()
            sys.exit()

        # Player requests stats
        elif player_input == 's':
            print("Requesting stats...")
            client.s_sendCommand("s", "")
            stats = client.s_recv(4096)
            print("Stats:\n" + stats)
            while True:
                player_input_for_stats = input("Type \"C\" to continue: ").lower()
                if player_input_for_stats != 'c':
                    print("That's not the correct format...")
                else:
                    break
            client.displayLobby()

        # Enter a Game ID# to join an existing game
        elif player_input.isnumeric():
            client.client_socket.send(player_input.encode())
            response = client.s_recv(4096)
            if response == str(-1):
                print("Unfortunately that game is already full")
            elif response == str(-2):
                print("Unfortunately a game with that GameID# does not exist")
            else:
                client.start_game()

        else:
            print("Your input is invalid. Please try again...")


# Define the main program
def main():
    """Starts client connection and lobby input"""
    global game_list
    game_list = []

    # If there are more than 3 arguments
    if len(argv) >= 3:
        # Set the address to argument 1, and port number to argument 2
        address = argv[1]
        port_number = argv[2]
    else:
        # Ask the user to input the address and port number
        address = input("Please enter the address: ")
        port_number = input("Please enter the port: ")

    # Prepare the window for client data
    clearScreen()

    print("Welcome to Tic-Tac-Toe! Game created by Network Noggins!")

    # Ask the user to enter their name and check for empty name...
    while True:
        player_name = input("Please enter a username: ")
        if not player_name:
            print("Sorry, you need to type a name, please try again...")
            continue
        else:
            break

    # Initialize the client object
    client = TTTClientGame()
    # Connect to the server
    client.connect(address, port_number)

    try:
        # Encode the player name to the server
        client.client_socket.send(player_name.encode())
    except:
        # If any error occurred, the connection might be lost
        client.__connect_failed__()

    while True:
        gameLobby(client)


if __name__ == "__main__":
    # If this script is running as a standalone program,
    # start the main program.
    main()
