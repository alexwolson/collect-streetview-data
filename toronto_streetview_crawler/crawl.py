#!/usr/bin/env python3
"""
Crawl Google Street View panoramas within Toronto's boundary.
"""

import sqlite3
import argparse
import sys
from datetime import datetime
from shapely.geometry import Point
from streetlevel.streetview import find_panorama, find_panorama_by_id
from .load_boundary import load_toronto_boundary, get_boundary_centerpoint


def init_db(conn):
    """Initialize the database with required tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS panoramas (
            id TEXT PRIMARY KEY,
            lat REAL,
            lon REAL,
            metadata_populated INTEGER DEFAULT 0,
            within_boundary INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS neighbors (
            from_pano_id TEXT,
            to_pano_id TEXT,
            created_at TEXT,
            PRIMARY KEY (from_pano_id, to_pano_id),
            FOREIGN KEY (from_pano_id) REFERENCES panoramas (id),
            FOREIGN KEY (to_pano_id) REFERENCES panoramas (id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            from_pano_id TEXT,
            to_pano_id TEXT,
            direction TEXT,
            created_at TEXT,
            PRIMARY KEY (from_pano_id, to_pano_id),
            FOREIGN KEY (from_pano_id) REFERENCES panoramas (id),
            FOREIGN KEY (to_pano_id) REFERENCES panoramas (id)
        )
    """)
    
    # Create indexes for better performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_metadata ON panoramas (metadata_populated)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_boundary ON panoramas (within_boundary)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_created ON panoramas (created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_neighbors_from ON neighbors (from_pano_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_from ON links (from_pano_id)")
    
    conn.commit()


def save_panorama_metadata_to_db(conn, panorama):
    """Save panorama metadata to the database."""
    # Extract basic metadata
    metadata = {
        'id': panorama.id,
        'lat': panorama.lat,
        'lon': panorama.lon,
        'date': getattr(panorama, 'date', None),
        'heading': getattr(panorama, 'heading', None),
        'pitch': getattr(panorama, 'pitch', None),
        'roll': getattr(panorama, 'roll', None),
        'address': getattr(panorama, 'address', None),
        'country_code': getattr(panorama, 'country_code', None),
        'source': getattr(panorama, 'source', None),
        'is_third_party': getattr(panorama, 'is_third_party', None),
        'upload_date': getattr(panorama, 'upload_date', None),
        'artworks': getattr(panorama, 'artworks', None),
        'building_level': getattr(panorama, 'building_level', None),
        'building_levels': getattr(panorama, 'building_levels', None),
        'copyright_message': getattr(panorama, 'copyright_message', None),
        'depth': getattr(panorama, 'depth', None),
        'elevation': getattr(panorama, 'elevation', None),
        'historical': getattr(panorama, 'historical', None),
        'image_sizes': getattr(panorama, 'image_sizes', None),
        'neighbors': getattr(panorama, 'neighbors', None),
        'links': getattr(panorama, 'links', None),
        'permalink': getattr(panorama, 'permalink', None),
        'places': getattr(panorama, 'places', None),
        'street_names': getattr(panorama, 'street_names', None),
        'tile_size': getattr(panorama, 'tile_size', None),
        'uploader': getattr(panorama, 'uploader', None),
        'uploader_icon_url': getattr(panorama, 'uploader_icon_url', None)
    }
    
    # Convert to JSON string for storage
    import json
    metadata_json = json.dumps(metadata, default=str)
    
    # Update the panorama record with metadata
    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE panoramas 
        SET lat = ?, lon = ?, updated_at = ?
        WHERE id = ?
    """, (panorama.lat, panorama.lon, now, panorama.id))
    
    # Store full metadata in a separate table or as JSON in the main table
    # For now, we'll just update the basic fields and mark as populated
    print(f"Metadata extracted for {panorama.id}: {len(metadata)} fields")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Crawl Google Street View panoramas within Toronto's boundary.")
    parser.add_argument("--db", default="streetview_toronto.db", help="SQLite database file.")
    parser.add_argument("--max-new", type=int, default=50, help="Maximum number of new panoramas to process in one run.")
    parser.add_argument("--radius", type=int, default=50, help="Initial search radius for the starting panorama.")
    parser.add_argument("--extra-radii", type=str, default="100,200", help="Comma-separated list of additional radii to try if initial search fails.")
    args = parser.parse_args()

    print("Toronto Street View Crawler")
    print("=" * 50)
    print(f"DB: {args.db}")
    print(f"Max new: {args.max_new}")
    print(f"Radii: {[args.radius] + [int(r) for r in args.extra_radii.split(',') if r]}")

    conn = sqlite3.connect(args.db)
    init_db(conn)

    boundary_gdf = load_toronto_boundary()
    if boundary_gdf is None:
        print("❌ Failed to load boundary data. Exiting.")
        sys.exit(1)
    
    # Combine all geometries into a single polygon for efficient checking
    # DeprecationWarning: The 'unary_union' attribute is deprecated, use the 'union_all()' method instead.
    boundary_polygon = boundary_gdf.geometry.unary_union

    # Seed the crawl if the database is empty
    if conn.execute("SELECT COUNT(*) FROM panoramas").fetchone()[0] == 0:
        print("Seeding crawl with Toronto centerpoint...")
        centerpoint = get_boundary_centerpoint(boundary_gdf)
        if centerpoint is None:
            print("❌ Failed to calculate centerpoint. Exiting.")
            sys.exit(1)
        lat, lon = centerpoint
        
        radii = [args.radius] + [int(r) for r in args.extra_radii.split(',') if r]
        start_panorama = None
        for r in radii:
            print(f"Searching for initial panorama near {lat:.6f}, {lon:.6f} with radius {r}m...")
            start_panorama = find_panorama(lat=lat, lon=lon, radius=r)
            if start_panorama:
                break
        
        if start_panorama:
            within = 1 if Point(start_panorama.lon, start_panorama.lat).within(boundary_polygon) else 0
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO panoramas (id, lat, lon, metadata_populated, within_boundary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (start_panorama.id, start_panorama.lat, start_panorama.lon, 0, within, now, now))
            conn.commit()
            print(f"Seeded start panorama: {start_panorama.id} at {start_panorama.lat:.6f}, {start_panorama.lon:.6f} (within={within})")
        else:
            print("❌ Could not find a starting panorama. Exiting.")
            sys.exit(1)
    else:
        print("Using existing database as seed")

    processed_count = 0
    while processed_count < args.max_new:
        # Get a panorama that needs metadata populated or neighbors/links expanded
        # Prioritize panoramas within the boundary for expansion
        cursor = conn.execute("""
            SELECT id, lat, lon, within_boundary
            FROM panoramas
            WHERE metadata_populated = 0 OR (within_boundary = 1 AND id NOT IN (SELECT from_pano_id FROM neighbors))
            ORDER BY within_boundary DESC, created_at ASC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if not row:
            print("No more panoramas to process.")
            break

        pano_id, lat, lon, within_boundary_flag = row
        
        # Check if within_boundary_flag is None (meaning it hasn't been checked yet)
        if within_boundary_flag is None:
            point = Point(lon, lat)
            within_boundary_flag = 1 if point.within(boundary_polygon) else 0
            now = datetime.utcnow().isoformat()
            conn.execute("UPDATE panoramas SET within_boundary = ?, updated_at = ? WHERE id = ?",
                        (within_boundary_flag, now, pano_id))
            conn.commit()
            print(f"Checked boundary for {pano_id}: within_boundary={within_boundary_flag}")

        # Load panorama metadata if not already populated
        if conn.execute("SELECT metadata_populated FROM panoramas WHERE id = ?", (pano_id,)).fetchone()[0] == 0:
            print(f"Populating metadata for {pano_id}...")
            try:
                panorama = find_panorama_by_id(pano_id)
                if panorama:
                    save_panorama_metadata_to_db(conn, panorama)
                    conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                                (datetime.utcnow().isoformat(), pano_id))
                    conn.commit()
                    print(f"Metadata populated for {pano_id}")
                else:
                    print(f"Warning: Could not retrieve panorama {pano_id} by ID. Marking as populated to avoid retries.")
                    conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                                (datetime.utcnow().isoformat(), pano_id))
                    conn.commit()
            except Exception as e:
                print(f"Error populating metadata for {pano_id}: {e}")
                # Mark as populated to avoid infinite retries on persistent errors
                conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                            (datetime.utcnow().isoformat(), pano_id))
                conn.commit()
                
        # Only expand neighbors/links if the panorama is within the boundary
        if within_boundary_flag == 1:
            # Check if neighbors/links have already been processed for this panorama
            if conn.execute("SELECT COUNT(*) FROM neighbors WHERE from_pano_id = ?", (pano_id,)).fetchone()[0] == 0:
                print(f"Expanding from {pano_id} (within boundary)...")
                try:
                    panorama = find_panorama_by_id(pano_id) # Re-fetch if not already in memory
                    if panorama:
                        # Add neighbors to queue
                        for neighbor in panorama.neighbors:
                            point = Point(neighbor.lon, neighbor.lat)
                            within = 1 if point.within(boundary_polygon) else 0
                            now = datetime.utcnow().isoformat()
                            conn.execute("""
                                INSERT OR IGNORE INTO panoramas (id, lat, lon, metadata_populated, within_boundary, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (neighbor.id, neighbor.lat, neighbor.lon, 0, within, now, now))
                            conn.execute("INSERT OR IGNORE INTO neighbors (from_pano_id, to_pano_id, created_at) VALUES (?, ?, ?)",
                                        (pano_id, neighbor.id, now))
                        conn.commit()
                        print(f"Added {len(panorama.neighbors)} neighbors for {pano_id}")

                        # Add links to queue
                        for link in panorama.links:
                            # The pano object in link might not have lat/lon directly, so we only store the link itself
                            # The target pano will be discovered via neighbors or a separate search if needed
                            target_pano_id = str(link.pano).split(' (')[0] if ' (' in str(link.pano) else str(link.pano)
                            now = datetime.utcnow().isoformat()
                            conn.execute("""
                                INSERT OR IGNORE INTO links (from_pano_id, to_pano_id, direction, created_at)
                                VALUES (?, ?, ?, ?)
                            """, (pano_id, target_pano_id, link.direction, now))
                        conn.commit()
                        print(f"Added {len(panorama.links)} links for {pano_id}")
                    else:
                        print(f"Warning: Could not retrieve panorama {pano_id} for expansion.")
                except Exception as e:
                    print(f"Error expanding from {pano_id}: {e}")
        
        processed_count += 1
        if processed_count % 25 == 0:
            print(f"Populated {processed_count} panoramas...")

    print("Done.")
    conn.close()


if __name__ == "__main__":
    exit(main())
