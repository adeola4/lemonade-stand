"""Wire all modules into the executive loop."""
from __future__ import annotations

from modules.qla_engine import run_qla_deal_sourcing, run_qla_full_cycle
from modules.outreach import generate_outreach, decide_channel
from modules.pipeline import load_pipeline, save_pipeline, add_deal, advance_stage, get_pipeline_summary, DealRecord
from modules.email_sender import send_outreach_email, configure_apps_script
from modules.documents import generate_loi, generate_nda, generate_offer_letter, generate_term_sheet, generate_due_diligence_checklist, generate_purchase_agreement_outline