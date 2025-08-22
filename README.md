# Toronto StreetView Crawler

A Python package for crawling Google Street View panoramas within Toronto's municipal boundaries.

## Features

- **Boundary Loading**: Download and load Toronto's municipal boundary from the Toronto Open Data portal
- **Panorama Discovery**: Find Street View panoramas at specific coordinates
- **Intelligent Crawling**: Crawl panoramas within Toronto's boundaries using neighbors and links
- **SQLite Storage**: Persistent storage with deduplication and metadata tracking
- **Resume Capability**: Continue crawling from where you left off

## Installation

### Quick Install

```bash
git clone https://github.com/yourusername/collect-streetview-data.git
cd collect-streetview-data
pip install -e .
```

### Manual Install

```bash
git clone https://github.com/yourusername/collect-streetview-data.git
cd collect-streetview-data
pip install -r requirements.txt
```

## Usage

### 1. Load Toronto Boundary

```bash
toronto-boundary
```

This will:
- Download Toronto's municipal boundary from the open data portal
- Save it in multiple formats (GeoJSON, Shapefile, GeoPackage)
- Create a visualization
- Calculate the centerpoint

### 2. Get a Single Panorama

```bash
toronto-panorama
```

This will:
- Load the Toronto boundary
- Find the centerpoint
- Search for the nearest Street View panorama
- Save all panorama metadata to JSON

### 3. Crawl Panoramas

```bash
toronto-crawl --max-new 100 --radius 50
```

This will:
- Start crawling from Toronto's centerpoint (if database is empty)
- Or continue from existing data (if resuming)
- Discover new panoramas via neighbors and links
- Only expand within Toronto's boundaries
- Store everything in SQLite

#### Crawler Options

- `--db`: Database file path (default: `streetview_toronto.db`)
- `--max-new`: Maximum new panoramas to process per run (default: 50)
- `--radius`: Initial search radius in meters (default: 50)
- `--extra-radii`: Comma-separated additional radii to try (default: "100,200")

## Package Structure

```
toronto_streetview_crawler/
├── __init__.py
├── load_boundary.py      # Boundary loading and processing
├── get_panorama.py       # Single panorama retrieval
└── crawl.py             # Panorama crawling engine
```

## Database Schema

The crawler uses SQLite with three main tables:

- **`panoramas`**: Stores panorama IDs, coordinates, and metadata status
- **`neighbors`**: Tracks neighbor relationships between panoramas
- **`links`**: Tracks link relationships between panoramas

## Memory Management

The crawler is designed to be memory-efficient:
- Processes one panorama at a time
- Uses streaming database operations
- Only loads the boundary polygon once
- Does not store the entire database in memory

## Dependencies

- `toronto-open-data`: Access Toronto's open data portal
- `geopandas`: Geospatial data handling
- `shapely`: Geometric operations
- `streetlevel`: Google Street View API access
- `matplotlib`: Visualization (optional)
- `sqlite3`: Database operations (built-in)

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Building Package

```bash
python setup.py sdist bdist_wheel
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Boundary download fails**: Check internet connection and Toronto Open Data portal status
2. **No panoramas found**: Try increasing the search radius
3. **Database errors**: Ensure write permissions in the current directory
4. **Import errors**: Make sure all dependencies are installed

### Getting Help

- Check the issue tracker for known problems
- Review the logs for error details
- Ensure you're using the latest version
