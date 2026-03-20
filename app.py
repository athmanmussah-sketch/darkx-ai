from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import re
import random
from urllib.parse import urlparse
import nltk
from nltk.tokenize import sent_tokenize
from textblob import TextBlob
import wikipedia
import os
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

# Download NLTK data on startup
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class DarkXAI:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]
        self.session = requests.Session()
    
    def get_random_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    def analyze_query(self, query):
        """Analyze query intent and type"""
        query_lower = query.lower()
        
        # Detect question type
        question_types = {
            'definition': ['nini', 'maana', 'definition', 'meaning', 'what is'],
            'how': ['vipi', 'how to', 'jinsi ya', 'namna ya'],
            'why': ['kwanini', 'why', 'kwa nini'],
            'when': ['lini', 'when', 'wakati gani'],
            'where': ['wapi', 'where'],
            'who': ['nani', 'who']
        }
        
        question_type = 'general'
        for qtype, keywords in question_types.items():
            if any(keyword in query_lower for keyword in keywords):
                question_type = qtype
                break
        
        return {
            'type': question_type,
            'is_question': query_lower.endswith('?') or any(k in query_lower for k in ['nini', 'vipi', 'kwanini'])
        }
    
    def search_wikipedia(self, query):
        """Search Wikipedia for information"""
        try:
            # Clean query for Wikipedia
            search_query = query.replace('?', '').replace('nini', '').replace('maana ya', '').strip()
            summary = wikipedia.summary(search_query, sentences=3)
            return f"📚 Wikipedia: {summary}"
        except:
            return None
    
    def search_web(self, query, num_results=3):
        """Search web and scrape content"""
        results = []
        try:
            for url in search(query, num_results=num_results):
                parsed = urlparse(url)
                # Skip social media
                if any(bad in parsed.netloc for bad in ['youtube', 'facebook', 'twitter', 'instagram']):
                    continue
                
                # Scrape content
                content = self.scrape_website(url, query)
                if content:
                    results.append(f"🌐 {parsed.netloc}: {content[:500]}")
                    
                time.sleep(1)  # Be polite to servers
                
        except Exception as e:
            print(f"Search error: {e}")
        
        return results
    
    def scrape_website(self, url, query):
        """Scrape and extract relevant content from website"""
        try:
            headers = self.get_random_headers()
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Find main content
            main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
            if not main_content:
                main_content = soup.body
            
            # Extract paragraphs
            paragraphs = main_content.find_all('p')
            text = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 50])
            
            # Clean text
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'[^\w\s\.\,\!\?\-]', '', text)
            
            # Find sentences relevant to query
            sentences = sent_tokenize(text)
            query_words = set(query.lower().split())
            relevant = []
            
            for sentence in sentences[:10]:  # Check first 10 sentences
                if any(word in sentence.lower() for word in query_words):
                    relevant.append(sentence)
            
            if relevant:
                return ' '.join(relevant[:3])
            elif text:
                return text[:300]
            
            return None
            
        except Exception as e:
            print(f"Scraping error for {url}: {e}")
            return None
    
    def generate_response(self, query, info_sources):
        """Generate a well-structured response"""
        
        if not info_sources:
            return "Samahani, sikuweza kupata taarifa za kutosha. Jaribu kuuliza swali tofauti au ueleze zaidi."
        
        response_parts = []
        
        # Add introduction
        if query.endswith('?'):
            response_parts.append(f"📝 **Kuhusu swali lako:** {query}\n")
        else:
            response_parts.append(f"📝 **Uchambuzi wangu:**\n")
        
        # Add information from sources
        response_parts.append("**📊 Taarifa nilizopata:**\n")
        for i, info in enumerate(info_sources[:3], 1):
            response_parts.append(f"{i}. {info}\n")
        
        # Add helpful note
        response_parts.append("\n💡 *Je, ungependa nifafanue zaidi au uulize swali jingine?*")
        
        return '\n'.join(response_parts)
    
    def process_query(self, query):
        """Main processing pipeline"""
        
        if len(query) < 3:
            return "Tafadhali andika swali lenye maana zaidi ili nikusaidie vizuri."
        
        # Analyze query
        analysis = self.analyze_query(query)
        
        # Collect information
        info_sources = []
        
        # Try Wikipedia for knowledge questions
        if analysis['type'] in ['definition', 'what', 'who']:
            wiki_info = self.search_wikipedia(query)
            if wiki_info:
                info_sources.append(wiki_info)
        
        # Search web for more information
        web_results = self.search_web(query)
        info_sources.extend(web_results)
        
        # Generate response
        response = self.generate_response(query, info_sources)
        
        return response

# Initialize AI
darkx = DarkXAI()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'response': 'Tafadhali andika swali lako.'}), 400
        
        # Process message
        response = darkx.process_query(message)
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'Samahani, kuna hitilafu. Jaribu tena.'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
