import os
import logging
from aiohttp import web
from modules.file_manager import file_manager

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

# --- THE PREMIUM DOMAIN HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream | {filename}</title>
    
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />

    <style>
        body { margin: 0; padding: 0; font-family: 'Montserrat', sans-serif; background-color: #000000; overflow-x: hidden; display: flex; justify-content: center; align-items: center; min-height: 100vh; color: #fff; }
        .stars { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; background-image: radial-gradient(2px 2px at 20px 30px, #ffffff, transparent), radial-gradient(2px 2px at 40px 70px, #ffffff, transparent), radial-gradient(3px 3px at 150px 160px, #ffffff, transparent), radial-gradient(2px 2px at 90px 40px, #ffffff, transparent), radial-gradient(2px 2px at 130px 80px, #ffffff, transparent), radial-gradient(3px 3px at 200px 250px, #ffffff, transparent), radial-gradient(2px 2px at 250px 90px, #ffffff, transparent); background-repeat: repeat; background-size: 300px 300px; animation: starMove 15s linear infinite; opacity: 0.8; }
        @keyframes starMove { from { transform: translateY(0); } to { transform: translateY(-300px); } }
        .blue-glow { position: fixed; top: 50%; left: 50%; width: 100vw; height: 100vh; transform: translate(-50%, -50%); background: radial-gradient(circle, rgba(0, 85, 255, 0.12) 0%, transparent 60%); pointer-events: none; z-index: 1; }
        .domain-container { position: relative; width: 90%; max-width: 950px; padding: 30px; border-radius: 20px; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 0 40px rgba(0, 119, 255, 0.2), inset 0 0 20px rgba(0, 0, 0, 1); z-index: 10; text-align: center; }
        .title { font-size: 1.4rem; font-weight: 700; color: #ffffff; text-shadow: 0 0 10px rgba(255, 255, 255, 0.5), 0 0 20px rgba(0, 140, 255, 0.6); margin-bottom: 25px; word-wrap: break-word; letter-spacing: 1px; }
        .player-wrapper { border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.9); border: 1px solid rgba(255, 255, 255, 0.1); --plyr-color-main: #0088ff; --plyr-video-control-color: #ddd; --plyr-video-control-background-hover: rgba(0, 136, 255, 0.5); background: #000; }
        .footer { margin-top: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
        .expire-text { font-size: 0.9rem; color: #ff4444; background: rgba(255, 0, 0, 0.1); padding: 10px 20px; border-radius: 8px; border: 1px solid rgba(255, 0, 0, 0.3); letter-spacing: 0.5px; }
        .download-btn { background: transparent; color: #ffffff; text-decoration: none; padding: 10px 25px; border-radius: 8px; font-weight: 700; font-size: 0.95rem; transition: all 0.3s ease; border: 2px solid #0088ff; box-shadow: 0 0 15px rgba(0, 136, 255, 0.2) inset, 0 0 15px rgba(0, 136, 255, 0.2); display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .download-btn:hover { background: #0088ff; color: #000; box-shadow: 0 0 25px rgba(0, 136, 255, 0.6); }
        @media (max-width: 768px) { .footer { flex-direction: column; gap: 15px; } .title { font-size: 1.1rem; } }
    </style>
</head>
<body>
    <div class="stars"></div>
    <div class="blue-glow"></div>
    <div class="domain-container">
        <h1 class="title">✦ {filename} ✦</h1>
        <div class="player-wrapper">
            <video id="anime-player" playsinline controls>
                <source src="/stream/{token}" type="video/mp4" />
            </video>
        </div>
        <div class="footer">
            <div class="expire-text">⚠️ Link expires in 24 Hours</div>
            <a href="/stream/{token}?download=true" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Download
            </a>
        </div>
    </div>
    <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const player = new Plyr('#anime-player', {
                controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'settings', 'pip', 'fullscreen'],
                settings: ['speed'],
                speed: { selected: 1, options: [0.5, 1, 1.5, 2] }
            });
            const videoKey = 'resume_time_{token}';
            player.on('ready', () => {
                const savedTime = localStorage.getItem(videoKey);
                if (savedTime) player.currentTime = parseFloat(savedTime);
            });
            player.on('timeupdate', () => {
                localStorage.setItem(videoKey, player.currentTime);
            });
        });
    </script>
</body>
</html>
"""

@routes.get('/')
async def index(request):
    return web.Response(text="Streaming Bot is Live! 🚀")

@routes.get('/watch/{token}')
async def watch_video(request):
    token = request.match_info.get('token')
    file_path = file_manager.get_video_path(token)

    if not file_path or not os.path.exists(file_path):
        return web.Response(text="❌ Error: Video not found or link expired.", status=404)

    # File ka asli naam nikalna
    filename = os.path.basename(file_path)

    # 🔥 THE FIX: HTML mein se {filename} aur {token} ko asli data se Replace karna
    final_html = HTML_TEMPLATE.replace("{token}", token).replace("{filename}", filename)

    return web.Response(text=final_html, content_type='text/html')

@routes.get('/stream/{token}')
async def stream_video(request):
    token = request.match_info.get('token')
    file_path = file_manager.get_video_path(token)

    if not file_path or not os.path.exists(file_path):
        return web.Response(text="Video not found", status=404)

    # Web FileResponse natively streaming support karta hai (Buffering ke liye)
    return web.FileResponse(file_path)

async def start_web_server():
    app = web.Application()
    app.add_routes(routes)
    from config import Config
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, Config.HOST, Config.PORT)
    await site.start()
    logger.info(f"🌍 Web Server running at http://{Config.HOST}:{Config.PORT}")
