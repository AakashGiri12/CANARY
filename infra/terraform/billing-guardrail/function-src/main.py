"""Cloud Function (Gen1, Pub/Sub-triggered): the account-wide kill switch.

Triggered by every threshold a Cloud Billing budget crosses (50%, 90%,
100% — see main.tf). Only actually acts at >=100%: disconnects billing
from the project (the "nuclear option" — the only approach that
guarantees zero further overage, since it stops billing for literally
everything in the project, not just the resources this function knows
to look for) and, belt-and-suspenders, explicitly stops any running
Compute Engine instances immediately rather than waiting on whatever
delay GCP's own billing-disable-triggered cleanup has.

NOT deployed or tested by Claude — written carefully against Google's
documented reference pattern for this exact use case, but there was no
way to verify it against live GCP APIs without the user's credentials.
Test-fire it (see the module's README) before trusting it.
"""

from __future__ import annotations

import base64
import json
import os

PROJECT_ID = os.environ["GCP_PROJECT_ID"]


def stop_billing(event: dict, context) -> None:
    pubsub_data = base64.b64decode(event["data"]).decode("utf-8")
    notification = json.loads(pubsub_data)

    cost_amount = notification.get("costAmount", 0)
    budget_amount = notification.get("budgetAmount", 0)
    print(f"budget notification: cost={cost_amount} budget={budget_amount}")

    if cost_amount < budget_amount:
        print("under budget — no action")
        return

    print(f"cost ({cost_amount}) >= budget ({budget_amount}) — acting now")
    _stop_compute_instances(PROJECT_ID)
    _disable_billing(PROJECT_ID)


def _disable_billing(project_id: str) -> None:
    from google.cloud import billing_v1

    client = billing_v1.CloudBillingClient()
    project_name = f"projects/{project_id}"

    info = client.get_project_billing_info(name=project_name)
    if not info.billing_enabled:
        print("billing already disabled")
        return

    client.update_project_billing_info(
        name=project_name,
        project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
    )
    print(f"billing disabled for {project_id}")


def _stop_compute_instances(project_id: str) -> None:
    from google.cloud import compute_v1

    client = compute_v1.InstancesClient()
    for zone, response in client.aggregated_list(project=project_id):
        if not response.instances:
            continue
        zone_name = zone.split("/")[-1]
        for instance in response.instances:
            if instance.status == "RUNNING":
                print(f"stopping {instance.name} in {zone_name}")
                try:
                    client.stop(project=project_id, zone=zone_name, instance=instance.name)
                except Exception as exc:  # keep going — disabling billing is the real backstop
                    print(f"failed to stop {instance.name}: {exc}")
