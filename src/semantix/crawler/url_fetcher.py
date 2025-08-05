#!/usr/bin/env python3
"""
URL Fetcher for job posting URLs using Scrapy-Playwright.

This script visits a company's career home page and extracts job posting URLs
based on patterns defined in a YAML configuration file.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from urllib.parse import ParseResult

import click
import scrapy
import yaml
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request, Response

# Global variable to store extraction results
extraction_results = {}


class JobUrlSpider(scrapy.Spider):
    """Spider to extract job posting URLs from company career pages."""

    name = "job_url_spider"

    def __init__(self, home_url: str = None, pattern_config: Dict[str, Any] = None, 
                 restart_from_page: Optional[int] = None, existing_data: Optional[Dict[str, Any]] = None, 
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.home_url = home_url
        self.pattern_config = pattern_config or {}
        self.restart_from_page = restart_from_page or 1
        self.job_urls: List[Dict[str, Any]] = []
        self.unique_urls = set()  # Track unique URLs across all pages
        self.pages_crawled = 0
        self.total_pages = None
        self.pagination_config = self.pattern_config.get("pagination", {})
        self.empty_pages_count = 0  # Track consecutive empty pages
        self.max_empty_pages = 5   # Stop if we hit too many empty pages in a row
        self.current_page_number = restart_from_page or 1  # Track current page for sequential processing
        
        # Load existing data if restarting
        if existing_data:
            self.job_urls = existing_data.get("jobs", [])
            self.unique_urls = {job["url"] for job in self.job_urls}
            self.pages_crawled = existing_data.get("total_pages_crawled", 0)
            self.logger.info(f"Loaded {len(self.job_urls)} existing job URLs from previous crawl")
        
        if home_url:
            self.base_domain = urlparse(home_url).netloc

    def start_requests(self):
        """Generate initial requests."""
        start_page = self.restart_from_page
        if start_page > 1:
            # If restarting from a specific page, build the URL for that page
            start_url = self._build_page_url(start_page)
        else:
            start_url = self.home_url
            
        yield Request(
            url=start_url,
            callback=self.parse,
            meta={
                "playwright": True, 
                "playwright_include_page": True, 
                "page_number": start_page,
                "playwright_page_goto_kwargs": {"timeout": 60000}
            },
        )

    async def parse(self, response: Response):
        """Parse the career page to extract job posting URLs."""
        current_page = response.meta.get("page_number", 1)
        
        try:
            page = response.meta["playwright_page"]
            self.logger.info(f"Processing page {current_page}")
            
            # Wait for dynamic content if specified
            if "wait_for" in self.pattern_config:
                wait_config = self.pattern_config["wait_for"]
                try:
                    if wait_config.get("type") == "selector":
                        await page.wait_for_selector(wait_config["value"], timeout=15000)
                    elif wait_config.get("type") == "timeout":
                        await page.wait_for_timeout(wait_config["value"])
                except Exception as e:
                    self.logger.warning(f"Page {current_page}: Wait condition failed: {e}")

            # Check if there's a next page by examining the next button status
            has_next_page = False
            if self.pagination_config.get("enabled", False):
                try:
                    has_next_page = await self._check_next_page_available(page)
                    self.logger.info(f"Page {current_page}: Next page available: {has_next_page}")
                except Exception as e:
                    self.logger.error(f"Page {current_page}: Failed to check next page availability: {e}")
                    
            # After processing current page, generate request for next page sequentially
            if has_next_page:
                next_page = current_page + 1
                
                # Add delay between pages to be respectful
                await page.wait_for_timeout(2000)  # 2 second delay between pages
                
                next_page_url = self._build_page_url(next_page)
                self.logger.info(f"Queuing next page: {next_page}")
                
                yield Request(
                    url=next_page_url,
                    callback=self.parse,
                    meta={
                        "playwright": True, 
                        "playwright_include_page": True, 
                        "page_number": next_page,
                        "playwright_page_goto_kwargs": {"timeout": 60000}
                    },
                    dont_filter=True,  # Allow duplicate URLs for different pages
                )
            else:
                self.logger.info(f"Page {current_page}: No more pages available. Crawling complete.")

            # Extract job posting URLs from current page
            page_jobs = []
            try:
                page_jobs = self._extract_jobs_from_page(response)
            except Exception as e:
                self.logger.error(f"Page {current_page}: Job extraction failed: {e}")
            
            # Add unique jobs to our collection
            new_jobs_count = 0
            for job_data in page_jobs:
                if job_data["url"] not in self.unique_urls:
                    self.unique_urls.add(job_data["url"])
                    self.job_urls.append(job_data)
                    new_jobs_count += 1
            
            # Track empty pages for early termination
            if len(page_jobs) == 0:
                self.empty_pages_count += 1
                self.logger.warning(f"Page {current_page}: Empty page detected ({self.empty_pages_count}/{self.max_empty_pages})")
                if self.empty_pages_count >= self.max_empty_pages:
                    self.logger.error(f"Too many consecutive empty pages ({self.empty_pages_count}). Stopping crawl.")
                    # Note: In Scrapy, we can't easily stop the entire crawl from here,
                    # but this will help with debugging
            else:
                self.empty_pages_count = 0  # Reset counter on successful page
            
            self.pages_crawled += 1
            self.logger.info(f"Page {current_page}: Found {len(page_jobs)} total jobs, {new_jobs_count} new unique jobs. Total unique: {len(self.job_urls)}")
            
            # Update global results
            global extraction_results
            extraction_results["jobs"] = self.job_urls
            extraction_results["total_jobs"] = len(self.job_urls)
            extraction_results["total_pages_crawled"] = self.pages_crawled
            extraction_results["total_pages_attempted"] = self.total_pages or "unknown"
            extraction_results["extraction_timestamp"] = datetime.now().isoformat()

        except Exception as e:
            self.logger.error(f"Page {current_page}: Critical error during parsing: {e}")
        finally:
            # Always close the page
            try:
                page = response.meta.get("playwright_page")
                if page:
                    await page.close()
            except Exception as e:
                self.logger.warning(f"Page {current_page}: Error closing page: {e}")

    async def _detect_total_pages(self, page, response: Response) -> Optional[int]:
        """Detect total number of pages from pagination elements."""
        detection_config = self.pagination_config.get("page_detection", {})
        method = detection_config.get("method", "selector")
        
        if method == "selector":
            # Try to find pagination info using CSS selectors
            selector = detection_config.get("selector", "")
            if selector:
                elements = response.css(selector)
                if elements:
                    # Try to extract page numbers from text
                    text_pattern = detection_config.get("text_pattern", r"Page \d+ of (\d+)")
                    for element in elements:
                        text = element.get()
                        if text:
                            match = re.search(text_pattern, text)
                            if match:
                                return int(match.group(1))
            
            # Alternative: look for individual page links
            page_links = response.css("a[href*='page=']::attr(href)").getall()
            if page_links:
                max_page = 0
                for link in page_links:
                    match = re.search(r'page=(\d+)', link)
                    if match:
                        max_page = max(max_page, int(match.group(1)))
                if max_page > 0:
                    return max_page
                    
            # Try to detect "last" page link
            last_page_links = response.css("a[href*='page=']:contains('Last'), a[href*='page=']:contains('»')::attr(href)").getall()
            if last_page_links:
                for link in last_page_links:
                    match = re.search(r'page=(\d+)', link)
                    if match:
                        return int(match.group(1))
        
        elif method == "manual":
            # Use manually specified max pages
            return self.pagination_config.get("max_pages", 1)
        
        # Fallback: try to detect by looking for "next" button and following pagination
        return await self._detect_pages_by_navigation(page, response)
    
    async def _detect_pages_by_navigation(self, page, response: Response) -> Optional[int]:
        """Detect total pages by checking if next button exists and following pagination."""
        detection_config = self.pagination_config.get("page_detection", {})
        next_selector = detection_config.get("next_button_selector", ".pagination .next, .pager .next")
        
        # For now, let's limit to a reasonable number to avoid infinite loops
        # In a production system, you might want to actually navigate through pages
        max_reasonable_pages = 200  # Safety limit
        
        # Check if there's a next button (indicates more pages)
        next_elements = response.css(next_selector)
        if next_elements:
            # For Apple specifically, let's try to find the page number pattern in the URL or page
            # This is a heuristic approach - we'll look for patterns that suggest many pages
            page_text = response.text
            
            # Look for patterns like "1-20 of 3380 results" or similar
            results_pattern = r'(\d+)-(\d+) of (\d+)'
            match = re.search(results_pattern, page_text)
            if match:
                total_results = int(match.group(3))
                results_per_page = int(match.group(2)) - int(match.group(1)) + 1
                total_pages = (total_results + results_per_page - 1) // results_per_page
                return min(total_pages, max_reasonable_pages)
        
        return 1  # Default to single page if we can't detect
    
    async def _check_next_page_available(self, page) -> bool:
        """Check if next page is available by examining the next button status."""
        try:
            next_button_selector = self.pagination_config.get("next_button_selector", 'button[data-analytics-pagination="next"]')
            disabled_attribute = self.pagination_config.get("next_button_disabled_attribute", "disabled")
            
            # Wait for pagination elements to load
            try:
                await page.wait_for_selector(next_button_selector, timeout=5000)
            except Exception:
                self.logger.warning("Next button selector not found, assuming no more pages")
                return False
            
            # Check if next button is disabled
            next_button = await page.query_selector(next_button_selector)
            if not next_button:
                self.logger.warning("Next button element not found")
                return False
            
            # Check if the disabled attribute is present
            is_disabled = await next_button.get_attribute(disabled_attribute)
            if is_disabled is not None:
                self.logger.info(f"Next button is disabled: {disabled_attribute}='{is_disabled}'")
                return False
                
            # Also check aria-disabled attribute as a fallback
            aria_disabled = await next_button.get_attribute("aria-disabled")
            if aria_disabled == "true":
                self.logger.info(f"Next button is aria-disabled: aria-disabled='{aria_disabled}'")
                return False
            
            self.logger.info("Next button is enabled, more pages available")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking next page availability: {e}")
            return False
    
    def _build_page_url(self, page_number: int) -> str:
        """Build URL for a specific page number.
        
        Special case: If page_number is 1 and home_url doesn't have page parameter,
        return home_url as-is (some sites don't use page parameter for first page).
        """
        page_param = self.pagination_config.get("page_param", "page")
        
        # Parse the original URL
        parsed_url = urlparse(self.home_url)
        query_params = parse_qs(parsed_url.query)
        
        # Special case: if requesting page 1 and home URL doesn't have page parameter,
        # return home URL as-is (first page might not need page parameter)
        if page_number == 1 and page_param not in query_params:
            return self.home_url
        
        # Add or update the page parameter
        query_params[page_param] = [str(page_number)]
        
        # Rebuild the query string
        new_query = urlencode(query_params, doseq=True)
        
        # Rebuild the URL
        new_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return new_url
    
    def _extract_jobs_from_page(self, response: Response) -> List[Dict[str, Any]]:
        """Extract job data from a single page."""
        page_jobs = []
        selectors = self.pattern_config.get("job_url_selectors", [])
        
        for selector_config in selectors:
            selector = selector_config["selector"]
            attribute = selector_config.get("attribute", "href")
            
            # Get elements matching the selector
            elements = response.css(selector)
            
            for element in elements:
                # Extract URL from specified attribute
                if attribute == "text":
                    url = element.get()
                else:
                    url = element.attrib.get(attribute)
                
                if url:
                    # Convert relative URLs to absolute
                    full_url = urljoin(self.home_url, url)
                    
                    # Filter out non-job URLs
                    if not self._is_job_url(full_url):
                        continue
                    
                    # Extract metadata
                    metadata = self._extract_metadata(element, selector_config)
                    
                    job_data = {
                        "url": full_url,
                        "title": metadata.get("title", ""),
                        "location": metadata.get("location", ""),
                        "department": metadata.get("department", ""),
                        "job_type": metadata.get("job_type", ""),
                        "posted_date": metadata.get("posted_date", ""),
                        "company": self.pattern_config.get("company_name", ""),
                        "source_url": response.url,
                        "metadata": metadata,
                    }
                    
                    page_jobs.append(job_data)
        
        return page_jobs

    def _is_job_url(self, url: str) -> bool:
        """Check if URL is a valid job posting URL."""
        # Filter out common non-job URLs
        exclude_patterns = [
            '.pdf',
            '.jpg', '.jpeg', '.png', '.gif',
            'locationPicker',
            '/apply/',
            '/profile/',
            '/search',
            '/filter',
            'javascript:',
            'mailto:',
            'tel:',
            '#'
        ]
        
        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # For Apple specifically, check for job detail URLs
        if 'jobs.apple.com' in url_lower and '/details/' in url_lower:
            return True
        
        # General job URL patterns
        job_patterns = [
            '/job/', '/jobs/', '/career/', '/careers/',
            '/position/', '/positions/', '/opening/', '/openings/',
            '/details/', '/listing/', '/apply'
        ]
        
        for pattern in job_patterns:
            if pattern in url_lower:
                return True
        
        return False

    def _extract_metadata(self, element, selector_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from job listing element."""
        metadata = {}
        
        # Extract metadata based on configuration
        metadata_config = selector_config.get("metadata", {})
        
        # Handle None or empty metadata config
        if not metadata_config:
            return metadata
        
        for field, field_config in metadata_config.items():
            try:
                if isinstance(field_config, str):
                    # Simple CSS selector
                    field_element = element.css(field_config)
                    if field_element:
                        metadata[field] = field_element.get().strip()
                elif isinstance(field_config, dict):
                    # Complex selector with attribute specification
                    field_selector = field_config["selector"]
                    field_attribute = field_config.get("attribute", "text")
                    
                    field_element = element.css(field_selector)
                    
                    if field_element:
                        if field_attribute == "text":
                            value = field_element.get()
                        else:
                            value = field_element.attrib.get(field_attribute)
                        
                        if value:
                            # Apply text transformations if specified
                            if "transform" in field_config:
                                transform = field_config["transform"]
                                if transform == "strip":
                                    value = value.strip()
                                elif transform == "lower":
                                    value = value.lower()
                                elif transform == "upper":
                                    value = value.upper()
                            
                            metadata[field] = value
            except Exception as e:
                # Silently continue on metadata extraction errors
                continue
        
        return metadata


def load_pattern_config(pattern_file: Path) -> Dict[str, Any]:
    """Load and validate pattern configuration from YAML file."""
    try:
        with open(pattern_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = ["job_url_selectors"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in pattern configuration")
        
        return config
    
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")
    except FileNotFoundError:
        raise ValueError(f"Pattern file not found: {pattern_file}")


@click.command()
@click.option(
    "--home-url",
    required=True,
    help="The home URL of the company's career page to crawl",
)
@click.option(
    "--output-file",
    required=True,
    type=click.Path(),
    help="Path to the output JSON file",
)
@click.option(
    "--pattern-yaml",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML configuration file with extraction patterns",
)
@click.option(
    "--user-agent",
    default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    help="User agent string to use for requests",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--restart-from-page",
    type=int,
    default=None,
    help="Restart crawling from a specific page number (useful for resuming failed crawls)",
)
def main(
    home_url: str,
    output_file: str,
    pattern_yaml: str,
    user_agent: str,
    verbose: bool,
    restart_from_page: Optional[int],
) -> None:
    """
    Fetch job posting URLs from company career pages using Scrapy-Playwright.
    
    This tool visits the specified home URL and extracts job posting URLs
    based on patterns defined in the YAML configuration file.
    """
    try:
        # Load pattern configuration
        pattern_config = load_pattern_config(Path(pattern_yaml))
        
        # Load existing data if restarting from a specific page
        existing_data = None
        if restart_from_page and restart_from_page > 1:
            output_path = Path(output_file)
            if output_path.exists():
                try:
                    with open(output_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    click.echo(f"Loaded existing data: {existing_data.get('total_jobs', 0)} jobs from {existing_data.get('total_pages_crawled', 0)} pages")
                    click.echo(f"Restarting from page {restart_from_page}")
                except Exception as e:
                    click.echo(f"Warning: Could not load existing data: {e}", err=True)
                    existing_data = None
        
        # Configure Scrapy settings
        settings = {
            "USER_AGENT": user_agent,
            "ROBOTSTXT_OBEY": True,
            "DOWNLOAD_HANDLERS": {
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "headless": True,
            },
            "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,  # 60 seconds
            "PLAYWRIGHT_DEFAULT_TIMEOUT": 60000,  # 60 seconds
            "DOWNLOAD_TIMEOUT": 60,  # 60 seconds
            "LOG_LEVEL": "DEBUG" if verbose else "INFO",
            "CONCURRENT_REQUESTS": 1,  # Be respectful to the server  
            "DOWNLOAD_DELAY": 5,  # Increase delay to avoid rate limiting
            "RANDOMIZE_DOWNLOAD_DELAY": 0.5,  # Add randomness to delays
            "RETRY_TIMES": 3,  # Retry failed requests
            "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],  # Add timeout and rate limit codes
            "SCHEDULER_PRIORITY_QUEUE": "scrapy.pqueues.ScrapyPriorityQueue",  # Ensure FIFO order
            "DEPTH_PRIORITY": 1,  # Process requests in depth order (sequential)
        }
        
        # Global variable to store results
        global extraction_results
        if existing_data:
            # Start with existing data when restarting
            extraction_results = existing_data.copy()
        else:
            extraction_results = {
                "source_url": home_url,
                "total_jobs": 0,
                "extraction_timestamp": "",
                "company_name": pattern_config.get("company_name", ""),
                "jobs": [],
            }
        
        # Create and run spider
        process = CrawlerProcess(settings=settings)
        
        # Pass spider class and arguments instead of instance
        process.crawl(
            JobUrlSpider, 
            home_url=home_url, 
            pattern_config=pattern_config,
            restart_from_page=restart_from_page,
            existing_data=existing_data
        )
        process.start()
        
        # Save results to JSON file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = extraction_results
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        click.echo(f"Successfully extracted {results['total_jobs']} job URLs")
        click.echo(f"Results saved to: {output_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()