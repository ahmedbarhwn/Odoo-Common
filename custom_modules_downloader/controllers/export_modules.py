from odoo import http, tools
from odoo.http import request, content_disposition
from odoo.exceptions import UserError
import zipfile
import os
import io
import logging

_logger = logging.getLogger(__name__)

class ExportModulesController(http.Controller):

    def _get_custom_addons_paths(self):
        """Get custom addons paths only"""
        custom_paths = []
        
        # Get addons paths from tools.config
        if hasattr(tools.config, 'options') and 'addons_path' in tools.config.options:
            paths = tools.config.options['addons_path'].split(',')
            for path in paths:
                path = path.strip()
                if path and ('custom' in path.lower() or 'addons' in path.lower()):
                    if os.path.exists(path):
                        custom_paths.append(path)
        
        # Common custom paths
        common_custom_paths = [
            '/odoo/custom_addons',
            '/mnt/extra-addons',
            './custom_addons',
            '/opt/odoo/custom_addons',
            '/var/lib/odoo/addons',
        ]
        
        for path in common_custom_paths:
            if os.path.exists(path) and path not in custom_paths:
                custom_paths.append(path)
        
        return custom_paths

    def _is_custom_module(self, module_path):
        """Check if module is a custom module (has __manifest__.py or __openerp__.py)"""
        manifest_files = ['__manifest__.py', '__openerp__.py']
        return any(os.path.exists(os.path.join(module_path, mf)) for mf in manifest_files)

    @http.route('/export/custom_modules', type='http', auth='public', methods=['GET'])
    def export_custom_modules(self, **kwargs):
        """Export all custom modules only"""
        try:
            custom_paths = self._get_custom_addons_paths()
            
            if not custom_paths:
                return request.make_response(
                    "No custom addons paths found",
                    status=404,
                    headers=[('Content-Type', 'text/plain')]
                )
            
            buffer = io.BytesIO()
            modules_count = 0
            
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for addons_path in custom_paths:
                    if not os.path.exists(addons_path):
                        continue
                    
                    _logger.info(f"Processing custom addons path: {addons_path}")
                    
                    # Get only directories that are valid modules
                    for item in os.listdir(addons_path):
                        item_path = os.path.join(addons_path, item)
                        
                        if os.path.isdir(item_path) and self._is_custom_module(item_path):
                            modules_count += 1
                            _logger.info(f"Adding custom module: {item}")
                            
                            # Add all files in the module
                            for root, dirs, files in os.walk(item_path):
                                # Skip hidden directories and __pycache__
                                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                                
                                for file in files:
                                    # Skip compiled Python files and other unwanted files
                                    if file.endswith(('.pyc', '.pyo')) or file.startswith('.'):
                                        continue
                                        
                                    full_path = os.path.join(root, file)
                                    # Create archive name relative to the module
                                    rel_path = os.path.relpath(full_path, item_path)
                                    arcname = os.path.join(item, rel_path)
                                    zipf.write(full_path, arcname)
            
            if modules_count == 0:
                return request.make_response(
                    "No custom modules found",
                    status=404,
                    headers=[('Content-Type', 'text/plain')]
                )
            
            buffer.seek(0)
            _logger.info(f"Successfully exported {modules_count} custom modules")
            
            return request.make_response(
                buffer.read(),
                headers=[
                    ('Content-Type', 'application/zip'),
                    ('Content-Disposition', content_disposition(f'custom_modules_{modules_count}.zip'))
                ]
            )
            
        except Exception as e:
            _logger.error(f"Error exporting custom modules: {str(e)}")
            return request.make_response(
                f"Error: {str(e)}",
                status=500,
                headers=[('Content-Type', 'text/plain')]
            )

    @http.route('/export/custom_modules/button', type='http', auth='public')
    def custom_modules_button_page(self, **kwargs):
        """Simple page with download button for custom modules"""
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Export Custom Modules</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                body { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }
                .card {
                    border: none;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    backdrop-filter: blur(10px);
                    background: rgba(255,255,255,0.9);
                }
                .btn-custom {
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    border: none;
                    border-radius: 25px;
                    padding: 15px 40px;
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                    transition: all 0.3s ease;
                    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
                }
                .btn-custom:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 15px 35px rgba(102, 126, 234, 0.5);
                    color: white;
                }
                .icon {
                    font-size: 4rem;
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 20px;
                }
                #status {
                    margin-top: 20px;
                    display: none;
                }
                .spinner {
                    display: none;
                    margin-right: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center p-5">
                                <div class="icon">
                                    <i class="fas fa-download"></i>
                                </div>
                                <h2 class="mb-4">Export Custom Modules</h2>
                                <p class="text-muted mb-4">Download all your custom Odoo modules in a single ZIP file</p>
                                
                                <button id="downloadBtn" class="btn btn-custom btn-lg">
                                    <i class="fas fa-download me-2"></i>
                                    Download Custom Modules
                                </button>
                                
                                <div id="status"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                document.getElementById('downloadBtn').addEventListener('click', function() {
                    const btn = this;
                    const originalContent = btn.innerHTML;
                    const statusDiv = document.getElementById('status');
                    
                    // Show loading state
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Preparing Download...';
                    btn.disabled = true;
                    
                    statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-info-circle me-2"></i>Preparing your custom modules...</div>';
                    statusDiv.style.display = 'block';
                    
                    // Create download link
                    const link = document.createElement('a');
                    link.href = '/export/custom_modules';
                    link.download = 'custom_modules.zip';
                    
                    // Handle download
                    link.addEventListener('click', function() {
                        setTimeout(() => {
                            statusDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Download started successfully!</div>';
                            
                            // Reset button after 3 seconds
                            setTimeout(() => {
                                btn.innerHTML = originalContent;
                                btn.disabled = false;
                                statusDiv.style.display = 'none';
                            }, 3000);
                        }, 1000);
                    });
                    
                    // Trigger download
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                });
            </script>
        </body>
        </html>
        '''
        return html