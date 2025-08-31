import json
from pathlib import Path

class GameConfig:
    # Default configuration
    _defaults = {
        "border_size": 20,
        "font_size": 32,
        "text_color": [255, 255, 150],
        "bg_color": [0, 0, 128],
        "yellow_color": [255, 220, 50],
        "red_color": [220, 0, 0],
        "empty_color": [220, 220, 220],
        "base_url": "http://localhost:8000",
        "num_columns": 7,
        "num_rows": 6,
        "width": 800,
        "height": 720,
        "font": "freesansbold.ttf"
    }
    
    @classmethod
    def load(cls, config_file='game_config.json'):
        """Load configuration from JSON file"""
        config_path = Path(config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Update class attributes with loaded values
                for key, value in loaded_config.items():
                    if hasattr(cls, key) or key in cls._defaults:
                        setattr(cls, key, value)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}, using defaults")
        else:
            # Create config file with defaults
            cls.save(config_file)
        
        # Set any missing attributes to defaults
        for key, value in cls._defaults.items():
            if not hasattr(cls, key):
                setattr(cls, key, value)
    

    @classmethod
    def save(cls, config_file='game_config.json'):
        """Save current configuration to file"""
        config = {}
        for key in cls._defaults:
            config[key] = getattr(cls, key, cls._defaults[key])
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Error saving config: {e}")
