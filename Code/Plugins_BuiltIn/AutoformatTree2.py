TRIKSMODULENAME = "Auto Tree Sorter V2"
UPDATE_ROWS = 1

def run(file_path, rows):
    parent_elements = [
        "triggerData", "trigger1Data", "trigger2Data", "trigger3Data",
        "analyzerName", "arithmeticOperators", "channel1", "channel2",
        "channel3", "channel4", "channel5", "region", "trigger", "revision"
    ]
    
    processed_rows = []
    
    for row in rows:
        parts = row.strip().split(',')
        
        if len(parts) >= 4:
            original_name = parts[1]
            current_name = original_name
            description_processed = False
            
            # Description Processing
            if "Description" in original_name:
                technical_tags = ""
                if '[' in original_name and ']' in original_name:
                    before_desc = original_name.split('Description')[0]
                    if '[' in before_desc and ']' in before_desc:
                        technical_tags = before_desc
                        current_name = "Description"
                
                try:
                    offset = int(parts[2], 16)
                    length = int(parts[3], 16)
                    
                    with open(file_path, 'rb') as file:
                        file.seek(offset)
                        data_bytes = file.read(length)
                        ascii_string = data_bytes.decode('ascii', errors='ignore').strip()
                        
                        # UPDATE current_name!
                        current_name = f"{technical_tags}{ascii_string}"
                        parts[1] = current_name
                        description_processed = True
                        
                except (ValueError, IOError, Exception):
                    pass
            
            # Now let's check the UPDATED current_name
            is_parent = False
            for parent_element in parent_elements:
                if parent_element in current_name:
                    is_parent = True
                    break
            
            # Add tags only if the Description has not been processed.
            if not description_processed:
                if is_parent:
                    if original_name.startswith('[') and ']' in original_name:
                        bracket_pos = original_name.find(']') + 1
                        existing_tags = original_name[:bracket_pos]
                        remaining_name = original_name[bracket_pos:]
                        parts[1] = f"{existing_tags}[parent]{remaining_name}"
                    else:
                        parts[1] = f"[parent]{original_name}"
                else:
                    if original_name.startswith('[') and ']' in original_name:
                        bracket_pos = original_name.find(']') + 1
                        existing_tags = original_name[:bracket_pos]
                        remaining_name = original_name[bracket_pos:]
                        parts[1] = f"{existing_tags}[dictionary]{remaining_name}"
                    else:
                        parts[1] = f"[dictionary]{original_name}"
        
        processed_rows.append(','.join(parts))
    
    return processed_rows
