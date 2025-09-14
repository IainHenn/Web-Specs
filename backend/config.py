import json
import os

def generate_notif_settings(system_info):
    config_path = os.path.join("notif_config.json")
    print(f"system_info: {system_info}")
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            for key, value in system_info.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, dict):
                            for nested_nested_key, nested_nested_value in nested_value.items():
                                if isinstance(nested_nested_value, float) or isinstance(nested_nested_value, int):
                                    system_info[key][nested_key][nested_nested_key] = .80
                        else:
                            if isinstance(nested_value, float) or isinstance(nested_value, int):
                                system_info[key][nested_key] = .80
                else:
                    system_info[key] = .80    
            json.dump(system_info, f, indent=4)

def update_settings(changes):
    config_path = os.path.join("notif_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config_dict = json.load(f)
            for key, value in changes.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, dict):
                            for nested_nested_key, nested_nested_value in nested_value.items():
                                if isinstance(nested_nested_value, float) or isinstance(nested_nested_value, int):
                                    config_dict[key][nested_key][nested_nested_key] = changes[key][nested_key][nested_nested_key]
                        else:
                            if isinstance(nested_value, float) or isinstance(nested_value, int):
                                config_dict[key][nested_key] = changes[key][nested_key]
                else:
                    config_dict[key] = changes[key]