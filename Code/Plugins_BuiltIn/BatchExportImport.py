TRIKSMODULENAME = "Batch Binary Export/Import Tool"

import os
import json
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt

def run(file_path, rows):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Action selection dialog
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Batch Binary Operations")
    msg_box.setText("Choose operation:")
    msg_box.setIcon(QMessageBox.Question)
    
    export_btn = msg_box.addButton("Export All Binaries", QMessageBox.ActionRole)
    import_btn = msg_box.addButton("Import Binaries", QMessageBox.ActionRole)
    cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
    
    msg_box.exec_()
    clicked_button = msg_box.clickedButton()
    
    if clicked_button == export_btn:
        return export_binaries(file_path, rows)
    elif clicked_button == import_btn:
        return import_binaries(file_path, rows)
    else:
        return rows

def export_binaries(file_path, rows):
    """Export all binary data to the selected folder"""
    # Selecting the folder for export
    folder_path = QFileDialog.getExistingDirectory(
        None,
        "Select Folder for Binary Export",
        "",
        QFileDialog.ShowDirsOnly
    )
    
    if not folder_path:
        return rows
    
    try:
        # Creating a structure for metadata
        metadata = {
            "source_file": os.path.basename(file_path),
            "export_date": "", # Adding the date later
            "binaries": []
        }
        
        # Looping through all lines and exporting binary data
        exported_count = 0
        for row in rows:
            parts = row.strip().split(',')
            if len(parts) >= 4:
                row_id = parts[0]
                name = parts[1]
                offset_hex = parts[2]
                length_hex = parts[3]
                
                # Skipping lines without offset/length
                if not offset_hex or not length_hex:
                    continue
                
                try:
                    offset = int(offset_hex, 16)
                    length = int(length_hex, 16)
                    
                    # Reading binary data from the file
                    with open(file_path, 'rb') as src_file:
                        src_file.seek(offset)
                        binary_data = src_file.read(length)
                    
                    # Creating a safe file name
                    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    if not safe_name:
                        safe_name = "unnamed"
                    
                    # Generating the file name: ID_Name.bin
                    bin_filename = f"{row_id}_{safe_name}.bin"
                    bin_filepath = os.path.join(folder_path, bin_filename)
                    
                    # Saving the binary data
                    with open(bin_filepath, 'wb') as bin_file:
                        bin_file.write(binary_data)
                    
                    # Adding information to the metadata
                    metadata["binaries"].append({
                        "row_id": row_id,
                        "name": name,
                        "offset": offset_hex,
                        "length": length_hex,
                        "filename": bin_filename,
                        "original_row": row
                    })
                    
                    exported_count += 1
                    
                except (ValueError, IOError, Exception):
                    continue
        
        # Saving the metadata file
        metadata_path = os.path.join(folder_path, "export_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as meta_file:
            json.dump(metadata, meta_file, indent=2, ensure_ascii=False)
        
        # Success message
        QMessageBox.information(
            None,
            "Export Complete",
            f"Successfully exported {exported_count} binary files to:\n{folder_path}\n\nMetadata saved to: export_metadata.json"
        )
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Export Error",
            f"Error during export:\n{str(e)}"
        )
    
    return rows

def import_binaries(file_path, rows):
    """Importing binary data from folders"""
    # Selecting a metadata file
    metadata_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select Export Metadata File (export_metadata.json)",
        "",
        "JSON Files (*.json);;All Files (*)"
    )
    
    if not metadata_path or not os.path.exists(metadata_path):
        return rows
    
    try:
        # Loading metadata
        with open(metadata_path, 'r', encoding='utf-8') as meta_file:
            metadata = json.load(meta_file)
        
        folder_path = os.path.dirname(metadata_path)
        imported_count = 0
        updated_rows = rows.copy()
        
        # Looping through all metadata records
        for binary_info in metadata.get("binaries", []):
            bin_filename = binary_info.get("filename")
            row_id = binary_info.get("row_id")
            original_row = binary_info.get("original_row")
            
            if not bin_filename or not row_id:
                continue
            
            bin_filepath = os.path.join(folder_path, bin_filename)
            
            if os.path.exists(bin_filepath):
                # Reading imported binary data
                with open(bin_filepath, 'rb') as bin_file:
                    imported_data = bin_file.read()
                
                # Finding the corresponding row in rows
                for i, row in enumerate(updated_rows):
                    if row.startswith(row_id + ','):
                        # Replacing the row with the original from the metadata
                        updated_rows[i] = original_row
                        imported_count += 1
                        break
        
        # Confirming import
        if imported_count > 0:
            reply = QMessageBox.question(
                None,
                "Import Confirmation",
                f"Successfully prepared {imported_count} binary files for import.\n\nApply changes to current project?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                QMessageBox.information(
                    None,
                    "Import Complete",
                    f"Successfully imported {imported_count} binary files"
                )
                return updated_rows
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Import Error",
            f"Error during import:\n{str(e)}"
        )
    
    return rows
