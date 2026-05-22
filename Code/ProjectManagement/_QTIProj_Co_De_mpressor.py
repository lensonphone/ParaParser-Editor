import lzma
import os
import sys
import struct

class QPARParser:
    def __init__(self):
        self.header = b"QPARPARSERPROJ.V002.S" # Increment the version
        self.header_len = len(self.header)
        
    def process_data(self, input_data: bytes, bin_file_path: str = None) -> tuple:
        """Universal data processing method with bin file path support"""
        try:
            # Robust header validation
            if len(input_data) >= self.header_len:
                if input_data[:self.header_len] == self.header:
                    print("Detected compressed data - decompressing...")
                    return self._decompress(input_data)
            
            print("Detected raw data - compressing...")
            return self._compress(input_data, bin_file_path)
            
        except Exception as e:
            print(f"Processing error: {e}", file=sys.stderr)
            raise
    
    def _compress(self, data: bytes, bin_file_path: str = None) -> bytes:
        """Cross-platform compression with file path support"""
        try:
            # Prepare file path data
            path_data = b""
            if bin_file_path:
                # Encode the path in UTF-8 and add the length
                encoded_path = bin_file_path.encode('utf-8')
                path_data = struct.pack('>I', len(encoded_path)) + encoded_path
                print(f"Adding file path: {bin_file_path} ({len(encoded_path)} bytes)")
            
            # Use default settings for maximum compatibility
            filters = [
                {
                    "id": lzma.FILTER_LZMA2,
                    "preset": 6, # Medium level for compatibility
                }
            ]
            
            compressor = lzma.LZMACompressor(
                format=lzma.FORMAT_RAW,
                filters=filters
            )
            
            # Compress data with path information
            compressed = compressor.compress(path_data + data)
            compressed += compressor.flush()
            
            print(f"Compression: {len(data)} -> {len(compressed)} bytes")
            return self.header + compressed
            
        except Exception as e:
            print(f"Compression error: {e}", file=sys.stderr)
            raise
    
    def _decompress(self, compressed_data: bytes) -> tuple:
        """Cross-platform decompression with file path extraction"""
        try:
            if not compressed_data.startswith(self.header):
                raise ValueError("Invalid header format")
            
            raw_compressed = compressed_data[self.header_len:]
            print(f"Decompressing: header {self.header_len} + data {len(raw_compressed)} bytes")
            
            decompressor = lzma.LZMADecompressor(
                format=lzma.FORMAT_RAW,
                filters=[{"id": lzma.FILTER_LZMA2}]
            )
            
            result = decompressor.decompress(raw_compressed)
            
            # Extract the file path (if any)
            bin_file_path = None
            if len(result) >= 4:
                # Read the path length (4 bytes) big-endian)
                path_length = struct.unpack('>I', result[:4])[0]
                
                if path_length > 0 and len(result) >= 4 + path_length:
                    # Extract the encoded path
                    encoded_path = result[4:4 + path_length]
                    bin_file_path = encoded_path.decode('utf-8')
                    # The rest of the data is the payload
                    data = result[4 + path_length:]
                    print(f"Extracted file path: {bin_file_path}")
                else:
                    data = result
            else:
                data = result
            
            print(f"Decompressed to: {len(data)} bytes")
            return data, bin_file_path
            
        except Exception as e:
            print(f"Decompression error: {e}", file=sys.stderr)
            raise

    def is_compressed_file(self, file_path: str) -> bool:
        """Checks if the file is compressed by header"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(self.header_len)
                return header == self.header
        except:
            return False

    def process_file(self, input_file: str, output_file: str = None, bin_file_path: str = None):
        """Processing a file with support for the path to the bin file"""
        try:
            # Reading the input file
            with open(input_file, 'rb') as f:
                input_data = f.read()
            
            # Defining the processing mode
            if self.is_compressed_file(input_file):
                # Decompression
                result_data, extracted_path = self.process_data(input_data)
                
                # Saving the result
                if output_file is None:
                    output_file = input_file + '.decompressed'
                
                with open(output_file, 'wb') as f:
                    f.write(result_data)
                
                print(f"Decompressed file saved as: {output_file}")
                if extracted_path:
                    print(f"Extracted bin file path: {extracted_path}")
                return result_data, extracted_path
                
            else:
                # Compression
                result_data = self.process_data(input_data, bin_file_path)
                
                # Saving the result
                if output_file is None:
                    output_file = input_file + '.compressed'
                
                with open(output_file, 'wb') as f:
                    f.write(result_data)
                
                print(f"Compressed file saved as: {output_file}")
                return result_data, bin_file_path
                
        except Exception as e:
            print(f"File processing error: {e}", file=sys.stderr)
            raise

# Usage example
if __name__ == "__main__":
    parser = QPARParser()
    
    # Compression example with the path to the bin file
    compressed_data, bin_path = parser.process_data(
        b"Your raw data here", 
        "C:/project/assets/main.bin"
    )
    
    # Decompression example
    decompressed_data, extracted_bin_path = parser.process_data(compressed_data)
    print(f"Decompressed data: {decompressed_data}")
    print(f"Extracted bin path: {extracted_bin_path}")
