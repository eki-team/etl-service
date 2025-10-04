"""
Service for automatic tag generation from text content
"""
import re
from typing import List, Set, Dict
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class TagGenerator:
    """Service for generating tags from text content"""
    
    # Common stop words in English
    STOP_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
        'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
        'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
        'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
        'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
        'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
        'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had',
        'were', 'said', 'did', 'having', 'may', 'should', 'am', 'being', 'does'
    }
    
    # Domain-specific keywords (NASA/Space related)
    DOMAIN_KEYWORDS = {
        'space': ['space', 'spacecraft', 'orbital', 'satellite', 'cosmos', 'universe'],
        'nasa': ['nasa', 'agency', 'administration', 'aeronautics'],
        'astronomy': ['astronomy', 'astronomical', 'telescope', 'observatory', 'celestial'],
        'planets': ['planet', 'mars', 'jupiter', 'saturn', 'venus', 'mercury', 'neptune', 'uranus', 'earth'],
        'mission': ['mission', 'expedition', 'voyage', 'exploration', 'probe'],
        'technology': ['technology', 'engineering', 'system', 'instrument', 'equipment'],
        'science': ['science', 'scientific', 'research', 'study', 'discovery', 'data'],
        'rocket': ['rocket', 'launch', 'booster', 'propulsion'],
        'galaxy': ['galaxy', 'galaxies', 'milky way', 'nebula', 'star', 'stars'],
        'physics': ['physics', 'quantum', 'gravity', 'relativity', 'energy'],
    }
    
    def __init__(self):
        """Initialize tag generator"""
        pass
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text for tag extraction
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces and hyphens
        text = re.sub(r'[^\w\s\-]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_keywords_frequency(self, text: str, max_keywords: int = 20) -> List[str]:
        """
        Extract keywords based on word frequency
        
        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        # Clean text
        cleaned_text = self.clean_text(text)
        
        # Split into words
        words = cleaned_text.split()
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words
            if word not in self.STOP_WORDS and len(word) > 3
        ]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Get most common words
        most_common = word_counts.most_common(max_keywords)
        
        return [word for word, count in most_common]
    
    def extract_keywords_tfidf(self, text: str, max_keywords: int = 15) -> List[str]:
        """
        Extract keywords using TF-IDF
        
        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        try:
            # Clean text
            cleaned_text = self.clean_text(text)
            
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=max_keywords,
                stop_words='english',
                ngram_range=(1, 2),  # Include bigrams
                min_df=1
            )
            
            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform([cleaned_text])
            
            # Get feature names (keywords)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            scores = tfidf_matrix.toarray()[0]
            
            # Sort by score
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return keywords
            return [keyword for keyword, score in keyword_scores[:max_keywords]]
            
        except Exception as e:
            print(f"⚠️  TF-IDF extraction failed: {e}")
            return []
    
    def extract_domain_tags(self, text: str) -> List[str]:
        """
        Extract domain-specific tags (NASA/Space related)
        
        Args:
            text: Input text
            
        Returns:
            List of domain tags
        """
        cleaned_text = self.clean_text(text)
        tags = []
        
        for category, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in cleaned_text:
                    tags.append(category)
                    break  # Only add category once
        
        return tags
    
    def extract_named_entities(self, text: str) -> List[str]:
        """
        Extract potential named entities (simple approach)
        
        Args:
            text: Input text
            
        Returns:
            List of potential named entities
        """
        # Find capitalized words (simple NER)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Count occurrences
        entity_counts = Counter(capitalized)
        
        # Return entities that appear more than once
        entities = [
            entity.lower() for entity, count in entity_counts.items()
            if count > 1 and len(entity) > 3
        ]
        
        return entities[:10]  # Limit to 10 entities
    
    def generate_tags(
        self,
        text: str,
        max_tags: int = 15,
        include_domain: bool = True,
        include_entities: bool = True
    ) -> List[str]:
        """
        Generate tags from text using multiple methods
        
        Args:
            text: Input text
            max_tags: Maximum number of tags to return
            include_domain: Include domain-specific tags
            include_entities: Include named entities as tags
            
        Returns:
            List of unique tags
        """
        all_tags = set()
        
        # 1. Extract domain tags
        if include_domain:
            domain_tags = self.extract_domain_tags(text)
            all_tags.update(domain_tags)
        
        # 2. Extract keywords using frequency
        frequency_keywords = self.extract_keywords_frequency(text, max_keywords=10)
        all_tags.update(frequency_keywords[:5])  # Add top 5
        
        # 3. Extract keywords using TF-IDF
        tfidf_keywords = self.extract_keywords_tfidf(text, max_keywords=10)
        all_tags.update(tfidf_keywords[:5])  # Add top 5
        
        # 4. Extract named entities
        if include_entities:
            entities = self.extract_named_entities(text)
            all_tags.update(entities[:3])  # Add top 3
        
        # Convert to list and limit
        tags = list(all_tags)[:max_tags]
        
        # Sort alphabetically
        tags.sort()
        
        return tags
    
    def generate_category(self, text: str, tags: List[str]) -> str:
        """
        Determine the main category based on text and tags
        
        Args:
            text: Input text
            tags: Generated tags
            
        Returns:
            Main category
        """
        # Check domain categories
        for category, keywords in self.DOMAIN_KEYWORDS.items():
            if category in tags:
                return category
        
        # Default category based on content
        cleaned_text = self.clean_text(text)
        
        if any(word in cleaned_text for word in ['research', 'study', 'data', 'experiment']):
            return 'science'
        elif any(word in cleaned_text for word in ['mission', 'launch', 'expedition']):
            return 'mission'
        elif any(word in cleaned_text for word in ['technology', 'system', 'engineering']):
            return 'technology'
        else:
            return 'general'


# Global tag generator instance
tag_generator = TagGenerator()
