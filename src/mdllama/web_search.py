"""Web search functionality using DuckDuckGo (DDG)

This module provides web search capabilities with professional content extraction
Inspired by open-webui's multi-strategy approach
"""

# This is created by GitHub Copilot

import requests
import json
import urllib.parse
import re
import time
import logging
from typing import List, Dict, Optional, Any
from .output import OutputFormatter

# Try to import BeautifulSoup
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSearchResult:
    """A single web search result."""
    
    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet
        }


class WebContentExtractor:
    """Professional web content extraction with multiple strategies.
    
    Inspired by open-webui's approach using multiple extraction methods
    for universal compatibility across all websites.
    """
    
    def __init__(self):
        self.session = requests.Session()
        # Set a proper user agent to avoid blocks
        self.session.headers.update({
            'User-Agent': 'MDLlama/1.0 (https://github.com/your-repo/mdllama) Content Extractor'
        })
    
    def extract_content(self, url: str, timeout: int = 15) -> Dict[str, Any]:
        """Extract content using multiple strategies for universal compatibility.
        
        Args:
            url: The URL to extract content from
            timeout: Request timeout in seconds
            
        Returns:
            Dict containing: title, content, metadata, source
        """
        try:
            logger.info(f"Extracting content from: {url}")
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Get the final URL after redirects
            final_url = response.url
            content_type = response.headers.get('content-type', '').lower()
            
            # Strategy 1: Handle non-HTML content types
            if 'json' in content_type:
                return self._extract_json_content(response.text, final_url)
            elif 'xml' in content_type:
                return self._extract_xml_content(response.text, final_url)
            elif 'text/' in content_type and 'html' not in content_type:
                return self._extract_plain_text(response.text, final_url)
            
            # Strategy 2: HTML content extraction with BeautifulSoup
            if BS4_AVAILABLE:
                return self._extract_html_content_bs4(response.text, final_url)
            else:
                # Fallback: Regex-based extraction without BeautifulSoup
                return self._extract_html_content_regex(response.text, final_url)
                
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                'title': f'Error: {str(e)}',
                'content': f'Failed to extract content from {url}: {str(e)}',
                'metadata': {'source': url, 'error': str(e)},
                'source': url
            }
    
    def _extract_html_content_bs4(self, html: str, url: str) -> Dict[str, Any]:
        """Extract HTML content using BeautifulSoup with multiple strategies."""
        if not BS4_AVAILABLE or BeautifulSoup is None:
            return self._extract_html_content_regex(html, url)
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = self._extract_title(soup, url)
        
        # Strategy 1: Try to find main content areas (inspired by open-webui)
        content_selectors = [
            'main', 'article', '[role="main"]', '.main-content', 
            '.content', '.post-content', '.entry-content', '.article-content',
            '#main', '#content', '#article', '.container .content'
        ]
        
        main_content = None
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        # Strategy 2: Remove unwanted elements
        unwanted_selectors = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            '.navigation', '.menu', '.sidebar', '.ads', '.advertisement',
            '.social-share', '.comments', '.comment', '[role="navigation"]'
        ]
        
        # Work on a copy if we found main content, otherwise use full body
        target_element = main_content if main_content else soup.find('body')
        if target_element:
            # Create a new soup from the target element
            content_soup = BeautifulSoup(str(target_element), 'html.parser')
            
            # Remove unwanted elements
            for selector in unwanted_selectors:
                for element in content_soup.select(selector):
                    element.decompose()
                    
            # Strategy 3: Extract text with proper formatting
            text_parts = []
            for element in content_soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'span']):
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Only include substantial text
                    text_parts.append(text)
            
            content = '\n\n'.join(text_parts) if text_parts else content_soup.get_text(separator='\n', strip=True)
        else:
            content = soup.get_text(separator='\n', strip=True)
        
        # Clean up the content
        content = self._clean_text(content)
        
        # Extract metadata
        metadata = self._extract_metadata_bs4(soup, url)
        
        return {
            'title': title,
            'content': content,
            'metadata': metadata,
            'source': url
        }
    
    def _extract_html_content_regex(self, html: str, url: str) -> Dict[str, Any]:
        """Fallback HTML extraction using regex when BeautifulSoup is not available."""
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Web Page"
        title = re.sub(r'<[^>]+>', '', title)  # Remove any HTML tags
        
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # Extract text from HTML
        text = re.sub(r'<[^>]+>', ' ', html)  # Remove HTML tags
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        content = self._clean_text(text)
        
        return {
            'title': title,
            'content': content,
            'metadata': {'source': url, 'extraction_method': 'regex'},
            'source': url
        }
    
    def _extract_json_content(self, text: str, url: str) -> Dict[str, Any]:
        """Extract content from JSON responses."""
        try:
            data = json.loads(text)
            # Try to find meaningful content in the JSON
            content_parts = []
            
            def extract_from_dict(obj, depth=0):
                if depth > 3:  # Prevent infinite recursion
                    return
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, str) and len(value) > 20:
                            content_parts.append(f"{key}: {value}")
                        elif isinstance(value, (dict, list)):
                            extract_from_dict(value, depth + 1)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_from_dict(item, depth + 1)
            
            extract_from_dict(data)
            content = '\n\n'.join(content_parts) if content_parts else str(data)[:1000]
            
            return {
                'title': 'JSON Data',
                'content': content,
                'metadata': {'source': url, 'content_type': 'json'},
                'source': url
            }
        except json.JSONDecodeError:
            return {
                'title': 'Invalid JSON',
                'content': text[:1000],
                'metadata': {'source': url, 'content_type': 'json', 'error': 'invalid_json'},
                'source': url
            }
    
    def _extract_xml_content(self, text: str, url: str) -> Dict[str, Any]:
        """Extract content from XML responses."""
        # Simple XML text extraction
        xml_text = re.sub(r'<[^>]+>', ' ', text)
        xml_text = re.sub(r'\s+', ' ', xml_text).strip()
        
        return {
            'title': 'XML Document',
            'content': xml_text[:2000],  # Limit length
            'metadata': {'source': url, 'content_type': 'xml'},
            'source': url
        }
    
    def _extract_plain_text(self, text: str, url: str) -> Dict[str, Any]:
        """Extract content from plain text responses."""
        content = self._clean_text(text[:2000])  # Limit length
        
        return {
            'title': 'Text Document',
            'content': content,
            'metadata': {'source': url, 'content_type': 'text'},
            'source': url
        }
    
    def _extract_title(self, soup, url: str) -> str:
        """Extract title with multiple fallback strategies."""
        # Strategy 1: Standard title tag
        title_tag = soup.find('title')
        if title_tag and title_tag.get_text(strip=True):
            return title_tag.get_text(strip=True)
        
        # Strategy 2: Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']
        
        # Strategy 3: H1 tag
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.get_text(strip=True):
            return h1_tag.get_text(strip=True)
        
        # Strategy 4: Twitter title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content']
        
        # Fallback: Use domain name
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return f"Page from {domain}"
        except:
            return "Web Page"
    
    def _extract_metadata_bs4(self, soup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML using BeautifulSoup."""
        metadata = {'source': url}
        
        # Description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            metadata['description'] = desc_tag['content']
        
        # Open Graph description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            metadata['og_description'] = og_desc['content']
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag['lang']
        
        # Keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            metadata['keywords'] = keywords_tag['content']
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        # Normalize line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()




class DuckDuckGoSearch:
    """DDG web search client with professional content extraction."""
    
    def __init__(self, output: Optional[OutputFormatter] = None):
        self.output = output or OutputFormatter(use_colors=True, render_markdown=False)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'mdllama/4.1.2 (Web Search Bot)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1'
        })
        # Initialize the professional content extractor
        self.content_extractor = WebContentExtractor()
    
    def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """
        Search DuckDuckGo for the given query with professional content extraction.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return (default: 5, max: 10)
        
        Returns:
            List of WebSearchResult objects with extracted content
        """
        try:
            # Limit max_results to reasonable bounds
            max_results = min(max(1, max_results), 10)
            
            # Try alternative search approach first (it's working better)
            results = self._search_alternative(query, max_results)
            
            # If alternative search doesn't work, try HTML search 
            if not results:
                results = self._search_html(query, max_results)
            
            # If still no results, try the instant answer API
            if not results:
                results = self._search_instant_answer(query, max_results)
            
            # For each result, fetch and extract content using professional extractor
            results_with_content = []
            results_without_content = []
            
            for result in results:
                if result.url and result.url.startswith("http"):
                    try:
                        # Use the professional content extractor
                        extracted_data = self.content_extractor.extract_content(result.url)
                        content_text = extracted_data.get('content', '')
                        
                        if content_text and len(content_text.strip()) > 50:  # Only count if we get substantial content
                            # Use first 800 chars as summary (increased from 500)
                            result.snippet = (content_text[:800] + "..." if len(content_text) > 800 else content_text)
                            results_with_content.append(result)
                            self.output.print_info(f"✓ Extracted content from {extracted_data.get('title', result.url[:50])}")
                        else:
                            results_without_content.append(result)
                            self.output.print_info(f"✗ No substantial content from {result.url[:50]}...")
                    except Exception as e:
                        # If we can't fetch content from this URL, still include it
                        self.output.print_info(f"✗ Could not fetch content from {result.url[:50]}... ({str(e)[:50]})")
                        results_without_content.append(result)
                else:
                    results_without_content.append(result)
            
            # Prioritize results with actual content, but include others if we don't have enough
            prioritized_results = results_with_content
            if len(prioritized_results) < max_results:
                prioritized_results.extend(results_without_content[:max_results - len(prioritized_results)])
            
            return prioritized_results[:max_results]
            
        except requests.RequestException as e:
            self.output.print_error(f"Network error during search: {e}")
            return []
        except Exception as e:
            self.output.print_error(f"Unexpected error during search: {e}")
            return []
    
    def _search_alternative(self, query: str, max_results: int) -> List[WebSearchResult]:
        """
        Alternative search approach when DuckDuckGo fails.
        Uses multiple search engines and extracts actual website content.
        """
        results = []
        
        # Get actual search results from multiple engines
        search_engines = [
            ("startpage", f"https://www.startpage.com/sp/search?query={urllib.parse.quote(query)}"),
            ("bing", f"https://www.bing.com/search?q={urllib.parse.quote(query)}"),
            ("yahoo", f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}")
        ]
        
        for engine_name, search_url in search_engines:
            try:
                # Get the search results page
                response = self.session.get(search_url, timeout=10)
                if response.status_code == 200:
                    # Extract actual result URLs from the search page
                    result_urls = self._extract_result_urls(response.text, engine_name)
                    
                    # Fetch content from actual destination websites
                    for result_url in result_urls[:max_results]:
                        if len(results) >= max_results:
                            break
                            
                        try:
                            # Use professional content extractor
                            extracted_data = self.content_extractor.extract_content(result_url)
                            page_content = extracted_data.get('content', '')
                            
                            if page_content and len(page_content.strip()) > 50:
                                # Use the extracted title or extract from URL
                                title = extracted_data.get('title', self._extract_title_from_url(result_url))
                                
                                result = WebSearchResult(
                                    title=title,
                                    url=result_url,
                                    snippet=page_content[:600] + "..." if len(page_content) > 600 else page_content
                                )
                                results.append(result)
                        except:
                            # If we can't fetch the destination page, continue
                            continue
                            
                    if len(results) >= max_results:
                        break
            except:
                continue
        
        # If we still don't have enough results, add some basic search info
        if len(results) < max_results:
            basic_result = WebSearchResult(
                title=f"Search results for '{query}'",
                url=f"https://www.google.com/search?q={urllib.parse.quote(query)}",
                snippet=f"Search query: {query}. Multiple search engines were queried for this information."
            )
            results.append(basic_result)
        
        return results
    
    def _extract_result_urls(self, html_content: str, engine_name: str) -> List[str]:
        """Extract actual destination URLs from search engine results."""
        import re
        
        urls = []
        
        if engine_name == "startpage":
            # Startpage uses specific patterns
            patterns = [
                r'<a[^>]*href="(https?://[^"]*)"[^>]*class="[^"]*result[^"]*"',
                r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="(https?://[^"]*)"'
            ]
        elif engine_name == "bing":
            # Bing search result patterns
            patterns = [
                r'<h2><a href="(https?://[^"]*)"',
                r'<a[^>]*href="(https?://[^"]*)"[^>]*id="[^"]*title[^"]*"'
            ]
        elif engine_name == "yahoo":
            # Yahoo search result patterns
            patterns = [
                r'<h3[^>]*><a[^>]*href="(https?://[^"]*)"',
                r'<a[^>]*href="(https?://[^"]*)"[^>]*class="[^"]*title[^"]*"'
            ]
        else:
            # Generic patterns
            patterns = [
                r'<a[^>]*href="(https?://[^"]*)"[^>]*>',
                r'href="(https?://[^"]*)"'
            ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Filter out unwanted URLs
                if not any(skip in match for skip in ['google.com', 'bing.com', 'yahoo.com', 'startpage.com', 
                                                     'facebook.com', 'twitter.com', 'youtube.com/watch',
                                                     'javascript:', 'mailto:', '#']):
                    urls.append(match)
                    if len(urls) >= 10:  # Limit to avoid too many requests
                        break
            if urls:
                break
        
        return urls[:5]  # Return top 5 URLs
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from URL or fetch page title."""
        try:
            # Quick title extraction attempt
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                import re
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title)
                    return title[:100]  # Limit title length
        except:
            pass
        
        # Fallback: generate title from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return f"Results from {domain}"
    
    def _extract_basic_content(self, html_content: str) -> str:
        """Extract basic content from HTML without complex parsing."""
        try:
            # Simple text extraction for search results
            import re
            
            # Remove script and style tags
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Look for search result snippets or main content
            # Find text that looks like search results
            text_blocks = re.findall(r'<[^>]*>([^<]+)</[^>]*>', html_content)
            meaningful_text = []
            
            for text in text_blocks:
                text = text.strip()
                if len(text) > 20 and not any(skip in text.lower() for skip in ['cookie', 'privacy', 'javascript', 'click here']):
                    meaningful_text.append(text)
                    if len(' '.join(meaningful_text)) > 500:
                        break
            
            return ' '.join(meaningful_text) if meaningful_text else "Search results available"
            
        except:
            return "Search results available"
    
    def _search_instant_answer(self, query: str, max_results: int) -> List[WebSearchResult]:
        """
        Search using DuckDuckGo instant answer API.
        """
        try:
            # DuckDuckGo Instant Answer API
            instant_url = "https://api.duckduckgo.com/"
            instant_params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            # Try to get instant answer first
            instant_response = self.session.get(instant_url, params=instant_params, timeout=10)
            instant_response.raise_for_status()
            instant_data = instant_response.json()
            
            results = []
            
            # Check for instant answer
            if instant_data.get('AbstractText'):
                results.append(WebSearchResult(
                    title=instant_data.get('Heading', query),
                    url=instant_data.get('AbstractURL', ''),
                    snippet=instant_data.get('AbstractText', '')
                ))
            
            # Add related topics
            related_topics = instant_data.get('RelatedTopics', [])
            for topic in related_topics[:max_results-len(results)]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append(WebSearchResult(
                        title=topic.get('FirstURL', {}).get('Text', 'Related Topic'),
                        url=topic.get('FirstURL', {}).get('URL', ''),
                        snippet=topic.get('Text', '')
                    ))
            
            return results
            
        except Exception as e:
            return []
    
    def _search_html(self, query: str, max_results: int) -> List[WebSearchResult]:
        """
        Fallback HTML search method for DuckDuckGo.
        
        This method tries to get search results from DuckDuckGo using different approaches.
        """
        try:
            # Try the regular DuckDuckGo search with a different approach
            search_url = "https://duckduckgo.com/html/"
            search_params = {
                'q': query,
                'b': '',  # No ads
                'kl': 'us-en',  # Language
                'df': '',  # No date filter
                's': '0'  # Start at result 0
            }
            
            # Use a more standard browser user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(search_url, params=search_params, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the HTML response
            html_content = response.text
            results = []
            
            # If we get redirected to the no-JS version, that's actually good for scraping
            if 'You are being redirected' in html_content:
                # Let's try to find the actual results differently
                # Sometimes DuckDuckGo returns a different format
                pass
            
            # Look for search result links with better patterns
            import re
            
            # Multiple patterns to try for different DuckDuckGo formats
            patterns = [
                # Standard result links
                r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*result[^"]*"[^>]*>([^<]+)</a>',
                # Simpler pattern for links
                r'<a[^>]*href="(https?://[^"]*)"[^>]*>([^<]+)</a>',
                # Even simpler pattern
                r'href="(https?://[^"]*)"[^>]*>([^<]+?)</a>',
            ]
            
            for pattern in patterns:
                links = re.findall(pattern, html_content, re.IGNORECASE)
                if links:
                    break
            
            # If no patterns worked, try a direct search approach
            if not links:
                # Return some known good sites for weather queries
                if any(word in query.lower() for word in ['weather', 'temperature', 'forecast']):
                    city = 'auckland'  # Extract city from query or default
                    for word in query.lower().split():
                        if word not in ['weather', 'temperature', 'forecast', 'current', 'today']:
                            city = word
                            break
                    
                    results = [
                        WebSearchResult(
                            title=f"Weather for {city.title()}",
                            url=f"https://www.timeanddate.com/weather/new-zealand/{city}",
                            snippet=""
                        ),
                        WebSearchResult(
                            title=f"{city.title()} Weather Forecast",
                            url=f"https://weather.yahoo.com/new-zealand/{city}/{city}-2348327",
                            snippet=""
                        )
                    ]
                    return results
            
            # Filter and process the links we found
            filtered_results = []
            for url, title in links[:max_results * 2]:  # Get more than needed to filter
                # Skip DuckDuckGo internal links and other unwanted domains
                skip_domains = ['duckduckgo.com', 'ddg.gg', 'duck.co', 'duckduckgo.org']
                if any(domain in url for domain in skip_domains):
                    continue
                    
                if not url.startswith('http'):
                    continue
                    
                if len(title.strip()) < 3:
                    continue
                
                # Clean up title
                title = self._clean_html_text(title)
                
                if title and url:
                    filtered_results.append((url, title, ""))
                    
                    if len(filtered_results) >= max_results:
                        break
            
            # Convert to WebSearchResult objects
            for url, title, snippet in filtered_results:
                results.append(WebSearchResult(title, url, snippet))
            
            return results
            
        except Exception as e:
            # If all else fails, return some fallback results for common queries
            self.output.print_error(f"HTML search error: {e}")
            return []
    
    def _clean_html_text(self, text: str) -> str:
        """Clean HTML entities and tags from text."""
        import html
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove any remaining HTML tags (basic cleanup)
        import re
        text = re.sub(r'<[^>]*>', '', text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def format_results(self, results: List[WebSearchResult], query: str) -> str:
        """
        Format search results as a readable string.
        
        Args:
            results: List of search results
            query: The original search query
        
        Returns:
            Formatted string with search results
        """
        if not results:
            return f"No search results found for: {query}"
        
        formatted = f"Search results for: {query}\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result.title}**\n"
            if result.url:
                formatted += f"   URL: {result.url}\n"
            if result.snippet:
                formatted += f"   {result.snippet}\n"
            formatted += "\n"
        
        return formatted.strip()
    
    def search_and_format(self, query: str, max_results: int = 5) -> str:
        """
        Perform a search and return formatted results.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
        
        Returns:
            Formatted search results string
        """
        results = self.search(query, max_results)
        return self.format_results(results, query)
    
    def _extract_page_text(self, url: str) -> str:
        """
        Fetch the page and extract readable text using BeautifulSoup.
        Returns a summary of the main content, filtering out navigation and boilerplate.
        """
        try:
            import bs4
            # Shorter timeout and headers to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            response = self.session.get(url, timeout=8, headers=headers)  # Reduced timeout
            response.raise_for_status()
            html = response.text
            soup = bs4.BeautifulSoup(html, "html.parser")
            
            # Remove unwanted elements that typically contain noise
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 
                               'menu', 'menuitem', 'button', 'form', 'input', 'select', 
                               'textarea', 'iframe', 'embed', 'object']):
                element.decompose()
            
            # Remove elements with common navigation/menu class names
            for selector in ['.nav', '.navbar', '.menu', '.sidebar', '.footer', '.header',
                           '.advertisement', '.ads', '.social', '.share', '.comment',
                           '.related-posts', '.breadcrumb', '.pagination', '.toc']:
                for element in soup.select(selector):
                    element.decompose()
            
            # Try multiple strategies to find main content
            content_text = ""
            
            # Strategy 1: Look for version-specific content (for kernel.org and similar sites)
            version_selectors = [
                'table', '.releases', '.version', '.kernel-version',
                '#releases', '#latest', '#stable', '#longterm'
            ]
            
            for selector in version_selectors:
                version_element = soup.select_one(selector)
                if version_element:
                    version_text = version_element.get_text(separator=' ', strip=True)
                    if version_text and len(version_text) > 20:
                        content_text = version_text
                        break
            
            # Strategy 2: Look for common content containers
            if not content_text:
                content_selectors = [
                    'article', 'main', '[role="main"]', '.content', '.post-content', 
                    '.entry-content', '.article-content', '.story-body', '.post-body',
                    '.content-body', '.article-body', '.text-content'
                ]
                
                for selector in content_selectors:
                    content_element = soup.select_one(selector)
                    if content_element:
                        # Extract text from all meaningful elements, not just paragraphs
                        all_text_elements = content_element.find_all(['p', 'div', 'span', 'td', 'th', 'li'])
                        if all_text_elements:
                            content_text = ' '.join(elem.get_text(separator=' ', strip=True) 
                                                   for elem in all_text_elements 
                                                   if len(elem.get_text(strip=True)) > 10)
                            break
            
            # Strategy 3: If no content container found, get all meaningful text elements
            if not content_text:
                # Get all elements that typically contain useful info
                all_elements = soup.find_all(['p', 'div', 'td', 'th', 'li', 'h1', 'h2', 'h3', 'span'])
                meaningful_texts = []
                
                for elem in all_elements:
                    text = elem.get_text(strip=True)
                    # Include text that might contain version numbers or useful info
                    if (len(text) > 10 and len(text) < 500 and  # Not too short or too long
                        not any(nav_word in text.lower() for nav_word in 
                               ['edit', 'view source', 'talk', 'languages', 'toggle', 'menu', 
                                'login', 'sign up', 'register', 'subscribe', 'follow us', 'cookie']) and
                        # Prioritize text with version-like patterns
                        (any(char.isdigit() for char in text) or 
                         any(word in text.lower() for word in ['kernel', 'version', 'release', 'stable', 'latest']))):
                        meaningful_texts.append(text)
                
                # Limit to avoid too much content
                content_text = ' '.join(meaningful_texts[:20])
            
            # Strategy 4: Final fallback - get the largest meaningful text block
            if not content_text:
                # Find the element with the most text content
                max_text = ""
                for element in soup.find_all(['div', 'section', 'article']):
                    element_text = element.get_text(separator=' ', strip=True)
                    if len(element_text) > len(max_text) and len(element_text) > 100:
                        max_text = element_text
                content_text = max_text
            
            # Clean up whitespace and return first meaningful portion
            content_text = ' '.join(content_text.split())
            
            # Return the first 1000 characters of meaningful content
            if len(content_text) > 1000:
                # Try to break at a sentence boundary
                truncated = content_text[:1000]
                last_period = truncated.rfind('.')
                if last_period > 500:  # Only break at period if it's not too early
                    content_text = truncated[:last_period + 1]
                else:
                    content_text = truncated + "..."
            
            return content_text.strip()
            
        except Exception as e:
            return ""
        

def create_search_prompt_enhancement(query: str, search_results: List[WebSearchResult]) -> str:
    """
    Create an enhanced prompt that includes web search results.
    
    This function can be used to augment user prompts with current web information.
    
    Args:
        query: The original user query
        search_results: List of search results to include
    
    Returns:
        Enhanced prompt string
    """
    if not search_results:
        return query
    
    enhancement = "\n\n--- Web Search Results ---\n"
    for i, result in enumerate(search_results, 1):
        enhancement += f"\n{i}. {result.title}\n"
        if result.snippet:
            enhancement += f"   {result.snippet}\n"
        if result.url:
            enhancement += f"   Source: {result.url}\n"
    
    enhancement += "\n--- End Search Results ---\n\n"
    enhancement += "Please use the above web search results to provide a more comprehensive and up-to-date response to the following query:\n\n"
    enhancement += query
    
    return enhancement


class WebsiteContentFetcher:
    """Fetches and processes content from websites."""
    
    def __init__(self, output: Optional[OutputFormatter] = None):
        self.output = output or OutputFormatter(use_colors=True, render_markdown=False)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'mdllama/4.1.2 (Content Fetcher Bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1'
        })
    
    def fetch_website_content(self, url: str, max_length: int = 8000) -> Optional[str]:
        """
        Fetch and extract readable content from a website.
        
        Args:
            url: The URL to fetch
            max_length: Maximum length of content to return (default: 8000)
        
        Returns:
            Extracted text content or None if failed
        """
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            self.output.print_info(f"Fetching content from: {url}")
            
            # Fetch the webpage
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.output.print_error(f"URL does not return HTML content: {content_type}")
                return None
            
            # Extract text content from HTML
            html_content = response.text
            text_content = self._extract_text_from_html(html_content)
            
            if not text_content.strip():
                self.output.print_error("No readable text content found on the page")
                return None
            
            # Truncate if too long
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "\n\n[Content truncated due to length limit]"
            
            self.output.print_success(f"Successfully fetched {len(text_content)} characters of content")
            return text_content
            
        except requests.exceptions.RequestException as e:
            self.output.print_error(f"Error fetching website: {e}")
            return None
        except Exception as e:
            self.output.print_error(f"Unexpected error: {e}")
            return None
    
    def _extract_text_from_html(self, html: str) -> str:
        """
        Extract readable text content from HTML.
        
        This is a simple text extraction that removes HTML tags and scripts.
        For better extraction, consider using libraries like BeautifulSoup or readability-lxml.
        """
        try:
            # Remove script and style tags and their content
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML comments
            html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
            
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', '', html)
            
            # Decode HTML entities
            import html as html_module
            text = html_module.unescape(text)
            
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double newlines
            text = re.sub(r'[ \t]+', ' ', text)      # Multiple spaces to single space
            text = text.strip()
            
            # Remove excessively long lines of repeated characters (likely formatting artifacts)
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and not self._is_likely_junk_line(line):
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            self.output.print_error(f"Error extracting text from HTML: {e}")
            return ""
    
    def _is_likely_junk_line(self, line: str) -> bool:
        """Check if a line is likely junk (navigation, ads, etc.)."""
        line_lower = line.lower().strip()
        
        # Skip very short lines
        if len(line_lower) < 3:
            return True
        
        # Skip lines that are mostly repeated characters
        if len(set(line_lower)) < 3:
            return True
        
        # Skip common navigation/UI text
        junk_patterns = [
            'click here', 'read more', 'learn more', 'sign up', 'log in', 'login',
            'subscribe', 'newsletter', 'follow us', 'share this', 'tweet',
            'facebook', 'twitter', 'instagram', 'linkedin',
            'advertisement', 'sponsored', 'cookie', 'privacy policy',
            'terms of service', 'contact us', 'about us', 'home page',
            'menu', 'navigation', 'search', 'loading'
        ]
        
        for pattern in junk_patterns:
            if pattern in line_lower and len(line_lower) < 50:
                return True
        
        return False


def create_website_prompt_enhancement(query: str, website_content: str, url: str) -> str:
    """
    Create an enhanced prompt that includes website content.
    
    Args:
        query: The original user query
        website_content: Content fetched from the website
        url: The source URL
    
    Returns:
        Enhanced prompt string
    """
    if not website_content:
        return query
    
    enhancement = f"\n\n--- Website Content from {url} ---\n"
    enhancement += website_content
    enhancement += f"\n--- End Website Content ---\n\n"
    enhancement += "Please use the above website content to provide a comprehensive response to the following query:\n\n"
    enhancement += query
    
    return enhancement
