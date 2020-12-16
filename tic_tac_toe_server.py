#! /usr/bin/python3

# Import the socket module
import socket
# Import multi-threading module
import threading
# Import the time module
import time
# Import command line arguments
from sys import argv
import pickle


class TTTServer:
    """TTTServer deals with networking and communication with the TTTClient."""

    def __init__(self):
        """Initializes the server object with a server socket."""
        # Create a TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def bind(self, port_number):
        """Binds the server with the designated port and start listening to
        the binded address."""
        while True:
            try:
                # Bind to an address with the designated port
                # The empty string "" is a symbolic name
                # meaning all available interfaces
                self.server_socket.bind(("", int(port_number)))
                print("Reserved port " + str(port_number))
                # Start listening to the binded address
                self.server_socket.listen(1)
                print("Listening to port " + str(port_number))
                # Break the while loop if no error is caught
                break
            except:
                # Caught an error
                print("There is an error when trying to bind " + str(port_number))
                # Ask the user what to do with the error
                choice = input("[A]bort, [C]hange port, or [R]etry?")
                if choice.lower() == "a":
                    exit()
                elif choice.lower() == "c":
                    port_number = input("Please enter the port: ")

    def close(self):
        """Close the socket"""
        self.server_socket.close()


class TTTServerGame(TTTServer):
    """TTTServerGame deals with the game logic on the server side."""

    def __init__(self):
        """Initializes the server game object."""
        TTTServer.__init__(self)

    def start(self):
        """Starts the server and let it accept clients."""
        # Use a simple lock to synchronize access when matching players
        self.lock_matching = threading.Lock()
        # Start the main loop
        self.__main_loop()

    def __main_loop(self):
        """(Private) The main loop."""
        # Loop to infinitely accept new clients
        while True:
            # Accept a connection from a client
            print("Waiting for new client...")
            connection, client_address = self.server_socket.accept()
            print("Received connection from " + str(client_address))

            # 4096 can be any number, it's just a buffer
            # Receive the player name and decode it
            player_name = connection.recv(4096).decode()
            print("We received a player name. It is:", player_name)

            # It's important we append the name first, then create the player so that it has correct ID number...
            player_names_list.append(player_name)

            # Initialize a new Player object to store all the client's information, including name
            new_player = Player(connection, player_name)
            player_list.append(new_player)

            try:
                # Start a new thread to deal with this client
                threading.Thread(target=self.__client_thread, args=(new_player,)).start()
            except:
                print("Failed to create thread.")

    def send_lobby(self, player):
        """Send updated Lobby to client"""
        data = pickle.dumps(game_list)
        player.connection.send(data)

    def send_stats(self, player):
        """Send game stats to the client"""
        print("Sending stats...")
        stats = ""
        for p in player_list:
            stats += str(p.player_name) + " has won " + str(p.gamesWon) + " games and lost " + str(
                p.gamesLost) + " games\n"
        player.send(stats)

    def process_lobby_input(self, player, lobby_input):
        """Processes lobby input from the client"""
        global chatHistory
        if lobby_input == 'c':
            # Check for empty chat history
            if len(chatHistory) == 0:
                player.send(" ")
            else:
                player.send(chatHistory)
        if lobby_input[0] == '>':
            chatHistory += (player.player_name + ": " + lobby_input[1:] + "\n")
            print("chat: " + lobby_input[1:])
        if lobby_input == 'n':
            # Create a new game with this client as player 1
            self.create_game(player)

        elif lobby_input == 's':
            self.send_stats(player)

        if lobby_input.isnumeric():
            # Client wants to join an existing game
            try:
                gameFound = False
                for game in game_list:
                    if game.GameID != int(lobby_input):
                        continue
                    if game.Player2 == 'Waiting for player':
                        player.send("1")
                        gameFound = True
                        self.join_game(player, game)
                        player.is_waiting = True
                        player.match.is_waiting = True
                    else:
                        player.send("-1")
                if (not gameFound):
                    player.send("-2")
            except:
                print("Client could not join game!")

        if lobby_input == 'r':
            self.send_lobby(player)
        return

    def create_game(self, player):
        """Create a game with the other player"""
        global game_count
        # Create a new game with this client as player 1
        print(str(player.player_name) + " just created a new game. Waiting for other player...")
        game_count += 1
        game1 = gameDetails()
        game1.GameID = game_count
        game1.Player1 = player.player_name
        game1.Player1ID = player.id
        player.is_waiting = False

        game_list.append(game1)

        # Start Game
        while True:
            if player.is_waiting:
                game_list.remove(game1)
                return
            else:
                time.sleep(1)

    def join_game(self, player2, gameDet):
        """Client wants join and existing game"""
        print("Other player is joining game...")
        try:
            gameDet.Player2 = player2.player_name
            gameDet.Player2ID = player2.id
            player1 = getPlayer(gameDet.Player1ID)
            game = Game(getPlayer(gameDet.Player1ID), player2)
            player1.role = "X"
            player2.role = "O"
            game.start()
        except:
            print("Player was unable to join game...")

    def __client_thread(self, player):
        """(Private) This is the client thread."""
        # Wrap the whole client thread with a try and catch so that the
        # server would not be affected even if a client messes up
        try:
            self.send_lobby(player)
            while player.is_waiting:
                print("Waiting for input from: " + player.player_name)
                incomingMessage = player.recvmessage()
                print(player.player_name + " input:" + incomingMessage)
                # "E" means the client wants to exit, close the thread
                if incomingMessage == "e":
                    # Client wants to Exit
                    print("Player " + str(player.id) + " is exiting the game")
                    player_names_list.remove(player.player_name)
                    player_list.remove(player)

                    # Kill the thread
                    player.close_thread()
                else:
                    self.process_lobby_input(player, incomingMessage)
        except:
            print("Player " + str(player.id) + " disconnected")


class Player:
    """Player class describes a client with connection to the server and
    as a player in the tic tac toe game."""

    def __init__(self, connection, player_name):
        """Initialize a player with its connection to the server"""
        # Generate a unique id for this player
        self.id = len(player_list)
        # Assign the corresponding connection
        self.connection = connection
        # Assign a name to the player
        self.player_name = player_name
        # Set the player waiting status to True
        self.is_waiting = True
        self.match = None
        self.gamesWon = 0
        self.gamesLost = 0
        print("Creating player name: " + str(player_name))
        print("With ID number: " + str(self.id))

    def send(self, msg):
        """Sends a message to the client"""
        try:
            self.connection.send(msg.encode())
        except:
            # If any error occurred, the connection might be lost
            self.__connection_lost()

    def recvmessage(self):
        """Receives messages from the client"""
        try:
            return self.connection.recv(4096).decode()
        except:
            self.__connection_lost()

    def recv(self, size, expected_type):
        """Receives a packet with specified size from the client and check
        its integrity by comparing its command type token with the expected
        one."""
        try:
            msg = self.connection.recv(size).decode()
            # If received a quit signal from the client
            if msg[0] == "q":
                # Print why the quit signal
                print(msg[1:])
                # Connection lost
                self.__connection_lost()
            # If the message is not the expected type
            elif msg[0] != expected_type:
                # Connection lost
                self.__connection_lost()
            # If received an integer from the client
            elif msg[0] == "i":
                # Return the integer
                return int(msg[1:])
            # In other case
            else:
                # Return the message
                return msg[1:]
            # Simply return the raw message if anything unexpected happended
            # because it shouldn't matter any more
            return msg
        except:
            print("The message check failed, client probably disconnected...")
            # If any error occurred, the connection might be lost
            self.__connection_lost()
        return None

    def close_thread(self):
        """Closes the client thread"""
        try:
            self.send("Q" + "The other player has lost connection" +
                      " with the server.\nGame over.")
        except:
            print("Thread closing...")
            pass
        # Raise an error so that the client thread can finish
        raise Exception

    def send_match_info(self, opponentID):
        """Sends a the matched information to the client, which includes
        the assigned role and the matched player."""
        # Send to client the opponent id
        self.send("A" + str(opponentID))
        # Waiting for client to confirm
        if self.recv(2, "c") != "1":
            self.__connection_lost()
        # Send to client the assigned role
        self.send("R" + self.role)
        # Waiting for client to confirm
        if self.recv(2, "c") != "2":
            self.__connection_lost()
        # Sent to client the matched player's ID
        self.send("I" + str(self.match.id))
        # Waiting for client to confirm
        if self.recv(2, "c") != "3":
            self.__connection_lost()

    def __connection_lost(self):
        """(Private) This function will be called when the connection is lost."""
        # This player has lost connection with the server
        print("Player " + str(self.id) + " connection lost.")
        # Tell the other player that the game is finished
        try:
            self.match.send("Q" + "The other player has lost connection" +
                            " with the server.\nGame over.")
        except:
            print("Connection lost!")
            pass
        # Raise an error so that the client thread can finish
        raise Exception


def getPlayer(playerID):
    """Returns the player with their corresponding ID"""
    for player in player_list:
        if player.id == playerID:
            return player
    return None


class Game:
    """Game class describes a game with two different players."""

    def __init__(self, player1, player2):
        """Initializes the game class"""
        player1.is_waiting = False
        player2.is_waiting = False
        self.player1 = player1
        self.player2 = player2
        self.board_content = list("         ")

    def start(self):
        """Starts the game."""
        # Send both players the match info
        print("Starting game...")
        self.player1.match = self.player2
        self.player2.match = self.player1
        self.player1.send_match_info(self.player2.id)
        self.player2.send_match_info(self.player1.id)

        # Print the match info onto screen
        print("Player " + str(self.player1.id) + " is matched with Player " + str(self.player2.id))

        while True:
            # Player 1 move
            if self.move(self.player1, self.player2):
                return
            # Player 2 move
            if self.move(self.player2, self.player1):
                return

    def move(self, moving_player, waiting_player):
        """Lets a player make a move."""
        # Send both players the current board content
        moving_player.send("B" + ("".join(self.board_content)))
        waiting_player.send("B" + ("".join(self.board_content)))
        # Let the moving player move, Y stands for yes it's turn to move,
        # and N stands for no and waiting
        moving_player.send("C" + "Y")
        waiting_player.send("C" + "N")
        # Receive the move from the moving player
        move = int(moving_player.recv(2, "i"))
        # Send the move to the waiting player
        waiting_player.send("I" + str(move))
        # Check if the position is empty
        if self.board_content[move - 1] == " ":
            # Write the it into the board
            self.board_content[move - 1] = moving_player.role
        else:
            print("Player " + str(moving_player.id) +
                  " is attempting to take a position that's already " +
                  "been taken.")

        # Check if this will result in a win
        result, winning_path = self.check_winner(moving_player)
        if result >= 0:
            # If there is a result
            # Send back the latest board content
            moving_player.send("B" + ("".join(self.board_content)))
            waiting_player.send("B" + ("".join(self.board_content)))

            if result == 0:
                # If this game ends with a draw
                # Send the players the result
                moving_player.send("C" + "D")
                waiting_player.send("C" + "D")
                print("Game between player " + str(self.player1.id) + " and player "
                      + str(self.player2.id) + " ends with a draw.")
                return True
            if result == 1:
                # If this player wins the game
                # Send the players the result
                moving_player.send("C" + "W")
                waiting_player.send("C" + "L")
                moving_player.gamesWon += 1
                waiting_player.gamesLost += 1
                # Send the players the winning path
                moving_player.send("P" + winning_path)
                waiting_player.send("P" + winning_path)
                print("Player " + str(self.player1.id) + " beats player "
                      + str(self.player2.id) + " and finishes the game.")
                return True
            return False

    def check_winner(self, player):
        """Checks if the player wins the game. Returns 1 if wins,
        0 if it's a draw, -1 if there's no result yet."""
        s = self.board_content

        # Check columns
        if len({s[0], s[1], s[2], player.role}) == 1:
            return 1, "012"
        if len({s[3], s[4], s[5], player.role}) == 1:
            return 1, "345"
        if len({s[6], s[7], s[8], player.role}) == 1:
            return 1, "678"

        # Check rows
        if len({s[0], s[3], s[6], player.role}) == 1:
            return 1, "036"
        if len({s[1], s[4], s[7], player.role}) == 1:
            return 1, "147"
        if len({s[2], s[5], s[8], player.role}) == 1:
            return 1, "258"

        # Check diagonal
        if len({s[0], s[4], s[8], player.role}) == 1:
            return 1, "048"
        if len({s[2], s[4], s[6], player.role}) == 1:
            return 1, "246"

        # If there's no empty position left, draw
        if " " not in s:
            return 0, ""

        # The result cannot be determined yet
        return -1, ""


class gameDetails:
    """Stores the game details for players and their ID's"""
    def __init__(self):
        self.GameID = 0
        self.Player1 = 'Waiting for player'
        self.Player2 = 'Waiting for player'
        self.Player1ID = 0
        self.Player2ID = 1

    def __str__(self):
        return str(self.GameID) + ', ' + self.Player1 + ', ' + self.Player2

    def __repr__(self):
        return str(self)


# Define the main program
def main():
    """The start of the server program"""
    global player_names_list
    global player_list
    global game_list
    global game_count
    global chatHistory

    player_names_list = []
    player_list = []
    game_list = []
    game_count = 0
    chatHistory = ""

    # If there are more than 2 arguments
    if len(argv) >= 2:
        # Set port number to argument 1
        port_number = argv[1]
    else:
        # Ask the user to input port number
        port_number = input("Please enter the port: ")

    # Initialize the server object
    server = TTTServerGame()

    # Bind the server with the port
    server.bind(port_number)

    # Start the server
    server.start()

    # Close the server
    server.close()


if __name__ == "__main__":
    # If this script is running as a standalone program,
    # start the main program.
    main()
