import threading
from http.server import HTTPServer
import json
import logging
import pygame
import uuid
import random
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Tuple
from GameRequestHandler import GameRequestHandler 
from GameConfig import GameConfig


class Player(IntEnum):
    EMPTY = 0
    RED = 1
    YELLOW = 2


class GameState(IntEnum):
    RUNNING = 0
    RED_WINS = 1
    YELLOW_WINS = 2
    DRAW = 3


@dataclass
class GameMove:
    player: Player
    column: int
    row: int
    turn: int


class ConnectFour:
    def __init__(self):
        pygame.init()
        GameConfig.load()
        
        # Initialize pygame components
        self.screen = pygame.display.set_mode((GameConfig.width, GameConfig.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(GameConfig.font, GameConfig.font_size)
        pygame.display.set_caption('Four wins - VLM edition')
        
        # Game state
        self.game_id = ""
        self.current_player = Player.RED
        self.turn = 1
        self.state = GameState.RUNNING
        self.board = [[Player.EMPTY for _ in range(GameConfig.num_columns)] 
                     for _ in range(GameConfig.num_rows)]
        self.move_history: List[GameMove] = []
        
        # Visual properties
        self.radius = (self.screen.get_height() - 3 * GameConfig.border_size) / (GameConfig.num_rows + 1) / 2
        self.space = self.radius / 8
        
        self.new_game()

    def new_game(self) -> str:
        """Initialize a new game and return the game ID."""
        self.game_id = str(uuid.uuid4())
        self.current_player = Player.RED
        self.turn = 1
        self.state = GameState.RUNNING
        self.move_history.clear()
        
        # Clear board
        for row in range(GameConfig.num_rows):
            for col in range(GameConfig.num_columns):
                self.board[row][col] = Player.EMPTY
                
        logging.info(f"New game started with ID: {self.game_id}")
        return self.game_id

    def _get_display_color(self, player: Player) -> tuple:
        """Get the display color for a player."""
        color_map = {
            Player.EMPTY: GameConfig.empty_color,
            Player.RED: GameConfig.red_color,
            Player.YELLOW: GameConfig.yellow_color
        }
        return color_map.get(player, GameConfig.empty_color)

    def _column_to_letter(self, column: int) -> str:
        """Convert column index to letter (0->A, 1->B, etc.)."""
        return chr(column + 65)

    def _letter_to_column(self, letter: str) -> int:
        """Convert letter to column index (A->0, B->1, etc.)."""
        return ord(letter.upper()) - 65

    def render_text(self, text: str, pos_x: int, pos_y: int):
        """Render text at specified position."""
        rendered_text = self.font.render(text, True, GameConfig.text_color, GameConfig.bg_color)
        text_rect = rendered_text.get_rect(center=(pos_x, pos_y))
        self.screen.blit(rendered_text, text_rect)

    def render_environment(self):
        """Render the game board background and labels."""
        self.screen.fill("black")
        
        # Draw main game area
        border = GameConfig.border_size
        rect = pygame.Rect(border, border, 
                          GameConfig.width - 2*border, 
                          GameConfig.height - 2*border)
        pygame.draw.rect(self.screen, GameConfig.bg_color, rect)

        # Draw empty circles for board positions
        for col in range(1, GameConfig.num_columns + 1):
            for row in range(1, GameConfig.num_rows + 1):
                x = col * 2 * (self.radius + self.space) - border
                y = row * 2 * (self.radius + self.space) - border
                pygame.draw.circle(self.screen, Player.EMPTY, (x, y), self.radius)

        # Draw row labels
        for i in range(GameConfig.num_rows):
            text = str(GameConfig.num_rows - i)
            y = 10 + 2*border + GameConfig.font_size + i*2*(self.radius + self.space)
            self.render_text(text, GameConfig.font_size//2, y)

        # Draw column labels
        for i in range(GameConfig.num_columns):
            text = self._column_to_letter(i)
            x = (i+1) * 2 * (self.radius + self.space) - 4*self.space
            y = self.screen.get_height() - border
            self.render_text(text, x, y)

    def draw_stone(self, player: Player, column: int, row: int):
        """Draw a stone at the specified board position."""
        x = (column + 1) * 2 * (self.radius + self.space) - GameConfig.border_size
        y = (GameConfig.num_rows - row) * 2 * (self.radius + self.space) - GameConfig.border_size
        color = self._get_display_color(player)
        pygame.draw.circle(self.screen, color, (x, y), self.radius)

    def render_stones(self):
        """Render all stones on the board."""
        for row in range(GameConfig.num_rows):
            for col in range(GameConfig.num_columns):
                self.draw_stone(self.board[row][col], col, row)

    def is_valid_move(self, column: int) -> bool:
        """Check if a move in the given column is valid."""
        return (0 <= column < GameConfig.num_columns and 
                self.board[GameConfig.num_rows - 1][column] == Player.EMPTY and
                self.state == GameState.RUNNING)

    def get_next_row(self, column: int) -> int:
        """Get the next available row in a column."""
        for row in range(GameConfig.num_rows):
            if self.board[row][column] == Player.EMPTY:
                return row
        return -1

    def add_stone(self, column: int) -> str:
        """Add a stone to the specified column (1-indexed)."""
        column_idx = column - 1  # Convert to 0-indexed
        
        if not self.is_valid_move(column_idx):
            return "Invalid move"
        
        row = self.get_next_row(column_idx)
        if row == -1:
            return "Column full"
            
        # Place the stone
        self.board[row][column_idx] = self.current_player
        move = GameMove(self.current_player, column_idx, row, self.turn)
        self.move_history.append(move)
        
        # Record move and check for win
        self._record_move(move)
        self._check_game_over()
        
        # Switch players
        self.current_player = Player.YELLOW if self.current_player == Player.RED else Player.RED
        self.turn += 1
        
        # AI move if it's yellow's turn and game is still running
        if self.current_player == Player.YELLOW and self.state == GameState.RUNNING:
            self._make_ai_move(move)
            
        return f"{{'url': '{GameConfig.base_url}/screens/{self.game_id}_turn{self.turn-1}.png'}}"

    def _make_ai_move(self, last_move: GameMove):
        """Make an AI move using simple strategy."""
        # Try to block winning moves first
        blocking_col = self._find_blocking_move(last_move)
        if blocking_col != -1:
            logging.info(f"AI blocking at column {blocking_col + 1}")
            self.add_stone(blocking_col + 1)
        else:
            # Random move
            valid_columns = [col for col in range(GameConfig.num_columns) 
                           if self.is_valid_move(col)]
            if valid_columns:
                column = random.choice(valid_columns)
                logging.info(f"AI random move at column {column + 1}")
                self.add_stone(column + 1)

    def _find_blocking_move(self, last_move: GameMove) -> int:
        """Find a column to block the opponent's winning move."""
        # Check for three in a row/column/diagonal that need blocking
        threats = [
            self._check_row_threat(last_move),
            self._check_column_threat(last_move),
            self._check_diagonal_threat(last_move)
        ]
        
        for threat in threats:
            if threat != -1:
                return threat
        return -1

    def _check_row_threat(self, last_move: GameMove) -> int:
        """Check for horizontal threats and return blocking column."""
        row, col = last_move.row, last_move.column
        player = last_move.player
        
        # Count consecutive stones in both directions
        count = 1
        left_end = col
        right_end = col
        
        # Count left
        for c in range(col - 1, -1, -1):
            if self.board[row][c] == player:
                count += 1
                left_end = c
            else:
                break
                
        # Count right  
        for c in range(col + 1, GameConfig.num_columns):
            if self.board[row][c] == player:
                count += 1
                right_end = c
            else:
                break
                
        # Check if we can block
        if count >= 3:
            # Check left side
            if left_end > 0 and self.board[row][left_end - 1] == Player.EMPTY:
                if row == 0 or self.board[row - 1][left_end - 1] != Player.EMPTY:
                    return left_end - 1
            # Check right side
            if right_end < GameConfig.num_columns - 1 and self.board[row][right_end + 1] == Player.EMPTY:
                if row == 0 or self.board[row - 1][right_end + 1] != Player.EMPTY:
                    return right_end + 1
        return -1

    def _check_column_threat(self, last_move: GameMove) -> int:
        """Check for vertical threats and return blocking column."""
        row, col = last_move.row, last_move.column
        player = last_move.player
        
        # Count consecutive stones going down
        count = 1
        for r in range(row - 1, -1, -1):
            if self.board[r][col] == player:
                count += 1
            else:
                break
                
        # If 3 in a column, block above
        if count >= 3 and row + 1 < GameConfig.num_rows:
            if self.board[row + 1][col] == Player.EMPTY:
                return col
        return -1

    def _check_diagonal_threat(self, last_move: GameMove) -> int:
        """Check for diagonal threats and return blocking column."""
        # Simplified diagonal check - can be expanded
        return -1

    def _record_move(self, move: GameMove):
        """Record move to file and capture screenshot."""
        self._capture_screenshot()
        
        game_result = self._get_game_status_string()
        player_name = "red" if move.player == Player.RED else "yellow"
        move_notation = f"{self._column_to_letter(move.column)}{move.row + 1}"
        screenshot_url = f"{GameConfig.base_url}/screens/{self.game_id}_turn{move.turn}.png"
        
        result_file = f"./screens/{self.game_id}.jsonl"
        with open(result_file, "a", encoding="utf-8") as f:
            json_data = {
                "game_id": self.game_id,
                "turn": move.turn,
                "player": player_name,
                "move": move_notation,
                "url": screenshot_url,
                "status": game_result
            }
            f.write(json.dumps(json_data) + "\n")
            
        logging.info(f"Turn {move.turn}: {player_name} -> {move_notation}")

    def _capture_screenshot(self):
        """Capture and save screenshot of current game state."""
        self.render_stones()
        filename = f"./screens/{self.game_id}_turn{self.turn}.png"
        pygame.image.save(self.screen, filename)

    def _get_game_status_string(self) -> str:
        """Get string representation of current game state."""
        status_map = {
            GameState.RUNNING: "running",
            GameState.RED_WINS: "red wins",
            GameState.YELLOW_WINS: "yellow wins",
            GameState.DRAW: "draw"
        }
        return status_map.get(self.state, "unknown")

    def _check_game_over(self):
        """Check if the game is over and update state."""
        winner = self._check_winner()
        if winner != Player.EMPTY:
            self.state = GameState.RED_WINS if winner == Player.RED else GameState.YELLOW_WINS
            logging.info(f"Game over: {self._get_game_status_string()}")
        elif self._is_board_full():
            self.state = GameState.DRAW
            logging.info("Game over: draw")

    def _check_winner(self) -> Player:
        """Check if there's a winner and return the winning player."""
        # Check all possible winning combinations
        for row in range(GameConfig.num_rows):
            for col in range(GameConfig.num_columns):
                player = self.board[row][col]
                if player == Player.EMPTY:
                    continue
                    
                # Check all directions from this position
                directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # right, down, diagonal-right, diagonal-left
                for dr, dc in directions:
                    if self._check_line(row, col, dr, dc, player):
                        return player
        return Player.EMPTY

    def _check_line(self, start_row: int, start_col: int, dr: int, dc: int, player: Player) -> bool:
        """Check if there are 4 consecutive stones in a line."""
        count = 0
        for i in range(4):
            r, c = start_row + i * dr, start_col + i * dc
            if (0 <= r < GameConfig.num_rows and 0 <= c < GameConfig.num_columns and 
                self.board[r][c] == player):
                count += 1
            else:
                break
        return count == 4

    def _is_board_full(self) -> bool:
        """Check if the board is full."""
        return all(self.board[GameConfig.num_rows - 1][col] != Player.EMPTY 
                  for col in range(GameConfig.num_columns))

    def process_http_move(self, coordinates: str) -> str:
        """Process a move received via HTTP."""
        if not coordinates:
            return "No coordinates provided"
            
        try:
            column = self._letter_to_column(coordinates[0])
            if 0 <= column < GameConfig.num_columns:
                return self.add_stone(column + 1)  # Convert to 1-indexed
            else:
                return "Invalid column"
        except (IndexError, ValueError):
            return "Invalid move format"

    def handle_keyboard_input(self):
        """Handle keyboard input for local play."""
        keys = pygame.key.get_pressed()
        key_mappings = {
            (pygame.K_1, pygame.K_a): 1,
            (pygame.K_2, pygame.K_b): 2,
            (pygame.K_3, pygame.K_c): 3,
            (pygame.K_4, pygame.K_d): 4,
            (pygame.K_5, pygame.K_e): 5,
            (pygame.K_6, pygame.K_f): 6,
            (pygame.K_7, pygame.K_g): 7,
        }
        
        for key_combo, column in key_mappings.items():
            if any(keys[key] for key in key_combo):
                if self.is_valid_move(column - 1):  # Convert to 0-indexed for validation
                    self.add_stone(column)
                break

    def run(self):
        """Main game loop."""
        self.render_environment()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.render_stones()
            self.handle_keyboard_input()
            
            pygame.display.flip()
            self.dt = self.clock.tick(10) / 1000

        pygame.quit()


def start_http_server(game_instance, port: int = 8000):
    """Start HTTP server for remote game access."""
    GameRequestHandler.game_instance = game_instance
    server = HTTPServer(('localhost', port), GameRequestHandler)
    logging.info(f"Starting HTTP server on port {port}")
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        filename='four-wins.log', 
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create game instance
    game = ConnectFour()
    
    # Start HTTP server
    http_server = start_http_server(game, 8000)
    
    # Run the game
    game.run()