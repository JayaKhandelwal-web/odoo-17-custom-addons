from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import json
import numpy as np

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # =======================
    # AI SEARCH IMAGES FIELDS
    # =======================
    
    # Main relationship with AI images
    product_image_ids = fields.One2many(
        'ai.product.image', 
        'product_id', 
        string='AI Search Images',
        help='Images used for AI-powered similarity search'
    )
    
    # =======================
    # COMPUTED FIELDS FOR UI
    # =======================
    
    # Basic image statistics
    has_search_images = fields.Boolean(
        string='Has Search Images',
        compute='_compute_search_image_stats',
        store=False,
        help='True if product has AI search images'
    )
    
    search_images_count = fields.Integer(
        string='Total Images',
        compute='_compute_search_image_stats',
        store=False,
        help='Total number of AI search images'
    )
    
    completed_views = fields.Integer(
        string='Processed Views',
        compute='_compute_search_image_stats', 
        store=False,
        help='Number of successfully processed images'
    )
    
    is_multiview_product = fields.Boolean(
        string='Multi-View Product',
        compute='_compute_search_image_stats',
        store=False,
        help='True if product has multiple view angles'
    )
    
    images_processing_status = fields.Char(
        string='Processing Status',
        compute='_compute_search_image_stats',
        store=False,
        help='Overall processing status of all images'
    )
    
    primary_search_image_id = fields.Many2one(
        'ai.product.image',
        string='Primary Search Image', 
        compute='_compute_search_image_stats',
        store=False,
        help='Main image used for search comparisons'
    )
    
    # =======================
    # COMPUTED METHODS
    # =======================
    
    @api.depends('product_image_ids', 'product_image_ids.processing_status', 
                 'product_image_ids.is_primary_view', 'product_image_ids.view_type')
    def _compute_search_image_stats(self):
        """Compute comprehensive statistics for AI search images"""
        for record in self:
            images = record.product_image_ids
            
            # Basic counts
            record.search_images_count = len(images)
            record.has_search_images = len(images) > 0
            
            # Processing status counts
            completed_images = images.filtered(lambda x: x.processing_status == 'completed')
            processing_images = images.filtered(lambda x: x.processing_status == 'processing') 
            failed_images = images.filtered(lambda x: x.processing_status == 'failed')
            pending_images = images.filtered(lambda x: x.processing_status == 'pending')
            
            record.completed_views = len(completed_images)
            record.is_multiview_product = len(images) > 1
            
            # Overall processing status
            if not images:
                record.images_processing_status = 'No Images'
            elif len(completed_images) == len(images):
                record.images_processing_status = f'All Processed ({len(completed_images)})'
            elif len(failed_images) > 0:
                record.images_processing_status = f'Some Failed ({len(failed_images)}/{len(images)})'
            elif len(processing_images) > 0:
                record.images_processing_status = f'Processing... ({len(processing_images)})'
            elif len(pending_images) > 0:
                record.images_processing_status = f'Pending ({len(pending_images)})'
            else:
                record.images_processing_status = 'Mixed Status'
            
            # Primary image selection
            # Priority: Primary view that's completed > Any completed > Any primary > First image
            primary_completed = completed_images.filtered(lambda x: x.is_primary_view)
            if primary_completed:
                record.primary_search_image_id = primary_completed[0]
            elif completed_images:
                record.primary_search_image_id = completed_images[0] 
            elif images.filtered(lambda x: x.is_primary_view):
                record.primary_search_image_id = images.filtered(lambda x: x.is_primary_view)[0]
            elif images:
                record.primary_search_image_id = images[0]
            else:
                record.primary_search_image_id = False
    
    # =======================
    # ACTION METHODS
    # =======================
    
    def action_process_all_images(self):
        """Process all pending/failed images for this product"""
        try:
            # Find images that need processing
            processable_images = self.product_image_ids.filtered(
                lambda x: x.processing_status in ['pending', 'failed']
            )
            
            if not processable_images:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Images to Process',
                        'message': f'All {len(self.product_image_ids)} images are already processed or currently processing.',
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            # Schedule processing for all processable images
            processed_count = 0
            for image in processable_images:
                try:
                    image._schedule_delayed_auto_processing()
                    processed_count += 1
                except Exception as e:
                    _logger.warning(f"Failed to schedule processing for image {image.image_name}: {e}")
            
            return {
                'type': 'ir.actions.client', 
                'tag': 'display_notification',
                'params': {
                    'title': 'Batch Processing Started',
                    'message': f'Scheduled {processed_count} images for processing. Check status in a few moments.',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Batch processing failed for product {self.name}: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification', 
                'params': {
                    'title': 'Processing Failed',
                    'message': f'Error during batch processing: {str(e)[:100]}...',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_reset_failed_images(self):
        """Reset all failed images to pending status for retry"""
        try:
            failed_images = self.product_image_ids.filtered(
                lambda x: x.processing_status == 'failed'
            )
            
            if not failed_images:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Failed Images',
                        'message': 'All images are processed successfully or pending.',
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            # Reset failed images and schedule reprocessing
            reset_count = 0
            for image in failed_images:
                try:
                    image.write({
                        'processing_status': 'pending',
                        'processing_error': False,
                        'vector_size': 0,
                        'feature_vector': False,
                        'combined_features': False,
                    })
                    # Schedule reprocessing
                    image._schedule_delayed_auto_processing()
                    reset_count += 1
                except Exception as e:
                    _logger.warning(f"Failed to reset image {image.image_name}: {e}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Images Reset Successfully',
                    'message': f'Reset and scheduled {reset_count} failed images for reprocessing.',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Reset failed images error for product {self.name}: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reset Failed',
                    'message': f'Error during reset: {str(e)[:100]}...',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_delete_all_images(self):
        """Delete all AI search images for this product"""
        try:
            images_count = len(self.product_image_ids)
            
            if images_count == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Images to Delete',
                        'message': 'This product has no AI search images.',
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            # Delete all images
            self.product_image_ids.unlink()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Images Deleted',
                    'message': f'Deleted {images_count} AI search images.',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Delete all images failed for product {self.name}: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Delete Failed',
                    'message': f'Error: {str(e)[:100]}...',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # =======================
    # SEARCH & SIMILARITY METHODS
    # =======================
    
    def get_best_matching_image(self, search_features=None):
        """Get the best image for similarity comparison"""
        try:
            # Get only successfully processed images
            completed_images = self.product_image_ids.filtered(
                lambda x: x.processing_status == 'completed' and 
                         (x.feature_vector or x.combined_features)
            )
            
            if not completed_images:
                return None
            
            # Priority 1: Images with combined multi-view features (most comprehensive)
            multiview_images = completed_images.filtered(lambda x: x.combined_features)
            if multiview_images:
                # Prefer primary view among multi-view images
                primary_multiview = multiview_images.filtered(lambda x: x.is_primary_view)
                return primary_multiview[0] if primary_multiview else multiview_images[0]
            
            # Priority 2: Primary view images (main perspective)
            primary_images = completed_images.filtered(lambda x: x.is_primary_view)
            if primary_images:
                return primary_images[0]
            
            # Priority 3: Any completed image (fallback)
            return completed_images[0]
            
        except Exception as e:
            _logger.error(f"Best matching image selection failed for {self.name}: {e}")
            return None
    
    def calculate_product_similarity(self, other_product):
        """Calculate similarity score between two products using their best images"""
        try:
            if not other_product or other_product.id == self.id:
                return 0.0
            
            # Get best representative images from both products
            self_image = self.get_best_matching_image()
            other_image = other_product.get_best_matching_image()
            
            if not self_image or not other_image:
                return 0.0
            
            # Use the advanced multi-view similarity calculation
            similarity = self_image.calculate_multiview_similarity(other_image)
            
            # Apply product-level bonuses
            # Same category bonus
            if self.categ_id and other_product.categ_id and self.categ_id.id == other_product.categ_id.id:
                similarity *= 1.05  # 5% bonus for same category
            
            # Similar name bonus (basic text similarity)
            if self.name and other_product.name:
                name_similarity = self._calculate_name_similarity(self.name, other_product.name)
                similarity += (name_similarity * 0.02)  # Small text similarity bonus
            
            return min(float(similarity), 1.0)  # Cap at 1.0
            
        except Exception as e:
            _logger.error(f"Product similarity calculation failed between {self.name} and {other_product.name}: {e}")
            return 0.0
    
    def _calculate_name_similarity(self, name1, name2):
        """Simple text similarity for product names"""
        try:
            # Convert to lowercase and split into words
            words1 = set(name1.lower().split())
            words2 = set(name2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            # Jaccard similarity (intersection / union)
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            _logger.warning(f"Name similarity calculation failed: {e}")
            return 0.0
    
    def find_similar_products(self, limit=10, min_confidence=0.7):
        """Find products similar to this product using AI image matching"""
        try:
            if not self.has_search_images or not self.primary_search_image_id:
                return []
            
            # Get all other products with processed images
            other_products = self.env['product.template'].search([
                ('id', '!=', self.id),
                ('has_search_images', '=', True),
                ('completed_views', '>', 0)
            ])
            
            if not other_products:
                return []
            
            # Calculate similarities
            similarities = []
            for product in other_products:
                try:
                    similarity = self.calculate_product_similarity(product)
                    if similarity >= min_confidence:
                        similarities.append({
                            'product': product,
                            'similarity': similarity,
                            'confidence_percentage': round(similarity * 100, 1)
                        })
                except Exception as e:
                    _logger.warning(f"Similarity calculation failed for product {product.name}: {e}")
                    continue
            
            # Sort by similarity (highest first) and limit results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            _logger.error(f"Find similar products failed for {self.name}: {e}")
            return []
    
    # =======================
    # UI ACTION METHODS
    # =======================
    
    def action_open_image_search_wizard(self):
        """Open AI image search wizard from product form"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Image Search',
            'res_model': 'image.search.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_search_from_product': True,
                'default_product_id': self.id,
                'form_view_initial_mode': 'edit'
            }
        }
    
    def action_view_ai_images(self):
        """Open AI images in tree/form view"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'AI Images - {self.name}',
            'res_model': 'ai.product.image',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'create': True,
                'edit': True,
            }
        }
    
    def action_find_similar_products(self):
        """Find and display similar products"""
        try:
            similar_products = self.find_similar_products(limit=20, min_confidence=0.6)
            
            if not similar_products:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Similar Products Found',
                        'message': 'No similar products found with sufficient confidence level.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            # Create context with similarity data
            similarity_context = {
                'search_mode': True,
                'similarity_data': {
                    str(item['product'].id): item['confidence_percentage'] 
                    for item in similar_products
                },
                'reference_product_id': self.id,
            }
            
            # Get product IDs for domain
            product_ids = [item['product'].id for item in similar_products]
            
            return {
                'type': 'ir.actions.act_window',
                'name': f'Products Similar to "{self.name}" ({len(similar_products)} found)',
                'res_model': 'product.template',
                'view_mode': 'kanban,tree,form',
                'domain': [('id', 'in', product_ids)],
                'context': similarity_context,
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Find similar products action failed: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Search Failed',
                    'message': f'Error: {str(e)[:100]}...',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # =======================
    # UTILITY METHODS
    # =======================
    
    def get_image_processing_summary(self):
        """Get detailed processing summary for debugging"""
        try:
            images = self.product_image_ids
            if not images:
                return "No AI search images"
            
            summary = {
                'total': len(images),
                'completed': len(images.filtered(lambda x: x.processing_status == 'completed')),
                'processing': len(images.filtered(lambda x: x.processing_status == 'processing')),
                'pending': len(images.filtered(lambda x: x.processing_status == 'pending')),
                'failed': len(images.filtered(lambda x: x.processing_status == 'failed')),
                'multiview': len(images.filtered(lambda x: x.combined_features)),
                'primary_views': len(images.filtered(lambda x: x.is_primary_view)),
            }
            
            return f"Total: {summary['total']}, Completed: {summary['completed']}, " \
                   f"Failed: {summary['failed']}, Multi-view: {summary['multiview']}"
            
        except Exception as e:
            return f"Error getting summary: {e}"
    
    def validate_ai_images_setup(self):
        """Validate AI images setup for this product"""
        try:
            validation_results = {
                'valid': True,
                'warnings': [],
                'errors': [],
                'recommendations': []
            }
            
            if not self.product_image_ids:
                validation_results['errors'].append("No AI search images found")
                validation_results['valid'] = False
                return validation_results
            
            completed_images = self.product_image_ids.filtered(lambda x: x.processing_status == 'completed')
            if not completed_images:
                validation_results['errors'].append("No processed images available for search")
                validation_results['valid'] = False
            
            primary_images = self.product_image_ids.filtered(lambda x: x.is_primary_view)
            if not primary_images:
                validation_results['warnings'].append("No primary view image defined")
            
            failed_images = self.product_image_ids.filtered(lambda x: x.processing_status == 'failed')
            if failed_images:
                validation_results['warnings'].append(f"{len(failed_images)} images failed to process")
            
            if len(completed_images) == 1:
                validation_results['recommendations'].append("Consider adding more view angles for better accuracy")
            
            return validation_results
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation failed: {e}"],
                'warnings': [],
                'recommendations': []
            }