TRIKSMODULENAME = "Educational Template"
"""
TRIKSMODULENAME - This is the name of the module that will be shown in the list of user modules.
"""

UPDATE_ROWS = 1   
"""
UPDATE_ROWS - Allows you to enable or disable updating the driver module list.

For example, you only need to export some modules and modify
the original file itself - then you do not need to update the list. UPDATE_ROWS = 0

Or you want to rewrite the module list through your plugin, or change it,
then you need to use UPDATE_ROWS = 1

If you accidentally forgot to add the UPDATE_ROWS variable,
then the lines will be updated automatically, but if there is nothing in return, an error may occur.
"""


def run(file_path, rows):
    """
    EDUCATIONAL TEMPLATE - HOW MODULES WORK:
    
    This template shows the basic structure of a processing module.
    
    KEY CONCEPTS:
    - Every module MUST have TRIKSMODULENAME and run() function
    - file_path: Path to the main com.qti.*** binary file for reading data
    - rows: List of data strings in format "ID,Name,Offset,Length"
    - Return: Must return a list of processed rows
    
    PROCESSING FLOW:
    1. Module receives data from previous step
    2. You can read binary data using file_path and offsets
    3. Process the rows as needed
    4. Return modified rows to next processing step
    5. Also it can be used to Batch Patch Data in com.qti.*** binary file
    
    TIP: Use this as a starting point for your custom Tricks modules!
    """
    
    # Always create a new list for processed results
    processed_rows = []
    
    # Example: Process each row (this just copies them)
    for row in rows:
        # You can add your processing logic here
        # For example: parse row, read binary data, modify content
        
        processed_rows.append(row)  # Just passing through unchanged
    
    # Example of reading binary data (commented out for template)
    """
    # How to read data from the binary file:
    try:
        offset = 0x1000  # Example offset
        length = 0x50    # Example length
        with open(file_path, 'rb') as file:
            file.seek(offset)
            data = file.read(length)
            # Process the binary data here
    except Exception as e:
        print(f"Error reading file: {e}")
    """
    
    print(f"[Template] Processed {len(processed_rows)} rows")
    return processed_rows
