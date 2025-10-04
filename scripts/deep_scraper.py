#!/usr/bin/env python3
"""
Deep Content Scraper para Publicaciones de Biología Espacial
Extrae contenido completo: título, autores, texto completo, y referencias
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re
from fake_useragent import UserAgent

class DeepContentScraper:
    def __init__(self, max_articles=None):
        """
        Inicializa el scraper
        
        Args:
            max_articles (int, optional): Numero maximo de articulos a scrape.
                                        Si es None, scrape todos los articulos.
        """
        self.max_articles = max_articles
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def clean_text(self, text):
        """Limpia y normaliza texto extraído"""
        if not text:
            return ""
        # Remover espacios extras y saltos de línea
        text = re.sub(r'\s+', ' ', text.strip())
        # Remover caracteres especiales problemáticos
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        return text
    
    def extract_authors(self, soup):
        """Extrae lista completa de autores"""
        authors = []
        
        # Intentar varios selectores para autores
        author_selectors = [
            '.contrib-group .contrib',
            '.authors-list .author',
            '.author-list .author',
            '.contrib-group a[href*="author"]',
            '.authors .author',
            'div.contrib-group span.given-names, div.contrib-group span.surname',
            '.citation .authors .author'
        ]
        
        for selector in author_selectors:
            author_elements = soup.select(selector)
            if author_elements:
                for element in author_elements:
                    author_text = self.clean_text(element.get_text())
                    if author_text and len(author_text) > 2:
                        authors.append(author_text)
                break
        
        # Si no encontramos autores con selectores, buscar en metadatos
        if not authors:
            meta_authors = soup.find_all('meta', attrs={'name': re.compile('author', re.I)})
            for meta in meta_authors:
                content = meta.get('content', '')
                if content:
                    authors.append(self.clean_text(content))
        
        # Limpiar duplicados manteniendo orden
        seen = set()
        unique_authors = []
        for author in authors:
            if author not in seen:
                seen.add(author)
                unique_authors.append(author)
        
        return unique_authors[:20]  # Limitar a 20 autores máximo
    
    def extract_abstract(self, soup):
        """Extrae el abstract del artículo"""
        abstract_selectors = [
            'div.abstract p',
            '.abstract-content p',
            '#abstract p',
            '.summary p',
            'div[class*="abstract"] p',
            'section.abstract p'
        ]
        
        for selector in abstract_selectors:
            elements = soup.select(selector)
            if elements:
                abstract_parts = []
                for element in elements:
                    text = self.clean_text(element.get_text())
                    if text and len(text) > 10:
                        abstract_parts.append(text)
                if abstract_parts:
                    return ' '.join(abstract_parts)
        
        return ""
    
    def extract_full_text(self, soup):
        """Extrae el texto completo del artículo"""
        # Intentar extraer secciones principales
        sections = {}
        
        # Selectores para diferentes secciones
        section_selectors = {
            'introduction': ['#introduction', '.introduction', 'section[title*="Introduction"]'],
            'methods': ['#methods', '.methods', '#materials-methods', 'section[title*="Method"]'],
            'results': ['#results', '.results', 'section[title*="Result"]'],
            'discussion': ['#discussion', '.discussion', 'section[title*="Discussion"]'],
            'conclusion': ['#conclusion', '.conclusion', 'section[title*="Conclusion"]']
        }
        
        for section_name, selectors in section_selectors.items():
            for selector in selectors:
                section_elem = soup.select_one(selector)
                if section_elem:
                    paragraphs = section_elem.find_all('p')
                    if paragraphs:
                        section_text = []
                        for p in paragraphs:
                            text = self.clean_text(p.get_text())
                            if text and len(text) > 20:
                                section_text.append(text)
                        if section_text:
                            sections[section_name] = section_text
                        break
        
        # Si no encontramos secciones específicas, extraer todos los párrafos del cuerpo
        if not sections:
            body_selectors = [
                'div.pmc-article-content p',
                '.article-body p',
                '.content p',
                'main p',
                'article p'
            ]
            
            for selector in body_selectors:
                paragraphs = soup.select(selector)
                if paragraphs and len(paragraphs) > 3:
                    all_text = []
                    for p in paragraphs:
                        text = self.clean_text(p.get_text())
                        if text and len(text) > 20:
                            all_text.append(text)
                    if all_text:
                        sections['full_content'] = all_text
                    break
        
        return sections
    
    def extract_references(self, soup):
        """Extrae las referencias/citas del artículo"""
        references = []
        
        # Selectores para referencias
        ref_selectors = [
            '.ref-list .ref',
            '#references .ref',
            '.references .reference',
            '.bibliography .reference',
            'div.ref-list li',
            'ol.references li'
        ]
        
        for selector in ref_selectors:
            ref_elements = soup.select(selector)
            if ref_elements:
                for ref in ref_elements[:50]:  # Limitar a 50 referencias
                    ref_text = self.clean_text(ref.get_text())
                    if ref_text and len(ref_text) > 10:
                        references.append(ref_text)
                break
        
        return references
    
    def scrape_article_content(self, url):
        """Extrae todo el contenido de un artículo"""
        print(f"Scraping: {url}")
        
        try:
            # Hacer request con headers apropiados
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extraer título limpio
            title_elem = soup.find('title')
            title = self.clean_text(title_elem.get_text()) if title_elem else ""
            # Remover " - PMC" del final
            title = re.sub(r'\s*-\s*PMC\s*$', '', title)
            
            # Extraer todos los componentes
            authors = self.extract_authors(soup)
            abstract = self.extract_abstract(soup)
            full_text = self.extract_full_text(soup)
            references = self.extract_references(soup)
            
            # Contar elementos
            word_count = 0
            if abstract:
                word_count += len(abstract.split())
            for section, paragraphs in full_text.items():
                for paragraph in paragraphs:
                    word_count += len(paragraph.split())
            
            result = {
                'url': url,
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'full_text': full_text,
                'references': references,
                'statistics': {
                    'total_authors': len(authors),
                    'abstract_words': len(abstract.split()) if abstract else 0,
                    'total_words': word_count,
                    'references_count': len(references),
                    'sections_found': list(full_text.keys())
                },
                'scraped_at': datetime.now().isoformat(),
                'success': True
            }
            
            print(f"Exito: {len(authors)} autores, {word_count} palabras, {len(references)} referencias")
            return result
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'success': False,
                'scraped_at': datetime.now().isoformat()
            }
    
    def scrape_all_articles(self, input_file, sample_size=None):
        """
        Scrape articulos del JSON original
        
        Args:
            input_file (str): Ruta al archivo JSON con los datos originales
            sample_size (int, optional): Numero de articulos a procesar. 
                                       Si es None, usa self.max_articles o todos.
        """
        
        # Cargar datos originales
        with open(input_file, 'r') as f:
            original_data = json.load(f)
        
        # Determinar cuantos articulos procesar
        total_available = len(original_data)
        
        if sample_size is not None:
            articles_to_process = min(sample_size, total_available)
        elif self.max_articles is not None:
            articles_to_process = min(self.max_articles, total_available)
        else:
            articles_to_process = total_available
        
        # Tomar muestra de articulos
        articles_to_scrape = original_data[:articles_to_process]
        
        print(f"Total de articulos disponibles: {total_available}")
        print(f"Articulos a procesar: {articles_to_process}")
        print(f"Tiempo estimado: {articles_to_process * 2 / 60:.1f} minutos")
        
        results = []
        
        for i, article in enumerate(articles_to_scrape):
            print(f"\nArticulo {i+1}/{articles_to_process} ({(i+1)/articles_to_process*100:.1f}%)")
            
            # Scrape contenido completo
            content = self.scrape_article_content(article['url'])
            
            # Agregar información original
            content['original_data'] = {
                'pmc_id': article.get('pmc_id'),
                'doi': article.get('doi'),
                'figures_count': article.get('figures_count', 0),
                'tables_count': article.get('tables_count', 0),
                'original_title': article.get('original_title', '')
            }
            
            results.append(content)
            
            # Guardar backup cada 50 articulos
            if (i + 1) % 50 == 0:
                backup_file = f'../data/deep_backup_{i+1}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Backup guardado: {backup_file}")
            
            # Delay entre requests
            time.sleep(1.5)
        
        # Guardar resultados finales
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'../data/complete_deep_content_{articles_to_process}articles_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nSCRAPING COMPLETADO!")
        print(f"Archivo final guardado: {output_file}")
        
        # Estadísticas finales
        successful = sum(1 for r in results if r.get('success', False))
        failed = articles_to_process - successful
        total_words = sum(r.get('statistics', {}).get('total_words', 0) for r in results if r.get('success', False))
        total_authors = sum(r.get('statistics', {}).get('total_authors', 0) for r in results if r.get('success', False))
        total_references = sum(r.get('statistics', {}).get('references_count', 0) for r in results if r.get('success', False))
        
        print(f"\nESTADISTICAS FINALES:")
        print(f"Articulos exitosos: {successful}/{articles_to_process} ({successful/articles_to_process*100:.1f}%)")
        print(f"Articulos fallidos: {failed}")
        if successful > 0:
            print(f"Total de palabras extraidas: {total_words:,}")
            print(f"Total de autores encontrados: {total_authors}")
            print(f"Total de referencias: {total_references}")
            print(f"Promedio de palabras por articulo: {total_words/successful:.0f}")
        
        return output_file

def main():
    """
    Funcion principal con configuracion flexible
    """
    
    # CONFIGURACION - Cambia estos valores segun necesites:
    
    # Opcion 1: Numero especifico de articulos
    ARTICLES_TO_SCRAPE = 10  # Cambia este numero (5, 10, 50, 100, etc.)
    
    # Opcion 2: Para scrape todos los articulos disponibles, usa None
    # ARTICLES_TO_SCRAPE = None
    
    # Archivo de entrada
    input_file = '../data/space_biology_publications_20251004_104550.json'
    
    # Crear scraper con limite configurable
    scraper = DeepContentScraper(max_articles=ARTICLES_TO_SCRAPE)
    
    print("INICIANDO SCRAPING PROFUNDO DE PUBLICACIONES")
    print("=" * 60)
    
    if ARTICLES_TO_SCRAPE is None:
        print("Procesando TODOS los articulos disponibles")
    else:
        print(f"Procesando maximo {ARTICLES_TO_SCRAPE} articulos")
    
    print("Se haran backups automaticos cada 50 articulos")
    print("=" * 60)
    
    # Ejecutar scraping
    output_file = scraper.scrape_all_articles(input_file)
    
    print(f"\nPara ver los resultados:")
    print(f"less {output_file}")
    print(f"Para analisis en Python:")
    print(f"import json")
    print(f"with open('{output_file}', 'r') as f:")
    print(f"    data = json.load(f)")

if __name__ == "__main__":
    main()