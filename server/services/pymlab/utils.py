def parse_list(value):
    # Check if the value is a list
    if value.startswith('[') and value.endswith(']'):
        # Remove brackets
        value = value[1:-1]
        result = []
        nested_level = 0
        start = 0

        # Iterate through characters in the value
        for i, char in enumerate(value):
            if char == '[':
                nested_level += 1
            elif char == ']':
                nested_level -= 1
            elif char == ',' and nested_level == 0:
                # Split at the top level commas
                result.append(parse_list(value[start:i]))
                start = i + 1

        # Add the last part after the last comma (or whole value if no commas)
        result.append(parse_list(value[start:]))

        return result
    else:
        # If it's not a list, return the value itself
        return convert_type(value)

def convert_type(value):
    # Convert string to appropriate type
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        return str(value)

def fetch_parameters(config_path):
    parameters = {}
    with open(config_path, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) >= 4 and parts[0] == 'PARAM':
                param_name = parts[1]
                param_type = parts[2]
                param_value = ' '.join(parts[3:])

                if param_type.startswith('list'):
                    # If it's a list type, parse the value accordingly
                    parameters[param_name] = parse_list(param_value)
                else:
                    if param_type == 'int':
                        parameters[param_name] = int(param_value)
                    elif param_type == 'float':
                        parameters[param_name] = float(param_value)
                    elif param_type == 'bool':
                        parameters[param_name] = param_value.lower() == 'true'
                    else:
                        parameters[param_name] = str(param_value)

    return parameters
