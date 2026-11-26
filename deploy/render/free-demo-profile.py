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
  for(const key of ['oe_access_token','oe_refresh_token','oe_remember_me','oe_user_full_name'])localStorage.removeItem(key);
  sessionStorage.setItem('oe_access_token',data.access_token);
  sessionStorage.setItem('oe_refresh_token',data.refresh_token);
  sessionStorage.removeItem('oe_manual_login');
  localStorage.setItem('oe_user_email','demo@openconstructionerp.com');
  localStorage.setItem('oe_session_hint','1');
  location.replace('/projects');
 }catch(error){status.textContent=error.message||'Unable to open demo.';retry.hidden=false;}
}
document.getElementById('retry').addEventListener('click',openDemo);openDemo();
</script></body></html>"""

DEMO_UI_STYLE = "<style id=\"apana-demo-ui\">\naside[data-tour=\"sidebar\"] a[href=\"https://github.com/datadrivenconstruction/OpenConstructionERP\"],\naside[data-tour=\"sidebar\"] a[href=\"https://t.me/datadrivenconstruction\"],\n[data-testid=\"sidebar-learn\"],\n[data-testid=\"header-learn-restore\"],\naside[data-tour=\"sidebar\"] a[href=\"/modules/developer-guide\"],\naside[data-tour=\"sidebar\"] button[aria-haspopup=\"dialog\"][class*=\"border-dashed\"],\nbutton[aria-label=\"Support us\"],\nheader a[href^=\"mailto:info@datadrivenconstruction\"],\nheader a[href^=\"mailto:info@openconstructionerp\"] {display:none!important}\n</style>"

class AdminDemoEntry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
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
                    html = html.replace("</head>", DEMO_UI_STYLE + "</head>", 1)
                    await HTMLResponse(html, headers={"Cache-Control": "no-store"})(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def create_app():
    from app.core.processes import process_registry
    # Periodic enterprise tasks and vector warm-ups are unnecessary for this demo.
    # Manual procurement/site operations continue through their normal API routes.
    process_registry.schedule_boot = lambda: None
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
