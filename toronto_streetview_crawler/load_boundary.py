#!/usr/bin/env python3
"""
Load Toronto boundary data using the toronto-open-data library.
"""

import os
import zipfile
import tempfile
import geopandas as gpd
from toronto_open_data import TorontoOpenData
import matplotlib.pyplot as plt
from .logging_config import setup_logging, print_header, print_success, print_error, print_info, console


def load_toronto_boundary():
    """
    Load Toronto's boundary shapefile using the toronto-open-data library.
    
    Returns:
        geopandas.GeoDataFrame: Toronto boundary data
    """
    try:
        client = TorontoOpenData()
        print_info("Loading Toronto boundary data...")
        dataset_id = '841fb820-46d0-46ac-8dcb-d20f27e57bcc'
        print_info("Downloading boundary dataset...")
        downloaded_data = client.download_dataset(dataset_id)
        
        if not downloaded_data:
            print_info("No data downloaded. Checking cache...")
            cache_path = f"cache/{dataset_id}/toronto-boundary-wgs84"
            if os.path.exists(cache_path):
                print_info(f"Found cached data at: {cache_path}")
                return load_shapefile_from_zip(cache_path)
            else:
                print_info("No cached data found")
                return None
        
        print_info(f"Downloaded {len(downloaded_data)} resources")
        cache_path = f"cache/{dataset_id}/toronto-boundary-wgs84"
        if os.path.exists(cache_path):
            print_info(f"Loading from cache: {cache_path}")
            return load_shapefile_from_zip(cache_path)
        else:
            print_info("Cache path not found")
            return None
    except Exception as e:
        print_error(f"Error loading Toronto boundary data: {e}")
        return None


def load_shapefile_from_zip(zip_path):
    """
    Load a shapefile from a zip file.
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print_info(f"Extracting shapefile to temporary directory: {temp_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if not shp_files:
                print_error("No .shp file found in zip")
                return None
            shp_file = os.path.join(temp_dir, shp_files[0])
            print_info(f"Loading shapefile: {shp_file}")
            gdf = gpd.read_file(shp_file)
            print_success(f"Successfully loaded boundary data with {len(gdf)} features")
            print_info(f"Columns: {list(gdf.columns)}")
            print_info(f"CRS: {gdf.crs}")
            return gdf
    except Exception as e:
        print_error(f"Error loading shapefile from zip: {e}")
        return None


def get_boundary_centerpoint(boundary_gdf):
    """
    Calculate the centerpoint of the boundary.
    
    Args:
        boundary_gdf (geopandas.GeoDataFrame): Boundary data
        
    Returns:
        tuple: (latitude, longitude) of the centerpoint
    """
    if boundary_gdf is None or len(boundary_gdf) == 0:
        return None
    
    # Get the centroid of the first geometry
    centroid = boundary_gdf.geometry.iloc[0].centroid
    return (centroid.y, centroid.x)  # (lat, lon)


def visualize_boundary(boundary_gdf, save_path=None):
    """
    Visualize the boundary data.
    
    Args:
        boundary_gdf (geopandas.GeoDataFrame): Boundary data
        save_path (str, optional): Path to save the plot
    """
    if boundary_gdf is None:
        print_error("No boundary data to visualize")
        return
    
    try:
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        boundary_gdf.plot(ax=ax, edgecolor='black', facecolor='lightblue', alpha=0.7)
        
        # Add centerpoint
        centerpoint = get_boundary_centerpoint(boundary_gdf)
        if centerpoint:
            lat, lon = centerpoint
            ax.plot(lon, lat, 'ro', markersize=10, label=f'Center: ({lat:.6f}, {lon:.6f})')
            ax.legend()
        
        ax.set_title('Toronto Municipal Boundary')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print_success(f"Boundary visualization saved to: {save_path}")
        
        plt.show()
    except Exception as e:
        print_error(f"Visualization failed: {e}")


def save_boundary_data(boundary_gdf, output_dir="output"):
    """
    Save boundary data in multiple formats.
    
    Args:
        boundary_gdf (geopandas.GeoDataFrame): Boundary data
        output_dir (str): Output directory
    """
    if boundary_gdf is None:
        print_error("No boundary data to save")
        return
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Save as GeoJSON
        geojson_path = os.path.join(output_dir, "toronto_boundary.geojson")
        boundary_gdf.to_file(geojson_path, driver='GeoJSON')
        print_success(f"Boundary data saved as GeoJSON: {geojson_path}")
        
        # Save as Shapefile
        shp_path = os.path.join(output_dir, "toronto_boundary.shp")
        boundary_gdf.to_file(shp_path, driver='ESRI Shapefile')
        print_success(f"Boundary data saved as Shapefile: {shp_path}")
        
        # Save as GeoPackage
        gpkg_path = os.path.join(output_dir, "toronto_boundary.gpkg")
        boundary_gdf.to_file(gpkg_path, driver='GPKG')
        print_success(f"Boundary data saved as GeoPackage: {gpkg_path}")
        
    except Exception as e:
        print_error(f"Error saving boundary data: {e}")


def main():
    """Main function for command-line usage."""
    # Setup logging
    logger = setup_logging()
    
    print_header("Toronto Boundary Loader", "Download and process Toronto's municipal boundary")
    
    # Load boundary data
    boundary_gdf = load_toronto_boundary()
    
    if boundary_gdf is None:
        print_error("Failed to load boundary data")
        return 1
    
    print_success("Boundary loaded successfully")
    
    # Get centerpoint
    centerpoint = get_boundary_centerpoint(boundary_gdf)
    if centerpoint:
        lat, lon = centerpoint
        print_info(f"📍 Centerpoint: {lat:.6f}, {lon:.6f}")
    
    # Save data
    save_boundary_data(boundary_gdf)
    
    # Visualize (optional - comment out if running headless)
    try:
        visualize_boundary(boundary_gdf, "output/toronto_boundary.png")
    except Exception as e:
        print_warning(f"Visualization failed (this is normal in headless environments): {e}")
    
    print_success("Boundary data processing complete!")
    return 0


if __name__ == "__main__":
    exit(main())
