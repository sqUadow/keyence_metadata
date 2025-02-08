import re
import sys

def parse_metadata(filepath):
    """Parses Keyence microscope metadata from a TIFF file.
    
    Args:
        filepath: Path to the TIFF file.
        
    Returns:
        Dictionary containing the extracted metadata.
    """
    try:
        # Read file with utf-8 encoding, ignoring decode errors
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Find the <Data> ... </Data> block
        match = re.search(r'<Data>(.*?)</Data>', content, re.DOTALL)
        if not match:
            print("No <Data> block found in file")
            return {}

        data_str = match.group(1)
        metadata = {}

        # --- Image Section ---
        image_match = re.search(r'<Image [^>]*>(.*?)</Image>', data_str, re.DOTALL)
        if image_match:
            image_data = image_match.group(1)
            metadata['Comment'] = _extract_value(image_data, 'Comment')
            metadata['OriginalImageSize_Width'] = _extract_value(image_data, 'OriginalImageSize', 'Width')
            metadata['OriginalImageSize_Height'] = _extract_value(image_data, 'OriginalImageSize', 'Height')
            metadata['DigitalZoom'] = _extract_value(image_data, 'DigitalZoom')
            metadata['Calibration'] = _extract_value(image_data, 'Calibration')

        # --- Lens Section ---
        lens_match = re.search(r'<Lens [^>]*>(.*?)</Lens>', data_str, re.DOTALL)
        if lens_match:
            lens_data = lens_match.group(1)
            metadata['LensName'] = _extract_value(lens_data, 'LensName')
            metadata['Magnification'] = _extract_value(lens_data, 'Magnification')
            metadata['NumericalAperture'] = _extract_value(lens_data, 'NumericalAperture')
            metadata['WorkingDistance'] = _extract_value(lens_data, 'WorkingDistance')

        # --- Shooting Section ---
        shooting_match = re.search(r'<Shooting [^>]*>(.*?)</Shooting>', data_str, re.DOTALL)
        if shooting_match:
            shooting_data = shooting_match.group(1)
            metadata['StageLocationX'] = _extract_value(shooting_data, 'StageLocationX')
            metadata['StageLocationY'] = _extract_value(shooting_data, 'StageLocationY')
            metadata['StageLocationZ'] = _extract_value(shooting_data, 'StageLocationZ')
            metadata['Channel'] = _extract_value(shooting_data, 'Channel')
            metadata['Observation'] = _extract_value(shooting_data, 'Observation')

        return metadata
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {}

def _extract_value(data_str, tag, subtag=None, search_in=None):
    """Helper function to extract values from the XML-like structure."""
    try:
        if search_in:
            outer_match = re.search(rf'<{search_in} [^>]*>(.*?)</{search_in}>', data_str, re.DOTALL)
            if not outer_match:
                return None
            data_str = outer_match.group(1)

        if subtag:
            pattern = rf'<{tag} [^>]*>.*?<{subtag} [^>]*>(.*?)</{subtag}>.*?</{tag}>'
        else:
            pattern = rf'<{tag} [^>]*>(.*?)</{tag}>'

        match = re.search(pattern, data_str, re.DOTALL)
        return match.group(1) if match else None
    except Exception as e:
        print(f"Error extracting value for {tag}: {str(e)}")
        return None

def print_metadata_table(metadata):
    """Prints the metadata in a formatted table."""
    if not metadata:
        print("No metadata found in file.")
        return

    print("-" * 50)
    print(f"{'Parameter':<30} | {'Value':<15}")
    print("-" * 50)
    for key, value in metadata.items():
        if value is not None:
            print(f"{key:<30} | {value:<15}")
    print("-" * 50)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_tiff_metadata.py <tiff_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    metadata = parse_metadata(filepath)
    print_metadata_table(metadata)