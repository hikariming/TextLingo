def success_response(data, message="Success"):
    return {
        "success": True,
        "message": message,
        "data": data
    }

def error_response(message="Error", code=400):
    return {
        "success": False,
        "message": message
    }, code