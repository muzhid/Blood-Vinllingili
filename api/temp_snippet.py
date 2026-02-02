
def format_blood_request_message(blood_type, location, urgency, req_name, req_phone):
    lines = [f"🚨 <b>BLOOD REQUEST</b>", f"Type: {blood_type}"]
    
    # Condition: Hide location if Not Specified or Unknown
    if location and location not in ["Not Specified", "Unknown", "None"]:
        lines.append(f"Location: {location}")
        
    # Condition: Hide urgency if not High (or Critical) for cleanliness
    if urgency and urgency in ["High", "Critical", "Urgent"]:
        lines.append(f"Urgency: {urgency}")
        
    lines.append(f"Requester: {req_name} - {req_phone}")
    
    return "\n".join(lines)
