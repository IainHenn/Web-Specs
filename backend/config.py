import json
import os
from live_info import get_db_connection
from datetime import datetime

def generate_notif_settings(system_info):
    def set_values(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "percent" or "percent" in k:
                    if isinstance(v, dict):
                        for nk in v:
                            v[nk] = 80
                    else:
                        obj[k] = 80
                elif isinstance(v, dict):
                    set_values(v)
                elif isinstance(v, float) or isinstance(v, int):
                    obj[k] = 80 if "percent" in k else ''
                else:
                    obj[k] = v
        return obj

    config_path = os.path.join("notif_config.json")
    if not os.path.exists(config_path):
        system_info = set_values(system_info)
        with open(config_path, "w") as f:
            json.dump(system_info, f, indent=4)

def update_settings(changes):
    config_path = os.path.join("notif_config.json")
    print(f"changes: {changes}")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config_dict = json.load(f)
            for key, value in changes.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, dict):
                            for nested_nested_key, nested_nested_value in nested_value.items():
                                if isinstance(nested_nested_value, float) or isinstance(nested_nested_value, int) or nested_nested_value == "":
                                    config_dict[key][nested_key][nested_nested_key] = changes[key][nested_key][nested_nested_key]
                        else:
                            if isinstance(nested_value, float) or isinstance(nested_value, int) or nested_value == "":
                                config_dict[key][nested_key] = changes[key][nested_key]
                else:
                    if isinstance(value, float) or isinstance(value, int) or value == "":
                        config_dict[key] = changes[key]

        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=4)

def setup_email_config(email, app_password):
    email_config_path = os.path.join("email_config.json")
    email_config = {
        "sender_email": email,
        "app_password": app_password,
    }
    try:
        if not os.path.exists(email_config_path):
            with open(email_config_path, "w") as f:
                json.dump(email_config, f, indent=4)
        else:
            with open(email_config_path, "r") as f:
                existing_config = json.load(f)
            existing_config.update(email_config)
            with open(email_config_path, "w") as f:
                json.dump(existing_config, f, indent=4)
    except Exception as e:
        print(f"Error setting up email config: {e}")

def check_thresholds(system_info):
    conn = get_db_connection()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config_path = os.path.join("notif_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config_dict = json.load(f)
            with conn.cursor() as cursor:
                for key, value in system_info.items():
                    if isinstance(value, dict):
                        for nested_key, nested_value in value.items():
                            if isinstance(nested_value, dict):
                                for nested_nested_key, nested_nested_value in nested_value.items():
                                    sys_val = system_info[key][nested_key][nested_nested_key]
                                    conf_val = config_dict[key][nested_key][nested_nested_key]
                                    if (
                                        (isinstance(sys_val, (float, int)) and isinstance(conf_val, (float, int)))
                                        and sys_val >= conf_val
                                    ):
                                        cursor.execute(
                                            "INSERT INTO alerts (timestamp, component, value, threshold_value, sent) VALUES (%s, %s, %s, %s, %s)",
                                            (current_timestamp, f"{key}-{nested_key}-{nested_nested_key}", sys_val, conf_val, False)
                                        )
                            else:
                                sys_val = system_info[key][nested_key]
                                conf_val = config_dict[key][nested_key]
                                if (
                                    (isinstance(sys_val, (float, int)) and isinstance(conf_val, (float, int)))
                                    and sys_val >= conf_val
                                ):
                                    cursor.execute(
                                        "INSERT INTO alerts (timestamp, component, value, threshold_value, sent) VALUES (%s, %s, %s, %s, %s)",
                                        (current_timestamp, f"{key}-{nested_key}", sys_val, conf_val, False)
                                    )
                    else:
                        sys_val = system_info[key]
                        conf_val = config_dict[key]
                        if (
                            (isinstance(sys_val, (float, int)) and isinstance(conf_val, (float, int)))
                            and sys_val >= conf_val
                        ):
                            cursor.execute(
                                "INSERT INTO alerts (timestamp, component, value, threshold_value, sent) VALUES (%s, %s, %s, %s, %s)",
                                (current_timestamp, key, sys_val, conf_val, False)
                            )
    conn.commit()
    conn.close()
