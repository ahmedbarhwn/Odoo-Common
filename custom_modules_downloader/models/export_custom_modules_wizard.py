from odoo import models, fields, api
import os
import io
import base64
import zipfile
import logging
from odoo import tools

_logger = logging.getLogger(__name__)

class ExportCustomModulesWizard(models.TransientModel):
    _name = 'export.custom.modules.wizard'
    _description = 'Export Custom Modules Wizard'

    file_name = fields.Char(string="Filename")
    file_data = fields.Binary(string="Download File")

    def get_custom_addons_paths(self):
        custom_paths = []
        if hasattr(tools.config, 'options') and 'addons_path' in tools.config.options:
            paths = tools.config.options['addons_path'].split(',')
            for path in paths:
                path = path.strip()
                if path and ('custom' in path.lower() or 'addons' in path.lower()):
                    if os.path.exists(path):
                        custom_paths.append(path)
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

    def is_custom_module(self, module_path):
        manifest_files = ['__manifest__.py', '__openerp__.py']
        return any(os.path.exists(os.path.join(module_path, mf)) for mf in manifest_files)

    def generate_zip(self):
        buffer = io.BytesIO()
        modules_count = 0
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for path in self.get_custom_addons_paths():
                if not os.path.exists(path):
                    continue
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path) and self.is_custom_module(item_path):
                        modules_count += 1
                        for root, dirs, files in os.walk(item_path):
                            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                            for file in files:
                                if file.endswith(('.pyc', '.pyo')) or file.startswith('.'):
                                    continue
                                full_path = os.path.join(root, file)
                                rel_path = os.path.relpath(full_path, item_path)
                                arcname = os.path.join(item, rel_path)
                                zipf.write(full_path, arcname)
        buffer.seek(0)
        return base64.b64encode(buffer.read()), modules_count

    def action_download_zip(self):
        file_data, count = self.generate_zip()
        file_name = f'custom_modules_{count}.zip'
        return self.write({
            'file_name': file_name,
            'file_data': file_data
        })
