"""Web search functionality using DuckDuckGo (DDG)

This module provides web search capabilities
"""

# This is created by GitHub Copilot

import requests
import json
import urllib.parse
import re
from typing import List, Dict, Optional, Any
from .output import OutputFormatter


class WebSearchResult:
    """a single web search result."""
    
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


class DuckDuckGoSearch:
    """DDG web search client."""
    
    def __init__(self, output: Optional[OutputFormatter] = None):
        self.output = output or OutputFormatter(use_colors=True, render_markdown=False)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'mdllama/4.1.2 (Web Search Bot)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1'
        })
    
    def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """
        Search DuckDuckGo for the given query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return (default: 5, max: 10)
        
        Returns:
            List of WebSearchResult objects
        """
        try:
            # Limit max_results to reasonable bounds
            max_results = min(max(1, max_results), 10)
            
            # Try HTML search first as it's more reliable
            results = self._search_html(query, max_results)
            
            # If HTML search doesn't work, try the instant answer API
            if not results:
                results = self._search_instant_answer(query, max_results)
            
            # For each result, fetch and extract readable text from the URL
            for result in results:
                if result.url and result.url.startswith("http"):
                    page_text = self._extract_page_text(result.url)
                    if page_text:
                        # Only add if not already present and not too long
                        if not result.snippet or len(result.snippet) < 100:
                            # Use first 500 chars as summary
                            result.snippet = (page_text[:500] + "..." if len(page_text) > 500 else page_text)
            return results[:max_results]
            
        except requests.RequestException as e:
            self.output.print_error(f"Network error during search: {e}")
            return []
        except Exception as e:
            self.output.print_error(f"Unexpected error during search: {e}")
            return []
    
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
        
        This method scrapes DuckDuckGo's HTML search results as a fallback
        when the instant answer API doesn't provide enough results.
        """
        try:
            # DuckDuckGo lite search (simpler HTML structure)
            search_url = "https://lite.duckduckgo.com/lite/"
            search_params = {
                'q': query,
                'kd': '-1'  # No date restriction
            }
            
            # Use a more standard browser user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = self.session.get(search_url, params=search_params, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Simple HTML parsing to extract search results
            html_content = response.text
            results = []
            
            # Look for result blocks in DuckDuckGo lite's simpler HTML structure
            import re
            
            # Pattern to match result links - DuckDuckGo lite has simpler structure
            # Look for links that are search results (not ads or internal links)
            link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>'
            
            links = re.findall(link_pattern, html_content)
            
            # Filter out DuckDuckGo internal links and extract actual results
            filtered_results = []
            for url, title in links:
                # Skip DuckDuckGo internal links
                if ('duckduckgo.com' not in url and 
                    'ddg.gg' not in url and 
                    url.startswith('http') and
                    len(title.strip()) > 3):
                    
                    # Clean up title
                    title = self._clean_html_text(title)
                    
                    # Try to extract a snippet from nearby text (simple approach)
                    snippet = ""
                    
                    # For now, we'll just use the title as basic info
                    if title and url:
                        filtered_results.append((url, title, snippet))
                        
                        if len(filtered_results) >= max_results:
                            break
            
            # Convert to WebSearchResult objects
            for url, title, snippet in filtered_results:
                results.append(WebSearchResult(title, url, snippet))
            
            # If we still don't have results, create some basic ones from the query
            if not results and query:
                # This is a fallback to show that search was attempted
                results.append(WebSearchResult(
                    title=f"Search results for: {query}",
                    url="https://duckduckgo.com/?q=" + urllib.parse.quote(query),
                    snippet=f"No detailed results available. You can search manually for: {query}"
                ))
            
            return results
            
        except Exception as e:
            # If HTML search fails, return a basic result indicating the search attempt
            return [WebSearchResult(
                title=f"Search for: {query}",
                url="https://duckduckgo.com/?q=" + urllib.parse.quote(query),
                snippet=f"Web search encountered an issue. You can search manually for: {query}"
            )]
    
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
            response = self.session.get(url, timeout=10)
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
            
            # Strategy 1: Look for common content containers
            content_selectors = [
                'article', 'main', '[role="main"]', '.content', '.post-content', 
                '.entry-content', '.article-content', '.story-body', '.post-body',
                '.content-body', '.article-body', '.text-content'
            ]
            
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    # Extract text from paragraphs within this content area
                    paragraphs = content_element.find_all('p')
                    if paragraphs:
                        content_text = ' '.join(p.get_text(separator=' ', strip=True) for p in paragraphs)
                        break
            
            # Strategy 2: If no content container found, get paragraphs but filter better
            if not content_text:
                all_paragraphs = soup.find_all('p')
                # Filter out short paragraphs (likely navigation or boilerplate)
                meaningful_paragraphs = []
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    # Only include paragraphs that are substantial and don't look like navigation
                    if (len(text) > 50 and 
                        not any(nav_word in text.lower() for nav_word in 
                               ['edit', 'view source', 'talk', 'languages', 'toggle', 'menu', 
                                'login', 'sign up', 'register', 'subscribe', 'follow us'])):
                        meaningful_paragraphs.append(text)
                
                content_text = ' '.join(meaningful_paragraphs)
            
            # Strategy 3: Final fallback - get the largest text block
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
