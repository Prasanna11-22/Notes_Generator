"""
Formatting Service for generated Learning Materials.
"""

import html
import json
import re


class LearningMaterialFormatter:
    """
    Converts markdown learning materials into requested output formats:
    Markdown, HTML, Plain Text, and JSON.
    """

    @classmethod
    def format_content(cls, markdown_text: str, output_format: str) -> str:
        """
        Format the given markdown text to the requested output format.
        """
        fmt = output_format.lower().strip()
        if fmt == "markdown":
            return markdown_text
        elif fmt == "html":
            return cls.to_html(markdown_text)
        elif fmt == "plain text" or fmt == "text":
            return cls.to_plain_text(markdown_text)
        elif fmt == "json":
            return cls.to_json(markdown_text)
        else:
            raise ValueError(f"Unsupported output format: '{output_format}'")

    @classmethod
    def to_html(cls, markdown_text: str) -> str:
        """
        Converts basic Markdown formatting to clean HTML.
        Handles headers, code blocks, lists, bold, italics, paragraphs.
        """
        # Escape HTML to prevent injection, but allow selective tags during parsing
        text = html.escape(markdown_text)

        # 1. Code blocks: ```python ... ``` -> <pre><code class="language-python">...</code></pre>
        def replace_code_block(match):
            lang = match.group(1) or ""
            code_content = match.group(2)
            lang_attr = f' class="language-{lang.strip()}"' if lang else ""
            return f'<pre><code{lang_attr}>{code_content.strip()}</code></pre>'
        
        # Regex matching ```lang ... ```
        text = re.sub(r'```(\w*)\n(.*?)\n```', replace_code_block, text, flags=re.DOTALL)

        # 2. Inline code: `code` -> <code>code</code>
        text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)

        # 3. Headers: # Header -> <h1>Header</h1>
        text = re.sub(r'^######\s+(.*?)$', r'<h6>\1</h6>', text, flags=re.MULTILINE)
        text = re.sub(r'^#####\s+(.*?)$', r'<h5>\1</h5>', text, flags=re.MULTILINE)
        text = re.sub(r'^####\s+(.*?)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s+(.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^##\s+(.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^#\s+(.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

        # 4. Bold / Italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)

        # 5. Lists
        # Unordered list items: ^-\s+Item -> <li>Item</li>
        text = re.sub(r'^\s*-\s+(.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        # Wrap consecutive <li> items in <ul>
        # (This is a basic parser fallback, wrapping runs of <li> in <ul>)
        text = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\n\1</ul>\n', text)

        # 6. Paragraphs (lines not containing block elements)
        # Split by double newlines, wrap in <p> if they don't contain lists/code/headers
        blocks = text.split("\n\n")
        parsed_blocks = []
        block_elements = ("<pre>", "<code>", "<h1>", "<h2>", "<h3>", "<h4>", "<h5>", "<h6>", "<ul>", "<li>", "<div>")
        
        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue
            if any(stripped.startswith(elem) for elem in block_elements):
                parsed_blocks.append(stripped)
            else:
                # Replace remaining single newlines with spaces for paragraph continuity
                p_text = stripped.replace("\n", " ")
                parsed_blocks.append(f"<p>{p_text}</p>")

        return "\n".join(parsed_blocks)

    @classmethod
    def to_plain_text(cls, markdown_text: str) -> str:
        """
        Strips markdown notation to return clean, formatted plain text.
        """
        # Strip code block markers
        text = re.sub(r'```\w*\n(.*?)\n```', r'\1', markdown_text, flags=re.DOTALL)
        # Strip inline code backticks
        text = re.sub(r'`([^`\n]+)`', r'\1', text)
        # Strip bold/italic markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        # Strip italic stars
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        # Strip headers hashes
        text = re.sub(r'^#+\s+(.*?)$', r'\1', text, flags=re.MULTILINE)
        # Clean bullet dashes
        text = re.sub(r'^\s*-\s+(.*?)$', r'\1', text, flags=re.MULTILINE)
        return text.strip()

    @classmethod
    def to_json(cls, markdown_text: str) -> str:
        """
        Encapsulates markdown text inside a serialized JSON object.
        """
        return json.dumps({
            "content": markdown_text,
            "paragraphs_count": len(re.split(r'\n\n+', markdown_text.strip())),
            "character_length": len(markdown_text)
        })
