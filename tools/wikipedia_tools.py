"""
Tools to interact with Wikipedia.
It uses the `wikipedia-api` package. The URL is https://github.com/martin-majlis/Wikipedia-API
"""

import wikipediaapi
import os
import re
from datetime import datetime


class WikipediaSearcher:
    """A class to search Wikipedia and save results to markdown files."""
    
    def __init__(self, user_agent='fantastic-fishstick (gusmmm@proton.me)', language='en'):
        """Initialize the Wikipedia searcher with user agent and language."""
        self.wiki_wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language=language)
        self.results = []
    
    def _sanitize_filename(self, text):
        """Sanitize text for use in filenames by removing/replacing invalid characters."""
        # Replace spaces with underscores and remove invalid filename characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length to avoid filesystem issues
        return sanitized[:50].strip('_')
    
    def search(self, query):
        """Search for a page on Wikipedia."""
        page = self.wiki_wiki.page(query)
        
        if page.exists():
            result = {
                'query': query,
                'title': page.title,
                'summary': page.summary,
                'url': page.fullurl,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.results.append(result)
            return result
        else:
            return None
    
    def get_full_text(self, query, extract_format='wiki'):
        """
        Extract full text of a Wikipedia page with all sections.
        
        Args:
            query (str): The Wikipedia page to search for
            extract_format (str): Format for extraction - 'wiki' or 'html'
        
        Returns:
            dict: Dictionary containing query, title, full_text, sections, format, and timestamp
        """
        # Create a new Wikipedia instance with the specified extract format
        if extract_format.lower() == 'html':
            wiki_client = wikipediaapi.Wikipedia(
                user_agent='fantastic-fishstick (gusmmm@proton.me)',
                language='en',
                extract_format=wikipediaapi.ExtractFormat.HTML
            )
        else:
            wiki_client = wikipediaapi.Wikipedia(
                user_agent='fantastic-fishstick (gusmmm@proton.me)',
                language='en',
                extract_format=wikipediaapi.ExtractFormat.WIKI
            )
        
        page = wiki_client.page(query)
        
        if page.exists():
            result = {
                'query': query,
                'title': page.title,
                'summary': page.summary,
                'full_text': page.text,
                'sections': page.sections,  # Add sections for hierarchy
                'url': page.fullurl,
                'format': extract_format.lower(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return result
        else:
            return None
    
    def _format_sections_to_markdown(self, sections, level=1):
        """
        Recursively format Wikipedia sections to markdown with proper hierarchy.
        
        Args:
            sections: List of WikipediaPageSection objects
            level (int): Current heading level (1-6)
        
        Returns:
            str: Formatted markdown text with proper hierarchy
        """
        markdown_text = ""
        
        for section in sections:
            # Create markdown heading based on level (limit to h6)
            heading_level = min(level, 6)
            heading = "#" * heading_level
            
            # Add section title
            markdown_text += f"{heading} {section.title}\n\n"
            
            # Add section text if it exists
            if section.text.strip():
                markdown_text += f"{section.text.strip()}\n\n"
            
            # Recursively process subsections
            if section.sections:
                markdown_text += self._format_sections_to_markdown(section.sections, level + 1)
        
        return markdown_text
    
    def print_section_hierarchy(self, query, max_depth=3):
        """
        Print the section hierarchy of a Wikipedia page for debugging/preview.
        
        Args:
            query (str): The Wikipedia page to analyze
            max_depth (int): Maximum depth to display
        """
        result = self.get_full_text(query, extract_format='wiki')
        if not result or not result['sections']:
            print(f"No sections found for: {query}")
            return
        
        def _print_sections(sections, level=0):
            if level >= max_depth:
                return
            for section in sections:
                indent = "  " * level
                print(f"{indent}{'*' * (level + 1)} {section.title}")
                if section.sections:
                    _print_sections(section.sections, level + 1)
        
        print(f"\nSection hierarchy for: {result['title']}")
        print("=" * 50)
        _print_sections(result['sections'])
        print("=" * 50)
    
    def save_full_text_to_markdown(self, query, extract_format='wiki', filename=None, directory='temp', preserve_hierarchy=True):
        """
        Extract full text and save it to a markdown file with proper hierarchy.
        
        Args:
            query (str): The Wikipedia page to search for
            extract_format (str): Format for extraction - 'wiki' or 'html'
            filename (str): Optional custom filename
            directory (str): Directory to save the file
            preserve_hierarchy (bool): Whether to preserve section hierarchy in markdown format
        
        Returns:
            str: Path to the saved file or None if failed
        """
        result = self.get_full_text(query, extract_format)
        
        if not result:
            print(f"No Wikipedia page found for query: {query}")
            return None
        
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            query_part = self._sanitize_filename(query)
            hierarchy_suffix = "_structured" if preserve_hierarchy else ""
            
            # Use appropriate file extension based on format
            if extract_format.lower() == 'html':
                file_extension = 'html'
            else:
                file_extension = 'md'
            
            filename = f'wikipedia_fulltext_{query_part}_{extract_format}{hierarchy_suffix}_{timestamp}.{file_extension}'
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if extract_format.lower() == 'html':
                # Save as proper HTML file with HTML structure
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{result['title']} - Wikipedia</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .metadata {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .metadata h2 {{ margin-top: 0; color: #333; }}
        .metadata p {{ margin: 5px 0; }}
        .content {{ margin-top: 20px; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; }}
        a {{ color: #0645ad; }}
        a:visited {{ color: #0b0080; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h2>Wikipedia Article Metadata</h2>
        <p><strong>Query:</strong> {result['query']}</p>
        <p><strong>URL:</strong> <a href="{result['url']}" target="_blank">{result['url']}</a></p>
        <p><strong>Extract Format:</strong> {result['format']}</p>
        <p><strong>Extracted on:</strong> {result['timestamp']}</p>
    </div>
    
    <div class="content">
        <h1>{result['title']}</h1>
        {result['full_text']}
    </div>
</body>
</html>""")
            else:
                # Save as markdown file with proper hierarchy
                f.write(f"# {result['title']}\n\n")
                f.write(f"**Query:** {result['query']}\n\n")
                f.write(f"**URL:** [{result['url']}]({result['url']})\n\n")
                f.write(f"**Extract Format:** {result['format']}\n\n")
                f.write(f"**Hierarchy Preserved:** {'Yes' if preserve_hierarchy else 'No'}\n\n")
                f.write(f"**Extracted on:** {result['timestamp']}\n\n")
                f.write("---\n\n")
                
                if preserve_hierarchy and extract_format.lower() == 'wiki':
                    # Use structured format with proper markdown hierarchy
                    f.write("## Summary\n\n")
                    f.write(f"{result['summary']}\n\n")
                    
                    # Format sections with hierarchy
                    if result['sections']:
                        structured_content = self._format_sections_to_markdown(result['sections'], level=2)
                        f.write(structured_content)
                    else:
                        f.write("*No sections found.*\n\n")
                else:
                    # Fallback to raw text format
                    f.write(result['full_text'])
        
        print(f"Full text saved to: {filepath}")
        return filepath
    
    def save_to_markdown(self, filename=None, directory='temp'):
        """Save all search results to a markdown file."""
        if not self.results:
            print("No results to save.")
            return None
        
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create a descriptive filename with query info
            if len(self.results) == 1:
                # Single query - use the query in filename
                query_part = self._sanitize_filename(self.results[0]['query'])
                filename = f'wikipedia_{query_part}_{timestamp}.md'
            else:
                # Multiple queries - use generic name with count
                filename = f'wikipedia_search_{len(self.results)}_results_{timestamp}.md'
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Wikipedia Search Results\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"## Result {i}: {result['title']}\n\n")
                f.write(f"**Query:** {result['query']}\n\n")
                f.write(f"**URL:** [{result['url']}]({result['url']})\n\n")
                f.write(f"**Search Timestamp:** {result['timestamp']}\n\n")
                f.write(f"**Summary:**\n\n{result['summary']}\n\n")
                f.write("---\n\n")
        
        print(f"Results saved to: {filepath}")
        return filepath
    
    def print_results(self):
        """Print all search results to console."""
        for result in self.results:
            print(f"Page - Title: {result['title']}")
            print(f"Page - Summary: {result['summary'][:60]}...")  # First 60 characters
            print(f"Page - URL: {result['url']}")
            print("-" * 50)


# Example usage
if __name__ == "__main__":
    # Create searcher instance
    searcher = WikipediaSearcher()
    
    # Perform a search
    query = "Malaria"
    result = searcher.search(query)
    
    if result:
        # Print results to console
        searcher.print_results()
        
        # Save results to markdown file
        searcher.save_to_markdown()
        
        # Example: Extract and save full text with structured hierarchy
        print("\n--- Extracting full text with structured hierarchy ---")
        searcher.save_full_text_to_markdown(query, extract_format='wiki', preserve_hierarchy=True)
        
        # Example: Extract and save full text in raw format (no hierarchy)
        print("\n--- Extracting full text in raw format ---")
        searcher.save_full_text_to_markdown(query, extract_format='wiki', preserve_hierarchy=False)
        
        # Example: Extract and save full text in HTML format
        print("\n--- Extracting full text in HTML format ---")
        searcher.save_full_text_to_markdown(query, extract_format='html')
        
        # Example: Get full text directly (without saving)
        print("\n--- Getting full text directly ---")
        full_text_result = searcher.get_full_text(query, extract_format='wiki')
        if full_text_result:
            print(f"Full text length: {len(full_text_result['full_text'])} characters")
            print(f"Number of sections: {len(full_text_result['sections'])}")
            print(f"First 200 characters: {full_text_result['full_text'][:200]}...")
        
        # Example: Display section hierarchy
        print("\n--- Displaying section hierarchy ---")
        searcher.print_section_hierarchy(query, max_depth=3)
        
    else:
        print(f"No Wikipedia page found for query: {query}")