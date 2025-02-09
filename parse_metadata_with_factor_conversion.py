import re
import struct
import argparse
from pathlib import Path
import sys

def decode_double(value):
    """Decodes IEEE 754 double-precision value stored as integer."""
    try:
        return struct.unpack('d', struct.pack('Q', int(value)))[0]
    except (ValueError, TypeError):
        return None

def parse_metadata(content):
    """Parses Keyence microscope metadata from a TIFF file."""
    match = re.search(r'<Data>(.*?)</Data>', content, re.DOTALL)
    if not match:
        return {}

    data_str = match.group(1)
    metadata = {}

    def extract_and_mark(data, tag, subtag=None, search_in=None, is_double=False):
        """Extracts a value and adds '*' to the key if it's a double."""
        value = _extract_value(data, tag, subtag, search_in)
        key = tag
        if is_double:
            key += "*"
        return key, value

    # --- Image Section ---
    image_match = re.search(r'<Image [^>]*>(.*?)</Image>', data_str, re.DOTALL)
    if image_match:
        image_data = image_match.group(1)
        metadata['Comment'] = _extract_value(image_data, 'Comment')
        metadata['OriginalImageSize_Width'] = _extract_value(image_data, 'OriginalImageSize', 'Width')
        metadata['OriginalImageSize_Height'] = _extract_value(image_data, 'OriginalImageSize', 'Height')
        metadata['SavingImageSize_Width'] = _extract_value(image_data, 'SavingImageSize', 'Width')
        metadata['SavingImageSize_Height'] = _extract_value(image_data, 'SavingImageSize', 'Height')
        metadata['DigitalZoom'] = _extract_value(image_data, 'DigitalZoom')
        k, v = extract_and_mark(image_data, 'Calibration', is_double=True)
        metadata[k] = v
        k, v = extract_and_mark(image_data, 'Focus', is_double=True)
        metadata[k] = v
        metadata['PatchNumber'] = _extract_value(image_data, 'PatchNumber')

    # --- Lens Section ---
    lens_match = re.search(r'<Lens [^>]*>(.*?)</Lens>', data_str, re.DOTALL)
    if lens_match:
        lens_data = lens_match.group(1)
        metadata['LensName'] = _extract_value(lens_data, 'LensName')
        metadata['Magnification'] = _extract_value(lens_data, 'Magnification')
        k, v = extract_and_mark(lens_data, 'NumericalAperture', is_double=True)
        metadata[k] = v
        k, v = extract_and_mark(lens_data, 'WorkingDistance', is_double=True)
        metadata[k] = v
        metadata['LiquidImmersion'] = _extract_value(lens_data, 'LiquidImmersion')
        metadata['RevolverPosition'] = _extract_value(lens_data, 'RevolverPosition')

    # --- Shooting Section ---
    shooting_match = re.search(r'<Shooting [^>]*>(.*?)</Shooting>', data_str, re.DOTALL)
    if shooting_match:
        shooting_data = shooting_match.group(1)
        metadata['StageLocationX'] = _extract_value(shooting_data, 'StageLocationX')
        metadata['StageLocationY'] = _extract_value(shooting_data, 'StageLocationY')
        metadata['StageLocationZ'] = _extract_value(shooting_data, 'StageLocationZ')
        metadata['Channel'] = _extract_value(shooting_data, 'Channel')
        metadata['Observation'] = _extract_value(shooting_data, 'Observation')
        metadata['PseudoColor'] = _extract_value(shooting_data, 'PseudoColor', search_in='Parameter')
        metadata['Binning'] = _extract_value(shooting_data, 'Binnin', search_in='Parameter')
        metadata['ExposureTime_Numerator'] = _extract_value(shooting_data, 'ExposureTime', 'Numerator')
        metadata['ExposureTime_Denominator'] = _extract_value(shooting_data, 'ExposureTime', 'Denominator')
        metadata['PixelMode'] = _extract_value(shooting_data, 'PixelMode', search_in='Parameter')
        metadata['CameraGain'] = _extract_value(shooting_data, 'CameraGain', search_in='Parameter')
        metadata['CameraHardwareGain'] = _extract_value(shooting_data, 'CameraHardwareGain', search_in='Parameter')
    return metadata

def _extract_value(data_str, tag, subtag=None, search_in=None):
    """Helper function to extract values, correctly handling nested tags."""
    if search_in:
        outer_match = re.search(rf'<{search_in} [^>]*>(.*?)</{search_in}>', data_str, re.DOTALL)
        if not outer_match:
            return None
        data_str = outer_match.group(1)

    if subtag:
        pattern = rf'<{tag} [^>]*>.*?<{subtag} [^>]*>([^<]*)</{subtag}>.*?</{tag}>'
    else:
        pattern = rf'<{tag} [^>]*>([^<]*)</{tag}>'

    match = re.search(pattern, data_str, re.DOTALL)
    return match.group(1).strip() if match else None

def format_metadata(metadata, output_format='table'):
    """Formats metadata, decoding double values marked with '*'."""
    if not metadata:
        return "No metadata found."

    decoded_metadata = {}
    for key, value in metadata.items():
        if value is not None:
            if key.endswith('*'):
                decoded_value = decode_double(value)
                if decoded_value is not None:
                    if key == "Calibration*":
                        value = f"{decoded_value / 1000:.6f} um/pixel"
                    else:
                        value = f"{decoded_value:.6f}"
                else:
                    value = "Could not decode"
            decoded_metadata[key] = value

    if output_format == 'table':
        output = "* Indicates an IEEE 754 double-precision value that has been converted.\n"
        output += "Parameter\tValue\n"
        for key, value in decoded_metadata.items():
            output += f"{key}\t{value}\n"
        return output
    elif output_format == 'dict':
        return decoded_metadata  # Return the dictionary directly
    else:
        raise ValueError("Invalid output_format. Choose 'table' or 'dict'.")

def read_tiff_content(file_path):
    """Reads the TIFF file and returns the content as a string."""
    try:
        with open(file_path, 'rb') as f:  # Open in binary read mode
            content_bytes = f.read()
            # Try decoding with different encodings
            for encoding in ['utf-8', 'latin-1', 'ascii']:
                try:
                    content = content_bytes.decode(encoding)
                    return content
                except UnicodeDecodeError:
                    continue  # Try the next encoding
            # If none of the encodings work, raise the error
            raise UnicodeDecodeError("Could not decode the file content with any of the tried encodings.")

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Extract and display metadata from Keyence TIFF files.")
    parser.add_argument("file_path", type=str, help="Path to the TIFF file.")
    parser.add_argument("-o", "--output", type=str, default='table', choices=['table', 'dict'],
                        help="Output format: 'table' (default) or 'dict'.")
    parser.add_argument("-f", "--output_file", type=str, default=None,
                        help="Optional output file path.  If not specified, prints to stdout.")

    args = parser.parse_args()

    try:
        file_content = read_tiff_content(args.file_path)
        metadata = parse_metadata(file_content)
        formatted_output = format_metadata(metadata, args.output)

        if args.output_file:
            with open(args.output_file, 'w') as outfile:
                outfile.write(str(formatted_output))  # Ensure string output for file writing
            print(f"Metadata written to {args.output_file}")
        else:
            print(formatted_output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()