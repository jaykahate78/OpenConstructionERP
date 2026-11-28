"""Focused construction demo profile for Render's 512 MiB free instance.
The original application and every module remain in the upstream image.
"""
import logging
import asyncio
import contextlib
import ctypes
import gc
from app.core.module_loader import ModuleLoader
from app import main as upstream

SELECTED = {
    "oe_users", "oe_projects", "oe_contacts", "oe_boq", "oe_costs",
    "oe_catalog", "oe_procurement", "oe_site_inventory", "oe_daily_diary",
    "oe_fieldreports", "oe_progress", "oe_finance", "oe_dashboard",
}

original_discover = ModuleLoader.discover

def focused_discover(self, *args, **kwargs):
    manifests = original_discover(self, *args, **kwargs)
    keep = set(SELECTED)
    while True:
        missing = keep - self._manifests.keys()
        if missing:
            raise RuntimeError("Missing demo module dependencies: " + ", ".join(sorted(missing)))
        expanded = keep | {dep for name in keep for dep in self._manifests[name].depends}
        if expanded == keep:
            break
        keep = expanded
    for name, manifest in self._manifests.items():
        manifest.enabled = name in keep
        if name in keep:
            self._disabled.discard(name)
        else:
            self._disabled.add(name)
    logging.getLogger(__name__).info("Free demo: enabling %d construction modules", len(keep))
    return manifests

ModuleLoader.discover = focused_discover
original_seed_accounts = upstream._seed_demo_account

async def seed_accounts_only(*, defer_projects=False):
    # Account creation and existing passwords keep the upstream authentication.
    # Avoid the full showcase seeder, which imports all optional feature modules.
    await original_seed_accounts(defer_projects=True)
    return None

upstream._seed_demo_account = seed_accounts_only


# This entry uses the existing public demo sign-in; it grants no new role.
ADMIN_DEMO_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Apana Construction Demo</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b1220;color:#e5edf8;font:16px system-ui}main{padding:32px;text-align:center}button{padding:12px 20px;border:0;border-radius:10px;background:#347ef2;color:white;cursor:pointer}</style></head>
<body><main><h1>Construction ERP Demo</h1><p id="status" role="status">Opening Admin demo…</p><button id="retry" hidden>Try again</button></main>
<script>
async function openDemo(){
 const status=document.getElementById('status'),retry=document.getElementById('retry');
 retry.hidden=true;status.textContent='Opening Admin demo…';
 try{
  const response=await fetch('/api/v1/users/auth/demo-login/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'demo@openconstructionerp.com'})});
  if(!response.ok)throw new Error('Demo is temporarily unavailable. Please try again.');
  const data=await response.json();
  if(!data.access_token||!data.refresh_token)throw new Error('Demo sign-in could not complete.');
  for(const key of ['oe_access_token','oe_refresh_token','oe_remember','oe_user_full_name'])localStorage.removeItem(key);
  sessionStorage.setItem('oe_access_token',data.access_token);
  sessionStorage.setItem('oe_refresh_token',data.refresh_token);
  sessionStorage.removeItem('oe_manual_login');
  localStorage.setItem('oe_user_email','demo@openconstructionerp.com');
  localStorage.setItem('oe_session_tabs','1');
  location.replace('/projects');
 }catch(error){status.textContent=error.message||'Unable to open demo.';retry.hidden=false;}
}
document.getElementById('retry').addEventListener('click',openDemo);openDemo();
</script></body></html>"""

DEMO_UI_STYLE = "<style id=\"apana-demo-ui\">\naside[data-tour=\"sidebar\"] a[href=\"https://github.com/datadrivenconstruction/OpenConstructionERP\"],\naside[data-tour=\"sidebar\"] a[href=\"https://t.me/datadrivenconstruction\"],\n[data-testid=\"sidebar-learn\"],\n[data-testid=\"header-learn-restore\"],\naside[data-tour=\"sidebar\"] a[href=\"/modules/developer-guide\"],\naside[data-tour=\"sidebar\"] button[aria-haspopup=\"dialog\"][class*=\"border-dashed\"],\nbutton[aria-label=\"Support us\"],\nheader a[href^=\"mailto:info@datadrivenconstruction\"],\nheader a[href^=\"mailto:info@openconstructionerp\"] {display:none!important}\n</style>"

DEMO_SERVICE_WORKER = "// Apana demo navigation: always obtain the current UI from the server.\nself.addEventListener('install',event=>{event.waitUntil(self.skipWaiting());});\nself.addEventListener('activate',event=>{event.waitUntil(self.clients.claim());});\nself.addEventListener('fetch',event=>{\n if(event.request.mode==='navigate'){\n  event.respondWith(fetch(event.request,{cache:'no-store'}));\n }\n});\n"
DEMO_WORKER_REGISTRATION = "if('serviceWorker' in navigator){window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js',{scope:'/',updateViaCache:'none'}).then(registration=>registration.update()).catch(()=>{});});}"

DEMO_CLIENT_CLEANUP = "<style id=\"apana-demo-client-cleanup\">\n[data-testid^=\"pwa-install-prompt\"],\n[data-testid=\"header-help-menu\"],\n[data-testid^=\"settings-tab-converters\"],\n[data-testid^=\"settings-tab-packages\"],\n[data-testid^=\"settings-tab-modules\"],\n[data-testid^=\"settings-tab-advanced\"],\nbutton[aria-label=\"Report a bug or send feedback\"],\nbutton[aria-label^=\"Get release notes by email\"],\nbutton[aria-label=\"Build a module\"],\nbutton[title=\"Build a module\"],\nbutton[aria-label=\"What's new\"],\na[href*=\"github.com\"],\na[href*=\"t.me/datadrivenconstruction\"],\na[href*=\"openconstructionerp.com\"],\na[href*=\"datadrivenconstruction.io\"],\na[href*=\"gnu.org/licenses\"],\n[data-apana-demo-hidden] {display:none!important}\n#apana-demo-legal{display:block;padding:8px 16px;color:#8292a9;font:11px system-ui;text-decoration:none}\n</style><script>\n(()=>{\n const blocked=new Set(['converters','bimcad','bim-cad','bim_cad','cad','packages','modules','advanced']);\n if(location.pathname==='/settings'){\n  const params=new URLSearchParams(location.search);\n  if(blocked.has(params.get('tab')||'')){params.set('tab','general');history.replaceState(null,'',location.pathname+'?'+params.toString());}\n }\n const hide=e=>{if(e&&!e.hasAttribute('data-apana-demo-hidden'))e.setAttribute('data-apana-demo-hidden','');};\n function decorate(){\n  if(document.title.includes('OpenConstructionERP'))document.title=document.title.replaceAll('OpenConstructionERP','Apana Construction Demo');\n  document.querySelectorAll('button').forEach(e=>{\n   const text=(e.textContent||'').trim();\n   const label=e.getAttribute('aria-label')||'';\n   if(['About','Build a module',\"What's new\"].includes(text)||label.startsWith('Background services:'))hide(e);\n  });\n  document.querySelectorAll('h2,h3,h4').forEach(e=>{\n   if(['License & plan','License & Plan','Access and source','Release packages','Converters'].includes((e.textContent||'').trim())){\n    const card=e.closest('[class*=\"rounded-\"][class*=\"border\"]');if(card)hide(card);\n   }\n  });\n  const sidebar=document.querySelector('aside[data-tour=\"sidebar\"]');\n  if(sidebar){\n   sidebar.querySelectorAll('a[href=\"/api/source\"]').forEach(e=>hide(e.parentElement));\n   if(!sidebar.querySelector('#apana-demo-legal')){\n    const link=document.createElement('a');link.id='apana-demo-legal';link.href='/legal';link.textContent='Legal / Source';sidebar.append(link);\n   }\n  }\n }\n let queued=false;\n function schedule(){if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;decorate();});}}\n function boot(){decorate();new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});}\n if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();\n})();\n</script>"
DEMO_LEGAL_HTML = "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Legal / Source — Apana Construction Demo</title><style>body{background:#0b1220;color:#e4edf8;font:16px/1.65 system-ui;margin:0}main{max-width:800px;margin:60px auto;padding:28px}a{color:#79b7ff}h1{font-size:28px}section{padding:20px;border:1px solid #27394f;border-radius:14px;margin:20px 0}</style></head><body><main><a href=\"/projects\">← Return to demo</a><h1>Legal / Source</h1><p>Apana Tech Software operates and customizes this construction demo.</p><section><h2>Open-source foundation</h2><p>This demo is based on OpenConstructionERP 18.9.0 by DataDrivenConstruction.</p><p>Copyright © 2026 Artem Boiko / DataDrivenConstruction. Original copyright and license notices remain with the application and source.</p><p>License: GNU Affero General Public License v3.0 (AGPL-3.0).</p><p><a href=\"https://www.gnu.org/licenses/agpl-3.0.html\">Read AGPL-3.0</a> · <a href=\"/api/v1/licenses/\">Bundled third-party license notices</a></p></section><section><h2>Corresponding source</h2><p><a href=\"https://github.com/jaykahate78/OpenConstructionERP/tree/deploy/render-demo\">Customized demo source and deployment files</a></p><p><a href=\"https://github.com/datadrivenconstruction/OpenConstructionERP\">Original project source</a> · <a href=\"/api/source\">Application source information</a></p><p>Demo modifications include the selected free-plan modules, startup memory cleanup, direct demo entry, navigation cache behavior, company branding and a simplified client interface.</p></section></main></body></html>"

class AdminDemoEntry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").rstrip("/") in {"/legal", "/about"}:
            from starlette.responses import HTMLResponse
            await HTMLResponse(DEMO_LEGAL_HTML, headers={"Cache-Control": "no-store"})(scope, receive, send)
            return
        if scope["type"] == "http" and scope.get("path") in {"/sw.js", "/registerSW.js"}:
            from starlette.responses import Response
            script = DEMO_SERVICE_WORKER if scope["path"] == "/sw.js" else DEMO_WORKER_REGISTRATION
            await Response(script, media_type="application/javascript", headers={
                "Cache-Control": "no-store, max-age=0",
                "Service-Worker-Allowed": "/",
            })(scope, receive, send)
            return
        if scope["type"] == "http" and scope.get("path") in {"/demo/admin", "/demo/admin/"}:
            from starlette.responses import HTMLResponse
            response = HTMLResponse(ADMIN_DEMO_HTML, headers={
                "Cache-Control": "no-store",
                "X-Robots-Tag": "noindex, nofollow",
                "Referrer-Policy": "no-referrer",
            })
            await response(scope, receive, send)
            return
        # Serve the same SPA with demo-only presentation rules, without
        # rebuilding or changing any upstream JavaScript or source notices.
        if (scope["type"] == "http" and scope.get("method") == "GET"
                and not scope.get("path", "").startswith(("/api", "/assets", "/demo/"))
                and b"text/html" in dict(scope.get("headers", [])).get(b"accept", b"")):
            from app.cli_static import get_frontend_dir
            from starlette.responses import HTMLResponse
            directory = get_frontend_dir()
            if directory is not None:
                index = directory / "index.html"
                if index.is_file():
                    html = index.read_text(encoding="utf-8")
                    html = html.replace("</head>", DEMO_UI_STYLE + DEMO_CLIENT_CLEANUP + "</head>", 1)
                    await HTMLResponse(html, headers={"Cache-Control": "no-store"})(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def create_app():
    from app.core.processes import process_registry
    # Periodic enterprise tasks and vector warm-ups are unnecessary for this demo.
    # Manual procurement/site operations continue through their normal API routes.
    process_registry.schedule_boot = lambda: None
    from app.core.app_branding import write_branding
    write_branding({"mode": "text", "company_name": "Apana Construction Demo", "show_logo_edit": False})
    app = upstream.create_app()
    app.add_middleware(AdminDemoEntry)
    original_lifespan = app.router.lifespan_context
    libc = ctypes.CDLL(None)
    trim = getattr(libc, "malloc_trim", None)
    if trim is not None:
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int

    def release_temporary_memory():
        # Schema inspection and route construction leave large temporary graphs.
        # Collect cycles, then return unused glibc arenas to the container.
        gc.collect()
        if trim is not None:
            trim(0)

    async def memory_maintenance():
        while True:
            await asyncio.sleep(30)
            release_temporary_memory()

    @contextlib.asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application) as state:
            release_temporary_memory()
            task = asyncio.create_task(memory_maintenance())
            try:
                yield state
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app.router.lifespan_context = lifespan
    return app
