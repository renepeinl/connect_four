import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
from GameRequestHandler import GameRequestHandler 
from GameConfig import GameConfig

import logging
import pygame
import uuid
import random

class ConnectFour:

    '''border_size = 20
    font_size = 32        
    text_color = (255, 255, 150)
    bg_color = (0, 0, 128)
    yellow_color = (255,220,50)
    red_color = (220,0,0)
    empty_color = (220,220,220)'''
    empty = 0
    red = 1
    yellow = 2

    radius = 0
    space = 0

    #num_columns = 7
    #num_rows = 6
    running = True

    game_id  = ""
    reds_turn = True
    turn = 1

    dt = 0
    screen = None
    clock = None
    font = None    
    board = []

    game_result_file = ""
    #base_url = "http://localhost:8000"

        # pygame setup
    def __init__(self):
        pygame.init()
        GameConfig.load()
        self.screen = pygame.display.set_mode((GameConfig.width, GameConfig.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(GameConfig.font, GameConfig.font_size)
        #self.player_pos = pygame.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2)
        pygame.font.init()
        pygame.display.set_caption('Four wins - VLM edition')

        self.radius = (self.screen.get_height()-3*GameConfig.border_size) / (GameConfig.num_rows+1) / 2
        self.space = self.radius / 8
        
        for row in range(0, GameConfig.num_rows):
            new_row = []
            for column in range(0, GameConfig.num_columns):
                new_row.append(self.empty)
            self.board.append(new_row)
        self.new_game()

    def new_game(self):
        self.game_id = str(uuid.uuid4())
        logging.info(" ==========  New game has started ======== ")
        logging.info(f"game-id = {self.game_id}")
        self.game_result_file = f"./screens/{self.game_id}.jsonl"
        reds_turn = True
        turn = 1
        running = True
        for row in range(0, GameConfig.num_rows):
            new_row = []
            for column in range(0, GameConfig.num_columns):
                self.board[row][column] = self.empty
        return self.game_id

    def render_text(self, text, pos_x, pos_y):
        rendered_text = self.font.render(text, True, GameConfig.text_color, GameConfig.bg_color)
        textRect = rendered_text.get_rect()
        textRect.center = (pos_x, pos_y)
        self.screen.blit(rendered_text, textRect)

    def render_environment(self, border, width, height):
        self.screen.fill("black")
        rect = pygame.Rect(border, border, width-2*border, height-2*border)
        pygame.draw.rect(self.screen, GameConfig.bg_color, rect)

        for column in range(1, GameConfig.num_columns+1):
            for y in range(1,GameConfig.num_rows+1):
                pygame.draw.circle(self.screen, self.empty, pygame.Vector2(column*2*(self.radius+self.space)-GameConfig.border_size,  
                                                                            y*2*(self.radius+self.space)-GameConfig.border_size), self.radius)   
        for i in range(0, GameConfig.num_rows):        
            text = "{}".format(GameConfig.num_rows-i)
            self.render_text(text, GameConfig.font_size/2, 10+2*GameConfig.border_size + GameConfig.font_size + i*2*(self.radius+self.space))

        for i in range(0, GameConfig.num_columns+1):        
            text = chr(64 + i)
            self.render_text(text, i*2*(self.radius+self.space)-4*self.space, self.screen.get_height()-GameConfig.border_size)

    def draw_stone(self, color, column, row):
        x = column
        y = GameConfig.num_rows - row + 1
        pygame.draw.circle(self.screen, color, pygame.Vector2(column*2*(self.radius+self.space)-GameConfig.border_size,  
                                                              y*2*(self.radius+self.space)-GameConfig.border_size), self.radius) 

    def render_stones(self):
        for column in range(0, GameConfig.num_columns):
            for row in range(0, GameConfig.num_rows):
                stone_color = self.board[row][column]
                display_color = GameConfig.empty_color
                if stone_color == self.red:
                    display_color = GameConfig.red_color
                elif stone_color == self.yellow:
                    display_color = GameConfig.yellow_color
                self.draw_stone(display_color, column+1,row+1)

    def capture_screenshot(self): # (pygame Surface, tuple, tuple)
        self.render_stones()
        # uncomment the next lines if you want to capture only part of the screen
        #size = (400, 400)
        #pos = (0,0)
        #image = pygame.Surface(size)  # Create image surface
        #image.blit(screen,(0,0),(pos,size))  # Blit portion of the display to the image
        filename = f"./screens/{self.game_id}_turn{self.turn}.png"
        pygame.image.save(self.screen,filename)  # Save the image to the disk

    def allow_random_bot_move(self):
        column = random.randrange(1, 7)
        self.add_stone(column)

    def allow_clever_bot_move(self, last_row, last_column):
        column = -1
        #prevent four in a column
        column = self.prevent_column(last_row,last_column)
        logging.info(f"bot received column: {column} from column check")
        if(column != -1):
            logging.info(f"bot accepted column: {column}")
            self.add_stone(column)
            return
        else: #prevent for across
            column = self.prevent_cross(last_row,last_column)
            logging.info(f"bot received column: {column} from cross check")
            if(column != -1):
                logging.info(f"bot accepted column: {column}")
                self.add_stone(column+1)
                return
            else: #prevent four in a row
                column = self.prevent_row(last_row,last_column)
                logging.info(f"bot received column: {column} from row check")
                if(column != -1):
                    logging.info(f"bot accepted column: {column}")
                    self.add_stone(column)
                    return
        logging.info("random move")
        column = random.randrange(1, GameConfig.num_columns)
        self.add_stone(column)

    def prevent_row(self, last_row, last_column): 
        logging.info(f"prevent row: last row: {last_row}, last column: {last_column}")
        win_color = self.board[last_row][last_column]
        if win_color != self.red:
            logging.warning(f"prevent row: last move not recorded correctly {chr(last_column+65)}{last_row+1}")     
            return -1
        row=last_row
        subsequent_hits = 1
        win_color = self.empty
        for column in range(0, GameConfig.num_columns):       
            current_color = self.empty
            try: 
                current_color=self.board[row][column]
            except:
                logging.info(f"exception at prevent row: {column}{row} = {chr(column+65)}{row+1}")
            logging.info(f"prevent - checking row: {chr(column+65)}{row+1}")
            if (current_color == self.red and current_color == win_color):
                logging.info(f"subsequent stones in a row:  {subsequent_hits+1}")
                subsequent_hits += 1
                if subsequent_hits ==2:
                    try:
                        if self.board[row][column+1] == self.empty \
                                and self.board[row][column-2] == self.empty:
                            if row == 0 or self.board[row-1][column-2] != self.empty:  # don't need to do something, if space below is empty
                                logging.info(f"preventing row from {chr(column-1+65)}{row+1} to {chr(column+65)}{row+1}")
                                return column-1
                    except:
                        logging.info("border at one side detected, nothing to worry about")
                if subsequent_hits == 3:
                    try:
                        logging.info(f"preventing four in a row at {chr(column+65)}{row+1}")
                        if self.board[row][column+1] == self.empty:
                            logging.info(f"next cell at {chr(column+1+65)}{row+1} is empty")
                            return column+2  # must be one addition plus because add_stone is from player perspective, who starts at 1
                        logging.info(f"next cell at {chr(column+1+65)}{row+1} has stone of color {self.board[row][column+1]}")
                    except:
                        logging.info(f"there is no cell after {chr(column+65)}{row+1}")
                    try:
                        logging.info(f"preventing four in a row at {chr(column-3+65)}{row+1}")
                        if self.board[row][column-3] == self.empty:
                            logging.info(f"cell before row at {chr(column-2+65)}{row+1} is empty")
                            return column-2 # must be one addition plus because add_stone is from player perspective, who starts at 1
                        logging.info(f"cell before row at {chr(column-2+65)}{row+1} has stone of color {self.board[row][column-3]}")
                    except:
                        logging.info(f"there is no cell before {chr(column-1+65)}{row+1}")
            elif current_color != self.empty:
                win_color = current_color
                subsequent_hits = 1
        return -1
                
    def prevent_column(self, last_row, last_column):  
        logging.info(f"prevent column called for column {last_column}")
        win_color =self.board[last_row][last_column]
        if win_color != self.red:
            logging.warning(f"last move not recorded correctly {chr(last_column+65)}{last_row+1}")     
            return -1
        column = last_column  
        win_color = self.empty
        subsequent_hits = 1
        for row in range(0, GameConfig.num_rows):
            current_color = self.board[row][column]            
            logging.info(f"prevent - checking column: {chr(column+65)}{row+1} with current color = {current_color} and win color = {win_color}")
            if current_color == self.red:
                if current_color == win_color:
                    logging.info(f"checking column {chr(column+65)}: susequent stones: {subsequent_hits+1}")
                    subsequent_hits += 1
                    if subsequent_hits == 3:
                        logging.info(f"preventing four in a column at {chr(column+65)}{row+1}")
                        if self.board[row][column+1] == self.empty:
                            logging.info(f"next cell at {chr(column+65)}{row+2} is empty")
                            return column+1
                logging.info(f"new win colour is {current_color}")
                win_color = current_color
            elif current_color == self.empty:
                return -1
        return -1
    
    def prevent_cross(self, last_row, last_column):
        logging.info(f"prevent cross called for column {last_column} and row {last_row}")
        row = last_row
        column = last_column
        win_color = self.board[row][column]
        if win_color != self.red:
            logging.warning(f"last move not recorded correctly {chr(column+65)}{row+1}")     
            return -1
        #try right down
        try:
            if self.board[row-1][column+1] == win_color:
                if self.board[row-2][column+2] == win_color:
                    if self.board[row-3][column+3] == self.empty:
                        if self.board[row-2][column+3] != self.empty: # don't add a stone, if the cell below the critical one is not yet filled
                            return column+3
        except:
            logging.info("list index out of bounds during checking right down - check exceeded the board ")
        #try left down
        try:
            if self.board[row-1][column-1] == win_color:
                if self.board[row-2][column-2] == win_color:
                    if self.board[row-3][column-3] == self.empty:
                        if self.board[row-2][column-3] != self.empty: # don't add a stone, if the cell below the critical one is not yet filled
                            return column-3
        except:
            logging.info("list index out of bounds during checking left down - check exceeded the board")        
        #try right down for cell above last move
        try:
            row = last_row +1
            if self.board[row-1][column+1] == self.red:
                if self.board[row-2][column+2] == self.red:
                    if self.board[row-3][column+3] == self.red:
                        if self.board[row][column] == self.empty: # don't add a stone, if the critical cell is already filled
                            return column
        except:
            logging.info("list index out of bounds during checking right down - check exceeded the board")
        #try left down for cell above last move
        try:
            row = last_row +1
            if self.board[row-1][column-1] == self.red:
                if self.board[row-2][column-2] == self.red:
                    if self.board[row-3][column-3] == self.red:
                        if self.board[row][column] == self.empty:  # don't add a stone, if the critical cell is already filled
                            return column
        except:
            logging.info("list index out of bounds during checking left down - check exceeded the board")
        return -1

    def add_stone(self, column):
        column = column-1 #player starts to count at 1, internal index at 0
        for row in range(0,GameConfig.num_rows):
            if (self.board[row][column] == self.empty):
                current_color = self.yellow
                if (self.reds_turn):
                    current_color = self.red
                self.board[row][column] = current_color          
                break
            else:
                row+=1    
        self.write_metadata_result(row, column)
        self.reds_turn = not self.reds_turn
        self.turn += 1
        if(not self.reds_turn and self.running):
            #allow_random_bot_move()
            self.allow_clever_bot_move(row, column) #substract one becaus internally we start counting at 0
        return "{'url': '" + GameConfig.base_url + self.game_result_file[1:] +"'}"

    #writes the current status about the last move to the log, to the result file and determines whether somebody won
    def write_metadata_result(self, row, column):
        self.capture_screenshot()
        screenshot = f"/screens/{self.game_id}_turn{self.turn}.png"
        
        if(self.reds_turn):
            logging.info(f"Turn {self.turn}: red player adds the next stone at {chr(column+65)}{row+1}")
            self.check_game_over()
            game_result = "running" if self.running==True  else "red wins"
            with open(self.game_result_file, "a", encoding="utf-8") as outfile:
                json_line = '{ "game_id": "' + self.game_id + '", "turn": ' + str(self.turn) + \
                            ', "player": "red", "move": "'+chr(column+65) + str(row+1) + \
                            '", "url": "'+GameConfig.base_url + screenshot +'", "status": "'+game_result+'"}\n'
                outfile.write(json_line)
        else:
            logging.info(f"Turn {self.turn}: yellow player adds the next stone at {chr(column+65)}{row+1}")
            self.check_game_over()
            game_result = "running" if self.running==True  else "yellow wins"
            with open(self.game_result_file, "a", encoding="utf-8") as outfile:
                json_line = '{ "game_id": "' + self.game_id + '", "turn": ' + str(self.turn) + \
                             ', "player": "yellow", "move": "'+chr(column+65) + str(row+1) + \
                             '", "url": "'+GameConfig.base_url + screenshot +'", "status": "'+game_result+'"}\n'
                outfile.write(json_line)

    def check_game_over(self):
        #go through all rows to determine whether there are four in a row
        self.check_rows()        
        if self.running:
            #go through all columns to determine whether there are four in a row
            self.check_columns()
        if self.running:
            #go through all diagonals to determine whether there are four across
            self.check_cross()
        
    def check_rows(self):
        for row in range(0, GameConfig.num_rows):
            win_color = self.empty
            subsequent_hits = 1
            for column in range(0, GameConfig.num_columns):        
                current_color = self.board[row][column]
                logging.debug(f"checking row: {chr(column+65)}{row+1}")
                if (current_color != self.empty and current_color == win_color):
                    logging.info(f"subsequent stones: {subsequent_hits+1} in a row at {chr(column+65)}{row+1}")
                    subsequent_hits += 1
                    if subsequent_hits == 4:
                        self.show_game_statistics(win_color)
                        return
                elif current_color != self.empty:
                    win_color = current_color
                    subsequent_hits = 1

    def check_columns(self):  
        for column in range(0, GameConfig.num_columns):        
            win_color = self.empty
            subsequent_hits = 1
            for row in range(0, GameConfig.num_rows):
                current_color = self.board[row][column]
                logging.debug(f"checking column: {chr(column+65)}{row+1}")
                if (current_color != self.empty and current_color == win_color):
                    logging.info(f"subsequent stones: {subsequent_hits+1} in a column at {chr(column+65)}{row+1}")
                    subsequent_hits += 1
                    if subsequent_hits == 4:
                        self.show_game_statistics(win_color)
                        return
                elif current_color != self.empty:
                    win_color = current_color
                    subsequent_hits = 1

    def check_cross(self): 
        #check cross from left bottom to right upper
        for column in range(0, GameConfig.num_columns-3):        
            for row in range(0, GameConfig.num_rows-3):            
                current_color = "empty"
                if self.board[row][column] == self.red:
                    current_color = "red"
                elif self.board[row][column] == self.yellow:
                    current_color = "yellow"
                logging.debug(f"checking cross left: {chr(column+65)}{row+1} found color {current_color}")
                win_color = self.board[row][column]
                if win_color == self.empty:
                    continue
                if win_color == self.board[row+1][column+1]:
                    logging.info(f"2 subsequent {current_color} stones cross left at {chr(column+65)}{row+1}")
                    if win_color == self.board[row+2][column+2]:
                        logging.info(f"3 subsequent {current_color} stones cross left at {chr(column+65)}{row+1}")
                        if win_color == self.board[row+3][column+3]:
                            self.show_game_statistics(win_color)
                            return
        #check cross from right bottom to left upper
        for column in reversed(range(3, GameConfig.num_columns)):  
            for row in range(0, GameConfig.num_rows-3):            
                current_color = "empty"
                if self.board[row][column] == self.red:
                    current_color = "red"
                elif self.board[row][column] == self.yellow:
                    current_color = "yellow"
                logging.debug(f"checking cross right: {chr(column+65)}{row+1} found color {current_color}")
                win_color = self.board[row][column]
                if win_color == self.empty:
                    continue
                if win_color == self.board[row+1][column-1]:                
                    logging.info(f"2 subsequent {current_color} stones cross right at {chr(column+65)}{row+1}")
                    if win_color == self.board[row+2][column-2]:
                        logging.info(f"3 subsequent {current_color} stones cross right at {chr(column+65)}{row+1}")
                        if win_color == self.board[row+3][column-3]:
                            self.show_game_statistics(win_color)
                            return
                        

    def show_game_statistics(self, win_color):        
        if win_color == self.red:
            logging.info("red wins")
        else:
            logging.info("yellow wins")
        self.running = False

    def test_cross_right(self):
      self.board[0][6] = self.red
      self.board[1][5] = self.red
      self.board[2][4] = self.red   
      self.board[0][3] = self.yellow
      self.board[1][3] = self.yellow
      self.board[2][3] = self.yellow
      self.board[0][3] = self.yellow
      self.board[0][5] = self.red

    def test_cross_left(self):
      self.board[0][1] = self.red
      self.board[1][2] = self.red
      self.board[2][3] = self.red   
      self.board[0][2] = self.yellow
      self.board[0][3] = self.yellow
      self.board[0][4] = self.yellow
      self.board[1][3] = self.yellow
      self.board[0][5] = self.red

    def test_column(self):
      self.board[0][2] = self.red
      self.board[1][2] = self.red
      #self.board[2][2] = self.red   
      self.board[0][5] = self.yellow
      self.board[1][5] = self.yellow
      #self.board[2][5] = self.yellow
        
    def test_row(self):
      self.board[0][2] = self.red
      self.board[0][3] = self.red
      #self.board[0][4] = self.red   
      self.board[1][2] = self.yellow
      self.board[1][3] = self.yellow
      #self.board[1][4] = self.yellow


        
    def run(self):
        self.render_environment(GameConfig.border_size, GameConfig.width, GameConfig.height)
        running = True
        while running:
            # poll for events
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # fill the screen with a color to wipe away anything from last frame

            self.render_stones()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_1] or keys[pygame.K_a]:
                self.add_stone(1)
            if keys[pygame.K_2] or keys[pygame.K_b]:
                self.add_stone(2)
            if keys[pygame.K_3] or keys[pygame.K_c]:
                self.add_stone(3)
            if keys[pygame.K_4] or keys[pygame.K_d]:
                self.add_stone(4)
            if keys[pygame.K_5] or keys[pygame.K_e]:
                self.add_stone(5)
            if keys[pygame.K_6] or keys[pygame.K_f]:
                self.add_stone(6)
            if keys[pygame.K_7] or keys[pygame.K_g]:
                self.add_stone(7)

            # flip() the display to put your work on screen
            pygame.display.flip()

            # limits FPS to 60
            # dt is delta time in seconds since last frame, used for framerate-
            # independent physics.
            self.dt = self.clock.tick(10) / 1000

        pygame.quit()

    def processHttpMove(self, coordinates):
        logging.info(f"received http call with arguments {coordinates}")
        column = ord(coordinates[0])-64
        if column > -1 and column < GameConfig.num_columns:
            return self.add_stone(column)
        else:
            logging.info()
            return "illegal move: specified column does not exist"


def start_http_server(port=8000):
    """Start the HTTP server in a separate thread"""
    GameRequestHandler.game_instance = my_game
    server = HTTPServer(('localhost', port), GameRequestHandler)
    logging.info(f"Starting HTTP server on port {port}")
    
    # Run server in a separate thread so it doesn't block pygame
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    return server

# Usage in your main game file:
if __name__ == "__main__":
    my_game = Four_Wins()

    #logging = logging.getlogging("four-wins")
    logging.basicConfig(filename='four-wins.log', level=logging.INFO)
    # Start your HTTP server
    http_server = start_http_server(8000)

    
    
    #Test cases
    #my_game.test_cross_right()
    #my_game.test_cross_left()
    #my_game.test_column()
    #my_game.test_row()
   
    my_game.run()
