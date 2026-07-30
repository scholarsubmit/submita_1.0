"""
app/utils/uploads.py — secure file upload handling for submissions.
"""
import os
import secrets
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

# Byte signatures that should never appear in an uploaded assignment file —
# catches someone trying to smuggle executable/script content in disguise.
_MALWARE_SIGNATURES = (
    b'<?php', b'<%', b'<script', b'javascript:', b'vbscript:',
    b'eval(', b'exec(', b'system(', b'passthru(',
)


# Always blocked regardless of "any format" — these are executable/script
# formats with no legitimate reason to appear in an assignment's question
# paper, so "any format" is interpreted as "any document/content format."
_ALWAYS_BLOCKED_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'sh', 'msi', 'dll', 'scr', 'com', 'ps1', 'vbs', 'jar', 'app',
}

QUESTION_FILE_MAX_BYTES = 5 * 1024 * 1024  # 5MB, per the lecturer-facing limit


def save_question_file(file_storage):
    """
    For a lecturer's uploaded question paper: any format is accepted
    EXCEPT executables/scripts, capped at 5MB (a separate, smaller limit
    than student submissions, since a question paper is normally a
    single document, not a codebase). Returns (stored_filename,
    original_filename, error_message) — same contract as
    save_submission_file.
    """
    if not file_storage or not file_storage.filename:
        return None, None, None

    original_name = file_storage.filename
    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension in _ALWAYS_BLOCKED_EXTENSIONS:
        return None, None, f'File type .{extension} is not allowed for security reasons.'

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > QUESTION_FILE_MAX_BYTES:
        return None, None, 'File exceeds the 5MB limit.'
    if size == 0:
        return None, None, 'File is empty.'

    header = file_storage.read(2048)
    file_storage.seek(0)
    for signature in _MALWARE_SIGNATURES:
        if signature in header:
            return None, None, 'File contains disallowed content.'

    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_suffix = secrets.token_hex(6)
    stored_name = f'{timestamp}_{random_suffix}_{secure_filename(original_name)}'

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, stored_name))

    return stored_name, original_name, None


def save_submission_file(file_storage):
    """
    Validates and saves an uploaded file. Returns (stored_filename,
    original_filename, error_message). On success error_message is None
    and stored_filename/original_filename are set; on failure the
    opposite.
    """
    if not file_storage or not file_storage.filename:
        return None, None, None  # no file provided — not an error, it's optional

    allowed = current_app.config['ALLOWED_EXTENSIONS']
    original_name = file_storage.filename
    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension not in allowed:
        return None, None, f'File type .{extension} is not allowed.'

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    max_bytes = current_app.config['MAX_CONTENT_LENGTH']
    if size > max_bytes:
        return None, None, f'File exceeds the {max_bytes // (1024 * 1024)}MB limit.'
    if size == 0:
        return None, None, 'File is empty.'

    header = file_storage.read(2048)
    file_storage.seek(0)
    for signature in _MALWARE_SIGNATURES:
        if signature in header:
            return None, None, 'File contains disallowed content.'

    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_suffix = secrets.token_hex(6)
    stored_name = f'{timestamp}_{random_suffix}_{secure_filename(original_name)}'

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, stored_name))

    return stored_name, original_name, None
