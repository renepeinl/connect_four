import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

class GameRequestHandler(BaseHTTPRequestHandler):
    game_instance = None

    def do_POST(self):
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/four-wins':    
            game_id = self.game_instance.new_game()
            try:
                self.set_header(200, 'application/json')

                self.end_headers()
                response = {
                        'status': 'success',
                        'game-id': game_id
                    }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_error(500, str(e))

    def send_error(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'status': 'error',
            'message': message
        }
        self.wfile.write(json.dumps(response).encode())

    def set_header(self, status, content_type):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')

    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/four-wins':
            # Get the move parameter (e.g., ?move=A1)
            query_params = parse_qs(parsed_url.query)
            
            if 'move' in query_params:
                global my_game
                move = query_params['move'][0]  # Get the first value
                
                try:
                    # Call your game function here
                    # Replace 'make_move' with your actual method name
                    result = self.game_instance.processHttpMove(move)
                    
                    # Send success response
                    self.set_header(200, 'application/json')
                    self.end_headers()
                    
                    response = {
                        'status': 'success',
                        'move': move,
                        'result': result
                    }
                    self.wfile.write(json.dumps(response).encode())
                    
                except Exception as e:
                    # Send error response
                    self.send_error(400, str(e))
            else:
                # Missing move parameter
                self.send_error(400, 'Missing move parameter')
        
        elif parsed_url.path.startswith('/screens'):
            # endpoint to retrieve the screenshots
            try:                       
                image_path = '.' + parsed_url.path
                content_type = "text/jsonl+json" if parsed_url.path.endswith("jsonl") else "image/png"
                with open(image_path,"rb") as img_file:
                    file_data = img_file.read()
                    file_data_len = len(file_data)        
                    self.set_header(200, content_type)
                    self.send_header("Content-Length",file_data_len) 
                    self.end_headers()
                    self.wfile.write(file_data)
                
            except Exception as e:
                self.send_error(500, str(e))
        
        else:
            # Unknown endpoint
            self.send_error(404, 'Endpoint not found')
