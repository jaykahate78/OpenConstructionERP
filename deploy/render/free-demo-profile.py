"""Focused construction demo profile for Render's 512 MiB free instance.
The original application and every module remain in the upstream image.
"""
import logging
from app.core.module_loader import ModuleLoader
from app import main as upstream

SELECTED = {
    "oe_users", "oe_projects", "oe_contacts", "oe_boq", "oe_costs",
    "oe_catalog", "oe_procurement", "oe_supplier_catalogs", "oe_rfq_bidding",
    "oe_site_inventory", "oe_daily_diary", "oe_fieldreports", "oe_progress",
    "oe_schedule", "oe_tasks", "oe_finance", "oe_resources", "oe_equipment",
    "oe_dashboard", "oe_notifications", "oe_inspections", "oe_safety",
    "oe_documents", "oe_subcontractors", "oe_tendering", "oe_i18n_foundation",
    "oe_teams", "oe_approval_routes",
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

def create_app():
    from app.core.processes import process_registry
    # Periodic enterprise tasks and vector warm-ups are unnecessary for this demo.
    # Manual procurement/site operations continue through their normal API routes.
    process_registry.schedule_boot = lambda: None
    return upstream.create_app()
