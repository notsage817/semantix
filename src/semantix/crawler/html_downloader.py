#!/usr/bin/env python3
"""
HTML Downloader Script

Downloads HTML pages from URLs specified in a JSON source file and saves them to a directory.
Supports the processed job URLs format from url_fetcher.py output.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import socket


class HTMLDownloader:
    """Downloads HTML content from URLs and saves to files."""
    
    def __init__(self, html_dump_dir: str, delay: float = 1.0, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the HTML downloader.
        
        Args:
            html_dump_dir: Directory to save HTML files
            delay: Delay between requests in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.html_dump_dir = Path(html_dump_dir)
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.html_dump_dir.mkdir(parents=True, exist_ok=True)
        
        # User agent to avoid being blocked
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def sanitize_filename(self, url: str, job_id: Optional[str] = None) -> str:
        """
        Create a safe filename from URL and job ID.
        
        Args:
            url: The URL to create filename from
            job_id: Optional job ID to include in filename
            
        Returns:
            Sanitized filename
        """
        parsed = urlparse(url)
        
        if job_id:
            base_name = f"{job_id}_{parsed.path.replace('/', '_')}"
        else:
            base_name = parsed.path.replace('/', '_')
        
        # Remove invalid characters for filenames
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            base_name = base_name.replace(char, '_')
        
        # Remove leading/trailing underscores and ensure .html extension
        base_name = base_name.strip('_')
        if not base_name.endswith('.html'):
            base_name += '.html'
            
        return base_name
    
    def download_html(self, url: str) -> Optional[str]:
        """
        Download HTML content from a URL with retry logic.
        
        Args:
            url: URL to download
            
        Returns:
            HTML content as string, or None if failed after all retries
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                request = Request(url, headers={'User-Agent': self.user_agent})
                with urlopen(request, timeout=self.timeout) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    if attempt > 0:
                        print(f"  Success on attempt {attempt + 1}")
                    return content
                    
            except socket.timeout as e:
                last_exception = f"Timeout after {self.timeout}s"
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"  Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    
            except HTTPError as e:
                last_exception = f"HTTP {e.code}: {e.reason}"
                if e.code >= 500 and attempt < self.max_retries:  # Retry on server errors
                    wait_time = 2 ** attempt
                    print(f"  Server error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break  # Don't retry on client errors (4xx)
                    
            except URLError as e:
                last_exception = f"URL error: {e.reason}"
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    print(f"  Network error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break
                    
            except Exception as e:
                last_exception = f"Unexpected error: {e}"
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    print(f"  Error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break
        
        print(f"Error downloading {url}: {last_exception}", file=sys.stderr)
        return None
    
    def process_urls_from_json(self, url_source_file: str) -> None:
        """
        Process URLs from a JSON source file and download HTML pages.
        
        Args:
            url_source_file: Path to JSON file containing URLs
        """
        try:
            with open(url_source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading source file {url_source_file}: {e}", file=sys.stderr)
            return
        
        # Extract URLs from the jobs array
        jobs = data.get('jobs', [])
        if not jobs:
            print("No jobs found in source file", file=sys.stderr)
            return
        
        total_jobs = len(jobs)
        print(f"Found {total_jobs} URLs to download")
        
        success_count = 0
        failed_count = 0
        
        for i, job in enumerate(jobs, 1):
            url = job.get('url')
            job_id = job.get('job_id', '')
            
            if not url:
                print(f"Skipping job {i}: No URL found", file=sys.stderr)
                failed_count += 1
                continue
            
            print(f"[{i}/{total_jobs}] Downloading: {url}")
            
            # Generate filename
            filename = self.sanitize_filename(url, job_id)
            filepath = self.html_dump_dir / filename
            
            # Skip if file already exists
            if filepath.exists():
                print(f"  Skipping: File already exists - {filename}")
                success_count += 1
                continue
            
            # Download HTML content
            html_content = self.download_html(url)
            
            if html_content:
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"  Saved: {filename}")
                    success_count += 1
                except IOError as e:
                    print(f"  Error saving {filename}: {e}", file=sys.stderr)
                    failed_count += 1
            else:
                failed_count += 1
            
            # Add delay between requests to be respectful
            if i < total_jobs:
                time.sleep(self.delay)
        
        print(f"\nDownload complete:")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total: {total_jobs}")


def main():
    """Main entry point for the HTML downloader script."""
    parser = argparse.ArgumentParser(
        description="Download HTML pages from URLs in a JSON source file"
    )
    parser.add_argument(
        "--url-source-file",
        required=True,
        help="Path to JSON file containing URLs (e.g., processed_job_urls.json)"
    )
    parser.add_argument(
        "--html-dump-dir",
        required=True,
        help="Directory to save downloaded HTML files"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts (default: 3)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate source file exists
    if not os.path.isfile(args.url_source_file):
        print(f"Error: Source file not found: {args.url_source_file}", file=sys.stderr)
        sys.exit(1)
    
    # Create downloader and process URLs
    downloader = HTMLDownloader(
        args.html_dump_dir, 
        args.delay, 
        args.timeout, 
        args.max_retries
    )
    downloader.process_urls_from_json(args.url_source_file)


if __name__ == "__main__":
    main()