from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import logging
import numpy as np
import json

_logger = logging.getLogger(__name__)

class MultiViewAIProductImage(models.Model):
    _name = 'ai.product.image'
    _description = 'Multi-View AI Product Images with Direct Processing'
    _order = 'upload_date desc'
    
    # Basic Fields
    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    image_name = fields.Char(string='Image Name', required=True)
    image_file = fields.Binary(string='Image File', required=True, attachment=True)
    
    # Multi-View Fields
    view_type = fields.Selection([
        ('primary', 'Primary View'),
        ('side', 'Side View'), 
        ('left', 'Left View'),
        ('right', 'Right View'),
        ('top', 'Top View'),
        ('bottom', 'Bottom View'),
        ('angled', 'Angled View'),
        ('detail', 'Detail View'),
        ('low_light', 'Low Light View'),
        ('back', 'Back View')
    ], string='View Type', required=True, default='primary')
    
    is_primary_view = fields.Boolean(string='Primary View', default=False)
    
    # Auto-Processing Fields
    feature_vector = fields.Text(string='Individual Features')
    combined_features = fields.Text(string='Multi-View Combined Features')
    processing_status = fields.Selection([
        ('pending', 'Pending Processing'),
        ('processing', 'Currently Processing'),
        ('completed', 'Processing Complete'),
        ('failed', 'Processing Failed')
    ], string='Status', default='pending')
    
    vector_size = fields.Integer(string='Feature Count', default=0)
    processing_error = fields.Text(string='Processing Error')
    
    # Multi-View Relationships
    related_views = fields.One2many('ai.product.image', 'primary_image_id', string='Related Views')
    primary_image_id = fields.Many2one('ai.product.image', string='Primary Image')
    view_count = fields.Integer(string='Total Views', compute='_compute_view_count')
    
    # Metadata
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)
    last_processed = fields.Datetime(string='Last Processed')
    thumbnail = fields.Binary(string='Thumbnail')
    file_size = fields.Float(string='File Size (MB)', compute='_compute_file_size', store=True)
    
    @api.depends('related_views')
    def _compute_view_count(self):
        for record in self:
            if record.is_primary_view:
                record.view_count = len(record.related_views) + 1
            else:
                record.view_count = len(record.primary_image_id.related_views) + 1 if record.primary_image_id else 1
    
    @api.depends('image_file')
    def _compute_file_size(self):
        for record in self:
            if record.image_file:
                try:
                    size_bytes = len(base64.b64decode(record.image_file))
                    record.file_size = round(size_bytes / (1024 * 1024), 2)
                except:
                    record.file_size = 0.0
            else:
                record.file_size = 0.0
    
    @api.model
    def create(self, vals):
        """Enhanced create with direct processing (no threading)"""
        try:
            # Validate image data before creation
            if vals.get('image_file'):
                # Clean up base64 data (remove data URL prefix if present)
                image_data = vals['image_file']
                if image_data.startswith('data:'):
                    image_data = image_data.split(',', 1)[-1]
                
                # Ensure base64 padding is correct
                missing_padding = len(image_data) % 4
                if missing_padding:
                    image_data += '=' * (4 - missing_padding)
                
                vals['image_file'] = image_data
            
            record = super().create(vals)
            
            # Auto-generate thumbnail
            if record.image_file:
                record.thumbnail = record.image_file
            
            # Direct processing (no background threading)
            record._direct_auto_processing()
            
            return record
            
        except Exception as e:
            _logger.error(f"Image creation failed: {e}")
            raise ValidationError(f"Could not create image record: {str(e)}")
    
    def write(self, vals):
        """Enhanced write with direct processing (no threading)"""
        try:
            # Validate image data before update
            if vals.get('image_file'):
                image_data = vals['image_file']
                if image_data.startswith('data:'):
                    image_data = image_data.split(',', 1)[-1]
                
                # Fix base64 padding
                missing_padding = len(image_data) % 4
                if missing_padding:
                    image_data += '=' * (4 - missing_padding)
                
                vals['image_file'] = image_data
            
            result = super().write(vals)
            
            # If image file changed, update thumbnail and reprocess
            if 'image_file' in vals:
                for record in self:
                    if record.image_file:
                        record.thumbnail = record.image_file
                        # Direct reprocessing
                        record._direct_auto_processing()
            
            return result
            
        except Exception as e:
            _logger.error(f"Image update failed: {e}")
            raise ValidationError(f"Could not update image record: {str(e)}")
    
    def _direct_auto_processing(self):
        """Direct feature extraction without background threading"""
        try:
            self.processing_status = 'processing'
            self.processing_error = None
            
            # Commit status immediately so user can see processing started
            self.env.cr.commit()
            
            _logger.info(f"Starting direct processing for {self.image_name}")
            
            # Extract features from this image
            individual_features = self._extract_individual_features()
            
            if individual_features is not None:
                self.feature_vector = json.dumps(individual_features.tolist())
                self.vector_size = len(individual_features)
                
                # Update multi-view combined features
                self._update_multiview_features()
                
                self.processing_status = 'completed'
                self.last_processed = fields.Datetime.now()
                
                # Commit completion
                self.env.cr.commit()
                
                _logger.info(f"Direct processing completed for {self.image_name}: {self.vector_size} features extracted")
            else:
                raise Exception("Feature extraction returned None")
                
        except Exception as e:
            self.processing_status = 'failed'
            self.processing_error = str(e)
            self.env.cr.commit()
            _logger.error(f"Direct processing failed for {self.image_name}: {e}")
    
    def _extract_individual_features(self):
        """Extract features from single image"""
        try:
            from ..ai_engine.feature_extractor import get_feature_extractor
            
            extractor = get_feature_extractor()
            features = extractor.extract_features(self.image_file)
            
            return features
            
        except Exception as e:
            _logger.error(f"Individual feature extraction failed: {e}")
            return None
    
    def _update_multiview_features(self):
        """Update combined multi-view features for related images"""
        try:
            # Get all related views (including this one)
            if self.is_primary_view:
                all_views = [self] + list(self.related_views.filtered(lambda x: x.processing_status == 'completed'))
            elif self.primary_image_id:
                primary = self.primary_image_id
                all_views = [primary] + list(primary.related_views.filtered(lambda x: x.processing_status == 'completed'))
            else:
                all_views = [self]  # Single view
            
            # Collect features from all processed views
            view_features = []
            for view in all_views:
                if view.feature_vector and view.processing_status == 'completed':
                    try:
                        features = np.array(json.loads(view.feature_vector))
                        view_features.append({
                            'features': features,
                            'view_type': view.view_type,
                            'is_primary': view.is_primary_view
                        })
                    except:
                        continue
            
            if len(view_features) > 1:
                # Combine multi-view features
                combined = self._combine_view_features(view_features)
                combined_json = json.dumps(combined.tolist())
                
                # Update combined features for all related views
                for view in all_views:
                    view.combined_features = combined_json
                
                _logger.info(f"Multi-view features updated for {len(all_views)} views of product {self.product_id.name}")
            
        except Exception as e:
            _logger.error(f"Multi-view feature update failed: {e}")
    
    def _combine_view_features(self, view_features_list):
        """Statistically combine features from multiple views"""
        try:
            # Extract feature arrays
            feature_arrays = [vf['features'] for vf in view_features_list]
            
            # Stack features
            stacked_features = np.array(feature_arrays)
            
            # Statistical combinations
            mean_features = np.mean(stacked_features, axis=0)
            max_features = np.max(stacked_features, axis=0)
            
            # View-weighted features (primary view gets higher weight)
            weights = []
            for vf in view_features_list:
                if vf['is_primary']:
                    weights.append(2.0)  # Primary view double weight
                elif vf['view_type'] in ['side', 'angled']:
                    weights.append(1.5)  # Important views higher weight
                else:
                    weights.append(1.0)  # Standard weight
            
            weights = np.array(weights).reshape(-1, 1)
            weighted_features = np.average(stacked_features, axis=0, weights=weights.flatten())
            
            # Combine different statistical measures
            combined = np.concatenate([
                weighted_features,                    # Weighted average (most important)
                mean_features[:len(mean_features)//3],  # Global mean (reduced)
                max_features[:len(max_features)//3],    # Peak features (reduced)
            ])
            
            return combined.astype(np.float32)
            
        except Exception as e:
            _logger.error(f"Feature combination failed: {e}")
            # Fallback to mean of all features
            feature_arrays = [vf['features'] for vf in view_features_list]
            return np.mean(feature_arrays, axis=0).astype(np.float32)
    
    def calculate_multiview_similarity(self, other_image):
        """Calculate similarity using multi-view enhanced features"""
        try:
            # Use combined features if available, otherwise individual features
            features1 = self._get_best_features()
            features2 = other_image._get_best_features()
            
            if features1 is None or features2 is None:
                return 0.0
            
            # Multi-view enhanced cosine similarity
            similarity = self._enhanced_cosine_similarity(features1, features2)
            
            # View type bonus (same view types get slight bonus)
            if self.view_type == other_image.view_type:
                similarity *= 1.05  # 5% bonus
            
            # Multi-view bonus (parts with more views get reliability bonus)
            view_bonus = min(self.view_count, other_image.view_count) / 20.0
            similarity += view_bonus
            
            return min(float(similarity), 1.0)  # Cap at 1.0
            
        except Exception as e:
            _logger.error(f"Multi-view similarity calculation failed: {e}")
            return 0.0
    
    def _get_best_features(self):
        """Get the best available features (combined if available, otherwise individual)"""
        try:
            # Prefer combined multi-view features
            if self.combined_features:
                return np.array(json.loads(self.combined_features))
            elif self.feature_vector:
                return np.array(json.loads(self.feature_vector))
            else:
                return None
        except:
            return None
    
    def _enhanced_cosine_similarity(self, vec1, vec2):
        """Enhanced cosine similarity with multi-view considerations"""
        try:
            # Ensure same dimensions
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
            
            # Standard cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 > 0 and norm2 > 0:
                return dot_product / (norm1 * norm2)
            return 0.0
        except:
            return 0.0
    
    # Manual Processing Actions
    def action_manual_process(self):
        """Manual processing trigger for individual images"""
        try:
            if self.processing_status == 'processing':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Already Processing',
                        'message': f'Image {self.image_name} is already being processed.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            self._direct_auto_processing()
            
            if self.processing_status == 'completed':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Processing Completed',
                        'message': f'Successfully processed {self.image_name}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Processing Failed',
                        'message': f'Failed to process {self.image_name}: {self.processing_error}',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Manual processing action failed: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Processing Error',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # Display Methods
    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = f"{record.product_id.name} - {record.view_type} ({record.processing_status})"
            result.append((record.id, name))
        return result