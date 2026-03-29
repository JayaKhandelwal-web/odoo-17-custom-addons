"""
Database Feature Verification Tool
Checks if feature vectors are actually extracted and stored properly
Helps diagnose whether the issue is in feature extraction or similarity matching
"""

import json
import logging
import numpy as np
from datetime import datetime

_logger = logging.getLogger(__name__)

def verify_database_features(env):
    """
    Comprehensive verification of feature extraction in database
    Returns detailed report about what's actually stored
    """
    try:
        if env is None:
            return {'error': 'No environment provided'}
        
        # Check if model exists
        model_name = 'ai.product.image'
        if model_name not in env:
            return {'error': f'Model {model_name} not found in environment'}
        
        verification_report = {
            'timestamp': datetime.now().isoformat(),
            'database_stats': {},
            'feature_analysis': {},
            'processing_status_analysis': {},
            'sample_records': [],
            'issues_found': [],
            'recommendations': []
        }
        
        # 1. Basic database statistics
        try:
            all_images = env[model_name].search([])
            total_count = len(all_images)
            
            # Count by processing status
            status_counts = {}
            for status in ['pending', 'processing', 'completed', 'processed', 'failed', 'error']:
                count = env[model_name].search_count([('processing_status', '=', status)])
                if count > 0:
                    status_counts[status] = count
            
            # Count images with feature vectors
            with_features = env[model_name].search_count([('feature_vector', '!=', False)])
            with_non_empty_features = env[model_name].search_count([
                ('feature_vector', '!=', False),
                ('feature_vector', '!=', '')
            ])
            
            verification_report['database_stats'] = {
                'total_images': total_count,
                'status_breakdown': status_counts,
                'images_with_feature_vectors': with_features,
                'images_with_non_empty_features': with_non_empty_features
            }
            
        except Exception as e:
            verification_report['issues_found'].append(f"Database stats collection failed: {e}")
        
        # 2. Detailed analysis of records with "completed" status
        try:
            completed_images = env[model_name].search([
                ('processing_status', '=', 'completed')
            ], limit=20)  # Analyze first 20
            
            feature_analysis = {
                'completed_status_count': len(completed_images),
                'actually_have_features': 0,
                'valid_feature_vectors': 0,
                'invalid_feature_vectors': 0,
                'feature_vector_lengths': [],
                'feature_vector_stats': []
            }
            
            for i, image in enumerate(completed_images[:10]):  # Detailed analysis of first 10
                record_analysis = {
                    'id': image.id,
                    'image_name': getattr(image, 'image_name', 'Unknown'),
                    'processing_status': image.processing_status,
                    'has_feature_vector': bool(image.feature_vector),
                    'feature_vector_type': type(image.feature_vector).__name__,
                    'feature_vector_length': None,
                    'feature_stats': None,
                    'is_valid_json': False,
                    'is_valid_features': False,
                    'issues': []
                }
                
                # Analyze feature vector
                if image.feature_vector:
                    feature_analysis['actually_have_features'] += 1
                    
                    try:
                        # Check if it's JSON string
                        if isinstance(image.feature_vector, str):
                            parsed_features = json.loads(image.feature_vector)
                            record_analysis['is_valid_json'] = True
                        else:
                            parsed_features = image.feature_vector
                        
                        # Convert to numpy array for analysis
                        features_array = np.array(parsed_features, dtype=np.float32)
                        record_analysis['feature_vector_length'] = len(features_array)
                        feature_analysis['feature_vector_lengths'].append(len(features_array))
                        
                        # Analyze feature statistics
                        if len(features_array) > 0:
                            stats = {
                                'mean': float(np.mean(features_array)),
                                'std': float(np.std(features_array)),
                                'min': float(np.min(features_array)),
                                'max': float(np.max(features_array)),
                                'non_zero_count': int(np.sum(features_array != 0)),
                                'nan_count': int(np.sum(np.isnan(features_array))),
                                'inf_count': int(np.sum(np.isinf(features_array)))
                            }
                            record_analysis['feature_stats'] = stats
                            feature_analysis['feature_vector_stats'].append(stats)
                            
                            # Check if features are valid
                            if (len(features_array) == 512 and 
                                stats['non_zero_count'] > 0 and 
                                stats['nan_count'] == 0 and 
                                stats['inf_count'] == 0):
                                record_analysis['is_valid_features'] = True
                                feature_analysis['valid_feature_vectors'] += 1
                            else:
                                feature_analysis['invalid_feature_vectors'] += 1
                                
                                # Identify specific issues
                                if len(features_array) != 512:
                                    record_analysis['issues'].append(f"Wrong length: {len(features_array)} (expected 512)")
                                if stats['non_zero_count'] == 0:
                                    record_analysis['issues'].append("All features are zero")
                                if stats['nan_count'] > 0:
                                    record_analysis['issues'].append(f"Contains {stats['nan_count']} NaN values")
                                if stats['inf_count'] > 0:
                                    record_analysis['issues'].append(f"Contains {stats['inf_count']} infinite values")
                        else:
                            record_analysis['issues'].append("Empty feature vector")
                            feature_analysis['invalid_feature_vectors'] += 1
                    
                    except json.JSONDecodeError as e:
                        record_analysis['issues'].append(f"JSON parsing failed: {e}")
                        feature_analysis['invalid_feature_vectors'] += 1
                    except Exception as e:
                        record_analysis['issues'].append(f"Feature analysis failed: {e}")
                        feature_analysis['invalid_feature_vectors'] += 1
                else:
                    record_analysis['issues'].append("No feature vector stored")
                
                verification_report['sample_records'].append(record_analysis)
            
            verification_report['feature_analysis'] = feature_analysis
            
        except Exception as e:
            verification_report['issues_found'].append(f"Feature analysis failed: {e}")
        
        # 3. Test feature extraction on a sample
        try:
            # Get one image that supposedly has features
            test_image = env[model_name].search([
                ('processing_status', '=', 'completed'),
                ('feature_vector', '!=', False)
            ], limit=1)
            
            if test_image:
                test_record = test_image[0]
                
                # Try to re-extract features from the same image
                if hasattr(test_record, 'image_file') and test_record.image_file:
                    try:
                        from .feature_extractor import get_feature_extractor
                        extractor = get_feature_extractor()
                        
                        # Re-extract features
                        new_features = extractor.extract_features(test_record.image_file)
                        
                        extraction_test = {
                            'test_image_id': test_record.id,
                            'extraction_successful': new_features is not None,
                            'new_feature_length': len(new_features) if new_features is not None else 0,
                            'new_feature_stats': None
                        }
                        
                        if new_features is not None:
                            extraction_test['new_feature_stats'] = {
                                'mean': float(np.mean(new_features)),
                                'std': float(np.std(new_features)),
                                'non_zero_count': int(np.sum(new_features != 0))
                            }
                            
                            # Compare with stored features
                            if test_record.feature_vector:
                                try:
                                    stored_features = json.loads(test_record.feature_vector)
                                    stored_array = np.array(stored_features, dtype=np.float32)
                                    
                                    if len(stored_array) == len(new_features):
                                        similarity = np.corrcoef(new_features, stored_array)[0,1]
                                        extraction_test['consistency_with_stored'] = float(similarity) if not np.isnan(similarity) else 0.0
                                    else:
                                        extraction_test['consistency_with_stored'] = 'Length mismatch'
                                except:
                                    extraction_test['consistency_with_stored'] = 'Comparison failed'
                        
                        verification_report['extraction_test'] = extraction_test
                        
                    except Exception as e:
                        verification_report['issues_found'].append(f"Feature extraction test failed: {e}")
                
        except Exception as e:
            verification_report['issues_found'].append(f"Extraction test setup failed: {e}")
        
        # 4. Generate recommendations based on findings
        issues = verification_report['issues_found']
        feature_analysis = verification_report.get('feature_analysis', {})
        
        if feature_analysis.get('valid_feature_vectors', 0) == 0:
            verification_report['recommendations'].append("CRITICAL: No valid feature vectors found - feature extraction is not working")
            verification_report['root_cause'] = 'feature_extraction_failure'
        elif feature_analysis.get('valid_feature_vectors', 0) < feature_analysis.get('completed_status_count', 0) * 0.5:
            verification_report['recommendations'].append("WARNING: Less than 50% of 'completed' records have valid features")
            verification_report['root_cause'] = 'partial_feature_extraction_failure'
        else:
            verification_report['recommendations'].append("Feature extraction appears to be working - issue may be in similarity matching")
            verification_report['root_cause'] = 'similarity_matching_issue'
        
        # Additional recommendations
        if feature_analysis.get('actually_have_features', 0) == 0:
            verification_report['recommendations'].append("No feature vectors stored at all - check image processing pipeline")
        
        if len(set(feature_analysis.get('feature_vector_lengths', []))) > 1:
            verification_report['recommendations'].append("Inconsistent feature vector lengths detected")
        
        # Summary
        verification_report['summary'] = {
            'total_images': verification_report['database_stats'].get('total_images', 0),
            'completed_status': feature_analysis.get('completed_status_count', 0),
            'valid_features': feature_analysis.get('valid_feature_vectors', 0),
            'feature_extraction_working': feature_analysis.get('valid_feature_vectors', 0) > 0,
            'likely_root_cause': verification_report.get('root_cause', 'unknown')
        }
        
        return verification_report
        
    except Exception as e:
        _logger.error(f"Database verification failed: {e}")
        return {
            'error': f'Verification failed: {e}',
            'timestamp': datetime.now().isoformat()
        }

def quick_feature_check(env, limit=5):
    """Quick check of feature extraction status"""
    try:
        model_name = 'ai.product.image'
        if model_name not in env:
            return {'error': f'Model {model_name} not found'}
        
        # Get sample of completed images
        completed_images = env[model_name].search([
            ('processing_status', '=', 'completed')
        ], limit=limit)
        
        results = []
        for img in completed_images:
            result = {
                'id': img.id,
                'name': getattr(img, 'image_name', 'Unknown'),
                'has_feature_vector': bool(img.feature_vector),
                'feature_vector_valid': False
            }
            
            if img.feature_vector:
                try:
                    if isinstance(img.feature_vector, str):
                        features = json.loads(img.feature_vector)
                    else:
                        features = img.feature_vector
                    
                    features_array = np.array(features, dtype=np.float32)
                    
                    if (len(features_array) == 512 and 
                        np.sum(features_array != 0) > 0 and 
                        not np.any(np.isnan(features_array))):
                        result['feature_vector_valid'] = True
                        result['non_zero_features'] = int(np.sum(features_array != 0))
                        result['feature_mean'] = float(np.mean(features_array))
                
                except:
                    result['parse_error'] = True
            
            results.append(result)
        
        summary = {
            'total_checked': len(results),
            'have_feature_vectors': sum(1 for r in results if r['has_feature_vector']),
            'valid_feature_vectors': sum(1 for r in results if r['feature_vector_valid']),
            'extraction_working': any(r['feature_vector_valid'] for r in results)
        }
        
        return {
            'summary': summary,
            'details': results,
            'diagnosis': 'Feature extraction working' if summary['extraction_working'] else 'Feature extraction NOT working'
        }
        
    except Exception as e:
        return {'error': f'Quick check failed: {e}'}

def test_single_image_extraction(env, image_id=None):
    """Test feature extraction on a specific image"""
    try:
        model_name = 'ai.product.image'
        if model_name not in env:
            return {'error': f'Model {model_name} not found'}
        
        # Get image record
        if image_id:
            image_record = env[model_name].browse(image_id)
        else:
            # Get any image with an actual image file
            records = env[model_name].search([('image_file', '!=', False)], limit=1)
            if not records:
                return {'error': 'No images with image files found'}
            image_record = records[0]
        
        if not image_record.image_file:
            return {'error': 'Image has no image file'}
        
        # Test extraction
        from .feature_extractor import get_feature_extractor
        extractor = get_feature_extractor()
        
        extraction_result = {
            'image_id': image_record.id,
            'image_name': getattr(image_record, 'image_name', 'Unknown'),
            'extraction_attempted': True,
            'extraction_successful': False,
            'feature_details': None,
            'error': None
        }
        
        try:
            features = extractor.extract_features(image_record.image_file)
            
            if features is not None:
                extraction_result['extraction_successful'] = True
                extraction_result['feature_details'] = {
                    'length': len(features),
                    'non_zero_count': int(np.sum(features != 0)),
                    'mean': float(np.mean(features)),
                    'std': float(np.std(features)),
                    'has_nan': bool(np.any(np.isnan(features))),
                    'has_inf': bool(np.any(np.isinf(features)))
                }
            else:
                extraction_result['error'] = 'Feature extraction returned None'
                
        except Exception as e:
            extraction_result['error'] = f'Feature extraction failed: {e}'
        
        return extraction_result
        
    except Exception as e:
        return {'error': f'Single image test failed: {e}'}

# Utility function for Odoo integration
def diagnose_search_issue(env):
    """Main diagnostic function to determine root cause of search issues"""
    try:
        # Run comprehensive verification
        verification = verify_database_features(env)
        
        # Quick assessment
        if 'error' in verification:
            return {
                'diagnosis': 'Database access error',
                'issue': 'database_access',
                'details': verification,
                'next_steps': ['Check database connection', 'Verify model exists']
            }
        
        root_cause = verification.get('root_cause', 'unknown')
        summary = verification.get('summary', {})
        
        if root_cause == 'feature_extraction_failure':
            return {
                'diagnosis': 'Feature extraction is not working properly',
                'issue': 'feature_extraction',
                'evidence': {
                    'completed_images': summary.get('completed_status', 0),
                    'valid_features': summary.get('valid_features', 0),
                    'extraction_working': summary.get('feature_extraction_working', False)
                },
                'next_steps': [
                    'Check feature extractor code',
                    'Test single image extraction',
                    'Verify image processing pipeline',
                    'Check for Python/library errors'
                ],
                'verification_report': verification
            }
        
        elif root_cause == 'partial_feature_extraction_failure':
            return {
                'diagnosis': 'Feature extraction working partially - some images not processed correctly',
                'issue': 'partial_feature_extraction',
                'evidence': summary,
                'next_steps': [
                    'Re-process failed images',
                    'Check for specific image format issues',
                    'Review processing logs'
                ],
                'verification_report': verification
            }
        
        else:
            return {
                'diagnosis': 'Feature extraction appears working - issue likely in similarity matching',
                'issue': 'similarity_matching',
                'evidence': summary,
                'next_steps': [
                    'Test similarity matcher with known features',
                    'Check confidence thresholds',
                    'Review similarity calculation logic',
                    'Test with lower confidence thresholds'
                ],
                'verification_report': verification
            }
            
    except Exception as e:
        return {
            'diagnosis': f'Diagnostic failed: {e}',
            'issue': 'diagnostic_error',
            'next_steps': ['Check system logs', 'Verify environment setup']
        }