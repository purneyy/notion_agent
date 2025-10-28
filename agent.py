import os
import asyncio
import ollama
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class NotionMCPTerminal:
    def __init__(self):
        self.client = ollama.Client()
        self.notion = None
        self.setup_notion()
    
    def setup_notion(self):
        """Setup direct Notion connection (no MCP server needed)"""
        print("🔧 Setting up Notion connection...")
        
        NOTION_API_KEY = os.getenv("NOTION_API_KEY")
        
        if not NOTION_API_KEY:
            print("❌ NOTION_API_KEY not found in .env file")
            print("   Get it from: https://www.notion.so/my-integrations")
            return
        
        try:
            self.notion = Client(auth=NOTION_API_KEY)
            # Test connection
            self.notion.search()
            print("✅ Notion connection successful!")
            return True
        except Exception as e:
            print(f"❌ Notion connection failed: {e}")
            return False
    
    def list_pages(self):
        """List all accessible pages"""
        try:
            results = self.notion.search()
            pages = []
            for page in results.get('results', []):
                title = "Untitled"
                if 'properties' in page:
                    # Try to get title from various property types
                    for prop_name, prop_value in page['properties'].items():
                        if prop_value.get('type') == 'title' and prop_value['title']:
                            title = prop_value['title'][0]['text']['content']
                            break
                        elif prop_value.get('type') == 'rich_text' and prop_value['rich_text']:
                            title = prop_value['rich_text'][0]['text']['content']
                            break
                
                pages.append({
                    'id': page['id'],
                    'title': title,
                    'url': page.get('url', 'No URL'),
                    'created_time': page.get('created_time', '')
                })
            
            return pages
        except Exception as e:
            return f"Error listing pages: {e}"
    
    def search_pages(self, query):
        """Search pages by query"""
        try:
            results = self.notion.search(query=query)
            pages = []
            for page in results.get('results', []):
                title = "Untitled"
                if 'properties' in page:
                    for prop_name, prop_value in page['properties'].items():
                        if prop_value.get('type') == 'title' and prop_value['title']:
                            title = prop_value['title'][0]['text']['content']
                            break
                
                pages.append({
                    'title': title,
                    'url': page.get('url', 'No URL'),
                    'id': page['id']
                })
            
            return pages
        except Exception as e:
            return f"Error searching pages: {e}"
    
    def create_page(self, title, parent_page_id=None):
        """Create a new page"""
        try:
            if not parent_page_id:
                parent_page_id = os.getenv("NOTION_PAGE_ID")
            
            if not parent_page_id:
                return "Error: No parent page ID provided. Set NOTION_PAGE_ID in .env or provide as parameter."
            
            new_page = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                },
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"Page created by Notion MCP Terminal"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            created_page = self.notion.pages.create(**new_page)
            return f"✅ Page '{title}' created successfully!\nURL: {created_page['url']}"
        
        except Exception as e:
            return f"Error creating page: {e}"
    
    def get_page_content(self, page_id):
        """Get content of a specific page"""
        try:
            blocks = self.notion.blocks.children.list(block_id=page_id)
            content = []
            
            for block in blocks.get('results', []):
                block_type = block['type']
                if block_type == 'paragraph' and block['paragraph']['rich_text']:
                    text = block['paragraph']['rich_text'][0]['text']['content']
                    content.append(f"📝 {text}")
                elif block_type == 'heading_1' and block['heading_1']['rich_text']:
                    text = block['heading_1']['rich_text'][0]['text']['content']
                    content.append(f"# {text}")
                elif block_type == 'heading_2' and block['heading_2']['rich_text']:
                    text = block['heading_2']['rich_text'][0]['text']['content']
                    content.append(f"## {text}")
                elif block_type == 'to_do' and block['to_do']['rich_text']:
                    text = block['to_do']['rich_text'][0]['text']['content']
                    checked = "✅" if block['to_do']['checked'] else "☐"
                    content.append(f"{checked} {text}")
            
            return "\n".join(content) if content else "No readable content found"
        
        except Exception as e:
            return f"Error getting page content: {e}"
    
    def process_natural_language(self, user_input):
        """Use Ollama to understand natural language and execute Notion operations"""
        try:
            # First, let Ollama understand the intent
            system_prompt = """You are a Notion assistant that understands natural language commands for Notion operations.

Available operations:
- LIST_PAGES: List all pages
- SEARCH_PAGES: Search pages with query
- CREATE_PAGE: Create new page with title
- GET_PAGE_CONTENT: Get content of specific page

Respond in this EXACT JSON format:
{
    "operation": "OPERATION_NAME",
    "parameters": {"param1": "value1", "param2": "value2"},
    "response": "What to show the user"
}

Example for "show me my pages":
{
    "operation": "LIST_PAGES", 
    "parameters": {},
    "response": "I'll list all your Notion pages"
}

Example for "create a page called Meeting Notes":
{
    "operation": "CREATE_PAGE",
    "parameters": {"title": "Meeting Notes"},
    "response": "Creating a new page called 'Meeting Notes'"
}"""

            response = self.client.chat(
                model='llama3.2:3b',
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            
            return response['message']['content']
            
        except Exception as e:
            return f"Error processing command: {e}"
    
    def execute_operation(self, operation, parameters):
        """Execute the actual Notion operation"""
        try:
            if operation == "LIST_PAGES":
                result = self.list_pages()
                if isinstance(result, list):
                    response = "📚 Your Notion Pages:\n"
                    for i, page in enumerate(result, 1):
                        response += f"{i}. {page['title']}\n"
                        response += f"   📎 URL: {page['url']}\n"
                        response += f"   🆔 ID: {page['id']}\n\n"
                    return response
                else:
                    return result
            
            elif operation == "SEARCH_PAGES":
                query = parameters.get('query', '')
                result = self.search_pages(query)
                if isinstance(result, list):
                    response = f"🔍 Search results for '{query}':\n"
                    for i, page in enumerate(result, 1):
                        response += f"{i}. {page['title']}\n"
                        response += f"   📎 URL: {page['url']}\n\n"
                    return response if result else f"No pages found for '{query}'"
                else:
                    return result
            
            elif operation == "CREATE_PAGE":
                title = parameters.get('title', 'Untitled Page')
                parent_id = parameters.get('parent_id')
                return self.create_page(title, parent_id)
            
            elif operation == "GET_PAGE_CONTENT":
                page_id = parameters.get('page_id')
                if not page_id:
                    return "Please specify which page you want to read (provide page ID)"
                return self.get_page_content(page_id)
            
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error executing operation: {e}"

def main():
    print("🚀 NOTION MCP TERMINAL")
    print("=" * 60)
    print("🤖 Natural Language Interface for Notion")
    print("💻 Powered by Ollama (Local AI)")
    print("=" * 60)
    
    terminal = NotionMCPTerminal()
    
    if not terminal.notion:
        print("\n❌ Cannot start without Notion connection.")
        print("Please check your NOTION_API_KEY in .env file")
        return
    
    print("\n✅ Ready! You can now interact with your Notion workspace naturally.")
    print("\n💬 Examples:")
    print("   • 'Show me all my pages'")
    print("   • 'Search for meeting notes'") 
    print("   • 'Create a new page called Shopping List'")
    print("   • 'What pages do I have?'")
    print("   • 'Make a page named Project Ideas'")
    print("\nType 'quit' to exit")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n🎯 You: ").strip()
            if user_input.lower() == 'quit':
                print("👋 Closing Notion MCP Terminal...")
                break
            
            if not user_input:
                continue
            
            print("🔄 Processing...")
            
            # Process natural language
            ai_response = terminal.process_natural_language(user_input)
            
            # Try to parse JSON response from AI
            try:
                import json
                parsed = json.loads(ai_response)
                operation = parsed.get('operation')
                parameters = parsed.get('parameters', {})
                response_message = parsed.get('response', '')
                
                if operation:
                    print(f"🤖 {response_message}")
                    # Execute the actual operation
                    result = terminal.execute_operation(operation, parameters)
                    print(f"\n📋 Result:\n{result}")
                else:
                    print(f"🤖 {ai_response}")
                    
            except json.JSONDecodeError:
                # If AI didn't return proper JSON, just show the response
                print(f"🤖 {ai_response}")
            
        except KeyboardInterrupt:
            print("\n👋 Closing Notion MCP Terminal...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()