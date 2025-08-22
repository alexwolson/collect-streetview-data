#!/usr/bin/env python3
"""
Crawl Google Street View panoramas within Toronto's boundary.
"""

import sqlite3
import argparse
import sys
import time
from datetime import datetime
from shapely.geometry import Point
from streetlevel.streetview import find_panorama, find_panorama_by_id
from .load_boundary import load_toronto_boundary, get_boundary_centerpoint
from .logging_config import (
    setup_logging, print_header, print_success, print_error, print_info, 
    print_warning, print_panorama_stats, create_progress_bar, console
)


def init_db(conn):
    """Initialize the database with required tables."""
    try:
        # Check if we need to migrate existing schema
        try:
            # Check if old schema exists (neighbors table with old column names)
            old_schema = conn.execute("PRAGMA table_info(neighbors)").fetchall()
            has_old_schema = any(col[1] == 'from_id' for col in old_schema)
            
            if has_old_schema:
                print_info("Detected existing database schema, migrating...")
                # Drop old tables and recreate with new schema
                conn.execute("DROP TABLE IF EXISTS neighbors")
                conn.execute("DROP TABLE IF EXISTS links")
                conn.execute("DROP TABLE IF EXISTS panoramas")
                print_info("Dropped old tables, recreating with new schema...")
                
                # Create new simplified table structure
                conn.execute("""
                    CREATE TABLE panoramas (
                        id TEXT PRIMARY KEY,
                        lat REAL,
                        lon REAL,
                        metadata_populated INTEGER DEFAULT 0,
                        within_boundary INTEGER,
                        neighbors_expanded INTEGER DEFAULT 0,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
            else:
                # Check if panoramas table exists but needs the new column
                try:
                    conn.execute("SELECT neighbors_expanded FROM panoramas LIMIT 1")
                    print_info("Database schema is up to date")
                except sqlite3.OperationalError:
                    print_info("Adding neighbors_expanded column to existing panoramas table...")
                    conn.execute("ALTER TABLE panoramas ADD COLUMN neighbors_expanded INTEGER DEFAULT 0")
                    print_success("Column added successfully")
                
                # Create tables if they don't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS panoramas (
                        id TEXT PRIMARY KEY,
                        lat REAL,
                        lon REAL,
                        metadata_populated INTEGER DEFAULT 0,
                        within_boundary INTEGER,
                        neighbors_expanded INTEGER DEFAULT 0,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_metadata ON panoramas (metadata_populated)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_boundary ON panoramas (within_boundary)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_expanded ON panoramas (neighbors_expanded)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_panoramas_created ON panoramas (created_at)")
            
            conn.commit()
            print_success("Database schema initialized successfully")
            
        except Exception as e:
            print_error(f"Error during migration: {e}")
            # Try to create tables without indexes first
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS panoramas (
                        id TEXT PRIMARY KEY,
                        lat REAL,
                        lon REAL,
                        metadata_populated INTEGER DEFAULT 0,
                        within_boundary INTEGER,
                        neighbors_expanded INTEGER DEFAULT 0,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
                
                conn.commit()
                print_success("Basic tables created (without indexes)")
                
            except Exception as e2:
                print_error(f"Failed to create basic tables: {e2}")
                raise
                
    except Exception as e:
        print_error(f"Error initializing database: {e}")
        raise


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
    
    # Update the panorama record with metadata
    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE panoramas 
        SET lat = ?, lon = ?, updated_at = ?
        WHERE id = ?
    """, (panorama.lat, panorama.lon, now, panorama.id))
    
    print_info(f"Metadata extracted for {panorama.id}: {len(metadata)} fields")


def get_db_stats(conn):
    """Get current database statistics."""
    try:
        total = conn.execute("SELECT COUNT(*) FROM panoramas").fetchone()[0]
        populated = conn.execute("SELECT COUNT(*) FROM panoramas WHERE metadata_populated = 1").fetchone()[0]
        within_boundary = conn.execute("SELECT COUNT(*) FROM panoramas WHERE within_boundary = 1").fetchone()[0]
        expanded = conn.execute("SELECT COUNT(*) FROM panoramas WHERE neighbors_expanded = 1").fetchone()[0]
        return total, populated, within_boundary, expanded
    except Exception as e:
        print_error(f"Error getting stats: {e}")
        return 0, 0, 0, 0


def expand_panorama_neighbors(conn, panorama, boundary_polygon):
    """Expand panorama by adding its neighbors to the queue (without storing edges)."""
    new_neighbors_count = 0
    
    # Process neighbors
    for neighbor in panorama.neighbors:
        point = Point(neighbor.lon, neighbor.lat)
        within = 1 if point.within(boundary_polygon) else 0
        now = datetime.utcnow().isoformat()
        
        # Add to panoramas table if new
        cursor = conn.execute("""
            INSERT OR IGNORE INTO panoramas (id, lat, lon, metadata_populated, within_boundary, neighbors_expanded, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (neighbor.id, neighbor.lat, neighbor.lon, 0, within, 0, now, now))
        
        if cursor.rowcount > 0:
            new_neighbors_count += 1
    
    # Mark this panorama as expanded
    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE panoramas SET neighbors_expanded = 1, updated_at = ? WHERE id = ?", (now, panorama.id))
    
    return new_neighbors_count


def main():
    """Main function for command-line usage."""
    # Setup logging
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description="Crawl Google Street View panoramas within Toronto's boundary.")
    parser.add_argument("--db", default="streetview_toronto.db", help="SQLite database file.")
    parser.add_argument("--max-new", type=int, default=50, help="Maximum number of new panoramas to process in one run.")
    parser.add_argument("--radius", type=int, default=50, help="Initial search radius for the starting panorama.")
    parser.add_argument("--extra-radii", type=str, default="100,200", help="Comma-separated list of additional radii to try if initial search fails.")
    args = parser.parse_args()

    print_header("Toronto Street View Crawler", f"DB: {args.db} | Max New: {args.max_new} | Radii: {[args.radius] + [int(r) for r in args.extra_radii.split(',') if r]}")

    conn = sqlite3.connect(args.db)
    init_db(conn)

    boundary_gdf = load_toronto_boundary()
    if boundary_gdf is None:
        print_error("Failed to load boundary data. Exiting.")
        sys.exit(1)
    
    # Combine all geometries into a single polygon for efficient checking
    boundary_polygon = boundary_gdf.geometry.unary_union

    # Seed the crawl if the database is empty
    if conn.execute("SELECT COUNT(*) FROM panoramas").fetchone()[0] == 0:
        print_info("Seeding crawl with Toronto centerpoint...")
        centerpoint = get_boundary_centerpoint(boundary_gdf)
        if centerpoint is None:
            print_error("Failed to calculate centerpoint. Exiting.")
            sys.exit(1)
        lat, lon = centerpoint
        
        radii = [args.radius] + [int(r) for r in args.extra_radii.split(',') if r]
        start_panorama = None
        for r in radii:
            print_info(f"Searching for initial panorama near {lat:.6f}, {lon:.6f} with radius {r}m...")
            start_panorama = find_panorama(lat=lat, lon=lon, radius=r)
            if start_panorama:
                break
        
        if start_panorama:
            within = 1 if Point(start_panorama.lon, start_panorama.lat).within(boundary_polygon) else 0
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO panoramas (id, lat, lon, metadata_populated, within_boundary, neighbors_expanded, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (start_panorama.id, start_panorama.lat, start_panorama.lon, 0, within, 0, now, now))
            conn.commit()
            print_success(f"Seeded start panorama: {start_panorama.id} at {start_panorama.lat:.6f}, {start_panorama.lon:.6f} (within={within})")
        else:
            print_error("Could not find a starting panorama. Exiting.")
            sys.exit(1)
    else:
        print_info("Using existing database as seed")

    # Show initial statistics
    print_panorama_stats(conn)

    # Create progress bar
    progress = create_progress_bar()
    
    processed_count = 0
    start_time = time.time()
    
    with progress:
        # Create the main task
        task = progress.add_task(
            "[cyan]Processing panoramas...", 
            total=args.max_new,
            start=True
        )
        
        while processed_count < args.max_new:
            # Get a panorama that needs metadata populated or neighbors expanded
            cursor = conn.execute("""
                SELECT id, lat, lon, within_boundary
                FROM panoramas
                WHERE metadata_populated = 0 OR (within_boundary = 1 AND neighbors_expanded = 0)
                ORDER BY within_boundary DESC, created_at ASC
                LIMIT 1
            """)
            row = cursor.fetchone()

            if not row:
                print_info("No more panoramas to process.")
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
                print_info(f"Checked boundary for {pano_id}: within_boundary={within_boundary_flag}")

            # Load panorama metadata if not already populated
            if conn.execute("SELECT metadata_populated FROM panoramas WHERE id = ?", (pano_id,)).fetchone()[0] == 0:
                print_info(f"Populating metadata for {pano_id}...")
                try:
                    panorama = find_panorama_by_id(pano_id)
                    if panorama:
                        save_panorama_metadata_to_db(conn, panorama)
                        conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                                    (datetime.utcnow().isoformat(), pano_id))
                        conn.commit()
                        # print_success(f"Metadata populated for {pano_id}")
                    else:
                        print_warning(f"Could not retrieve panorama {pano_id} by ID. Marking as populated to avoid retries.")
                        conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                                    (datetime.utcnow().isoformat(), pano_id))
                        conn.commit()
                except Exception as e:
                    print_error(f"Error populating metadata for {pano_id}: {e}")
                    # Mark as populated to avoid infinite retries on persistent errors
                    conn.execute("UPDATE panoramas SET metadata_populated = 1, updated_at = ? WHERE id = ?",
                                (datetime.utcnow().isoformat(), pano_id))
                    conn.commit()
                    
            # Only expand neighbors if the panorama is within the boundary and hasn't been expanded
            if within_boundary_flag == 1 and conn.execute("SELECT neighbors_expanded FROM panoramas WHERE id = ?", (pano_id,)).fetchone()[0] == 0:
                print_info(f"Expanding from {pano_id} (within boundary)...")
                try:
                    panorama = find_panorama_by_id(pano_id) # Re-fetch if not already in memory
                    if panorama:
                        new_neighbors = expand_panorama_neighbors(conn, panorama, boundary_polygon)
                        conn.commit()
                        print_info(f"Added {new_neighbors} new neighbors for {pano_id}")
                    else:
                        print_warning(f"Could not retrieve panorama {pano_id} for expansion.")
                except Exception as e:
                    print_error(f"Error expanding from {pano_id}: {e}")
            
            processed_count += 1
            
            # Update progress bar with current statistics
            total, populated, within_boundary, expanded = get_db_stats(conn)
            progress.update(
                task, 
                description=f"[cyan]Processing panoramas... [green]{populated}/{total} populated [yellow]• [blue]{within_boundary} in boundary [yellow]• [magenta]{expanded} expanded",
                completed=processed_count
            )
            
            # Show statistics every 10 panoramas
            if processed_count % 10 == 0:
                print_panorama_stats(conn)

    # Final statistics
    elapsed_time = time.time() - start_time
    print_success(f"Crawling complete! Processed {processed_count} panoramas in {elapsed_time:.1f} seconds")
    print_panorama_stats(conn)
    
    conn.close()


if __name__ == "__main__":
    exit(main())
