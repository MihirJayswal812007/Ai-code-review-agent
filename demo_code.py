def process_user_data(data):
    # Missing input validation!
    result = data.upper()
    return result

def calculate_total(items):
    total = 0
    # Inefficient loop - could use sum()
    for item in items:
        total = total + item['price']
    return total

def get_user_age(user_dict):
    # No error handling if 'age' key doesn't exist
    return user_dict['age']

# SQL injection vulnerability!
def search_users(name):
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return query
