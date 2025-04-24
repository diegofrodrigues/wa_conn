import base64
import mimetypes


def get_media_type(file_name):
        mime = mimetypes.guess_type(file_name)[0]
        if mime:
            mime = mime.split('/')[0]
            if mime == 'image' or mime == 'video' or mime == 'audio':
                return mime
            else:
                return 'document'
        return False
    
def get_mime_type(file_name):
    mime = mimetypes.guess_type(file_name)[0]
    return mime


def file_to_base64(file):
    with open(file, 'rb') as file:
        file_encoded = base64.b64encode(file.read())
        file_decoded = file_encoded.decode()
        return file_decoded
