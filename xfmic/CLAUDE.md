# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a documentation crawler project for archiving the AIUI documentation website (https://aiui-doc.xf-yun.com/project-1/doc-1/). The project consists of a Python-based web scraper that downloads and preserves documentation pages locally.

## Key Commands

### Install Dependencies
```bash
pip3 install -r requirements.txt
# Or: pip3 install requests beautifulsoup4 urllib3 lxml
```

### Run the Crawler
```bash
# Default mode: crawl navigation links only (recommended, faster)
python3 crawl_docs.py

# For recursive crawling of all links, edit crawl_docs.py main() function
# Replace spider.crawl() with spider.crawl_recursive(max_depth=3)
```

### Clean and Re-crawl
```bash
rm -rf docs && python3 crawl_docs.py
```

## Architecture

### Core Components

**crawl_docs.py** - Main crawler script with `DocsSpider` class:
- `parse_navigation()`: Parses left sidebar navigation menu from HTML using BeautifulSoup. Looks for `nav ul.summary` selector specifically for this documentation site.
- `get_file_path()`: Converts URLs to local file paths, preserving the URL structure (`/project-1/doc-123/` → `docs/project-1/doc-123.html`)
- `crawl()`: Default mode that only crawls links found in the navigation menu (154 pages)
- `crawl_recursive()`: Alternative mode for comprehensive crawling with depth limit

### Data Flow

1. Fetch base URL and extract navigation structure from sidebar
2. Parse all links matching `/project-1/doc-*` pattern
3. Download each page with 0.5s delay between requests
4. Save HTML files preserving URL path structure
5. Generate `_navigation.json` with complete navigation metadata

### Output Structure

```
docs/
├── _navigation.json        # Navigation metadata (url, text, href for 154 pages)
├── index.html              # Base URL page
├── project-1/
│   ├── doc-*.html         # Documentation pages
│   └── ...
└── [numbered].html         # Some pages map to root with numeric names
```

## Important Implementation Details

### SSL Certificate Handling
The target website has SSL certificate issues. The crawler disables SSL verification:
```python
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
response = self.session.get(url, verify=False, timeout=30)
```

### Navigation Parsing Strategy
The scraper specifically targets the documentation site's structure:
- Primary selector: `nav ul.summary`
- Filters links to only `/project-1/doc-*` paths
- Deduplicates URLs to avoid re-crawling
- Skips search links and empty text links

### File Path Mapping
URL to file path conversion handles:
- URL decoding for Chinese characters
- Unsafe filename character replacement
- Automatic `.html` extension addition
- Directory structure creation via `os.makedirs()`

## Configuration

Adjust these in `crawl_docs.py`:
- `output_dir`: Default is `docs/`
- `max_depth`: For recursive mode, default is 3
- Request delay: `time.sleep(0.5)` between pages
- User-Agent: Set to mimic browser requests
