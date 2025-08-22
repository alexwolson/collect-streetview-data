#!/usr/bin/env python3
"""
Get a Google Street View panorama from Toronto's centerpoint.
"""

import os
import json
from streetlevel.streetview import find_panorama
from .load_boundary import load_toronto_boundary, get_boundary_centerpoint
from .logging_config import setup_logging, print_header, print_success, print_error, print_info, print_warning, console


def get_panorama_data(panorama):
    """
    Extract all data from a StreetView panorama object.
    
    Args:
        panorama: StreetView panorama object
        
    Returns:
        dict: Dictionary containing all panorama data
    """
    panorama_data = {}
    all_attributes = [
        'id', 'lat', 'lon', 'date', 'heading', 'pitch', 'roll',
        'address', 'country_code', 'source', 'is_third_party', 'upload_date',
        'artworks', 'building_level', 'building_levels', 'copyright_message',
        'depth', 'elevation', 'historical', 'image_sizes', 'neighbors',
        'links', 'permalink', 'places', 'street_names', 'tile_size', 'uploader', 'uploader_icon_url'
    ]
    
    for attr in all_attributes:
        if hasattr(panorama, attr):
            value = getattr(panorama, attr)
            if value is not None:
                panorama_data[attr] = value
    
    return panorama_data


def save_panorama_data(panorama, output_dir="output"):
    """
    Save ALL panorama data to a JSON file.
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        panorama_data = get_panorama_data(panorama)
        processed_data = {}
        
        for key, value in panorama_data.items():
            try:
                if key == 'neighbors' and hasattr(value, '__iter__'):
                    neighbors_list = []
                    for neighbor in value:
                        if hasattr(neighbor, 'id') and hasattr(neighbor, 'lat') and hasattr(neighbor, 'lon'):
                            neighbors_list.append({
                                'id': neighbor.id,
                                'lat': neighbor.lat,
                                'lon': neighbor.lon,
                                'date': getattr(neighbor, 'date', None)
                            })
                        else:
                            neighbors_list.append(str(neighbor))
                    processed_data[key] = neighbors_list
                    
                elif key == 'links' and hasattr(value, '__iter__'):
                    links_list = []
                    for link in value:
                        if hasattr(link, 'pano') and hasattr(link, 'direction'):
                            pano_str = str(link.pano)
                            pano_id = pano_str.split(' (')[0] if ' (' in pano_str else pano_str
                            
                            links_list.append({
                                'pano_id': pano_id,
                                'pano_full': str(link.pano),
                                'direction': link.direction
                            })
                        else:
                            links_list.append(str(link))
                    processed_data[key] = links_list
                    
                elif key == 'address' and isinstance(value, str):
                    try:
                        if value.startswith('[') and value.endswith(']'):
                            clean_address = value.replace('[en:', '').replace(']', '').replace("'", '')
                            processed_data[key] = clean_address
                        else:
                            processed_data[key] = value
                    except:
                        processed_data[key] = value
                        
                elif key == 'historical' and isinstance(value, str):
                    try:
                        historical_data = []
                        parts = value.split(',')
                        for part in parts:
                            part = part.strip()
                            if part.startswith('[') or part.endswith(']'):
                                continue
                            if '(' in part and ')' in part:
                                id_part = part.split('(')[0].strip()
                                coord_part = part.split('(')[1].split(')')[0]
                                date_part = part.split('[')[1].split(']')[0] if '[' in part else None
                                
                                historical_data.append({
                                    'id': id_part,
                                    'coordinates': coord_part,
                                    'date': date_part
                                })
                            else:
                                historical_data.append(part)
                        processed_data[key] = historical_data
                    except:
                        processed_data[key] = value
                        
                elif key == 'street_names' and isinstance(value, str):
                    try:
                        if 'StreetLabel' in value:
                            name_match = value.split("name=en:")[1].split("'")[1] if "name=en:" in value else None
                            angles_match = value.split("angles=[")[1].split("]")[0] if "angles=[" in value else None
                            
                            street_info = {}
                            if name_match:
                                street_info['name'] = name_match
                            if angles_match:
                                try:
                                    angles = [float(angle) for angle in angles_match.split(', ')]
                                    street_info['angles'] = angles
                                except:
                                    street_info['angles'] = angles_match
                            
                            processed_data[key] = street_info
                        else:
                            processed_data[key] = value
                    except:
                        processed_data[key] = value
                        
                elif key == 'image_sizes' and isinstance(value, str):
                    try:
                        if 'Size(' in value:
                            sizes = []
                            size_parts = value.split('Size(')[1:]
                            for size_part in size_parts:
                                if 'x=' in size_part and 'y=' in size_part:
                                    x = size_part.split('x=')[1].split(',')[0]
                                    y = size_part.split('y=')[1].split(')')[0]
                                    sizes.append({'x': int(x), 'y': int(y)})
                            processed_data[key] = sizes
                        else:
                            processed_data[key] = value
                    except:
                        processed_data[key] = value
                        
                elif key == 'tile_size' and isinstance(value, str):
                    try:
                        if 'Size(' in value:
                            x = value.split('x=')[1].split(',')[0]
                            y = value.split('y=')[1].split(')')[0]
                            processed_data[key] = {'x': int(x), 'y': int(y)}
                        else:
                            processed_data[key] = value
                    except:
                        processed_data[key] = value
                        
                elif key == 'permalink' and callable(value):
                    try:
                        result = value()
                        processed_data[key] = result
                    except:
                        processed_data[key] = str(value)
                        
                else:
                    try:
                        json.dumps(value)
                        processed_data[key] = value
                    except (TypeError, ValueError):
                        processed_data[key] = str(value)
                        
            except Exception as e:
                print_warning(f"Error processing attribute '{key}': {e}")
                processed_data[key] = str(value)
        
        output_file = os.path.join(output_dir, "toronto_streetview_panorama.json")
        with open(output_file, 'w') as f:
            json.dump(processed_data, f, indent=2, default=str)
        
        print_success(f"Panorama data saved to: {output_file}")
        print_info(f"Saved {len(processed_data)} attributes:")
        for key in sorted(processed_data.keys()):
            value = processed_data[key]
            if isinstance(value, (list, dict)):
                print_info(f"  {key}: {type(value).__name__} with {len(value)} items")
            else:
                print_info(f"  {key}: {type(value).__name__}")
        
        if 'neighbors' in processed_data:
            neighbors = processed_data['neighbors']
            print_info(f"🔗 Neighbors: {len(neighbors) if isinstance(neighbors, list) else 'N/A'} items")
            if isinstance(neighbors, list) and len(neighbors) > 0:
                print_info(f"   First neighbor: {neighbors[0]}")
        
        if 'links' in processed_data:
            links = processed_data['links']
            print_info(f"🔗 Links: {len(links) if isinstance(links, list) else 'N/A'} items")
            if isinstance(links, list) and len(links) > 0:
                print_info(f"   First link: {links[0]}")
        
        return output_file
        
    except Exception as e:
        print_error(f"Error saving panorama data: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function for command-line usage."""
    # Setup logging
    logger = setup_logging()
    
    print_header("Toronto Street View Panorama Getter", "Find and save panorama data from Toronto's centerpoint")
    
    # Load Toronto boundary
    print_info("Loading Toronto boundary...")
    boundary_gdf = load_toronto_boundary()
    
    if boundary_gdf is None:
        print_error("Failed to load boundary data")
        return 1
    
    print_success("Boundary loaded successfully")
    
    # Get centerpoint
    centerpoint = get_boundary_centerpoint(boundary_gdf)
    if centerpoint is None:
        print_error("Failed to calculate centerpoint")
        return 1
    
    lat, lon = centerpoint
    print_info(f"📍 Centerpoint: {lat:.6f}, {lon:.6f}")
    
    # Find panorama
    print_info("🔍 Searching for Street View panorama...")
    panorama = find_panorama(lat=lat, lon=lon, radius=50)
    
    if panorama is None:
        print_error("No panorama found at centerpoint")
        return 1
    
    print_success(f"Found panorama: {panorama.id}")
    print_info(f"   Location: {panorama.lat:.6f}, {panorama.lon:.6f}")
    print_info(f"   Date: {panorama.date}")
    
    # Save panorama data
    print_info("💾 Saving panorama data...")
    output_file = save_panorama_data(panorama)
    
    if output_file:
        print_success(f"Panorama data saved to: {output_file}")
    else:
        print_error("Failed to save panorama data")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
