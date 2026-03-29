from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import logging
import numpy as np
import json

_logger = logging.getLogger(__name__)

class ImageSearchWizard(models.TransientModel):
    _name = 'image.search.wizard'
    _description = 'AI Image Search with Fixed Feature Extraction'
    
    # Search Input
    search_image = fields.Binary(string='Search Image', required=True, 
                                help="Upload an image to find similar parts")
    search_image_name = fields.Char(string='Image Name', default='search_image.jpg')
    
    # Search Configuration
    min_confidence = fields.Float(string='Minimum Confidence %', default=70.0, 
                                 help="Only show results above this confidence level")
    max_results = fields.Integer(string='Maximum Results', default=10,
                                help="Maximum number of products to display")
    
    # Search Results (stored temporarily)
    search_results = fields.Text(string='Search Results JSON')
    has_results = fields.Boolean(string='Has Results', default=False)
    
    # Search Status
    search_status = fields.Selection([
        ('ready', 'Ready to Search'),
        ('searching', 'Searching...'),
        ('completed', 'Search Completed'),
        ('error', 'Search Error')
    ], string='Status', default='ready')
    
    search_error = fields.Text(string='Search Error Message')
    total_matches = fields.Integer(string='Total Matches Found', default=0)
    
    def action_search_similar_products(self):
        """Execute AI image search and return results"""
        try:
            self.search_status = 'searching'
            self.search_error = None
            
            if not self.search_image:
                raise ValidationError("Please upload a search image first")
            
            # Extract features from search image
            search_features = self._extract_search_features()
            
            if search_features is None:
                raise Exception("Failed to extract features from search image")
            
            # Find similar products
            similar_products = self._find_similar_products(search_features)
            
            # Store results
            self.search_results = json.dumps(similar_products)
            self.total_matches = len(similar_products)
            self.has_results = len(similar_products) > 0
            self.search_status = 'completed'
            
            # Return to product kanban view with similarity display
            return self._show_search_results(similar_products)
            
        except Exception as e:
            self.search_status = 'error'
            self.search_error = str(e)
            _logger.error(f"Image search failed: {e}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search Failed',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                }
            }
    
    def _extract_search_features(self):
        """Extract features from uploaded search image - FIXED VERSION"""
        try:
            # Same import path as ai_product_image model
            from ..ai_engine.feature_extractor import get_feature_extractor
            
            _logger.info("Starting search image feature extraction")
            
            # Validate search image
            if not self.search_image:
                raise Exception("No search image data provided")
            
            # Clean and validate base64 data
            image_data = self.search_image
            
            # Handle data URL format (data:image/jpeg;base64,...)
            if isinstance(image_data, str) and image_data.startswith('data:'):
                image_data = image_data.split(',', 1)[-1]
            
            # Ensure proper base64 padding
            missing_padding = len(image_data) % 4
            if missing_padding:
                image_data += '=' * (4 - missing_padding)
            
            # Validate base64 format
            try:
                base64.b64decode(image_data)
            except Exception as e:
                raise Exception(f"Invalid image format: {e}")
            
            # Get feature extractor (same instance used for product images)
            extractor = get_feature_extractor()
            
            # Extract features using same method as product images
            features = extractor.extract_features(image_data)
            
            if features is None:
                raise Exception("Feature extraction returned None - check image format and size")
            
            if not isinstance(features, np.ndarray):
                raise Exception("Invalid feature format returned")
                
            if len(features) == 0:
                raise Exception("Empty feature vector returned")
            
            _logger.info(f"Successfully extracted {len(features)} features from search image")
            return features
            
        except ImportError as e:
            _logger.error(f"Feature extractor import failed: {e}")
            raise Exception(f"AI feature extractor not available: {str(e)}")
        except Exception as e:
            _logger.error(f"Search feature extraction failed: {e}")
            raise Exception(f"Failed to extract features from search image: {str(e)}")
    
    def _find_similar_products(self, search_features):
        """Find products similar to search image"""
        try:
            _logger.info("Starting similar product search")
            
            # Get all processed product images
            processed_images = self.env['ai.product.image'].search([
                ('processing_status', '=', 'completed'),
                ('feature_vector', '!=', False)
            ])
            
            if not processed_images:
                _logger.warning("No processed product images found in database")
                return []
            
            _logger.info(f"Comparing search image with {len(processed_images)} processed images")
            
            similarities = []
            
            # Compare search features with each stored product image
            for product_image in processed_images:
                try:
                    if not product_image.feature_vector:
                        continue
                    
                    # Calculate similarity
                    similarity = self._calculate_similarity(search_features, product_image)
                    
                    # Convert to percentage and filter by confidence
                    confidence_percentage = max(0, similarity * 100)
                    
                    if confidence_percentage >= self.min_confidence:
                        similarities.append({
                            'product_id': product_image.product_id.id,
                            'product_name': product_image.product_id.name,
                            'product_price': product_image.product_id.list_price,
                            'similarity_percentage': round(confidence_percentage, 1),
                            'view_type': product_image.view_type,
                            'view_count': product_image.view_count,
                            'is_multiview': bool(product_image.combined_features),
                            'image_id': product_image.id
                        })
                        
                        _logger.debug(f"Match found: {product_image.image_name} - {confidence_percentage:.1f}%")
                
                except Exception as e:
                    _logger.warning(f"Similarity calculation failed for {product_image.image_name}: {e}")
                    continue
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity_percentage'], reverse=True)
            
            # Group by product (take highest similarity per product)
            unique_products = {}
            for sim in similarities:
                product_id = sim['product_id']
                if product_id not in unique_products or sim['similarity_percentage'] > unique_products[product_id]['similarity_percentage']:
                    unique_products[product_id] = sim
            
            # Convert back to list and limit results
            result_list = list(unique_products.values())[:self.max_results]
            
            _logger.info(f"Found {len(result_list)} unique similar products above {self.min_confidence}% confidence")
            return result_list
            
        except Exception as e:
            _logger.error(f"Similar product search failed: {e}")
            raise Exception(f"Product search failed: {str(e)}")
    
    def _calculate_similarity(self, search_features, product_image):
        """Calculate similarity between search features and product image"""
        try:
            # Get product features (prefer combined multi-view)
            product_features = None
            
            if product_image.combined_features:
                try:
                    product_features = np.array(json.loads(product_image.combined_features))
                except:
                    pass
            
            if product_features is None and product_image.feature_vector:
                try:
                    product_features = np.array(json.loads(product_image.feature_vector))
                except:
                    pass
            
            if product_features is None:
                return 0.0
            
            # Ensure both are numpy arrays with consistent types
            search_vec = np.array(search_features, dtype=np.float32)
            product_vec = np.array(product_features, dtype=np.float32)
            
            # Handle dimension mismatch
            min_len = min(len(search_vec), len(product_vec))
            if min_len == 0:
                return 0.0
                
            search_vec = search_vec[:min_len]
            product_vec = product_vec[:min_len]
            
            # Cosine similarity calculation
            dot_product = np.dot(search_vec, product_vec)
            norm1 = np.linalg.norm(search_vec)
            norm2 = np.linalg.norm(product_vec)
            
            if norm1 > 0 and norm2 > 0:
                similarity = dot_product / (norm1 * norm2)
                
                # Multi-view bonus
                if product_image.combined_features:
                    similarity *= 1.05  # 5% bonus for multi-view
                
                return max(0.0, min(1.0, similarity))
            
            return 0.0
            
        except Exception as e:
            _logger.warning(f"Similarity calculation failed for {product_image.image_name}: {e}")
            return 0.0
    
    def _show_search_results(self, similar_products):
        """Display search results in enhanced kanban view"""
        try:
            if not similar_products:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Similar Products Found',
                        'message': f'No products found with confidence >= {self.min_confidence}%.\n\nTry lowering the confidence threshold or uploading a different image.',
                        'type': 'warning',
                    }
                }
            
            # Create context with similarity data
            similarity_context = {
                'search_mode': True,
                'similarity_data': {str(p['product_id']): p['similarity_percentage'] 
                                  for p in similar_products},
                'search_wizard_id': self.id,
                'min_confidence': self.min_confidence
            }
            
            # Get product IDs for domain filter
            product_ids = [p['product_id'] for p in similar_products]
            
            # Return to product kanban with similarity display
            return {
                'type': 'ir.actions.act_window',
                'name': f'Similar Products Found ({len(similar_products)} matches)',
                'res_model': 'product.template',
                'view_mode': 'kanban,tree,form',
                'domain': [('id', 'in', product_ids)],
                'context': similarity_context,
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Search results display failed: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Display Error',
                    'message': f'Results found but display failed: {str(e)}',
                    'type': 'warning',
                }
            }
    
    def action_new_search(self):
        """Reset and start new search"""
        self.search_image = False
        self.search_results = False
        self.has_results = False
        self.search_status = 'ready'
        self.search_error = False
        self.total_matches = 0
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'image.search.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }
    
    def get_search_summary(self):
        """Get search summary for display"""
        if self.has_results and self.search_results:
            try:
                results = json.loads(self.search_results)
                return {
                    'total_matches': len(results),
                    'avg_confidence': round(sum(r['similarity_percentage'] for r in results) / len(results), 1),
                    'top_match': max(results, key=lambda x: x['similarity_percentage']) if results else None,
                    'min_confidence_used': self.min_confidence
                }
            except:
                return None
        return None