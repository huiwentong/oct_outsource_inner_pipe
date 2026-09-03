import yaml

def get_config():
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config