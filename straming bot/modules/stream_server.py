import os
import aiohttp_jinja2
import jinja2
from aiohttp import web
from config import Config
from modules.file_manager import file_manager
import logging
import mimetypes

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@routes.get('/watch/{token}')
@aiohttp_jinja2.template('player.html')
async def watch_handler(request):
    """
    Serves the HTML player page.
    """
    token = request.match_info['token']
    file_path = file_manager.get_video_path(token)

    if not file_path or not os.path.exists(file_path):
        return web.Response(text="<h1>404 - Video Not Found or Expired</h1>", content_type='text/html', status=404)

    filename = os.path.basename(file_path)
    mime_type = file_manager.get_video_mime(token)
    
    # Construct the stream URL
    stream_url = f"{Config.BASE_URL}/stream/{token}"

    return {
        'filename': filename,
        'stream_url': stream_url,
        'mime_type': mime_type
    }

@routes.get('/stream/{token}')
async def stream_handler(request):
    """
    Handles the actual video streaming with HTTP Range support.
    """
    token = request.match_info['token']
    file_path = file_manager.get_video_path(token)

    if not file_path or not os.path.exists(file_path):
        return web.Response(status=404, text="Video not found")

    # Use aiohttp's built-in FileResponse
    # It automatically handles:
    # 1. 206 Partial Content
    # 2. Range Headers (seeking)
    # 3. Content-Type and Content-Length
    try:
        response = web.FileResponse(file_path)
        
        # Explicitly ensure Accept-Ranges is set (though FileResponse usually does it)
        response.enable_compression = False # Disable compression for video files
        response.headers['Accept-Ranges'] = 'bytes'
        
        # Serve the file
        return response
    except Exception as e:
        logger.error(f"Streaming error for {token}: {e}")
        return web.Response(status=500, text="Internal Server Error during streaming")

async def start_web_server():
    """Initializes and runs the aiohttp web app."""
    app = web.Application()
    
    # Setup Jinja2 for HTML templates
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    
    # Register routes
    app.add_routes(routes)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render binds to 0.0.0.0 and specific PORT
    site = web.TCPSite(runner, Config.HOST, Config.PORT)
    await site.start()
    
    logger.info(f"🌍 Web Server running at {Config.BASE_URL}")